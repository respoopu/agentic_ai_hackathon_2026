from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.promote_ckb_shortlist import (
    SignoffError,
    apply_attestations,
    validate_and_promote,
)

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
    def test_cli_accepts_date_only_as_of_as_singapore_time(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "seed.csv"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "promote_ckb_shortlist.py"),
                    "--as-of",
                    "2026-09-02",
                    "--out",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

    def test_attestation_ledger_overlays_generated_shortlist(self) -> None:
        row = approved_row()
        row.update(review_decision="", reviewed_at="", reviewed_by="")
        reviewed = apply_attestations(
            [row],
            {
                "decisions": {
                    "WEB-real-1": {
                        "review_decision": "approve",
                        "reviewed_at": "2026-09-02",
                        "reviewed_by": "Human Reviewer",
                        "review_notes": "Source checked.",
                    }
                },
            },
        )
        self.assertEqual("approve", reviewed[0]["review_decision"])
        self.assertEqual("Human Reviewer", reviewed[0]["reviewed_by"])

    def test_non_evidentiary_defaults_only_fill_blank_source_values(self) -> None:
        row = approved_row()
        row.update(research_batch="Row batch")
        reviewed = apply_attestations(
            [row],
            {
                "defaults": {"research_batch": "Default batch", "source_note": "web"},
                "decisions": {
                    "WEB-real-1": {
                        "review_decision": "approve",
                        "review_notes": "Source checked.",
                    }
                },
            },
        )

        self.assertEqual("Row batch", reviewed[0]["research_batch"])
        self.assertEqual("web", reviewed[0]["source_note"])

    def test_evidentiary_fields_cannot_be_attestation_defaults(self) -> None:
        with self.assertRaisesRegex(SignoffError, "must be recorded per decision"):
            apply_attestations(
                [approved_row()],
                {
                    "defaults": {"confirmed_join_alone_ok": "yes"},
                    "decisions": {
                        "WEB-real-1": {
                            "review_decision": "approve",
                            "review_notes": "Source checked.",
                        }
                    },
                },
            )

    def test_attestation_ledger_rejects_unknown_candidates(self) -> None:
        with self.assertRaisesRegex(SignoffError, "unknown candidates"):
            apply_attestations(
                [approved_row()],
                {"decisions": {"WEB-not-shortlisted": {"review_decision": "reject"}}},
            )

    def test_attestation_cannot_overwrite_generated_source_fields(self) -> None:
        with self.assertRaisesRegex(SignoffError, "unsupported attestation fields"):
            apply_attestations(
                [approved_row()],
                {
                    "decisions": {
                        "WEB-real-1": {
                            "review_decision": "approve",
                            "source_url": "https://attacker.invalid/replacement",
                        }
                    }
                },
            )

    def test_json_null_does_not_become_literal_none(self) -> None:
        reviewed = apply_attestations(
            [approved_row()],
            {
                "decisions": {
                    "WEB-real-1": {
                        "review_decision": "approve",
                        "confirmed": {"nearest_mrt": None},
                    }
                }
            },
        )
        self.assertEqual("", reviewed[0]["confirmed_nearest_mrt"])

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
