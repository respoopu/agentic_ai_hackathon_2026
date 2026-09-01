"""Bounded LangGraph request pipeline with detached validation on every edge."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from src.agents.broker import Broker
from src.agents.discovery import Discovery
from src.agents.guardian import Guardian
from src.agents.planner import Planner
from src.ckb.seed_loader import hydrate_listing
from src.ckb.store import KnowledgeBase
from src.constants import MAX_DISCOVERY_ROUNDS, MAX_GUARDIAN_REJECTIONS, MAX_REPLANS
from src.schema.listing import Listing, ListingRecord, PeerCohort
from src.schema.plan import PlanItem
from src.schema.state import HobbiState
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator


def _records(ckb: KnowledgeBase) -> dict[str, ListingRecord]:
    return {record.listing_id: record for record in ckb.all()}


def _hydrated(
    records: dict[str, ListingRecord], constraints: dict[str, Any], as_of: Any
) -> list[Listing]:
    configured = constraints.get("travel_times", {})
    listings: list[Listing] = []
    for record in records.values():
        travel = configured.get(record.listing_id, [20, 20]) if isinstance(configured, dict) else [20, 20]
        cohort_values = constraints.get("peer_cohorts", {})
        cohort = None
        if isinstance(cohort_values, dict) and record.listing_id in cohort_values:
            cohort = PeerCohort.model_validate(cohort_values[record.listing_id])
        listings.append(
            hydrate_listing(
                record,
                travel_min_home=int(travel[0]),
                travel_min_school=int(travel[1]),
                peer_cohort=cohort,
                as_of=as_of,
            )
        )
    return listings


def build_graph(
    *,
    personal_data: PersonalDataStore,
    ckb: KnowledgeBase,
    discovery_replay_path: str | Path | None = None,
    checkpointer: Any | None = None,
    sandbox_availability: Callable[[PlanItem], bool] | None = None,
):
    planner = Planner()
    discovery = Discovery()
    guardian = Guardian()
    broker = Broker()
    validator = Validator()

    def planner_node(state: HobbiState) -> dict[str, Any]:
        snapshot = personal_data.planner_snapshot(state["teen_id"])
        records = _records(ckb)
        constraints = dict(snapshot["constraints"])
        rejection_history = state.get("rejection_history", [])
        if "parental_rule:no_paid_activities" in rejection_history:
            constraints["max_item_cost_sgd"] = 0
        rejected_listing_ids = {
            reason.split(":", 1)[1]
            for reason in rejection_history
            if reason.startswith(("provider_vetting_required:", "listing_dead:"))
        }
        result = planner.create_plan(
            planning_key=state["teen_id"],
            declared_age=state["declared_age"],
            request=state["request"],
            ledger=snapshot["ledger"],
            preferences=snapshot["preferences"],
            listings=_hydrated(records, constraints, state["request"].requested_at),
            parental_rules=snapshot["parental_rules"],
            constraints=constraints,
            unavailable_listing_ids=(
                set(state.get("unavailable_listing_ids", []))
                | snapshot["booked_listing_ids"]
                | rejected_listing_ids
            ),
        )
        if result.plan is None:
            return {
                "candidate_plan": None,
                "binding_constraint": result.binding_constraint,
                "outcome": "no_viable_plan",
            }
        g1 = validator.g1_plan(result.plan)
        validator.require_pass(g1)
        personal_data.save_plan(state["teen_id"], result.plan, live=False)
        return {
            "candidate_plan": result.plan,
            "approved_plan": None,
            "resume_approved_plan": False,
            "ledger": snapshot["ledger"],
            "binding_constraint": result.binding_constraint,
            "gate_log": [g1],
            "outcome": None,
        }

    def after_planner(state: HobbiState) -> Literal["discovery", "g2", "end"]:
        if state.get("outcome") is not None or state.get("candidate_plan") is None:
            return "end"
        plan = state["candidate_plan"]
        if (
            plan.thin
            and discovery_replay_path is not None
            and state["discovery_rounds"] < MAX_DISCOVERY_ROUNDS
        ):
            return "discovery"
        return "g2"

    def discovery_node(state: HobbiState) -> dict[str, Any]:
        plan = state["candidate_plan"]
        if plan is None or discovery_replay_path is None:
            raise ValueError("Discovery requires a candidate plan and replay source")
        result = discovery.cached_replay(plan, discovery_replay_path, ckb)
        g1_in = validator.g1_records(result.records)
        validator.require_pass(g1_in)
        return {
            "discovery_rounds": state["discovery_rounds"] + 1,
            "gate_log": [g1_in],
        }

    def g2_node(state: HobbiState) -> dict[str, Any]:
        plan = state["candidate_plan"]
        if plan is None:
            raise ValueError("G2 requires a candidate plan")
        snapshot = personal_data.planner_snapshot(state["teen_id"])
        g2 = validator.g2(plan, snapshot["ledger"], _records(ckb))
        if not g2.passed:
            return {
                "approved_plan": None,
                "gate_log": [g2],
                "binding_constraint": ",".join(g2.reason_codes),
                "outcome": "no_viable_plan",
            }
        return {"approved_plan": plan, "gate_log": [g2]}

    def guardian_node(state: HobbiState) -> dict[str, Any]:
        plan = state["approved_plan"]
        if plan is None:
            raise ValueError("Guardian requires a G2-approved plan")
        snapshot = personal_data.guardian_snapshot(state["teen_id"], plan)
        verdict = guardian.review(
            plan=plan,
            listings=_records(ckb),
            provider_approval_ids=snapshot["provider_approval_ids"],
            attendance_approval_id=snapshot["attendance_approval_id"],
            spend_approval_id=snapshot["spend_approval_id"],
            parental_rules=snapshot["parental_rules"],
        )
        g3 = validator.g3(plan, verdict, _records(ckb))
        if verdict.approved:
            validator.require_pass(g3)
            return {"guardian_verdict": verdict, "gate_log": [g3]}
        next_rejections = state["guardian_rejects"] + 1
        replannable = any(
            reason.startswith(("provider_vetting_required:", "listing_dead:"))
            or reason == "parental_rule:no_paid_activities"
            for reason in verdict.reason_codes
        )
        common = {
            "guardian_verdict": verdict,
            "guardian_rejects": next_rejections,
            "rejection_history": verdict.reason_codes,
            "gate_log": [g3],
        }
        if next_rejections >= MAX_GUARDIAN_REJECTIONS or not replannable:
            return {
                **common,
                "outcome": "escalated_to_adult",
            }
        if state["replan_count"] >= MAX_REPLANS:
            return {
                **common,
                "outcome": "cap_breached",
            }
        return {
            **common,
            "replan_count": state["replan_count"] + 1,
            "candidate_plan": None,
            "approved_plan": None,
        }

    def after_guardian(state: HobbiState) -> Literal["planner", "broker", "end"]:
        if state.get("outcome") is not None:
            return "end"
        verdict = state.get("guardian_verdict")
        return "broker" if verdict is not None and verdict.approved else "planner"

    def broker_node(state: HobbiState) -> dict[str, Any]:
        plan = state["approved_plan"]
        verdict = state["guardian_verdict"]
        if plan is None or verdict is None:
            raise ValueError("Broker requires an approved plan and Guardian verdict")
        records = _records(ckb)
        result = broker.book(
            teen_id=state["teen_id"],
            plan=plan,
            verdict=verdict,
            listings=records,
            store=personal_data,
            unavailable_listing_ids=set(state.get("unavailable_listing_ids", [])),
            sandbox_availability=sandbox_availability,
        )
        if result.failure_reason:
            if state["replan_count"] >= MAX_REPLANS:
                return {"outcome": "cap_breached"}
            return {
                "unavailable_listing_ids": [
                    *state.get("unavailable_listing_ids", []),
                    result.unavailable_listing_id,
                ],
                "replan_count": state["replan_count"] + 1,
                "approved_plan": None,
                "guardian_verdict": None,
            }
        if result.commit_evidence is None:
            raise ValueError("Broker success requires durable commit evidence")
        g4_results = [
            validator.g4(record, evidence=result.commit_evidence)
            for record in result.records
        ]
        for gate in g4_results:
            validator.require_pass(gate)
        return {
            "booking_records": result.records,
            "gate_log": g4_results,
            "outcome": "booked",
        }

    def after_broker(state: HobbiState) -> Literal["planner", "end"]:
        return "end" if state.get("outcome") is not None else "planner"

    graph = StateGraph(HobbiState)
    graph.add_node("planner", planner_node)
    graph.add_node("discovery", discovery_node)
    graph.add_node("g2", g2_node)
    graph.add_node("guardian", guardian_node)
    graph.add_node("broker", broker_node)
    graph.add_conditional_edges(
        START,
        lambda state: "g2" if state.get("resume_approved_plan") else "planner",
        {"planner": "planner", "g2": "g2"},
    )
    graph.add_conditional_edges(
        "planner", after_planner, {"discovery": "discovery", "g2": "g2", "end": END}
    )
    graph.add_edge("discovery", "planner")
    graph.add_edge("g2", "guardian")
    graph.add_conditional_edges(
        "guardian", after_guardian, {"planner": "planner", "broker": "broker", "end": END}
    )
    graph.add_conditional_edges("broker", after_broker, {"planner": "planner", "end": END})
    return graph.compile(checkpointer=checkpointer)


class HobbiRuntime:
    """Owns a compiled graph and, when used, its persistent checkpoint connection."""

    def __init__(
        self,
        *,
        personal_data: PersonalDataStore,
        ckb: KnowledgeBase,
        checkpoint_path: str | Path | None = None,
        discovery_replay_path: str | Path | None = None,
        in_memory: bool = False,
        sandbox_availability: Callable[[PlanItem], bool] | None = None,
    ) -> None:
        self._checkpoint_connection: sqlite3.Connection | None = None
        serde = JsonPlusSerializer(
            allowed_msgpack_modules={
                ("src.schema.plan", "IntakeResult"),
                ("src.schema.plan", "SessionRequest"),
                ("src.schema.plan", "BudgetLedger"),
                ("src.schema.plan", "PlanItem"),
                ("src.schema.plan", "Plan"),
                ("src.schema.plan", "GuardianVerdict"),
                ("src.schema.events", "BookingRecord"),
                ("src.schema.events", "CommitEvidence"),
                ("src.schema.gates", "GateResult"),
                ("src.schema.gates", "TokenUsage"),
            }
        )
        if in_memory:
            checkpointer: Any = InMemorySaver(serde=serde)
        else:
            if checkpoint_path is None:
                raise ValueError("persistent runtime requires checkpoint_path")
            checkpoint = Path(checkpoint_path)
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            self._checkpoint_connection = sqlite3.connect(
                checkpoint, check_same_thread=False
            )
            checkpointer = SqliteSaver(self._checkpoint_connection, serde=serde)
        self.graph = build_graph(
            personal_data=personal_data,
            ckb=ckb,
            discovery_replay_path=discovery_replay_path,
            checkpointer=checkpointer,
            sandbox_availability=sandbox_availability,
        )

    def invoke(self, state: HobbiState) -> HobbiState:
        return self.graph.invoke(
            state,
            config={"configurable": {"thread_id": state["thread_id"]}},
        )

    def resume(self, thread_id: str) -> HobbiState:
        result = self.graph.invoke(
            None,
            config={"configurable": {"thread_id": thread_id}},
        )
        if result is None:
            raise KeyError(f"no checkpoint for thread {thread_id}")
        return result

    def close(self) -> None:
        if self._checkpoint_connection is not None:
            self._checkpoint_connection.close()
            self._checkpoint_connection = None
