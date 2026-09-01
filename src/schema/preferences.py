"""Preference evidence with decay and provenance ordering."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from src.schema.events import AttendanceEvent, DebriefRecord
from src.schema.plan import StrictModel

PROVENANCE_CONFIDENCE_CEILING = {
    "seed": 0.25,
    "debrief": 0.65,
    "attendance": 1.0,
}
DISLIKE_INFLUENCE_FLOOR = 0.15


class Axis(StrictModel):
    value: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    provenance: Literal["seed", "debrief", "attendance"]
    updated_at: datetime

    @model_validator(mode="after")
    def _confidence_matches_evidence(self) -> Axis:
        if self.confidence > PROVENANCE_CONFIDENCE_CEILING[self.provenance]:
            raise ValueError(f"confidence too high for {self.provenance} evidence")
        return self


class DislikeSignal(StrictModel):
    axis: str = Field(min_length=1)
    listing_id: str = Field(min_length=1)
    attribution: Literal["activity", "instance", "unattributed"]
    strength: float = Field(ge=0, le=1)
    recorded_at: datetime
    half_life_days: int = Field(default=90, gt=0)

    def effective_strength(self, at: datetime) -> float:
        elapsed_days = max(0.0, (at - self.recorded_at).total_seconds() / 86400)
        effective = self.strength * 0.5 ** (elapsed_days / self.half_life_days)
        return effective if effective >= DISLIKE_INFLUENCE_FLOOR else 0.0


def neutral_axis(at: datetime) -> Axis:
    return Axis(value=0, confidence=0, provenance="seed", updated_at=at)


class PreferenceModel(StrictModel):
    indoor_outdoor: Axis
    team_solo: Axis
    contact_noncontact: Axis
    intensity: Axis
    competitive_social: Axis
    dislikes: list[DislikeSignal] = Field(default_factory=list)
    attendance: list[AttendanceEvent] = Field(default_factory=list)
    debriefs: list[DebriefRecord] = Field(default_factory=list)
    seeded_at: datetime | None = None

    @classmethod
    def neutral(cls, at: datetime) -> PreferenceModel:
        return cls(
            indoor_outdoor=neutral_axis(at),
            team_solo=neutral_axis(at),
            contact_noncontact=neutral_axis(at),
            intensity=neutral_axis(at),
            competitive_social=neutral_axis(at),
            seeded_at=None,
        )
