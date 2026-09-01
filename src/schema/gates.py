"""Detached gate and instrumentation records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from src.schema.plan import StrictModel


class GateResult(StrictModel):
    gate: Literal["I0", "G1", "G2", "G3", "G4"]
    passed: bool
    schema_id: str = Field(min_length=1)
    payload_size: int = Field(ge=0)
    reason_codes: list[str] = Field(default_factory=list)
    checked_at: datetime


class TokenUsage(StrictModel):
    agent: str = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    recorded_at: datetime
