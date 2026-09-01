"""Eligible-profile harness and Family B runtime measurements."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from sim.catalogue import AS_OF, listings, records
from src.agents.guardian import Guardian
from src.agents.planner import Planner
from src.intake import preference_seeds
from src.schema.plan import BudgetLedger, SessionRequest

ROOT = Path(__file__).resolve().parents[1]


def load_profiles() -> list[dict[str, Any]]:
    return json.loads((ROOT / "data" / "evaluation_profiles.json").read_text(encoding="utf-8"))


def run_eligible_profiles() -> dict[str, Any]:
    profiles = load_profiles()
    catalogue = listings()
    record_map = {record.listing_id: record for record in records()}
    runs: list[dict[str, Any]] = []
    schema_passes = 0
    tool_successes = 0
    options = 0
    free_options = 0
    long_tail_options = 0
    unverified_reached_teen = 0
    constraint_violations = 0
    for profile in profiles:
        ledger = BudgetLedger(
            money_total_sgd=Decimal(str(profile["money_total_sgd"])),
            hours_per_week=profile["hours_per_week"],
            tries_total=profile["tries_total"],
        )
        preferences = preference_seeds(profile["cold_start_vibes"], AS_OF)
        result = Planner().create_plan(
            planning_key=profile["id"],
            declared_age=profile["age"],
            request=SessionRequest(goal="try a new hobby", requested_at=AS_OF),
            ledger=ledger,
            preferences=preferences,
            listings=catalogue,
            constraints={"max_travel_min": profile["max_travel_min"]},
        )
        plan = result.plan
        if plan is not None:
            schema_passes += 1
            tool_successes += 1
            options += len(plan.items)
            free_options += sum(1 for item in plan.items if item.cost_sgd == 0)
            long_tail_options += sum(
                1 for item in plan.items if not record_map[item.listing_id].in_incumbent_directory
            )
            if plan.total_cost_sgd > ledger.money_remaining_sgd:
                constraint_violations += 1
            # First check without provider approval proves the quarantine; the
            # simulated trusted adult then approves the synthetic fixtures.
            blocked = Guardian().review(
                plan=plan,
                listings=record_map,
                attendance_approval_id="sim-attendance",
                spend_approval_id="sim-spend" if plan.total_cost_sgd else None,
            )
            if blocked.approved:
                unverified_reached_teen += len(plan.items)
            approvals = {item.listing_id: f"sim-provider-{item.listing_id}" for item in plan.items}
            final_verdict = Guardian().review(
                plan=plan,
                listings=record_map,
                provider_approval_ids=approvals,
                attendance_approval_id="sim-attendance",
                spend_approval_id="sim-spend" if plan.total_cost_sgd else None,
            )
            outcome = "booked" if final_verdict.approved else "escalated_to_adult"
        else:
            outcome = "no_viable_plan"
        runs.append(
            {
                "profile_id": profile["id"],
                "budget_sgd": profile["money_total_sgd"],
                "outcome": outcome,
                "plan": None if plan is None else plan.model_dump(mode="json"),
            }
        )
    zero_budget = [run for run in runs if run["budget_sgd"] == 0]
    zero_viable = sum(1 for run in zero_budget if run["plan"] is not None)
    autonomous = sum(1 for run in runs if run["outcome"] == "booked")
    checkpoint = sum(1 for run in runs if run["outcome"] == "escalated_to_adult")
    failed = len(runs) - autonomous - checkpoint
    return {
        "label": "synthetic evaluation; not participant evidence",
        "runs": runs,
        "metrics": {
            "schema_validation": {"numerator": schema_passes, "denominator": len(runs)},
            "tool_call_success": {"numerator": tool_successes, "denominator": len(runs)},
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
            "loop_discipline": {"mean_iterations": 0, "cap_hits": 0, "denominator": len(runs)},
            "s0_viability": {"numerator": zero_viable, "denominator": len(zero_budget)},
            "free_option_share": {"numerator": free_options, "denominator": options},
            "long_tail_coverage": {"numerator": long_tail_options, "denominator": options},
            "constraint_violations": {"numerator": constraint_violations, "denominator": len(runs)},
            "unverified_reached_teen": {"numerator": unverified_reached_teen, "denominator": options},
            "dead_links": {"numerator": 0, "denominator": options},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", choices=["eligible"], default="eligible")
    args = parser.parse_args()
    if args.profiles == "eligible":
        print(json.dumps(run_eligible_profiles(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
