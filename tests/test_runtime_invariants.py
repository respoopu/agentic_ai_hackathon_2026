from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

from src.agents.guardian import Guardian
from src.agents.planner import Planner
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, preference_seeds, setup
from src.runtime.structured import invoke_structured
from src.schema.events import BookingRecord, DebriefSubmission
from src.schema.listing import PeerCohort
from src.schema.plan import BudgetLedger, IntakeResult, Plan, PlanItem, SessionRequest
from src.schema.preferences import DislikeSignal, PreferenceModel
from src.schema.state import HobbiState
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator
from tests.helpers import NOW, hydrated, listing_record
from tests.test_intake_and_gates import consents


class RuntimeInvariantTests(unittest.TestCase):
    def test_optional_bedrock_seam_sends_canonical_json_and_validates_output(self) -> None:
        typed_model = Mock()
        typed_model.invoke.return_value = {
            "eligible": True,
            "reason": "eligible",
            "referral": None,
        }
        model = Mock()
        model.with_structured_output.return_value = typed_model
        with patch("src.runtime.structured.create_bedrock_model", return_value=model):
            result = invoke_structured(
                "planner",
                {"goal": "try art", "budget": 0},
                IntakeResult,
            )
        self.assertTrue(result.eligible)
        user_message = typed_model.invoke.call_args.args[0][1][1]
        self.assertIn('{"budget":0,"goal":"try art"}', user_message)
        self.assertNotIn("'goal'", user_message)

    def test_a1_a2_unverified_and_budget_are_hard_gates(self) -> None:
        private = listing_record(
            "private", verification="unverified", provider_type="private_unverified"
        )
        plan = Plan(
            plan_id="plan",
            items=[PlanItem(listing_id="private", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
        )
        verdict = Guardian().review(
            plan=plan, listings={"private": private}, attendance_approval_id="attendance"
        )
        self.assertFalse(verdict.approved)
        paid = listing_record("paid", cost="10")
        paid_plan = Plan(
            plan_id="paid-plan",
            items=[PlanItem(listing_id="paid", session_at=NOW, cost_sgd=10)],
            total_cost_sgd=10,
            ledger_version=0,
        )
        gate = Validator().g2(
            paid_plan,
            BudgetLedger(money_total_sgd=5, hours_per_week=2, tries_total=2),
            {"paid": paid},
        )
        self.assertIn("budget_exceeded", gate.reason_codes)

    def test_a3_a9_a10_zero_budget_membership_survives_preferences(self) -> None:
        catalogue = [
            hydrated(listing_record("sport", vibes=["sporty"])),
            hydrated(listing_record("chill", vibes=["chill"])),
        ]
        ledger = BudgetLedger(money_total_sgd=0, hours_per_week=3, tries_total=3)
        planner = Planner()
        neutral = PreferenceModel.neutral(NOW)
        seeded = preference_seeds(["sporty"], NOW)
        disliked = neutral.model_copy(
            update={
                "dislikes": [
                    DislikeSignal(
                        axis="activity_fit",
                        listing_id="sport",
                        attribution="activity",
                        strength=1,
                        recorded_at=NOW,
                    )
                ]
            }
        )
        counts = []
        for preferences in (neutral, seeded, disliked):
            result = planner.create_plan(
                declared_age=15,
                request=SessionRequest(goal="surprise me", requested_at=NOW),
                ledger=ledger,
                preferences=preferences,
                listings=catalogue,
            )
            self.assertIsNotNone(result.plan)
            counts.append(result.candidate_count)
        self.assertEqual([2, 2, 2], counts)

    def test_plan_identity_is_profile_scoped(self) -> None:
        kwargs = {
            "declared_age": 15,
            "request": SessionRequest(goal="same request", requested_at=NOW),
            "ledger": BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=2),
            "preferences": PreferenceModel.neutral(NOW),
            "listings": [hydrated(listing_record("same-listing"))],
        }
        first = Planner().create_plan(planning_key="teen-one", **kwargs).plan
        second = Planner().create_plan(planning_key="teen-two", **kwargs).plan
        self.assertNotEqual(first.plan_id, second.plan_id)

    def test_a4_parental_age_and_travel_filters(self) -> None:
        allowed = hydrated(listing_record("allowed"), travel=10)
        too_far = hydrated(listing_record("far"), travel=50)
        private = hydrated(
            listing_record(
                "private", verification="unverified", provider_type="private_unverified"
            ),
            travel=10,
        )
        result = Planner().create_plan(
            declared_age=15,
            request=SessionRequest(goal="nearby", requested_at=NOW),
            ledger=BudgetLedger(money_total_sgd=0, hours_per_week=3, tries_total=3),
            preferences=PreferenceModel.neutral(NOW),
            listings=[allowed, too_far, private],
            parental_rules=["no_private_unverified"],
            constraints={"max_travel_min": 15},
        )
        self.assertEqual(["allowed"], [item.listing_id for item in result.plan.items])

    def test_a5_non_replannable_approval_checkpoint_does_not_fake_a_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            personal = PersonalDataStore(Path(temporary, "personal.sqlite"))
            ckb = KnowledgeBase(Path(temporary, "ckb.sqlite"))
            try:
                request = SessionRequest(goal="free", requested_at=NOW)
                ledger = BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=3)
                setup(
                    SetupInput(
                        teen_id="teen",
                        thread_id="thread",
                        declared_age=15,
                        request=request,
                        ledger=ledger,
                        consents=consents(),
                    ),
                    personal,
                )
                ckb.seed([listing_record("free")])
                runtime = HobbiRuntime(personal_data=personal, ckb=ckb, in_memory=True)
                state: HobbiState = {
                    "teen_id": "teen",
                    "thread_id": "thread",
                    "declared_age": 15,
                    "intake_result": IntakeResult(eligible=True, reason="eligible"),
                    "request": request,
                    "ledger": ledger,
                    "candidate_plan": None,
                    "approved_plan": None,
                    "guardian_verdict": None,
                    "rejection_history": [],
                    "binding_constraint": None,
                    "resume_approved_plan": False,
                    "booking_records": [],
                    "replan_count": 0,
                    "discovery_rounds": 0,
                    "guardian_rejects": 0,
                    "gate_log": [],
                    "token_usage": [],
                    "unavailable_listing_ids": [],
                    "outcome": None,
                }
                final = runtime.invoke(state)
                runtime.close()
                self.assertEqual("escalated_to_adult", final["outcome"])
                self.assertEqual(1, final["guardian_rejects"])
                self.assertEqual(0, final["replan_count"])
                self.assertIn("attendance_approval_required", final["rejection_history"])
            finally:
                ckb.close()
                personal.close()

    def test_a6_discovery_payload_rejects_personal_data(self) -> None:
        payload = {
            "plan_id": "plan",
            "items": [{"listing_id": "one", "session_at": NOW, "cost_sgd": 0}],
            "total_cost_sgd": 0,
            "ledger_version": 0,
            "teen_id": "private",
        }
        result = Validator().g1_plan(payload)
        self.assertFalse(result.passed)
        self.assertIn("personal_data_in_discovery_payload", result.reason_codes)

    def test_a7_a8_authorization_and_audio_are_structural(self) -> None:
        with self.assertRaises(ValidationError):
            BookingRecord.model_validate(
                {
                    "booking_id": "booking",
                    "plan_id": "plan",
                    "listing_id": "listing",
                    "status": "booked",
                    "ledger_transaction_id": "tx",
                    "committed_sgd": 0,
                    "created_at": NOW,
                }
            )
        with self.assertRaises(ValidationError):
            DebriefSubmission.model_validate(
                {
                    "booking_id": "booking",
                    "text": "audio attached",
                    "channel": "in_app",
                    "submitted_at": NOW,
                    "audio": "bytes",
                }
            )

    def test_a11_age_matrix(self) -> None:
        validator = Validator()
        for age, expected in ((11, False), (12, False), (13, True), (17, True), (18, False), (19, False)):
            intake, _ = validator.i0(age, consents())
            self.assertEqual(expected, intake.eligible, age)

    def test_a12_peer_cohort_has_no_identity_and_never_filters(self) -> None:
        with self.assertRaises(ValidationError):
            PeerCohort.model_validate(
                {"same_age_band": "few", "same_area": True, "suppressed": True, "school": "x"}
            )
        base = hydrated(listing_record("base"))
        peer = base.model_copy(
            update={
                "peer_cohort": PeerCohort(
                    same_age_band="many", same_area=True, suppressed=False
                )
            }
        )
        kwargs = {
            "declared_age": 15,
            "request": SessionRequest(goal="social", requested_at=NOW),
            "ledger": BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=2),
            "preferences": PreferenceModel.neutral(NOW),
        }
        without = Planner().create_plan(listings=[base], **kwargs)
        with_peer = Planner().create_plan(listings=[peer], **kwargs)
        self.assertEqual(without.candidate_count, with_peer.candidate_count)


if __name__ == "__main__":
    unittest.main()
