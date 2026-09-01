"""Typed request state carried by LangGraph."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from src.schema.events import BookingRecord
from src.schema.gates import GateResult, TokenUsage
from src.schema.plan import (
    BudgetLedger,
    GuardianVerdict,
    IntakeResult,
    Plan,
    SessionRequest,
)

TerminalOutcome = Literal[
    "booked",
    "escalated_to_adult",
    "no_viable_plan",
    "hold_this_week",
    "cap_breached",
]


class HobbiState(TypedDict):
    teen_id: str
    thread_id: str
    declared_age: int
    intake_result: IntakeResult
    request: SessionRequest
    ledger: BudgetLedger
    candidate_plan: Plan | None
    approved_plan: Plan | None
    guardian_verdict: GuardianVerdict | None
    booking_records: Annotated[list[BookingRecord], operator.add]
    replan_count: int
    discovery_rounds: int
    guardian_rejects: int
    gate_log: Annotated[list[GateResult], operator.add]
    token_usage: Annotated[list[TokenUsage], operator.add]
    unavailable_listing_ids: list[str]
    outcome: TerminalOutcome | None
