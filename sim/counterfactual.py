"""Executable static-vs-Hobbi evaluation over one shared synthetic environment."""

from __future__ import annotations

import json
import statistics
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sim.catalogue import AS_OF, listings, records, travel_times
from sim.harness import evaluation_consents, initial_state, load_profiles
from src.agents.observer import Observer
from src.agents.planner import Planner
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, preference_seeds, setup
from src.schema.events import AttendanceEvent, DebriefSubmission
from src.schema.plan import BudgetLedger, SessionRequest
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator

ROOT = Path(__file__).resolve().parents[1]
RESULT_FIELDS = {"attended", "hobbi_action", "static_vibe", "selected_listing_id"}


def _authored_result_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in RESULT_FIELDS:
                found.append(child_path)
            found.extend(_authored_result_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_authored_result_paths(child, f"{path}[{index}]"))
    return found


def load_longitudinal_scenario() -> dict[str, Any]:
    payload = json.loads(
        (ROOT / "data" / "synthetic_teen.json").read_text(encoding="utf-8")
    )
    leaked = _authored_result_paths(payload)
    if leaked:
        raise ValueError(
            "synthetic environment cannot contain authored policy results: "
            + ", ".join(leaked)
        )
    return payload


def _constraints(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "max_items": 1,
        "max_travel_min": profile["max_travel_min"],
        "travel_times": travel_times(),
    }


def _ledger(profile: dict[str, Any]) -> BudgetLedger:
    return BudgetLedger(
        money_total_sgd=Decimal(str(profile["money_total_sgd"])),
        hours_per_week=float(profile["hours_per_week"]),
        tries_total=int(profile["tries_total"]),
    )


def _attended(cycle: dict[str, Any], selected_vibes: list[str]) -> bool:
    preferred = cycle.get("preferred_vibe")
    return bool(cycle.get("available", True) and preferred in selected_vibes)


def _debrief(
    *, cycle: dict[str, Any], booking_id: str, attended: bool, occurred_at: Any
) -> DebriefSubmission | None:
    if attended:
        return None
    text = cycle.get("debrief_text")
    if not text:
        return None
    return DebriefSubmission(
        booking_id=booking_id,
        text=text,
        channel="in_app",
        submitted_at=occurred_at,
    )


def _plan_with_current_preferences(
    *,
    teen_id: str,
    profile: dict[str, Any],
    request: SessionRequest,
    ledger: BudgetLedger,
    preferences: Any,
    unavailable_listing_ids: set[str] | None = None,
) -> tuple[Any, Any]:
    result = Planner().create_plan(
        planning_key=teen_id,
        declared_age=int(profile["age"]),
        request=request,
        ledger=ledger,
        preferences=preferences,
        listings=listings(),
        constraints=_constraints(profile),
        unavailable_listing_ids=unavailable_listing_ids,
    )
    if result.plan is None:
        raise RuntimeError(f"evaluation policy produced no plan: {result.binding_constraint}")
    gate = Validator().g1_plan(result.plan)
    Validator.require_pass(gate)
    return result.plan, gate


