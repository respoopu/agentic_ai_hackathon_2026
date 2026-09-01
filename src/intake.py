"""Deterministic Intake/Setup boundary; no model is involved."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from src.agents.tools import ToolGuard
from src.schema.gates import GateResult
from src.schema.plan import (
    BudgetLedger,
    ConsentRecord,
    IntakeResult,
    SessionRequest,
    StrictModel,
)
from src.schema.preferences import Axis, PreferenceModel
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator

Vibe = Literal["sporty", "artistic", "chill", "explorative"]
VIBE_AXIS_VALUES: dict[str, dict[str, float]] = {
    "sporty": {"indoor_outdoor": 0.7, "intensity": 0.7, "team_solo": 0.3},
    "artistic": {"indoor_outdoor": -0.4, "contact_noncontact": 0.7, "intensity": -0.4},
    "chill": {"intensity": -0.8, "competitive_social": 0.5},
    "explorative": {"indoor_outdoor": 0.2, "team_solo": 0.0, "competitive_social": 0.2},
}


class SetupInput(StrictModel):
    teen_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    declared_age: int
    request: SessionRequest
    ledger: BudgetLedger
    consents: list[ConsentRecord]
    parental_rules: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    cold_start_vibes: list[Vibe] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _separate_trusted_adult_authority(self) -> SetupInput:
        forbidden = {
            "provider_approval_ids",
            "attendance_approval_id",
            "spend_approval_id",
            "spend_ceiling_sgd",
        }
        supplied = sorted(forbidden.intersection(self.constraints))
        if supplied:
            raise ValueError(
                "setup constraints cannot issue trusted-adult approvals: "
                + ", ".join(supplied)
            )
        return self


class SetupResult(StrictModel):
    intake: IntakeResult
    gate: GateResult
    persisted: bool


def preference_seeds(vibes: list[Vibe], at: datetime) -> PreferenceModel:
    model = PreferenceModel.neutral(at)
    if not vibes:
        return model
    values: dict[str, list[float]] = {}
    for vibe in vibes:
        for axis, value in VIBE_AXIS_VALUES[vibe].items():
            values.setdefault(axis, []).append(value)
    updates = {
        axis: Axis(
            value=sum(axis_values) / len(axis_values),
            confidence=0.2,
            provenance="seed",
            updated_at=at,
        )
        for axis, axis_values in values.items()
    }
    return PreferenceModel.model_validate(
        {**model.model_dump(), **updates, "seeded_at": at}
    )


def setup(input_data: SetupInput, store: PersonalDataStore, validator: Validator | None = None) -> SetupResult:
    guard = ToolGuard("intake")
    guard.require("reads", "declared_input")
    guard.require("writes", "Personal Data.setup")
    gatekeeper = validator or Validator()
    intake, gate = gatekeeper.i0(input_data.declared_age, input_data.consents)
    if not intake.eligible or not gate.passed:
        return SetupResult(intake=intake, gate=gate, persisted=False)
    preferences = preference_seeds(input_data.cold_start_vibes, input_data.request.requested_at)
    store.setup_profile(
        teen_id=input_data.teen_id,
        thread_id=input_data.thread_id,
        declared_age=input_data.declared_age,
        request=input_data.request,
        ledger=input_data.ledger,
        preferences=preferences,
        consents=input_data.consents,
        parental_rules=input_data.parental_rules,
        constraints=input_data.constraints,
    )
    return SetupResult(intake=intake, gate=gate, persisted=True)
