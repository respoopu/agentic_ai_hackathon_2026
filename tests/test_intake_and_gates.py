from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.agents.tools import COMPONENT_PERMISSIONS, ToolGuard, ToolPermissionError
from src.intake import SetupInput, setup
from src.schema.events import BookingRecord, CommitEvidence
from src.schema.plan import (
    BudgetLedger,
    ConsentRecord,
    GuardianVerdict,
    Plan,
    PlanItem,
    SessionRequest,
)
from src.store.personal_data import PersonalDataError, PersonalDataStore
from src.validation.orchestrator import Validator
from tests.helpers import NOW, listing_record


def consents(teen_id: str = "teen") -> list[ConsentRecord]:
    return [
        ConsentRecord(
            consent_id=f"{teen_id}-personal",
            teen_id=teen_id,
            kind="personal_data",
            granted=True,
            granted_by="teen",
            recorded_at=NOW,
        ),
        ConsentRecord(
            consent_id=f"{teen_id}-adult",
            teen_id=teen_id,
            kind="trusted_adult_authority",
            granted=True,
            granted_by="trusted_adult",
            recorded_at=NOW,
        ),
    ]


class IntakeAndGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = PersonalDataStore(Path(self.temp.name, "personal.sqlite"))
        self.request = SessionRequest(goal="find a hobby", requested_at=NOW)
        self.ledger = BudgetLedger(money_total_sgd=0, hours_per_week=3, tries_total=3)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def input_for(self, age: int, teen_id: str) -> SetupInput:
        return SetupInput(
            teen_id=teen_id,
            thread_id=f"thread-{teen_id}",
            declared_age=age,
            request=self.request,
            ledger=self.ledger,
            consents=consents(teen_id),
        )

    def test_age_boundary_stops_before_persistence(self) -> None:
        for age, referral in ((12, "trusted_adult"), (18, "general_activity_services")):
            result = setup(self.input_for(age, f"teen-{age}"), self.store)
            self.assertFalse(result.persisted)
            self.assertEqual(referral, result.intake.referral)
            with self.assertRaises(PersonalDataError):
                self.store.get_ledger(f"teen-{age}")

    def test_eligible_setup_and_skipped_cold_start(self) -> None:
        result = setup(self.input_for(13, "teen-13"), self.store)
        self.assertTrue(result.persisted)
        self.assertTrue(result.gate.passed)
        self.assertIsNone(self.store.planner_snapshot("teen-13")["preferences"].seeded_at)

    def test_missing_authority_blocks_setup(self) -> None:
        payload = self.input_for(15, "teen-missing")
        payload = payload.model_copy(update={"consents": payload.consents[:1]})
        result = setup(payload, self.store)
        self.assertFalse(result.persisted)
        self.assertIn("missing_trusted_adult_authority", result.gate.reason_codes)

    def test_g3_requires_matching_verdict_and_approvals(self) -> None:
        plan = Plan(
            plan_id="plan",
            items=[PlanItem(listing_id="paid", session_at=NOW, cost_sgd=Decimal(5))],
            total_cost_sgd=5,
            ledger_version=0,
        )
        record = listing_record("paid", cost="5")
        verdict = GuardianVerdict(
            verdict_id="verdict",
            plan_id="wrong",
            approved=True,
            reviewed_at=NOW,
        )
        gate = Validator().g3(plan, verdict, {"paid": record})
        self.assertFalse(gate.passed)
        self.assertEqual(["guardian_verdict_plan_mismatch"], gate.reason_codes)

    def test_gate_log_contains_shape_only(self) -> None:
        record = BookingRecord(
            booking_id="booking",
            plan_id="plan",
            listing_id="listing",
            guardian_verdict_id="verdict-secret",
            status="booked",
            ledger_transaction_id="transaction-secret",
            committed_sgd=0,
            created_at=NOW,
        )
        result = Validator().g4(
            record,
            evidence=CommitEvidence(
                transaction_ids=["transaction-secret"],
                ledger_version_before=0,
                ledger_version_after=1,
                transaction_rows=1,
            ),
        )
        serialized = result.model_dump_json()
        self.assertNotIn("verdict-secret", serialized)
        self.assertNotIn("transaction-secret", serialized)

    def test_g4_rejects_missing_transaction_evidence(self) -> None:
        record = BookingRecord(
            booking_id="booking",
            plan_id="plan",
            listing_id="listing",
            guardian_verdict_id="verdict",
            status="booked",
            ledger_transaction_id="expected-transaction",
            committed_sgd=0,
            created_at=NOW,
        )
        evidence = CommitEvidence(
            transaction_ids=["different-transaction"],
            ledger_version_before=4,
            ledger_version_after=5,
            transaction_rows=1,
        )
        result = Validator().g4(record, evidence=evidence)
        self.assertFalse(result.passed)
        self.assertEqual(["transaction_evidence_missing"], result.reason_codes)

    def test_permission_matrix_includes_intake_and_fails_closed(self) -> None:
        self.assertIn("intake", COMPONENT_PERMISSIONS)
        ToolGuard("planner").require("reads", "CKB")
        with self.assertRaises(ToolPermissionError):
            ToolGuard("planner").require("writes", "Personal Data")

    def test_setup_cannot_carry_trusted_adult_approvals(self) -> None:
        with self.assertRaises(ValueError):
            SetupInput(
                teen_id="teen",
                thread_id="thread",
                declared_age=15,
                request=self.request,
                ledger=self.ledger,
                consents=consents(),
                constraints={"attendance_approval_id": "self-issued"},
            )


if __name__ == "__main__":
    unittest.main()
