"""Executable checks for the eight adversarial evaluation scenarios."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from sim.catalogue import AS_OF, listings, records, travel_times
from sim.harness import evaluation_consents, initial_state
from src.agents.guardian import Guardian
from src.agents.planner import Planner
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, preference_seeds, setup
from src.schema.listing import PeerCohort
from src.schema.plan import BudgetLedger, Plan, PlanItem, SessionRequest
from src.schema.preferences import PreferenceModel
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator


def _request(goal: str = "find a safe free hobby") -> SessionRequest:
    return SessionRequest(goal=goal, requested_at=AS_OF)


def _plan(
    *,
    candidates: list[Any],
    age: int = 15,
    ledger: BudgetLedger | None = None,
    preferences: PreferenceModel | None = None,
    parental_rules: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
) -> Any:
    return Planner().create_plan(
        planning_key="adversarial",
        declared_age=age,
        request=_request(),
        ledger=ledger
        or BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=3),
        preferences=preferences or PreferenceModel.neutral(AS_OF),
        listings=candidates,
        parental_rules=parental_rules,
        constraints=constraints,
    )


def _unverified_provider_is_stopped() -> bool:
    record = records()[0]
    plan = Plan(
        plan_id="adversarial-unverified",
        items=[PlanItem(listing_id=record.listing_id, session_at=AS_OF, cost_sgd=0)],
        total_cost_sgd=0,
        ledger_version=0,
    )
    verdict = Guardian().review(
        plan=plan,
        listings={record.listing_id: record},
        attendance_approval_id="attendance-only",
    )
    return not verdict.approved and any(
        reason.startswith("provider_vetting_required:")
        for reason in verdict.reason_codes
    )


def _thin_plan_names_constraint() -> bool:
    result = _plan(
        candidates=[listings()[0]],
        constraints={"max_items": 3, "max_travel_min": 15},
    )
    return bool(
        result.plan
        and result.plan.thin
        and result.plan.binding_constraint
        and result.plan.total_cost_sgd == 0
    )


def _parental_rule_wins() -> bool:
    candidate_map = {listing.listing_id: listing for listing in listings()}
    result = _plan(
        candidates=[candidate_map["SYN-sport-paid"], candidate_map["SYN-chill-free"]],
        ledger=BudgetLedger(money_total_sgd=50, hours_per_week=2, tries_total=2),
        preferences=preference_seeds(["sporty"], AS_OF),
        parental_rules=["no_paid_activities"],
    )
    return bool(
        result.plan
        and result.plan.total_cost_sgd == 0
        and result.plan.items[0].listing_id == "SYN-chill-free"
    )


def _dead_listing_is_excluded() -> bool:
    source = listings()
    retired = type(source[0]).model_validate(
        {
            **source[0].model_dump(),
            "provider_type": "cc",
            "source_url": "https://www.onepa.gov.sg/adversarial-retired",
            "verification": "retired",
            "is_fictional": False,
            "freshness_state": "dead",
        }
    )
    fresh = source[1]
    result = _plan(candidates=[retired, fresh])
    return bool(
        result.plan
        and all(item.listing_id != retired.listing_id for item in result.plan.items)
    )


def _age_coverage_gap_is_actionable() -> bool:
    older_only = [
        listing.model_copy(update={"age_min": 16, "age_max": 17})
        for listing in listings()[:2]
    ]
    result = _plan(candidates=older_only, age=15)
    return (
        result.plan is None
        and result.outcome == "no_viable_plan"
        and result.binding_constraint == "ckb_coverage_gap:age"
    )


def _two_guardian_rejections_escalate() -> bool:
    with tempfile.TemporaryDirectory() as temporary:
        personal = PersonalDataStore(Path(temporary, "personal.sqlite"))
        ckb = KnowledgeBase(Path(temporary, "ckb.sqlite"))
        runtime: HobbiRuntime | None = None
        try:
            teen_id = "adversarial-guardian"
            request = _request()
            ledger = BudgetLedger(
                money_total_sgd=0, hours_per_week=2, tries_total=3
            )
            setup(
                SetupInput(
                    teen_id=teen_id,
                    thread_id="adversarial-guardian-thread",
                    declared_age=15,
                    request=request,
                    ledger=ledger,
                    consents=evaluation_consents(teen_id),
                    constraints={"max_items": 1, "travel_times": travel_times()},
                ),
                personal,
            )
            ckb.seed(records()[:3])
            runtime = HobbiRuntime(personal_data=personal, ckb=ckb, in_memory=True)
            result = runtime.invoke(
                initial_state(
                    teen_id=teen_id,
                    age=15,
                    request=request,
                    ledger=ledger,
                    thread_id="adversarial-guardian-run",
                )
            )
            return bool(
                result["outcome"] == "escalated_to_adult"
                and result["guardian_rejects"] == 2
                and not result["booking_records"]
            )
        finally:
            if runtime is not None:
                runtime.close()
            ckb.close()
            personal.close()


def _age_boundary_is_stopped_at_intake() -> bool:
    validator = Validator()
    results = [
        validator.i0(age, evaluation_consents(f"adversarial-age-{age}"))[0]
        for age in (12, 18)
    ]
    return all(not result.eligible for result in results) and {
        result.referral for result in results
    } == {"trusted_adult", "general_activity_services"}


def _suppressed_peer_signal_never_filters() -> bool:
    base = listings()[0]
    suppressed = base.model_copy(
        update={
            "peer_cohort": PeerCohort(
                same_age_band="few", same_area=True, suppressed=True
            )
        }
    )
    without = _plan(candidates=[base])
    with_suppressed = _plan(candidates=[suppressed])
    return bool(
        without.plan
        and with_suppressed.plan
        and without.candidate_count == with_suppressed.candidate_count == 1
        and without.plan.items[0].listing_id
        == with_suppressed.plan.items[0].listing_id
    )


def run_adversarial_set() -> dict[str, Any]:
    checks = [
        ("unverified_provider_quarantined", _unverified_provider_is_stopped),
        ("thin_plan_names_binding_constraint", _thin_plan_names_constraint),
        ("parental_rule_wins", _parental_rule_wins),
        ("dead_listing_excluded", _dead_listing_is_excluded),
        ("age_coverage_gap_actionable", _age_coverage_gap_is_actionable),
        ("two_guardian_rejections_escalate", _two_guardian_rejections_escalate),
        ("age_boundary_stopped_at_intake", _age_boundary_is_stopped_at_intake),
        ("suppressed_peer_signal_never_filters", _suppressed_peer_signal_never_filters),
    ]
    cases = [
        {"case": name, "passed": bool(check())}
        for name, check in checks
    ]
    violations = sum(not case["passed"] for case in cases)
    return {
        "label": "executable synthetic adversarial set; not participant evidence",
        "cases": cases,
        "constraint_violations": {
            "measured": True,
            "numerator": violations,
            "denominator": len(cases),
        },
    }
