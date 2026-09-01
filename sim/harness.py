"""Eligible-profile harness with metrics derived from real runtime state."""

from __future__ import annotations

import argparse
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from sim.catalogue import AS_OF, records, travel_times
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, setup
from src.schema.plan import BudgetLedger, ConsentRecord, IntakeResult, SessionRequest
from src.schema.state import HobbiState
from src.store.personal_data import PersonalDataStore

ROOT = Path(__file__).resolve().parents[1]


def load_profiles() -> list[dict[str, Any]]:
    return json.loads(
        (ROOT / "data" / "evaluation_profiles.json").read_text(encoding="utf-8")
    )


def evaluation_consents(teen_id: str) -> list[ConsentRecord]:
    return [
        ConsentRecord(
            consent_id=f"{teen_id}-personal",
            teen_id=teen_id,
            kind="personal_data",
            granted=True,
            granted_by="teen",
            recorded_at=AS_OF,
        ),
        ConsentRecord(
            consent_id=f"{teen_id}-adult",
            teen_id=teen_id,
            kind="trusted_adult_authority",
            granted=True,
            granted_by="trusted_adult",
            recorded_at=AS_OF,
        ),
    ]


def initial_state(
    *, teen_id: str, age: int, request: SessionRequest, ledger: BudgetLedger, thread_id: str
) -> HobbiState:
    return {
        "teen_id": teen_id,
        "thread_id": thread_id,
        "declared_age": age,
        "intake_result": IntakeResult(eligible=True, reason="eligible"),
        "request": request,
        "ledger": ledger,
        "candidate_plan": None,
        "approved_plan": None,
        "guardian_verdict": None,
        "rejection_history": [],
        "binding_constraint": None,
        "resume_approved_plan": False,
        "booking_records": [],
        "replan_count": 0,
        "discovery_rounds": 0,
        "guardian_rejects": 0,
        "gate_log": [],
        "token_usage": [],
        "unavailable_listing_ids": [],
        "outcome": None,
    }


