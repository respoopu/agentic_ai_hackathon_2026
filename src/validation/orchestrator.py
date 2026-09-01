"""G1-G4 and I0 checks. This module routes no business work."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError

from src.agents.tools import ToolGuard
from src.schema.events import BookingRecord, CommitEvidence
from src.schema.gates import GateResult
from src.schema.listing import ListingRecord
from src.schema.plan import (
    BudgetLedger,
    ConsentRecord,
    GuardianVerdict,
    IntakeResult,
    Plan,
)

FORBIDDEN_DISCOVERY_KEYS = frozenset(
    {"teen_id", "address", "exact_address", "school", "parental_rule", "parental_rules"}
)
RAW_CONTENT_KEYS = frozenset({"raw_html", "page_dump", "raw_content", "instructions"})


class GateValidationError(RuntimeError):
    def __init__(self, result: GateResult) -> None:
        self.result = result
        super().__init__(f"{result.gate} failed: {', '.join(result.reason_codes)}")


def _serializable(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Mapping):
        return {str(key): _serializable(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_serializable(value) for value in payload]
    return payload


def _contains_key(payload: Any, forbidden: frozenset[str]) -> bool:
    if isinstance(payload, Mapping):
        return any(
            str(key).lower() in forbidden or _contains_key(value, forbidden)
            for key, value in payload.items()
        )
    if isinstance(payload, (list, tuple)):
        return any(_contains_key(value, forbidden) for value in payload)
    return False


class Validator:
    def _result(
        self,
        gate: str,
        payload: Any,
        schema_id: str,
        reasons: list[str],
    ) -> GateResult:
        serialized = json.dumps(
            _serializable(payload), sort_keys=True, separators=(",", ":"), default=str
        ).encode()
        return GateResult(
            gate=gate,
            passed=not reasons,
            schema_id=schema_id,
            payload_size=len(serialized),
            reason_codes=reasons,
            checked_at=datetime.now(UTC),
        )

    @staticmethod
    def require_pass(result: GateResult) -> GateResult:
        if not result.passed:
            raise GateValidationError(result)
        return result

    def i0(self, declared_age: int, consents: list[ConsentRecord]) -> tuple[IntakeResult, GateResult]:
        ToolGuard("validator").require("gates", "I0")
        if declared_age < 13:
            intake = IntakeResult(eligible=False, reason="under_13", referral="trusted_adult")
            reasons = ["age_under_13"]
        elif declared_age > 17:
            intake = IntakeResult(
                eligible=False,
                reason="adult_mode_unavailable",
                referral="general_activity_services",
            )
            reasons = ["adult_mode_unavailable"]
        else:
            grants = {record.kind: record.granted for record in consents}
            missing = [
                kind
                for kind in ("personal_data", "trusted_adult_authority")
                if not grants.get(kind, False)
            ]
            reasons = [f"missing_{kind}" for kind in missing]
            intake = (
                IntakeResult(
                    eligible=False,
                    reason="consent_required",
                    referral="trusted_adult",
                )
                if missing
                else IntakeResult(eligible=True, reason="eligible", referral=None)
            )
        result = self._result(
            "I0",
            {"declared_age": declared_age, "consent_kinds": sorted(c.kind for c in consents)},
            "IntakeResult",
            reasons,
        )
        return intake, result

    def g1_plan(self, payload: Any) -> GateResult:
        ToolGuard("validator").require("gates", "G1")
        reasons: list[str] = []
        try:
            plan = payload if isinstance(payload, Plan) else Plan.model_validate(payload)
        except (TypeError, ValueError, ValidationError):
            plan = payload
            reasons.append("invalid_plan_schema")
        serialized = _serializable(plan)
        if _contains_key(serialized, FORBIDDEN_DISCOVERY_KEYS):
            reasons.append("personal_data_in_discovery_payload")
        return self._result("G1", serialized, "Plan", reasons)

    def g1_records(self, payload: Any) -> GateResult:
        ToolGuard("validator").require("gates", "G1")
        reasons: list[str] = []
        try:
            records = [
                value if isinstance(value, ListingRecord) else ListingRecord.model_validate(value)
                for value in payload
            ]
        except (TypeError, ValueError, ValidationError):
            records = payload
            reasons.append("invalid_listing_record")
        serialized = _serializable(records)
        if _contains_key(serialized, RAW_CONTENT_KEYS):
            reasons.append("raw_page_content_forbidden")
        return self._result("G1", serialized, "ListingRecord[]", reasons)

    def g2(
        self,
        plan: Plan,
        ledger: BudgetLedger,
        listings: Mapping[str, ListingRecord],
    ) -> GateResult:
        ToolGuard("validator").require("gates", "G2")
        reasons: list[str] = []
        if plan.ledger_version != ledger.version:
            reasons.append("stale_ledger_version")
        if plan.total_cost_sgd > ledger.money_remaining_sgd:
            reasons.append("budget_exceeded")
        if sum(item.duration_hours for item in plan.items) > ledger.hours_remaining:
            reasons.append("hours_exceeded")
        if len(plan.items) > ledger.tries_remaining:
            reasons.append("tries_exceeded")
        for item in plan.items:
            listing = listings.get(item.listing_id)
            if listing is None:
                reasons.append(f"listing_not_found:{item.listing_id}")
                continue
            expected = listing.cost_total_first_session or Decimal(0)
            if item.cost_sgd != expected:
                reasons.append(f"listing_cost_mismatch:{item.listing_id}")
            if listing.verification == "retired" or listing.freshness_state == "dead":
                reasons.append(f"listing_dead:{item.listing_id}")
        return self._result("G2", plan, "Plan", reasons)

    def g3(
        self,
        plan: Plan,
        verdict: GuardianVerdict | None,
        listings: Mapping[str, ListingRecord],
    ) -> GateResult:
        ToolGuard("validator").require("gates", "G3")
        reasons: list[str] = []
        if verdict is None:
            reasons.append("guardian_verdict_missing")
        elif not verdict.approved:
            reasons.append("guardian_verdict_rejected")
        elif verdict.plan_id != plan.plan_id:
            reasons.append("guardian_verdict_plan_mismatch")
        else:
            for item in plan.items:
                listing = listings.get(item.listing_id)
                if listing is None:
                    reasons.append(f"listing_not_found:{item.listing_id}")
                elif listing.verification != "verified" and not verdict.provider_approval_ids.get(
                    item.listing_id
                ):
                    reasons.append(f"provider_approval_missing:{item.listing_id}")
            if not verdict.attendance_approval_id:
                reasons.append("attendance_approval_missing")
            if plan.total_cost_sgd > 0 and not verdict.spend_approval_id:
                reasons.append("spend_approval_missing")
        return self._result("G3", verdict or {}, "GuardianVerdict", reasons)

    def g4(
        self,
        booking: BookingRecord,
        *,
        evidence: CommitEvidence,
    ) -> GateResult:
        ToolGuard("validator").require("gates", "G4")
        reasons: list[str] = []
        if booking.status != "booked" or not booking.ledger_transaction_id:
            reasons.append("booking_not_committed")
        if booking.ledger_transaction_id not in evidence.transaction_ids:
            reasons.append("transaction_evidence_missing")
        if evidence.transaction_rows != len(evidence.transaction_ids):
            reasons.append("transaction_row_count_mismatch")
        if evidence.ledger_version_after != evidence.ledger_version_before + 1:
            reasons.append("ledger_version_not_exactly_once")
        return self._result(
            "G4",
            {"booking": booking, "commit_evidence": evidence},
            "BookingRecord+CommitEvidence",
            reasons,
        )
