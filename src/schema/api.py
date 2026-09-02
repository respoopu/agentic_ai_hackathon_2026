"""Display-ready contracts for the local Hobbi demo frontend."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from src.schema.plan import StrictModel


class ActivityPlanView(StrictModel):
    listing_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    organiser: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    venue_name: str = Field(min_length=1)
    planning_area: str = Field(min_length=1)
    nearest_mrt: str | None = None
    source_url: str = Field(min_length=1)
    verification: Literal["verified", "unverified"]
    verified_at: date | None = None
    freshness_state: Literal["fresh", "stale"]
    age_min: int = Field(ge=0)
    age_max: int = Field(ge=0)
    beginner_friendly: bool
    join_alone_ok: bool
    guest_allowed: bool
    commitment: Literal["taster", "one_off", "short_course", "term"]
    schedule_kind: Literal["weekly", "fixed_dates", "drop_in"]
    schedule_note: str | None = None
    session_flexible: bool
    session_at: datetime
    duration_hours: float = Field(gt=0)
    cost_sgd: Decimal = Field(ge=0)


class PlanView(StrictModel):
    plan_id: str = Field(min_length=1)
    activities: list[ActivityPlanView] = Field(min_length=1)
    total_cost_sgd: Decimal = Field(ge=0)
    thin: bool
    binding_constraint: str | None = None


class ApprovalRequirements(StrictModel):
    attendance_required: bool = True
    provider_listing_ids: list[str] = Field(default_factory=list)
    spend_required: bool
    spend_ceiling_sgd: Decimal | None = Field(default=None, ge=0)


class PreparationView(StrictModel):
    meet: str = Field(min_length=1)
    bring: str = Field(min_length=1)
    people_come_alone: bool
    guest_allowed: bool


class AdultSummaryView(StrictModel):
    organiser: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    timing: datetime
    timing_note: str | None = None
    source_url: str = Field(min_length=1)


class BookingView(StrictModel):
    booking_id: str = Field(min_length=1)
    status: Literal["booked", "failed"]
    sandbox: bool = True
    activity: ActivityPlanView
    preparation: PreparationView
    adult_summary: AdultSummaryView


class PreferenceChange(StrictModel):
    axis: Literal[
        "indoor_outdoor",
        "team_solo",
        "contact_noncontact",
        "intensity",
        "competitive_social",
    ]
    before_value: float = Field(ge=-1, le=1)
    after_value: float = Field(ge=-1, le=1)
    before_confidence: float = Field(ge=0, le=1)
    after_confidence: float = Field(ge=0, le=1)
    evidence: Literal["seed", "debrief", "attendance"]


class AdaptationView(StrictModel):
    action: Literal["none", "replan", "try_to_commit", "hold_this_week"]
    reason_codes: list[str] = Field(default_factory=list)
    preference_changes: list[PreferenceChange] = Field(default_factory=list)
    dislikes_recorded: int = Field(ge=0)
    persisted: bool


class DemoSetupRequest(StrictModel):
    declared_age: int = Field(ge=13, le=17)
    goal: str = Field(min_length=1, max_length=500)
    money_total_sgd: Decimal = Field(ge=0)
    hours_per_week: float = Field(gt=0, le=40)
    tries_total: int = Field(gt=0, le=12)
    max_travel_min: int = Field(default=45, ge=5, le=120)
    cold_start_vibes: list[
        Literal["sporty", "artistic", "chill", "explorative"]
    ] = Field(default_factory=list, max_length=4)
    parental_rules: list[
        Literal["verified_only", "no_private_unverified", "no_paid_activities"]
    ] = Field(default_factory=list)


class DemoApproveRequest(StrictModel):
    teen_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    provider_listing_ids: list[str] = Field(default_factory=list)
    spend_ceiling_sgd: Decimal | None = Field(default=None, ge=0)


class DemoAttendanceRequest(StrictModel):
    teen_id: str = Field(min_length=1)
    booking_id: str = Field(min_length=1)
    attended: bool
    debrief: str | None = Field(default=None, max_length=2000)


class DemoNextPlanRequest(StrictModel):
    teen_id: str = Field(min_length=1)


class HealthView(StrictModel):
    ok: bool
    ready_for_real_planning: bool
    real_activities: int = Field(ge=0)
    verified_activities: int = Field(ge=0)


class PlanStepResponse(StrictModel):
    ok: bool
    teen_id: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    plan: PlanView | None = None
    approval_requirements: ApprovalRequirements | None = None


class BookingStepResponse(StrictModel):
    ok: bool
    outcome: str = Field(min_length=1)
    plan: PlanView | None = None
    bookings: list[BookingView] = Field(default_factory=list)


class AttendanceStepResponse(StrictModel):
    ok: bool
    adaptation: AdaptationView


class ApiErrorView(StrictModel):
    ok: Literal[False] = False
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
