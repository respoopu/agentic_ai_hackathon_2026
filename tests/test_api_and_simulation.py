from __future__ import annotations

import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from sim.adversarial import run_adversarial_set
from sim.counterfactual import load_longitudinal_scenario
from sim.counterfactual import run as counterfactual
from sim.harness import load_profiles, run_eligible_profiles
from sim.report import rows
from src.api import ApiAuthorizationError, HobbiService, _source_status
from src.store.personal_data import AuthorizationError
from tests.helpers import NOW, listing_record
from tests.test_intake_and_gates import consents

GUARDIAN_TOKEN = "guardian-test-token-0000000000000000"
COMPLIANCE_TOKEN = "compliance-test-token-000000000000"


class ApiAndSimulationTests(unittest.TestCase):
    def test_compliance_source_check_honors_robots_and_explicit_missing(self) -> None:
        denied = MagicMock()
        denied.status = 200
        denied.read.return_value = b"User-agent: *\nDisallow: /private\n"
        denied.__enter__.return_value = denied
        with patch("src.api.urllib.request.urlopen", return_value=denied) as fetch:
            self.assertEqual(
                "transient", _source_status("https://onepa.gov.sg/private/listing")
            )
        self.assertEqual(1, fetch.call_count)

        robots_missing = urllib.error.HTTPError(
            "https://onepa.gov.sg/robots.txt", 404, "missing", {}, None
        )
        listing_missing = urllib.error.HTTPError(
            "https://onepa.gov.sg/listing", 410, "gone", {}, None
        )
        with patch(
            "src.api.urllib.request.urlopen",
            side_effect=[robots_missing, listing_missing],
        ):
            self.assertEqual("missing", _source_status("https://onepa.gov.sg/listing"))

    def test_empty_ckb_is_explicitly_not_ready_and_fails_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(
                temporary, guardian_token=GUARDIAN_TOKEN, seed_artifact=None
            )
            try:
                health = service.handle({"operation": "health"})
                self.assertFalse(health["ready_for_real_planning"])
                self.assertEqual(0, health["ckb_usable_real_records"])
                response = service.handle(
                    {
                        "operation": "intake_and_plan",
                        "setup": {
                            "teen_id": "empty-teen",
                            "thread_id": "empty-thread",
                            "declared_age": 15,
                            "request": {
                                "goal": "find something free",
                                "requested_at": NOW.isoformat(),
                            },
                            "ledger": {
                                "money_total_sgd": 0,
                                "hours_per_week": 2,
                                "tries_total": 2,
                            },
                            "consents": [
                                value.model_dump(mode="json")
                                for value in consents("empty-teen")
                            ],
                        },
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertFalse(response["ok"])
                self.assertEqual("no_viable_plan", response["state"]["outcome"])
                self.assertTrue(response["state"]["binding_constraint"])
                self.assertEqual(["trusted_adult"], response["notification_required"])
            finally:
                service.close()

    def test_health_ignores_fictional_and_retired_rows_for_real_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(temporary, seed_artifact=None)
            try:
                fictional = listing_record(
                    "fictional", verification="unverified", provider_type="private_unverified"
                )
                retired = listing_record("retired").model_copy(
                    update={"verification": "retired", "freshness_state": "dead"}
                )
                service.ckb.seed([fictional, retired])
                health = service.handle({"operation": "health"})
                self.assertFalse(health["ready_for_real_planning"])
                self.assertEqual(2, health["ckb_records"])
                self.assertEqual(1, health["ckb_fictional_records"])
                self.assertEqual(2, health["ckb_unusable_records"])
            finally:
                service.close()

    def test_health_accepts_sourced_unverified_real_row_for_guardian_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(temporary, seed_artifact=None)
            try:
                service.ckb.seed([listing_record("real-unverified", verification="unverified")])
                health = service.handle({"operation": "health"})
                self.assertTrue(health["ready_for_real_planning"])
                self.assertEqual(1, health["ckb_usable_real_records"])
                self.assertEqual(0, health["ckb_verified_real_records"])
                self.assertEqual(1, health["ckb_unverified_real_records"])
            finally:
                service.close()

    def test_service_health_and_full_intake_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HobbiService(
                temporary,
                guardian_token=GUARDIAN_TOKEN,
                compliance_token=COMPLIANCE_TOKEN,
                seed_artifact=None,
            )
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
                        },
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertTrue(response["ok"])
                self.assertEqual("escalated_to_adult", response["state"]["outcome"])
                initial_gates = [gate["gate"] for gate in response["state"]["gate_log"]]
                self.assertLess(initial_gates.index("G1"), initial_gates.index("G2"))
                plan = response["state"]["approved_plan"]
                approvals = {
                    item["listing_id"]: f"adult-provider-{item['listing_id']}"
                    for item in plan["items"]
                    if service.ckb.get(item["listing_id"]).verification != "verified"
                }
                approved = service.handle(
                    {
                        "operation": "guardian_approve",
                        "teen_id": "api-teen",
                        "plan_id": plan["plan_id"],
                        "provider_approval_ids": approvals,
                        "attendance_approval_id": "adult-attendance",
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertEqual("booked", approved["state"]["outcome"])
                self.assertEqual(
                    ["G2", "G3", "G4"],
                    [gate["gate"] for gate in approved["state"]["gate_log"]],
                )
                booking = approved["state"]["booking_records"][0]
                with self.assertRaises(ApiAuthorizationError):
                    service.handle(
                        {
                            "operation": "attendance",
                            "teen_id": "api-teen",
                            "event": {
                                "booking_id": booking["booking_id"],
                                "attended": True,
                                "occurred_at": NOW.isoformat(),
                            },
                        },
                        authorization="wrong-profile-token",
                    )
                attendance = service.handle(
                    {
                        "operation": "attendance",
                        "teen_id": "api-teen",
                        "event": {
                            "booking_id": booking["booking_id"],
                            "attended": True,
                            "occurred_at": NOW.isoformat(),
                        },
                    },
                    authorization=response["teen_access_token"],
                )
                self.assertTrue(attendance["ok"])
                with self.assertRaises(AuthorizationError):
                    service.handle(
                        {
                            "operation": "intake_and_plan",
                            "setup": {
                                "teen_id": "api-teen",
                                "thread_id": "replacement-thread",
                                "declared_age": 17,
                                "request": {
                                    "goal": "replace rules",
                                    "requested_at": NOW.isoformat(),
                                },
                                "ledger": {
                                    "money_total_sgd": 500,
                                    "hours_per_week": 10,
                                    "tries_total": 10,
                                },
                                "consents": [
                                    value.model_dump(mode="json")
                                    for value in consents("api-teen")
                                ],
                            },
                        },
                        authorization=GUARDIAN_TOKEN,
                    )
                self.assertEqual(
                    15, service.personal_data.profile_identity("api-teen")["declared_age"]
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
            service = HobbiService(
                temporary,
                guardian_token=GUARDIAN_TOKEN,
                compliance_token=COMPLIANCE_TOKEN,
                seed_artifact=None,
            )
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
                            "constraints": {"max_items": 2},
                        },
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                plan = response["state"]["approved_plan"]
                approved = service.handle(
                    {
                        "operation": "guardian_approve",
                        "teen_id": "cascade-teen",
                        "plan_id": plan["plan_id"],
                        "attendance_approval_id": "adult-attendance",
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertEqual("booked", approved["state"]["outcome"])
                with patch(
                    "src.api._source_status",
                    side_effect=lambda url: (
                        "missing" if "a-retire-target" in url else "alive"
                    ),
                ):
                    cascade = service.handle(
                        {"operation": "compliance_scan", "replan_flagged": True},
                        authorization=COMPLIANCE_TOKEN,
                    )
                self.assertEqual(
                    ["a-retire-target"], cascade["result"]["retired_listing_ids"]
                )
                replacement = cascade["replans"][0]["state"]
                self.assertEqual("escalated_to_adult", replacement["outcome"])
                self.assertEqual(
                    ["teen", "trusted_adult"],
                    cascade["replans"][0]["notification_required"],
                )
                replacement_plan = replacement["approved_plan"]
                replacement_booking = service.handle(
                    {
                        "operation": "guardian_approve",
                        "teen_id": "cascade-teen",
                        "plan_id": replacement_plan["plan_id"],
                        "attendance_approval_id": "replacement-attendance",
                    },
                    authorization=GUARDIAN_TOKEN,
                )
                self.assertEqual("booked", replacement_booking["state"]["outcome"])
                self.assertNotIn(
                    "a-retire-target", service.personal_data.live_listing_ids()
                )
            finally:
                service.close()

    def test_harness_and_counterfactual_have_explicit_denominators(self) -> None:
        result = run_eligible_profiles()
        self.assertEqual({"numerator": 4, "denominator": 4}, result["metrics"]["s0_viability"])
        comparison = counterfactual()
        first = comparison["first_attendance"]
        long = comparison["longitudinal"]
        self.assertTrue(first["measured"])
        self.assertEqual((4, 4), (first["hobbi"]["completed"], first["hobbi"]["denominator"]))
        self.assertEqual((3, 4), (first["static"]["completed"], first["static"]["denominator"]))
        self.assertEqual(25.0, first["completion_rate_delta_percentage_points"])
        self.assertTrue(long["measured"])
        self.assertEqual({"numerator": 2, "denominator": 12}, long["hold_rate"])
        self.assertEqual(1.0, long["adaptation_latency"]["mean_cycles"])
        self.assertEqual(
            {"none", "replan", "try_to_commit", "hold_this_week"},
            {cycle["observer_action"] for cycle in long["hobbi_cycles"]},
        )

    def test_counterfactual_fixture_contains_inputs_not_authored_results(self) -> None:
        scenario = load_longitudinal_scenario()
        forbidden = {"attended", "hobbi_action", "static_vibe", "selected_listing_id"}
        self.assertTrue(scenario["cycles"])
        self.assertTrue(
            all(not forbidden.intersection(cycle) for cycle in scenario["cycles"])
        )

    def test_executable_adversarial_set_has_zero_violations(self) -> None:
        result = run_adversarial_set()
        self.assertEqual(8, len(result["cases"]))
        self.assertTrue(all(case["passed"] for case in result["cases"]))
        self.assertEqual(
            {"measured": True, "numerator": 0, "denominator": 8},
            result["constraint_violations"],
        )

    def test_static_arm_is_immutable_while_hobbi_replans_through_real_gates(self) -> None:
        long = counterfactual()["longitudinal"]
        self.assertEqual(
            1, len({cycle["listing_id"] for cycle in long["static_cycles"]})
        )
        self.assertGreater(
            len({cycle["listing_id"] for cycle in long["hobbi_cycles"]}), 1
        )
        self.assertTrue(
            all(
                cycle["gate_sequence"] == ["G1", "G2", "G3", "G4"]
                for cycle in long["hobbi_cycles"]
            )
        )
        self.assertEqual(
            {"numerator": 8, "denominator": 12}, long["adherence"]["hobbi"]
        )
        self.assertEqual(
            {"numerator": 2, "denominator": 12}, long["adherence"]["static"]
        )

    def test_report_emits_b1_through_b15(self) -> None:
        names = [name for name, _ in rows()]
        for number in range(1, 16):
            self.assertTrue(any(name.startswith(f"B{number} ") for name in names), number)


if __name__ == "__main__":
    unittest.main()
