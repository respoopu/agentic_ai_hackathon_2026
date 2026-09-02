"""Read-only deterministic planning policy and structured output seam."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal

from pydantic import Field

from src.agents.tools import ToolGuard
from src.schema.listing import Listing
from src.schema.plan import BudgetLedger, Plan, PlanItem, SessionRequest, StrictModel
from src.schema.preferences import PreferenceModel


class PlannerResult(StrictModel):
    plan: Plan | None = None
    outcome: str | None = None
    binding_constraint: str | None = None
    candidate_count: int = Field(ge=0)


class Planner:
    allowed_tools = frozenset({"read_ckb", "read_personal_data", "invoke_discovery"})

    def create_plan(
        self,
        *,
        planning_key: str = "",
        declared_age: int,
        request: SessionRequest,
        ledger: BudgetLedger,
        preferences: PreferenceModel,
        listings: Iterable[Listing],
        parental_rules: list[str] | None = None,
        constraints: dict[str, object] | None = None,
        unavailable_listing_ids: set[str] | None = None,
    ) -> PlannerResult:
        guard = ToolGuard("planner")
        guard.require("reads", "CKB")
        guard.require("reads", "Personal Data")
        rules = set(parental_rules or [])
        limits = constraints or {}
        unavailable = unavailable_listing_ids or set()
        max_travel = int(limits.get("max_travel_min", 10_000))
        max_item_cost = Decimal(str(limits.get("max_item_cost_sgd", ledger.money_remaining_sgd)))
        max_items = min(int(limits.get("max_items", 3)), ledger.tries_remaining)
        eligible: list[Listing] = []
        binding_counts = {
            "money": 0,
            "travel": 0,
            "time": 0,
            "schedule": 0,
            "age": 0,
            "rules": 0,
        }
        for listing in listings:
            if listing.listing_id in unavailable or listing.verification == "retired":
                continue
            if not listing.age_min <= declared_age <= listing.age_max:
                binding_counts["age"] += 1
                continue
            if min(listing.travel_min_home, listing.travel_min_school) > max_travel:
                binding_counts["travel"] += 1
                continue
            cost = listing.cost_total_first_session or Decimal(0)
            if cost > ledger.money_remaining_sgd or cost > max_item_cost:
                binding_counts["money"] += 1
                continue
            duration = (listing.schedule.duration_min or 60) / 60
            if duration > ledger.hours_remaining:
                binding_counts["time"] += 1
                continue
            if limits.get("weekday_evening_only") and not listing.schedule.is_weekday_evening():
                binding_counts["schedule"] += 1
                continue
            if "verified_only" in rules and listing.verification != "verified":
                binding_counts["rules"] += 1
                continue
            if "no_private_unverified" in rules and listing.provider_type == "private_unverified":
                binding_counts["rules"] += 1
                continue
            if "no_paid_activities" in rules and cost > 0:
                binding_counts["rules"] += 1
                continue
            allowed_areas = limits.get("allowed_planning_areas")
            if isinstance(allowed_areas, list) and listing.planning_area not in allowed_areas:
                binding_counts["travel"] += 1
                continue
            eligible.append(listing)

        if not eligible or max_items <= 0:
            constraint = max(binding_counts, key=binding_counts.get) if any(binding_counts.values()) else "tries"
            return PlannerResult(
                outcome="no_viable_plan",
                binding_constraint=f"ckb_coverage_gap:{constraint}",
                candidate_count=0,
            )

        at = request.requested_at

        def interest_score(listing: Listing) -> float:
            score = 0.0
            if "sporty" in listing.vibes:
                score += preferences.intensity.value * preferences.intensity.confidence
            if "chill" in listing.vibes:
                score -= preferences.intensity.value * preferences.intensity.confidence
            if "artistic" in listing.vibes:
                score += preferences.contact_noncontact.value * preferences.contact_noncontact.confidence
            for dislike in preferences.dislikes:
                applies = dislike.listing_id == listing.listing_id
                if dislike.attribution == "instance" and dislike.provider:
                    applies = dislike.provider == listing.provider
                elif dislike.attribution == "activity" and dislike.axis.startswith("vibe:"):
                    applies = dislike.axis.removeprefix("vibe:") in listing.vibes
                if applies:
                    score -= dislike.effective_strength(at)
            return score

        commitment_order = {"taster": 0, "one_off": 1, "short_course": 2, "term": 3}
        eligible.sort(
            key=lambda listing: (
                listing.cost_total_first_session or Decimal(0),
                commitment_order[listing.commitment],
                -interest_score(listing),
                0
                if listing.peer_cohort
                and not listing.peer_cohort.suppressed
                and listing.peer_cohort.same_age_band in {"some", "many"}
                else 1,
                min(listing.travel_min_home, listing.travel_min_school),
                listing.listing_id,
            )
        )
        selected: list[PlanItem] = []
        cost_used = Decimal(0)
        hours_used = 0.0
        for listing in eligible:
            if len(selected) >= max_items:
                break
            cost = listing.cost_total_first_session or Decimal(0)
            duration = (listing.schedule.duration_min or 60) / 60
            if cost_used + cost > ledger.money_remaining_sgd:
                continue
            if hours_used + duration > ledger.hours_remaining:
                continue
            session = (
                listing.next_sessions[0]
                if listing.next_sessions
                else request.requested_at + timedelta(days=7)
            )
            selected.append(
                PlanItem(
                    listing_id=listing.listing_id,
                    session_at=session,
                    cost_sgd=cost,
                    duration_hours=duration,
                )
            )
            cost_used += cost
            hours_used += duration
        if not selected:
            return PlannerResult(
                outcome="no_viable_plan",
                binding_constraint="ckb_coverage_gap:combined_constraints",
                candidate_count=len(eligible),
            )
        thin = len(selected) < min(2, max_items)
        binding = None
        if thin:
            binding = max(binding_counts, key=binding_counts.get) if any(binding_counts.values()) else "limited_supply"
        identity = "|".join(
            [planning_key, request.goal, str(ledger.version), *(item.listing_id for item in selected)]
        )
        plan = Plan(
            plan_id=f"plan_{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
            items=selected,
            total_cost_sgd=cost_used,
            ledger_version=ledger.version,
            thin=thin,
            binding_constraint=binding,
        )
        return PlannerResult(plan=plan, binding_constraint=binding, candidate_count=len(eligible))