def run_eligible_profiles() -> dict[str, Any]:
    profiles = load_profiles()
    record_map = {record.listing_id: record for record in records()}
    runs: list[dict[str, Any]] = []
    gate_runs = transaction_successes = transaction_attempts = 0
    options = free_options = long_tail_options = 0
    unverified_reached_teen = constraint_violations = 0
    total_iterations = cap_hits = 0

    for profile in profiles:
        teen_id = f"eval-{profile['id']}"
        thread_id = f"eval-thread-{teen_id}"
        request = SessionRequest(goal="try a new hobby", requested_at=AS_OF)
        ledger = BudgetLedger(
            money_total_sgd=Decimal(str(profile["money_total_sgd"])),
            hours_per_week=profile["hours_per_week"],
            tries_total=profile["tries_total"],
        )
        constraints = {
            "max_travel_min": profile["max_travel_min"],
            "travel_times": travel_times(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            personal = PersonalDataStore(Path(temporary, "personal.sqlite"))
            ckb = KnowledgeBase(Path(temporary, "ckb.sqlite"))
            runtime: HobbiRuntime | None = None
            try:
                ckb.seed(record_map.values())
                setup(
                    SetupInput(
                        teen_id=teen_id,
                        thread_id=thread_id,
                        declared_age=profile["age"],
                        request=request,
                        ledger=ledger,
                        consents=evaluation_consents(teen_id),
                        constraints=constraints,
                        cold_start_vibes=profile["cold_start_vibes"],
                    ),
                    personal,
                )
                runtime = HobbiRuntime(personal_data=personal, ckb=ckb, in_memory=True)
                first = runtime.invoke(
                    initial_state(
                        teen_id=teen_id,
                        age=profile["age"],
                        request=request,
                        ledger=ledger,
                        thread_id=thread_id,
                    )
                )
                first_plan = first.get("approved_plan") or first.get("candidate_plan")
                first_verdict = first.get("guardian_verdict")
                if first_plan is not None and first_verdict is not None and first_verdict.approved:
                    unverified_reached_teen += sum(
                        1
                        for item in first_plan.items
                        if record_map[item.listing_id].verification != "verified"
                        and not first_verdict.provider_approval_ids.get(item.listing_id)
                    )
                checkpoint_used = first["outcome"] != "booked" and first_plan is not None
                if checkpoint_used:
                    personal.issue_plan_approvals(
                        teen_id=teen_id,
                        plan_id=first_plan.plan_id,
                        provider_approval_ids={
                            item.listing_id: f"sim-provider-{item.listing_id}"
                            for item in first_plan.items
                            if record_map[item.listing_id].verification != "verified"
                        },
                        attendance_approval_id=f"sim-attendance-{first_plan.plan_id}",
                        spend_approval_id=(
                            f"sim-spend-{first_plan.plan_id}"
                            if first_plan.total_cost_sgd
                            else None
                        ),
                        spend_ceiling_sgd=(
                            first_plan.total_cost_sgd
                            if first_plan.total_cost_sgd
                            else None
                        ),
                    )
                    resumed = initial_state(
                        teen_id=teen_id,
                        age=profile["age"],
                        request=request,
                        ledger=ledger,
                        thread_id=f"{thread_id}-approved",
                    )
                    resumed["candidate_plan"] = first_plan
                    resumed["resume_approved_plan"] = True
                    final = runtime.invoke(resumed)
                else:
                    final = first
                gates = final["gate_log"]
                if gates and all(gate.passed for gate in gates):
                    gate_runs += 1
                plan = final.get("approved_plan") or final.get("candidate_plan")
                if plan is not None:
                    options += len(plan.items)
                    free_options += sum(1 for item in plan.items if item.cost_sgd == 0)
                    long_tail_options += sum(
                        1
                        for item in plan.items
                        if not record_map[item.listing_id].in_incumbent_directory
                    )
                    if plan.total_cost_sgd > ledger.money_remaining_sgd:
                        constraint_violations += 1
                    transaction_attempts += len(plan.items)
                transaction_successes += len(final["booking_records"])
                total_iterations += first["replan_count"] + first["discovery_rounds"]
                if final is not first:
                    total_iterations += final["replan_count"] + final["discovery_rounds"]
                cap_hits += int(first["outcome"] == "cap_breached")
                cap_hits += int(final is not first and final["outcome"] == "cap_breached")
                completion = (
                    "checkpoint"
                    if final["outcome"] == "booked" and checkpoint_used
                    else "autonomous"
                    if final["outcome"] == "booked"
                    else "failed"
                )
                runs.append(
                    {
                        "profile_id": profile["id"],
                        "budget_sgd": profile["money_total_sgd"],
                        "outcome": final["outcome"],
                        "completion": completion,
                        "pre_approval_gates": [
                            {"gate": gate.gate, "passed": gate.passed}
                            for gate in first["gate_log"]
                        ],
                        "approval_continuation_gates": [
                            {"gate": gate.gate, "passed": gate.passed} for gate in gates
                        ],
                        "plan": None if plan is None else plan.model_dump(mode="json"),
                    }
                )
            finally:
                if runtime is not None:
                    runtime.close()
                ckb.close()
                personal.close()

    zero_budget = [run for run in runs if run["budget_sgd"] == 0]
    zero_viable = sum(1 for run in zero_budget if run["outcome"] == "booked")
    autonomous = sum(1 for run in runs if run["completion"] == "autonomous")
    checkpoint = sum(1 for run in runs if run["completion"] == "checkpoint")
    failed = sum(1 for run in runs if run["completion"] == "failed")
    return {
        "label": "synthetic runtime evaluation; not participant evidence",
        "runs": runs,
        "metrics": {
            "schema_validation": {
                "measured": False,
                "observed_successful_continuations": gate_runs,
                "observed_continuation_denominator": len(runs),
                "note": "first-attempt agent-output parse attempts are not instrumented",
            },
            "tool_call_success": {
                "measured": False,
                "numerator": transaction_successes,
                "denominator": transaction_attempts,
                "note": "diagnostic covers sandbox booking commits only; CKB queries and external fetches are not instrumented",
            },
            "task_completion": {
                "autonomous": autonomous,
                "checkpoint": checkpoint,
                "failed": failed,
                "denominator": len(runs),
            },
            "token_cost": {
                "tokens": 0,
                "sgd": 0,
                "note": "deterministic offline policy path; Bedrock was not invoked",
            },
            "loop_discipline": {
                "mean_iterations": total_iterations / len(runs),
                "cap_hits": cap_hits,
                "denominator": len(runs),
            },
            "s0_viability": {"numerator": zero_viable, "denominator": len(zero_budget)},
            "free_option_share": {"numerator": free_options, "denominator": options},
            "long_tail_coverage": {
                "measured": False,
                "illustrative_numerator": long_tail_options,
                "illustrative_denominator": options,
                "note": "authored synthetic catalogue cannot support the long-tail product claim",
            },
            "constraint_violations": {
                "measured": False,
                "numerator": constraint_violations,
                "denominator": len(runs),
                "note": "diagnostic covers eligible synthetic runs; the required adversarial-set rate is not instrumented",
            },
            "unverified_reached_teen": {
                "numerator": unverified_reached_teen,
                "denominator": options,
            },
            "dead_links": {
                "measured": False,
                "note": "synthetic .invalid sources cannot measure live-link health",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", choices=["eligible"], default="eligible")
    parser.parse_args()
    print(json.dumps(run_eligible_profiles(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
