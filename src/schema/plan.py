"""Planning, budget, consent and approval contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BudgetLedger(StrictModel):
    money_total_sgd: Decimal = Field(ge=0)
    money_spent_sgd: Decimal = Field(default=Decimal(0), ge=0)
    money_committed_sgd: Decimal = Field(default=Decimal(0), ge=0)
    hours_per_week: float = Field(ge=0)
    hours_committed: float = Field(default=0, ge=0)
    tries_total: int = Field(ge=0)
    tries_used: int = Field(default=0, ge=0)
    tries_abandoned: int = Field(default=0, ge=0)
    version: int = Field(default=0, ge=0)

    @property
    def money_remaining_sgd(self) -> Decimal:
        return self.money_total_sgd - self.money_spent_sgd - self.money_committed_sgd

    @property
    def hours_remaining(self) -> float:
        return self.hours_per_week - self.hours_committed

    @property
    def tries_remaining(self) -> int:
        return self.tries_total - self.tries_used

    @model_validator(mode="after")
    def _balances(self) -> BudgetLedger:
        if self.money_spent_sgd + self.money_committed_sgd > self.money_total_sgd:
            raise ValueError("spent plus committed money exceeds total")
        if self.hours_committed > self.hours_per_week:
            raise ValueError("committed hours exceed weekly hours")
        if self.tries_used > self.tries_total:
            raise ValueError("used tries exceed total")
        if self.tries_abandoned > self.tries_used:
            raise ValueError("abandoned tries exceed used tries")
        return self


class SessionRequest(StrictModel):
    goal: str = Field(min_length=1, max_length=500)
    requested_at: datetime


class IntakeResult(StrictModel):
    eligible: bool
    reason: Literal["eligible", "under_13", "adult_mode_unavailable"]
    referral: Literal["trusted_adult", "general_activity_services"] | None = None

    @model_validator(mode="after")
    def _coherent(self) -> IntakeResult:
        expected = {
            "eligible": (True, None),
            "under_13": (False, "trusted_adult"),
            "adult_mode_unavailable": (False, "general_activity_services"),
        }[self.reason]
        if (self.eligible, self.referral) != expected:
            raise ValueError("intake eligibility, reason and referral disagree")
        return self


class ConsentRecord(StrictModel):
    consent_id: str = Field(min_length=1)
    teen_id: str = Field(min_length=1)
    kind: Literal["personal_data", "trusted_adult_authority", "peer_cohort"]
    granted: bool
    granted_by: Literal["teen", "trusted_adult"]
    recorded_at: datetime

    @model_validator(mode="after")
    def _authority_matches_kind(self) -> ConsentRecord:
        if self.kind == "personal_data" and self.granted_by != "teen":
            raise ValueError("personal-data consent for ages 13-17 is held by the teen")
        if self.kind == "trusted_adult_authority" and self.granted_by != "trusted_adult":
            raise ValueError("trusted-adult authority must be granted by the trusted adult")
        return self


class PlanItem(StrictModel):
    listing_id: str = Field(min_length=1)
    session_at: datetime
    cost_sgd: Decimal = Field(ge=0)
    duration_hours: float = Field(default=1.0, gt=0)


class Plan(StrictModel):
    plan_id: str = Field(min_length=1)
    items: list[PlanItem] = Field(min_length=1)
    total_cost_sgd: Decimal = Field(ge=0)
    ledger_version: int = Field(ge=0)
    thin: bool = False
    binding_constraint: str | None = None

    @model_validator(mode="after")
    def _total_matches(self) -> Plan:
        if sum((item.cost_sgd for item in self.items), Decimal(0)) != self.total_cost_sgd:
            raise ValueError("plan total does not equal item costs")
        if self.thin and not self.binding_constraint:
            raise ValueError("thin plans must name the binding constraint")
        logical_items = {(item.listing_id, item.session_at) for item in self.items}
        if len(logical_items) != len(self.items):
            raise ValueError("plan cannot contain a duplicate listing session")
        return self


class GuardianVerdict(StrictModel):
    verdict_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    approved: bool
    provider_approval_ids: dict[str, str] = Field(default_factory=dict)
    attendance_approval_id: str | None = None
    spend_approval_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    reviewed_at: datetime

    @model_validator(mode="after")
    def _reasoned(self) -> GuardianVerdict:
        if not self.approved and not self.reason_codes:
            raise ValueError("rejected verdict needs at least one reason code")
        if self.approved and self.reason_codes:
            raise ValueError("approved verdict cannot carry rejection reasons")
        return self
