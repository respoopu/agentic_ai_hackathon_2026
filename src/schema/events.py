"""Booking and longitudinal event contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from src.schema.plan import StrictModel


class BookingRecord(StrictModel):
    booking_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    listing_id: str = Field(min_length=1)
    guardian_verdict_id: str = Field(min_length=1)
    status: Literal["booked", "failed"]
    ledger_transaction_id: str | None = None
    committed_sgd: Decimal = Field(ge=0)
    committed_hours: float = Field(default=0, ge=0)
    created_at: datetime

    @model_validator(mode="after")
    def _transaction_for_success(self) -> BookingRecord:
        if self.status == "booked" and not self.ledger_transaction_id:
            raise ValueError("booked record needs a ledger transaction id")
        if self.status == "failed" and self.ledger_transaction_id is not None:
            raise ValueError("failed record cannot claim a ledger transaction")
        return self


class CommitEvidence(StrictModel):
    """Durable evidence that G4 can validate independently of Broker control flow."""

    transaction_ids: list[str] = Field(min_length=1)
    ledger_version_before: int = Field(ge=0)
    ledger_version_after: int = Field(ge=0)
    transaction_rows: int = Field(ge=1)
    replayed: bool = False

    @model_validator(mode="after")
    def _exactly_once_transition(self) -> CommitEvidence:
        if len(set(self.transaction_ids)) != len(self.transaction_ids):
            raise ValueError("commit evidence cannot contain duplicate transaction ids")
        if self.transaction_rows != len(self.transaction_ids):
            raise ValueError("every logical commitment needs one transaction row")
        if self.ledger_version_after != self.ledger_version_before + 1:
            raise ValueError("the committed plan must advance the ledger exactly once")
        return self


class AttendanceEvent(StrictModel):
    booking_id: str = Field(min_length=1)
    attended: bool
    occurred_at: datetime


class DebriefRecord(StrictModel):
    booking_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    submitted_at: datetime


class DebriefSubmission(StrictModel):
    booking_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    channel: Literal["in_app"]
    submitted_at: datetime
