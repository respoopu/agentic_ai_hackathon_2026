from __future__ import annotations

import tempfile
import unittest

from scripts.export_frontend_contract import build_contract
from src.api import HobbiService
from src.schema.api import (
    AdaptationView,
    ApprovalRequirements,
    BookingView,
    PlanView,
)
from tests.helpers import NOW, listing_record
from tests.test_intake_and_gates import consents

GUARDIAN_TOKEN = "guardian-test-token-0000000000000000"


class FrontendContractTests(unittest.TestCase):
    def test_contract_exposes_the_complete_demo_journey(self) -> None:
        contract = build_contract()
        self.assertEqual("3.1.0", contract["openapi"])
        self.assertEqual(
            {
                "/api/health",
                "/api/plan",
                "/api/approve",
                "/api/attendance",
                "/api/next-plan",
            },
            set(contract["paths"]),
        )
        self.assertIn("ActivityPlanView", contract["components"]["schemas"])
        self.assertIn("ShortlistStepResponse", contract["components"]["schemas"])

    def test_shortlist_options_are_independently_bookable_plans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(
                temporary,
                guardian_token=GUARDIAN_TOKEN,
                seed_artifact=None,
            )
            try:
                service.ckb.seed(
                    [
                        listing_record("option-1"),
                        listing_record("option-2"),
                        listing_record("option-3"),
                        listing_record("option-4"),
                        listing_record("duplicate-venue").model_copy(
                            update={"title": "Activity option-1 at another venue"}
                        ),
                    ]
                )
                teen_id = "shortlist-teen"
                response = service.handle(
                    {
                        "operation": "intake_and_plan",
                        "shortlist_size": 4,
                        "setup": {
                            "teen_id": teen_id,
                            "thread_id": "shortlist-thread",
                            "declared_age": 15,
                            "request": {
                                "goal": "show me a few choices",
                                "requested_at": NOW.isoformat(),
                            },
                            "ledger": {
                                "money_total_sgd": 0,
                                "hours_per_week": 2,
                                "tries_total": 3,
                            },
                            "constraints": {"max_items": 1},
                            "consents": [
                                value.model_dump(mode="json")
                                for value in consents(teen_id)
                            ],
                        },
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                shortlist = response["shortlist"]
                self.assertEqual(4, len(shortlist))
                listing_ids = [
                    option["plan_view"]["activities"][0]["listing_id"]
                    for option in shortlist
                ]
                self.assertEqual(4, len(set(listing_ids)))
                self.assertEqual(
                    1, len({"option-1", "duplicate-venue"}.intersection(listing_ids))
                )
                self.assertTrue(
                    all(len(option["plan_view"]["activities"]) == 1 for option in shortlist)
                )

                chosen = shortlist[2]
                approved = service.handle(
                    {
                        "operation": "guardian_approve",
                        "teen_id": teen_id,
                        "plan_id": chosen["plan_view"]["plan_id"],
                        "attendance_approval_id": "shortlist-attendance",
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertEqual(1, len(approved["bookings"]))
                self.assertEqual(
                    listing_ids[2], approved["bookings"][0]["activity"]["listing_id"]
                )
            finally:
                service.close()

    def test_display_contract_drives_booking_and_adapted_next_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(
                temporary,
                guardian_token=GUARDIAN_TOKEN,
                seed_artifact=None,
            )
            try:
                service.ckb.seed(
                    [
                        listing_record("a-chill", vibes=["chill"]),
                        listing_record("b-sport", vibes=["sporty"]),
                    ]
                )
                teen_id = "frontend-teen"
                initial = service.handle(
                    {
                        "operation": "intake_and_plan",
                        "setup": {
                            "teen_id": teen_id,
                            "thread_id": "frontend-thread",
                            "declared_age": 15,
                            "request": {
                                "goal": "find a low-pressure first try",
                                "requested_at": NOW.isoformat(),
                            },
                            "ledger": {
                                "money_total_sgd": 0,
                                "hours_per_week": 2,
                                "tries_total": 2,
                            },
                            "constraints": {"max_items": 1},
                            "consents": [
                                value.model_dump(mode="json")
                                for value in consents(teen_id)
                            ],
                        },
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                plan = PlanView.model_validate(initial["plan_view"])
                requirements = ApprovalRequirements.model_validate(
                    initial["approval_requirements"]
                )
                self.assertEqual("Activity a-chill", plan.activities[0].title)
                self.assertEqual("a-chill", plan.activities[0].listing_id)
                self.assertEqual([], requirements.provider_listing_ids)

                approved = service.handle(
                    {
                        "operation": "guardian_approve",
                        "teen_id": teen_id,
                        "plan_id": plan.plan_id,
                        "attendance_approval_id": "frontend-attendance-approval",
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                booking = BookingView.model_validate(approved["bookings"][0])
                self.assertTrue(booking.sandbox)
                self.assertEqual("Community Hall", booking.preparation.meet)

                attendance = service.handle(
                    {
                        "operation": "attendance",
                        "teen_id": teen_id,
                        "event": {
                            "booking_id": booking.booking_id,
                            "attended": False,
                            "occurred_at": NOW.isoformat(),
                        },
                        "debrief": {
                            "booking_id": booking.booking_id,
                            "text": "It was not my thing.",
                            "channel": "in_app",
                            "submitted_at": NOW.isoformat(),
                        },
                    },
                    authorization=initial["teen_access_token"],
                )
                adaptation = AdaptationView.model_validate(attendance["adaptation"])
                self.assertEqual(1, adaptation.dislikes_recorded)

                next_response = service.handle(
                    {"operation": "next_plan", "teen_id": teen_id},
                    authorization=initial["teen_access_token"],
                )
                next_plan = PlanView.model_validate(next_response["plan_view"])
                self.assertEqual("b-sport", next_plan.activities[0].listing_id)
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