def run_hobbi_policy(
    *,
    profile: dict[str, Any],
    cycles: list[dict[str, Any]],
    teen_id: str,
    stop_at_first_attendance: bool = False,
) -> dict[str, Any]:
    """Execute Planner/G1 directly, G2-G4 in-graph, Broker, and Observer."""

    record_map = {record.listing_id: record for record in records()}
    cycle_results: list[dict[str, Any]] = []
    pending_replan: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory() as temporary:
        personal = PersonalDataStore(Path(temporary, "personal.sqlite"))
        ckb = KnowledgeBase(Path(temporary, "ckb.sqlite"))
        runtime: HobbiRuntime | None = None
        try:
            ckb.seed(record_map.values())
            initial_ledger = _ledger(profile)
            initial_request = SessionRequest(
                goal="find one hobby experiment", requested_at=AS_OF
            )
            setup(
                SetupInput(
                    teen_id=teen_id,
                    thread_id=f"{teen_id}-setup",
                    declared_age=int(profile["age"]),
                    request=initial_request,
                    ledger=initial_ledger,
                    consents=evaluation_consents(teen_id),
                    constraints=_constraints(profile),
                    cold_start_vibes=profile.get("cold_start_vibes", []),
                ),
                personal,
            )
            runtime = HobbiRuntime(personal_data=personal, ckb=ckb, in_memory=True)
            for index, cycle in enumerate(cycles):
                requested_at = AS_OF + timedelta(days=int(cycle["day"]))
                request = SessionRequest(
                    goal="find one hobby experiment", requested_at=requested_at
                )
                before = personal.planner_snapshot(teen_id)
                replan_instruction = pending_replan
                pending_replan = None
                plan, g1 = _plan_with_current_preferences(
                    teen_id=teen_id,
                    profile=profile,
                    request=request,
                    ledger=before["ledger"],
                    preferences=before["preferences"],
                    unavailable_listing_ids=(
                        {replan_instruction["listing_id"]}
                        if replan_instruction is not None
                        else None
                    ),
                )
                personal.save_plan(teen_id, plan, live=False)
                personal.issue_plan_approvals(
                    teen_id=teen_id,
                    plan_id=plan.plan_id,
                    provider_approval_ids={
                        item.listing_id: f"{teen_id}-provider-{index}-{item.listing_id}"
                        for item in plan.items
                        if record_map[item.listing_id].verification != "verified"
                    },
                    attendance_approval_id=f"{teen_id}-attendance-{index}",
                    spend_approval_id=(
                        f"{teen_id}-spend-{index}" if plan.total_cost_sgd else None
                    ),
                    spend_ceiling_sgd=(plan.total_cost_sgd if plan.total_cost_sgd else None),
                )
                state = initial_state(
                    teen_id=teen_id,
                    age=int(profile["age"]),
                    request=request,
                    ledger=before["ledger"],
                    thread_id=f"{teen_id}-cycle-{index}",
                )
                state["candidate_plan"] = plan
                state["resume_approved_plan"] = True
                final = runtime.invoke(state)
                if final["outcome"] != "booked" or len(final["booking_records"]) != 1:
                    raise RuntimeError(
                        f"evaluation booking failed at cycle {index}: {final['outcome']}"
                    )
                booking = final["booking_records"][0]
                listing = record_map[booking.listing_id]
                plan_item = plan.items[0]
                if plan_item.listing_id != booking.listing_id:
                    raise RuntimeError("evaluation booking does not match planned item")
                occurred_at = plan_item.session_at
                attended = _attended(cycle, listing.vibes)
                event = AttendanceEvent(
                    booking_id=booking.booking_id,
                    attended=attended,
                    occurred_at=occurred_at,
                )
                observer = Observer().observe(
                    teen_id=teen_id,
                    event=event,
                    preferences=personal.planner_snapshot(teen_id)["preferences"],
                    listing=listing,
                    debrief=_debrief(
                        cycle=cycle,
                        booking_id=booking.booking_id,
                        attended=attended,
                        occurred_at=occurred_at,
                    ),
                    store=personal,
                )
                if observer.action == "replan":
                    pending_replan = {
                        "cycle": index + 1,
                        "listing_id": booking.listing_id,
                    }
                cycle_results.append(
                    {
                        "cycle": index + 1,
                        "request_day": int(cycle["day"]),
                        "session_day": (occurred_at - AS_OF).days,
                        "context": cycle["context"],
                        "preferred_vibe": cycle.get("preferred_vibe"),
                        "available": bool(cycle.get("available", True)),
                        "plan_id": plan.plan_id,
                        "listing_id": booking.listing_id,
                        "listing_vibes": listing.vibes,
                        "attended": attended,
                        "observer_action": observer.action,
                        "observer_reasons": observer.reason_codes,
                        "responding_to_replan_from_cycle": (
                            replan_instruction["cycle"]
                            if replan_instruction is not None
                            else None
                        ),
                        "ledger_version": personal.get_ledger(teen_id).version,
                        "planner_execution": "direct_production_component",
                        "g1_execution": "direct_production_validator",
                        "g1_passed": g1.passed,
                        "in_graph_gate_sequence": [
                            gate.gate for gate in final["gate_log"]
                        ],
                        "approval_mode": "synthetic_auto_issued_per_plan",
                    }
                )
                if stop_at_first_attendance and attended:
                    break
        finally:
            if runtime is not None:
                runtime.close()
            ckb.close()
            personal.close()
    return {"arm": "hobbi", "cycles": cycle_results}


