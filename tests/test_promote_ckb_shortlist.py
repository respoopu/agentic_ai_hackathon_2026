from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.promote_ckb_shortlist import SignoffError, validate_and_promote

AS_OF = datetime(2026, 9, 2, tzinfo=ZoneInfo("Asia/Singapore"))


def approved_row() -> dict[str, str]:
    return {
        "candidate_id": "WEB-real-1",
        "source_url": "https://example.gov.sg/real-activity",
        "review_decision": "approve",
        "reviewed_at": "2026-09-02",
        "reviewed_by": "Human Reviewer",
        "review_notes": "Checked source, participation terms and current access.",
        "confirmed_title": "Park nature walk",
        "confirmed_provider": "Official Parks Provider",
        "confirmed_provider_type": "cc",
        "confirmed_venue": "Neighbourhood Park",
        "confirmed_postal_code": "579799",
        "confirmed_planning_area": "Bishan",
        "confirmed_nearest_mrt": "Bishan",
        "confirmed_cost_one_off_sgd": "0",
        "confirmed_cost_recurring_sgd": "0",
        "confirmed_equipment_cost_sgd": "0",
        "confirmed_age_min": "13",
        "confirmed_age_max": "17",
        "confirmed_beginner_friendly": "yes",
        "confirmed_join_alone_ok": "yes",
        "confirmed_guest_allowed": "yes",
        "confirmed_commitment": "taster",
        "confirmed_schedule_kind": "drop_in",
        "confirmed_weekday": "",
        "confirmed_start_time": "",
        "confirmed_duration_min": "",
        "confirmed_first_session": "",
        "confirmed_num_sessions": "",
        "confirmed_fixed_dates": "",
        "confirmed_open_hours_note": "Open daily",
        "confirmed_weekday_evening_available": "yes",
        "confirmed_weekend_available": "yes",
        "confirmed_vibes": "explorative|chill",
        "confirmed_in_incumbent_directory": "no",
    }


class PromoteShortlistTests(unittest.TestCase):
    def test_promotes_only_complete_human_approved_rows(self) -> None:
        rejected = {
            "candidate_id": "SOC-reject",
            "review_decision": "reject",
            "reviewed_at": "2026-09-02",
            "reviewed_by": "Human Reviewer",
            "review_notes": "Registration has closed.",
        }
        rows, summary = validate_and_promote(
            [approved_row(), rejected], as_of=AS_OF
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("verified", rows[0]["verification"])
        self.assertEqual("Human Reviewer", rows[0]["verified_by"])
        self.assertEqual({"approved": 1, "rejected": 1, "reviewed": 2}, summary)

    def test_pending_rows_fail_closed(self) -> None:
        row = approved_row()
        row["review_decision"] = ""
        with self.assertRaisesRegex(SignoffError, "pending human review"):
            validate_and_promote([row], as_of=AS_OF)

    def test_agent_cannot_be_recorded_as_human_verifier(self) -> None:
        row = approved_row()
        row["reviewed_by"] = "Codex"
        with self.assertRaisesRegex(SignoffError, "must identify the human"):
            validate_and_promote([row], as_of=AS_OF)

    def test_builder_validation_rejects_incomplete_approval(self) -> None:
        row = approved_row()
        row["confirmed_cost_one_off_sgd"] = ""
        with self.assertRaisesRegex(SignoffError, "required"):
            validate_and_promote([row], as_of=AS_OF)

    def test_rejection_needs_reason_and_human_attestation(self) -> None:
        row = approved_row()
        row.update(review_decision="reject", review_notes="")
        with self.assertRaisesRegex(SignoffError, "need review_notes"):
            validate_and_promote([row], as_of=AS_OF)


if __name__ == "__main__":
    unittest.main()
