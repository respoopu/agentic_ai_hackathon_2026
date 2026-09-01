from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from src.agents.broker import Broker
from src.agents.compliance import Compliance
from src.agents.discovery import Discovery
from src.agents.guardian import Guardian
from src.agents.observer import Observer
from src.agents.planner import Planner
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, setup
from src.schema.events import AttendanceEvent, DebriefSubmission
from src.schema.listing import PeerCohort
from src.schema.plan import BudgetLedger, IntakeResult, Plan, PlanItem, SessionRequest
from src.schema.preferences import DislikeSignal, PreferenceModel
from src.schema.state import HobbiState
from src.store.personal_data import PersonalDataStore
from tests.helpers import NOW, hydrated, listing_record
from tests.test_intake_and_gates import consents


class AgentAndGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.personal = PersonalDataStore(Path(self.temp.name, "personal.sqlite"))
        self.ckb = KnowledgeBase(Path(self.temp.name, "ckb.sqlite"))
        self.request = SessionRequest(goal="try a free creative activity", requested_at=NOW)

    def tearDown(self) -> None:
        self.ckb.close()
        self.personal.close()
        self.temp.cleanup()

    def setup_teen(self, *, tries: int = 4, constraints: dict | None = None) -> BudgetLedger:
        ledger = BudgetLedger(money_total_sgd=20, hours_per_week=5, tries_total=tries)
        result = setup(
            SetupInput(
                teen_id="teen",
                thread_id="thread",
                declared_age=15,
                request=self.request,
                ledger=ledger,
                consents=consents(),
                constraints=constraints or {},
            ),
            self.personal,
        )
        self.assertTrue(result.persisted)
        return ledger

    def test_planner_supports_zero_budget_and_skipped_seed(self) -> None:
        ledger = BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=2)
        result = Planner().create_plan(
            declared_age=15,
            request=self.request,
            ledger=ledger,
            preferences=PreferenceModel.neutral(NOW),
            listings=[hydrated(listing_record("free"))],
        )
        self.assertIsNotNone(result.plan)
        self.assertEqual(Decimal(0), result.plan.total_cost_sgd)

    def test_peer_cohort_is_a_ranking_only_tiebreak(self) -> None:
        without_peer = hydrated(listing_record("a-without-peer"))
        with_peer = hydrated(listing_record("z-with-peer")).model_copy(
            update={
                "peer_cohort": PeerCohort(
                    same_age_band="many", same_area=True, suppressed=False
                )
            }
        )
        result = Planner().create_plan(
            declared_age=15,
            request=self.request,
            ledger=BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=1),
            preferences=PreferenceModel.neutral(NOW),
            listings=[without_peer, with_peer],
        )
        self.assertEqual("z-with-peer", result.plan.items[0].listing_id)

    def test_instance_dislike_downranks_the_provider(self) -> None:
        disliked_provider = hydrated(listing_record("a-bad-provider")).model_copy(
            update={"provider": "Provider to avoid"}
        )
        alternative = hydrated(listing_record("z-alternative")).model_copy(
            update={"provider": "Different provider"}
        )
        preferences = PreferenceModel.neutral(NOW).model_copy(
            update={
                "dislikes": [
                    DislikeSignal(
                        axis="activity_fit",
                        listing_id="prior-instance",
                        provider="Provider to avoid",
                        attribution="instance",
                        strength=0.8,
                        recorded_at=NOW,
                    )
                ]
            }
        )
        result = Planner().create_plan(
            declared_age=15,
            request=self.request,
            ledger=BudgetLedger(money_total_sgd=0, hours_per_week=2, tries_total=1),
            preferences=preferences,
            listings=[disliked_provider, alternative],
        )
        self.assertEqual("z-alternative", result.plan.items[0].listing_id)

    def test_unverified_provider_requires_distinct_approval(self) -> None:
        record = listing_record(
            "private", verification="unverified", provider_type="private_unverified"
        )
        plan = Plan(
            plan_id="plan",
            items=[PlanItem(listing_id="private", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
        )
        rejected = Guardian().review(
            plan=plan,
            listings={"private": record},
            attendance_approval_id="attendance",
        )
        self.assertFalse(rejected.approved)
        approved = Guardian().review(
            plan=plan,
            listings={"private": record},
            provider_approval_ids={"private": "provider-approval"},
            attendance_approval_id="attendance",
        )
        self.assertTrue(approved.approved)

    def test_discovery_cached_replay_is_typed_and_idempotent(self) -> None:
        plan = Plan(
            plan_id="thin",
            items=[PlanItem(listing_id="wanted", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
            thin=True,
            binding_constraint="limited_supply",
        )
        path = Path(__file__).resolve().parents[1] / "data" / "discovery_replay.json"
        first = Discovery().cached_replay(plan, path, self.ckb)
        second = Discovery().cached_replay(plan, path, self.ckb)
        self.assertEqual("cached_replay", first.mode)
        self.assertEqual(1, first.inserted)
        self.assertEqual(0, second.inserted)
        self.assertEqual("unverified", first.records[0].verification)

    def test_discovery_live_path_enforces_whitelist(self) -> None:
        plan = Plan(
            plan_id="thin-live",
            items=[PlanItem(listing_id="wanted", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
        )
        with self.assertRaises(PermissionError):
            Discovery().live(
                plan,
                ["https://evil.example/activity"],
                self.ckb,
                lambda _: listing_record("never"),
            )
        result = Discovery().live(
            plan,
            ["https://www.onepa.gov.sg/activity"],
            self.ckb,
            lambda _: listing_record("live-record"),
        )
        self.assertEqual("live", result.mode)
        self.assertEqual(1, result.inserted)

    def test_compliance_retires_and_flags_without_calling_pipeline(self) -> None:
        self.setup_teen()
        record = listing_record("retire-me")
        self.ckb.seed([record])
        plan = Plan(
            plan_id="live-plan",
            items=[PlanItem(listing_id="retire-me", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
        )
        self.personal.save_plan("teen", plan)
        result = Compliance().scan(
            ckb=self.ckb,
            personal_data=self.personal,
            source_status=lambda _: "missing",
            now=NOW,
        )
        self.assertEqual(["retire-me"], result.retired_listing_ids)
        self.assertEqual([{"plan_id": "live-plan", "teen_id": "teen"}], result.flagged_plans)
        self.assertEqual("retired", self.ckb.get("retire-me").verification)

    def test_compliance_transient_failure_marks_stale_without_retiring(self) -> None:
        self.setup_teen()
        self.ckb.seed([listing_record("temporarily-unreachable")])
        result = Compliance().scan(
            ckb=self.ckb,
            personal_data=self.personal,
            source_status=lambda _: "transient",
            now=NOW + timedelta(days=1),
        )
        self.assertEqual([], result.retired_listing_ids)
        self.assertEqual(["temporarily-unreachable"], result.stale_listing_ids)
        stored = self.ckb.get("temporarily-unreachable")
        self.assertEqual("verified", stored.verification)
        self.assertEqual("stale", stored.freshness_state)
        self.assertEqual(NOW, stored.last_seen_at)

    def test_broker_commits_multi_item_plan_once(self) -> None:
        self.setup_teen()
        first = listing_record("first", cost="3")
        second = listing_record("second", cost="4")
        self.ckb.seed([first, second])
        plan = Plan(
            plan_id="multi",
            items=[
                PlanItem(listing_id="first", session_at=NOW, cost_sgd=3),
                PlanItem(listing_id="second", session_at=NOW, cost_sgd=4),
            ],
            total_cost_sgd=7,
            ledger_version=0,
        )
        verdict = Guardian().review(
            plan=plan,
            listings={"first": first, "second": second},
            attendance_approval_id="attendance",
            spend_approval_id="spend",
        )
        broker = Broker()
        first_result = broker.book(
            teen_id="teen",
            plan=plan,
            verdict=verdict,
            listings={"first": first, "second": second},
            store=self.personal,
        )
        replay = broker.book(
            teen_id="teen",
            plan=plan,
            verdict=verdict,
            listings={"first": first, "second": second},
            store=self.personal,
        )
        self.assertEqual(2, len(first_result.records))
        self.assertTrue(replay.replayed)
        ledger = self.personal.get_ledger("teen")
        self.assertEqual(Decimal(7), ledger.money_committed_sgd)
        self.assertEqual(2, ledger.tries_used)
        self.assertEqual(1, ledger.version)
        self.assertEqual({"first", "second"}, self.personal.live_listing_ids())

    def test_observer_second_no_show_replans(self) -> None:
        self.setup_teen()
        record = listing_record("free")
        self.ckb.seed([record])
        plan = Plan(
            plan_id="single",
            items=[PlanItem(listing_id="free", session_at=NOW, cost_sgd=0)],
            total_cost_sgd=0,
            ledger_version=0,
        )
        verdict = Guardian().review(
            plan=plan,
            listings={"free": record},
            attendance_approval_id="attendance",
        )
        booking = Broker().book(
            teen_id="teen",
            plan=plan,
            verdict=verdict,
            listings={"free": record},
            store=self.personal,
        ).records[0]
        prior = AttendanceEvent(
            booking_id="prior-booking", attended=False, occurred_at=NOW - timedelta(days=7)
        )
        preferences = PreferenceModel.neutral(NOW).model_copy(update={"attendance": [prior]})
        result = Observer().observe(
            teen_id="teen",
            event=AttendanceEvent(booking_id=booking.booking_id, attended=False, occurred_at=NOW),
            preferences=preferences,
            listing=record,
            store=self.personal,
        )
        self.assertEqual("replan", result.action)
        self.assertEqual(1, self.personal.get_ledger("teen").tries_abandoned)

    def test_observer_moves_axis_only_after_second_activity_signal(self) -> None:
        class RecordingStore:
            def record_outcome(self, **_: object) -> bool:
                return True

        record = listing_record("sport", vibes=["sporty"])
        preferences = PreferenceModel.neutral(NOW).model_copy(
            update={
                "dislikes": [
                    DislikeSignal(
                        axis="vibe:sporty",
                        listing_id="earlier-sport",
                        attribution="activity",
                        strength=0.6,
                        recorded_at=NOW - timedelta(days=7),
                    )
                ]
            }
        )
        result = Observer().observe(
            teen_id="teen",
            event=AttendanceEvent(
                booking_id="booking-current", attended=False, occurred_at=NOW
            ),
            preferences=preferences,
            listing=record,
            debrief=DebriefSubmission(
                booking_id="booking-current",
                text="This activity was not my thing",
                channel="in_app",
                submitted_at=NOW,
            ),
            store=RecordingStore(),
        )
        self.assertEqual("debrief", result.preferences.intensity.provenance)
        self.assertEqual(-0.4, result.preferences.intensity.value)

    def test_langgraph_happy_path_and_persistent_checkpoint(self) -> None:
        ledger = self.setup_teen()
        records = [listing_record("free-one"), listing_record("free-two", vibes=["artistic"])]
        self.ckb.seed(records)
        checkpoint = Path(self.temp.name, "checkpoints.sqlite")
        runtime = HobbiRuntime(
            personal_data=self.personal,
            ckb=self.ckb,
            checkpoint_path=checkpoint,
        )
        state: HobbiState = {
            "teen_id": "teen",
            "thread_id": "thread",
            "declared_age": 15,
            "intake_result": IntakeResult(eligible=True, reason="eligible"),
            "request": self.request,
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
        pending = runtime.invoke(state)
        self.assertEqual("escalated_to_adult", pending["outcome"])
        self.assertEqual(1, pending["guardian_rejects"])
        plan = pending["approved_plan"]
        self.assertIsNotNone(plan)
        self.personal.issue_plan_approvals(
            teen_id="teen",
            plan_id=plan.plan_id,
            attendance_approval_id="attendance",
        )
        state.update(
            {
                "thread_id": "thread-approved",
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
                "outcome": None,
            }
        )
        final = runtime.invoke(state)
        runtime.close()
        self.assertEqual("booked", final["outcome"])
        self.assertEqual(
            ["G1", "G2", "G3", "G4", "G4"],
            [gate.gate for gate in final["gate_log"]],
        )
        self.assertTrue(checkpoint.exists())
        restarted = HobbiRuntime(
            personal_data=self.personal,
            ckb=self.ckb,
            checkpoint_path=checkpoint,
        )
        resumed = restarted.resume("thread-approved")
        restarted.close()
        self.assertEqual("booked", resumed["outcome"])
        self.assertEqual(len(final["booking_records"]), len(resumed["booking_records"]))

    def test_guardian_rejection_changes_the_next_plan(self) -> None:
        ledger = self.setup_teen(constraints={"max_items": 1})
        self.ckb.seed(
            [
                listing_record(
                    "a-private",
                    verification="unverified",
                    provider_type="private_unverified",
                ),
                listing_record("b-verified"),
            ]
        )
        runtime = HobbiRuntime(personal_data=self.personal, ckb=self.ckb, in_memory=True)
        final = runtime.invoke(
            {
                "teen_id": "teen",
                "thread_id": "adaptive-thread",
                "declared_age": 15,
                "intake_result": IntakeResult(eligible=True, reason="eligible"),
                "request": self.request,
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
        )
        runtime.close()
        self.assertEqual("escalated_to_adult", final["outcome"])
        self.assertEqual(1, final["replan_count"])
        self.assertEqual("b-verified", final["approved_plan"].items[0].listing_id)
        self.assertIn("provider_vetting_required:a-private", final["rejection_history"])
        self.assertEqual(
            ["G1", "G2", "G3", "G1", "G2", "G3"],
            [gate.gate for gate in final["gate_log"]],
        )
        self.assertFalse(final["gate_log"][-1].passed)

    def test_broker_availability_failure_replans_through_fresh_gates(self) -> None:
        ledger = self.setup_teen(constraints={"max_items": 1})
        records = [listing_record("a-full"), listing_record("b-open")]
        self.ckb.seed(records)
        snapshot = self.personal.planner_snapshot("teen")
        first = Planner().create_plan(
            planning_key="teen",
            declared_age=15,
            request=self.request,
            ledger=ledger,
            preferences=snapshot["preferences"],
            listings=[hydrated(record, travel=20) for record in records],
            constraints=snapshot["constraints"],
        ).plan
        second = Planner().create_plan(
            planning_key="teen",
            declared_age=15,
            request=self.request,
            ledger=ledger,
            preferences=snapshot["preferences"],
            listings=[hydrated(record, travel=20) for record in records],
            constraints=snapshot["constraints"],
            unavailable_listing_ids={"a-full"},
        ).plan
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        for plan, approval in ((first, "attendance-first"), (second, "attendance-second")):
            self.personal.save_plan("teen", plan, live=False)
            self.personal.issue_plan_approvals(
                teen_id="teen",
                plan_id=plan.plan_id,
                attendance_approval_id=approval,
            )
        runtime = HobbiRuntime(
            personal_data=self.personal,
            ckb=self.ckb,
            in_memory=True,
            sandbox_availability=lambda item: item.listing_id != "a-full",
        )
        final = runtime.invoke(
            {
                "teen_id": "teen",
                "thread_id": "availability-thread",
                "declared_age": 15,
                "intake_result": IntakeResult(eligible=True, reason="eligible"),
                "request": self.request,
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
        )
        runtime.close()
        self.assertEqual("booked", final["outcome"])
        self.assertEqual("b-open", final["booking_records"][0].listing_id)
        self.assertEqual(
            ["G1", "G2", "G3", "G1", "G2", "G3", "G4"],
            [gate.gate for gate in final["gate_log"]],
        )



if __name__ == "__main__":
    unittest.main()