def run_static_policy(
    *,
    profile: dict[str, Any],
    cycles: list[dict[str, Any]],
    teen_id: str,
    stop_at_first_attendance: bool = False,
) -> dict[str, Any]:
    """Recompute one immutable declared-preference recommendation every cycle."""

    fixed_preferences = preference_seeds(profile.get("cold_start_vibes", []), AS_OF)
    fixed_ledger = _ledger(profile)
    record_map = {record.listing_id: record for record in records()}
    cycle_results: list[dict[str, Any]] = []
    for index, cycle in enumerate(cycles):
        requested_at = AS_OF + timedelta(days=int(cycle["day"]))
        request = SessionRequest(
            goal="find one hobby experiment", requested_at=requested_at
        )
        plan, _ = _plan_with_current_preferences(
            teen_id=teen_id,
            profile=profile,
            request=request,
            ledger=fixed_ledger,
            preferences=fixed_preferences,
        )
        item = plan.items[0]
        listing = record_map[item.listing_id]
        attended = _attended(cycle, listing.vibes)
        cycle_results.append(
            {
                "cycle": index + 1,
                "request_day": int(cycle["day"]),
                "session_day": (item.session_at - AS_OF).days,
                "context": cycle["context"],
                "preferred_vibe": cycle.get("preferred_vibe"),
                "available": bool(cycle.get("available", True)),
                "plan_id": plan.plan_id,
                "listing_id": item.listing_id,
                "listing_vibes": listing.vibes,
                "attended": attended,
                "observer_action": None,
            }
        )
        if stop_at_first_attendance and attended:
            break
    return {"arm": "static", "cycles": cycle_results}


def _first_attendance_summary(result: dict[str, Any]) -> dict[str, Any]:
    attended = next((cycle for cycle in result["cycles"] if cycle["attended"]), None)
    return {
        "completed": attended is not None and attended["session_day"] <= 30,
        "days": None if attended is None else attended["session_day"],
        "planning_cycles": len(result["cycles"]),
        "teen_actions": 1 + len(result["cycles"]),
    }


def _median(values: list[int]) -> float | None:
    return None if not values else float(statistics.median(values))


