from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from sim.counterfactual import run as counterfactual
from sim.harness import load_profiles, run_eligible_profiles
from sim.report import rows
from src.api import HobbiService
from tests.helpers import NOW, listing_record
from tests.test_intake_and_gates import consents


class ApiAndSimulationTests(unittest.TestCase):
    def test_service_health_and_full_intake_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(temporary)
            try:
                service.ckb.seed([listing_record("api-free")])
                health = service.handle({"operation": "health"})
                self.assertTrue(health["ok"])
                response = service.handle(
                    {
                        "operation": "intake_and_plan",
                        "setup": {
                            "teen_id": "api-teen",
                            "thread_id": "api-thread",
                            "declared_age": 15,
                            "request": {"goal": "find something free", "requested_at": NOW.isoformat()},
                            "ledger": {
                                "money_total_sgd": 0,
                                "hours_per_week": 2,
                                "tries_total": 2,
                            },
                            "consents": [value.model_dump(mode="json") for value in consents("api-teen")],
                            "constraints": {
                                "attendance_approval_id": "adult-attendance",
                                "provider_approval_ids": {
                                    "DISCOVERY-activesg-yuhua-secondary-field": "adult-provider"
                                },
                            },
                        },
                    }
                )
                self.assertTrue(response["ok"])
                self.assertEqual("booked", response["state"]["outcome"])
                self.assertEqual(
                    ["I0", "G2", "G1", "G1", "G2", "G3", "G4", "G4"],
                    [gate["gate"] for gate in response["state"]["gate_log"]],
                )
            finally:
                service.close()

    def test_evaluation_profiles_are_twelve_and_age_eligible(self) -> None:
        profiles = load_profiles()
        self.assertEqual(12, len(profiles))
        self.assertEqual({13, 14, 15, 16, 17}, {profile["age"] for profile in profiles})
        self.assertTrue(any(not profile["cold_start_vibes"] for profile in profiles))

    def test_compliance_retirement_replans_through_fresh_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(temporary)
            try:
                service.ckb.seed(
                    [
                        listing_record("a-retire-target"),
                        listing_record("b-kept-booking"),
                        listing_record("c-replacement"),
                    ]
                )
                response = service.handle(
                    {
                        "operation": "intake_and_plan",
                        "setup": {
                            "teen_id": "cascade-teen",
                            "thread_id": "cascade-thread",
                            "declared_age": 15,
                            "request": {"goal": "find something free", "requested_at": NOW.isoformat()},
                            "ledger": {
                                "money_total_sgd": 0,
                                "hours_per_week": 6,
                                "tries_total": 6,
                            },
                            "consents": [
                                value.model_dump(mode="json") for value in consents("cascade-teen")
                            ],
                            "constraints": {
                                "max_items": 2,
                                "attendance_approval_id": "adult-attendance",
                                "provider_approval_ids": {
                                    "DISCOVERY-activesg-yuhua-secondary-field": "adult-provider"
                                },
                            },
                        },
                    }
                )
                self.assertEqual("booked", response["state"]["outcome"])
                with patch(
                    "src.api._source_alive",
                    side_effect=lambda url: "a-retire-target" not in url,
                ):
                    cascade = service.handle(
                        {"operation": "compliance_scan", "replan_flagged": True}
                    )
                self.assertEqual(
                    ["a-retire-target"], cascade["result"]["retired_listing_ids"]
                )
                self.assertEqual("booked", cascade["replans"][0]["state"]["outcome"])
                self.assertEqual(
                    ["retire", "Planner", "G2", "Guardian", "G3", "Broker"],
                    cascade["replans"][0]["path"],
                )
                self.assertEqual(["teen", "parent"], cascade["replans"][0]["notified"])
            finally:
                service.close()

    def test_harness_and_counterfactual_have_explicit_denominators(self) -> None:
        result = run_eligible_profiles()
        self.assertEqual({"numerator": 4, "denominator": 4}, result["metrics"]["s0_viability"])
        comparison = counterfactual()
        self.assertEqual(4, comparison["first_attendance"]["hobbi"]["denominator"])
        self.assertEqual(2, comparison["longitudinal"]["holds"])
        self.assertEqual(1, comparison["longitudinal"]["adaptation_latency_cycles"])

    def test_report_emits_b1_through_b15(self) -> None:
        names = [name for name, _ in rows()]
        for number in range(1, 16):
            self.assertTrue(any(name.startswith(f"B{number} ") for name in names), number)


if __name__ == "__main__":
    unittest.main()
