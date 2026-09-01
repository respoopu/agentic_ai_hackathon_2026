from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.schema.events import AttendanceEvent, DebriefRecord
from src.schema.plan import (
    BudgetLedger,
    ConsentRecord,
    GuardianVerdict,
    Plan,
    PlanItem,
    SessionRequest,
)
from src.schema.preferences import PreferenceModel
from src.store.personal_data import (
    AuthorizationError,
    PersonalDataError,
    PersonalDataStore,
    ReplayConflict,
    StaleLedgerVersion,
)

NOW = datetime(2026, 9, 1, tzinfo=UTC)


class PersonalDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name, "personal.sqlite")
        self.store = PersonalDataStore(self.path)
        self.request = SessionRequest(goal="try something creative", requested_at=NOW)
        self.ledger = BudgetLedger(
            money_total_sgd=Decimal(20),
            hours_per_week=3,
            tries_total=2,
        )
        self.preferences = PreferenceModel.neutral(NOW)
        self.consent = ConsentRecord(
            consent_id="consent-1",
            teen_id="teen-1",
            kind="personal_data",
            granted=True,
            granted_by="teen",
            recorded_at=NOW,
        )
        self.store.setup_profile(
            teen_id="teen-1",
            thread_id="thread-1",
            declared_age=15,
            request=self.request,
            ledger=self.ledger,
            preferences=self.preferences,
            consents=[self.consent],
        )
        self.item = PlanItem(
            listing_id="listing-1", session_at=NOW, cost_sgd=Decimal(8), duration_hours=1
        )
        self.plan = Plan(
            plan_id="plan-1", items=[self.item], total_cost_sgd=Decimal(8), ledger_version=0
        )
        self.verdict = GuardianVerdict(
            verdict_id="verdict-1",
            plan_id="plan-1",
            approved=True,
            attendance_approval_id="attendance-1",
            spend_approval_id="spend-1",
            reviewed_at=NOW,
        )
        self.store.save_plan("teen-1", self.plan)
        self.store.save_guardian_verdict("teen-1", self.verdict)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_ineligible_profile_is_never_persisted(self) -> None:
        with self.assertRaises(PersonalDataError):
            self.store.setup_profile(
                teen_id="teen-2",
                thread_id="thread-2",
                declared_age=12,
                request=self.request,
                ledger=self.ledger,
                preferences=self.preferences,
                consents=[],
            )

    def test_booking_replay_is_exactly_once_and_survives_reopen(self) -> None:
        first, replayed = self.store.commit_booking(
            teen_id="teen-1", plan=self.plan, item=self.item, verdict=self.verdict
        )
        second, replayed_second = self.store.commit_booking(
            teen_id="teen-1", plan=self.plan, item=self.item, verdict=self.verdict
        )
        self.assertFalse(replayed)
        self.assertTrue(replayed_second)
        self.assertEqual(first, second)
        self.assertEqual(Decimal(8), self.store.get_ledger("teen-1").money_committed_sgd)
        reopened = PersonalDataStore(self.path)
        self.assertEqual(1, reopened.get_ledger("teen-1").tries_used)
        reopened.close()

    def test_stale_ledger_version_stops_second_commitment(self) -> None:
        self.store.commit_booking(
            teen_id="teen-1", plan=self.plan, item=self.item, verdict=self.verdict
        )
        second_item = PlanItem(listing_id="listing-2", session_at=NOW, cost_sgd=1)
        stale_plan = Plan(
            plan_id="plan-2", items=[second_item], total_cost_sgd=1, ledger_version=0
        )
        stale_verdict = self.verdict.model_copy(
            update={"verdict_id": "verdict-2", "plan_id": "plan-2"}
        )
        self.store.save_plan("teen-1", stale_plan)
        self.store.save_guardian_verdict("teen-1", stale_verdict)
        with self.assertRaises(StaleLedgerVersion):
            self.store.commit_booking(
                teen_id="teen-1", plan=stale_plan, item=second_item, verdict=stale_verdict
            )

    def test_mismatched_verdict_cannot_authorize_booking(self) -> None:
        bad = self.verdict.model_copy(update={"plan_id": "another-plan"})
        with self.assertRaises(AuthorizationError):
            self.store.commit_booking(
                teen_id="teen-1", plan=self.plan, item=self.item, verdict=bad
            )

    def test_attendance_reconciles_once(self) -> None:
        booking, _ = self.store.commit_booking(
            teen_id="teen-1", plan=self.plan, item=self.item, verdict=self.verdict
        )
        event = AttendanceEvent(booking_id=booking.booking_id, attended=False, occurred_at=NOW)
        debrief = DebriefRecord(booking_id=booking.booking_id, text="too far", submitted_at=NOW)
        self.assertTrue(
            self.store.record_outcome(
                teen_id="teen-1",
                event=event,
                preferences=self.preferences,
                debrief=debrief,
            )
        )
        self.assertFalse(
            self.store.record_outcome(
                teen_id="teen-1",
                event=event,
                preferences=self.preferences,
                debrief=debrief,
            )
        )
        ledger = self.store.get_ledger("teen-1")
        self.assertEqual(Decimal(0), ledger.money_committed_sgd)
        self.assertEqual(Decimal(8), ledger.money_spent_sgd)
        self.assertEqual(1, ledger.tries_abandoned)

    def test_concurrent_duplicate_commit_is_serialized(self) -> None:
        def commit() -> tuple[str, bool]:
            store = PersonalDataStore(self.path)
            try:
                record, replayed = store.commit_booking(
                    teen_id="teen-1", plan=self.plan, item=self.item, verdict=self.verdict
                )
                return record.booking_id, replayed
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: commit(), range(2)))
        self.assertEqual(1, sum(1 for _, replayed in results if not replayed))
        self.assertEqual(1, sum(1 for _, replayed in results if replayed))
        self.assertEqual(1, self.store.get_ledger("teen-1").tries_used)

    def test_plan_ids_cannot_cross_profile_boundaries(self) -> None:
        second_consent = self.consent.model_copy(
            update={"consent_id": "consent-2", "teen_id": "teen-2"}
        )
        self.store.setup_profile(
            teen_id="teen-2",
            thread_id="thread-2",
            declared_age=15,
            request=self.request,
            ledger=self.ledger,
            preferences=self.preferences,
            consents=[second_consent],
        )
        with self.assertRaises(ReplayConflict):
            self.store.save_plan("teen-2", self.plan)


if __name__ == "__main__":
    unittest.main()