def run_first_attendance() -> dict[str, Any]:
    weekly_cycles = [
        {
            "day": day,
            "context": f"week {index + 1}",
            "available": True,
            "debrief_text": "This activity was not my thing",
        }
        for index, day in enumerate((0, 7, 14, 21, 28))
    ]
    profiles = [
        profile for profile in load_profiles() if profile["money_total_sgd"] == 0
    ]
    comparisons: list[dict[str, Any]] = []
    for profile in profiles:
        cycles = [
            {**cycle, "preferred_vibe": profile["preferred_vibe"]}
            for cycle in weekly_cycles
        ]
        horizon_profile = {**profile, "tries_total": len(cycles)}
        static = run_static_policy(
            profile=horizon_profile,
            cycles=cycles,
            teen_id=f"first-static-{profile['id']}",
            stop_at_first_attendance=True,
        )
        hobbi = run_hobbi_policy(
            profile=horizon_profile,
            cycles=cycles,
            teen_id=f"first-hobbi-{profile['id']}",
            stop_at_first_attendance=True,
        )
        comparisons.append(
            {
                "profile_id": profile["id"],
                "preferred_vibe": profile["preferred_vibe"],
                "static": _first_attendance_summary(static),
                "hobbi": _first_attendance_summary(hobbi),
                "static_listing_sequence": [
                    cycle["listing_id"] for cycle in static["cycles"]
                ],
                "hobbi_listing_sequence": [
                    cycle["listing_id"] for cycle in hobbi["cycles"]
                ],
            }
        )

    def arm_summary(arm: str) -> dict[str, Any]:
        completed = [row[arm] for row in comparisons if row[arm]["completed"]]
        return {
            "completed": len(completed),
            "denominator": len(comparisons),
            "median_days_among_completers": _median([row["days"] for row in completed]),
            "median_cycles_among_completers": _median(
                [row["planning_cycles"] for row in completed]
            ),
            "median_teen_actions_among_completers": _median(
                [row["teen_actions"] for row in completed]
            ),
        }

    static_summary = arm_summary("static")
    hobbi_summary = arm_summary("hobbi")
    denominator = len(comparisons)
    return {
        "measured": True,
        "label": "deterministic synthetic S$0 counterfactual; not participant evidence",
        "censor_days": 30,
        "population": (
            "eligible evaluation profiles with money_total_sgd=0, normalized to "
            "five weekly exploration opportunities"
        ),
        "tries_budget": len(weekly_cycles),
        "action_definition": (
            "one initial request plus one attend-or-no-show session action per cycle"
        ),
        "static": static_summary,
        "hobbi": hobbi_summary,
        "completion_rate_delta_percentage_points": (
            None
            if denominator == 0
            else (hobbi_summary["completed"] - static_summary["completed"])
            / denominator
            * 100
        ),
        "profiles": comparisons,
    }


def run_longitudinal() -> dict[str, Any]:
    scenario = load_longitudinal_scenario()
    profile = scenario["profile"]
    cycles = scenario["cycles"]
    static = run_static_policy(
        profile=profile,
        cycles=cycles,
        teen_id="longitudinal-static",
    )
    hobbi = run_hobbi_policy(
        profile=profile,
        cycles=cycles,
        teen_id="longitudinal-hobbi",
    )
    static_attended = sum(cycle["attended"] for cycle in static["cycles"])
    hobbi_attended = sum(cycle["attended"] for cycle in hobbi["cycles"])
    holds = sum(
        cycle["observer_action"] == "hold_this_week" for cycle in hobbi["cycles"]
    )
    latencies: list[int] = []
    triggered_replans = 0
    for index, cycle in enumerate(hobbi["cycles"]):
        if cycle["observer_action"] != "replan":
            continue
        triggered_replans += 1
        if index + 1 >= len(hobbi["cycles"]):
            continue
        next_cycle = hobbi["cycles"][index + 1]
        if (
            next_cycle["responding_to_replan_from_cycle"] == cycle["cycle"]
            and next_cycle["listing_id"] != cycle["listing_id"]
        ):
            latencies.append(1)
    denominator = len(cycles)
    return {
        "measured": True,
        "label": "deterministic 12-cycle synthetic policy replay; not participant evidence",
        "adherence": {
            "hobbi": {"numerator": hobbi_attended, "denominator": denominator},
            "static": {"numerator": static_attended, "denominator": denominator},
            "delta_percentage_points": (
                None
                if denominator == 0
                else (hobbi_attended - static_attended) / denominator * 100
            ),
        },
        "adaptation_latency": {
            "triggered_replans": triggered_replans,
            "resolved_replans": len(latencies),
            "unresolved_replans": triggered_replans - len(latencies),
            "latency_cycles": latencies,
            "mean_cycles": None if not latencies else sum(latencies) / len(latencies),
        },
        "hold_branch_reachability": {"numerator": holds, "denominator": denominator},
        "static_cycles": static["cycles"],
        "hobbi_cycles": hobbi["cycles"],
    }


def run() -> dict[str, Any]:
    return {
        "label": "executable deterministic simulation; not participant evidence",
        "first_attendance": run_first_attendance(),
        "longitudinal": run_longitudinal(),
    }


def main() -> int:
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
