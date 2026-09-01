"""Bounded LangGraph request pipeline with detached validation on every edge."""

from __future__ import annotations

import sqlite3
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
from src.schema.listing import Listing, ListingRecord
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
        listings.append(
            hydrate_listing(
                record,
                travel_min_home=int(travel[0]),
                travel_min_school=int(travel[1]),
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
):
    planner = Planner()
    discovery = Discovery()
    guardian = Guardian()
    broker = Broker()
    validator = Validator()

    def planner_node(state: HobbiState) -> dict[str, Any]:
        snapshot = personal_data.planner_snapshot(state["teen_id"])
        records = _records(ckb)
        result = planner.create_plan(
            planning_key=state["teen_id"],
            declared_age=state["declared_age"],
            request=state["request"],
            ledger=snapshot["ledger"],
            preferences=snapshot["preferences"],
            listings=_hydrated(records, snapshot["constraints"], state["request"].requested_at),
            parental_rules=snapshot["parental_rules"],
            constraints=snapshot["constraints"],
            unavailable_listing_ids=(
                set(state.get("unavailable_listing_ids", []))
                | snapshot["booked_listing_ids"]
            ),
        )
        if result.plan is None:
            return {"candidate_plan": None, "outcome": "no_viable_plan"}
        g2 = validator.g2(result.plan, snapshot["ledger"], records)
        if not g2.passed:
            return {
                "candidate_plan": result.plan,
                "gate_log": [g2],
                "outcome": "no_viable_plan",
            }
        return {
            "candidate_plan": result.plan,
            "approved_plan": result.plan,
            "ledger": snapshot["ledger"],
            "gate_log": [g2],
            "outcome": None,
        }

    def after_planner(state: HobbiState) -> Literal["discovery", "guardian", "end"]:
        if state.get("outcome") is not None or state.get("candidate_plan") is None:
            return "end"
        plan = state["candidate_plan"]
        if (
            plan.thin
            and discovery_replay_path is not None
            and state["discovery_rounds"] < MAX_DISCOVERY_ROUNDS
        ):
            return "discovery"
        return "guardian"

    def discovery_node(state: HobbiState) -> dict[str, Any]:
        plan = state["candidate_plan"]
        assert plan is not None and discovery_replay_path is not None
        g1_out = validator.g1_plan(plan)
        validator.require_pass(g1_out)
        result = discovery.cached_replay(plan, discovery_replay_path, ckb)
        g1_in = validator.g1_records(result.records)
        validator.require_pass(g1_in)
        return {
            "discovery_rounds": state["discovery_rounds"] + 1,
            "gate_log": [g1_out, g1_in],
        }

    def guardian_node(state: HobbiState) -> dict[str, Any]:
        plan = state["approved_plan"]
        assert plan is not None
        snapshot = personal_data.guardian_snapshot(state["teen_id"])
        verdict = guardian.review(
            plan=plan,
            listings=_records(ckb),
            provider_approval_ids=snapshot["provider_approval_ids"],
            attendance_approval_id=snapshot["attendance_approval_id"],
            spend_approval_id=snapshot["spend_approval_id"],
            parental_rules=snapshot["parental_rules"],
        )
        if verdict.approved:
            return {"guardian_verdict": verdict}
        next_rejections = state["guardian_rejects"] + 1
        if next_rejections >= MAX_GUARDIAN_REJECTIONS:
            return {
                "guardian_verdict": verdict,
                "guardian_rejects": next_rejections,
                "outcome": "escalated_to_adult",
            }
        if state["replan_count"] >= MAX_REPLANS:
            return {
                "guardian_verdict": verdict,
                "guardian_rejects": next_rejections,
                "outcome": "cap_breached",
            }
        return {
            "guardian_verdict": verdict,
            "guardian_rejects": next_rejections,
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
        assert plan is not None and verdict is not None
        records = _records(ckb)
        g3 = validator.g3(plan, verdict, records)
        validator.require_pass(g3)
        result = broker.book(
            teen_id=state["teen_id"],
            plan=plan,
            verdict=verdict,
            listings=records,
            store=personal_data,
            unavailable_listing_ids=set(state.get("unavailable_listing_ids", [])),
        )
        if result.failure_reason:
            if state["replan_count"] >= MAX_REPLANS:
                return {"gate_log": [g3], "outcome": "cap_breached"}
            return {
                "gate_log": [g3],
                "unavailable_listing_ids": [
                    *state.get("unavailable_listing_ids", []),
                    result.unavailable_listing_id,
                ],
                "replan_count": state["replan_count"] + 1,
                "approved_plan": None,
                "guardian_verdict": None,
            }
        g4_results = [
            validator.g4(record, ledger_applied=not result.replayed, replayed=result.replayed)
            for record in result.records
        ]
        for gate in g4_results:
            validator.require_pass(gate)
        return {
            "booking_records": result.records,
            "gate_log": [g3, *g4_results],
            "outcome": "booked",
        }

    def after_broker(state: HobbiState) -> Literal["planner", "end"]:
        return "end" if state.get("outcome") is not None else "planner"

    graph = StateGraph(HobbiState)
    graph.add_node("planner", planner_node)
    graph.add_node("discovery", discovery_node)
    graph.add_node("guardian", guardian_node)
    graph.add_node("broker", broker_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner", after_planner, {"discovery": "discovery", "guardian": "guardian", "end": END}
    )
    graph.add_edge("discovery", "planner")
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
