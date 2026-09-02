from __future__ import annotations

import csv
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CkbReviewArtifactTests(unittest.TestCase):
    def test_attestations_record_evidence_per_decision(self) -> None:
        payload = json.loads(
            (ROOT / "data" / "ckb_attestations.json").read_text(encoding="utf-8")
        )
        self.assertFalse(payload.get("defaults"))
        required = {
            "cost_recurring_sgd",
            "equipment_cost_sgd",
            "beginner_friendly",
            "join_alone_ok",
            "guest_allowed",
            "in_incumbent_directory",
        }
        for candidate_id, decision in payload["decisions"].items():
            self.assertTrue(decision.get("reviewed_at"), candidate_id)
            self.assertTrue(decision.get("reviewed_by"), candidate_id)
            if decision["review_decision"] == "approve":
                self.assertTrue(
                    required.issubset(decision.get("confirmed", {})), candidate_id
                )

    def test_shared_provenance_pages_are_explicitly_scoped(self) -> None:
        payload = json.loads(
            (ROOT / "data" / "ckb_attestations.json").read_text(encoding="utf-8")
        )
        decisions = payload["decisions"]
        for candidate_id in ("WEB-jw-table-tennis", "WEB-bishan-table-tennis"):
            self.assertIn(
                "selectable venue",
                decisions[candidate_id]["review_notes"].lower(),
                candidate_id,
            )
        self.assertIn(
            "directory entry",
            decisions["WEB-bishan-swim"]["review_notes"].lower(),
        )

    def test_public_candidate_capture_is_compact_unverified_and_nonfictional(self) -> None:
        payload = json.loads(
            (ROOT / "data" / "draft_social_candidates.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(0, payload["summary"]["error_count"])
        self.assertEqual(
            len(payload["candidates"]), payload["summary"]["candidate_count"]
        )
        self.assertGreater(payload["summary"]["candidate_count"], 0)
        self.assertGreaterEqual(payload["summary"]["lead_only_sources"], 0)
        for candidate in payload["candidates"]:
            self.assertEqual("unverified", candidate["verification"])
            self.assertFalse(candidate["is_fictional"])
            self.assertLessEqual(len(candidate["excerpt"]), 280)
            self.assertTrue(candidate["source_url"].startswith("https://t.me/"))

    def test_shortlist_is_balanced_diverse_and_unsigned(self) -> None:
        with (ROOT / "data" / "ckb_shortlist.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(46, len(rows))
        self.assertEqual(
            {"Jurong West": 25, "Punggol": 10, "Bishan": 10, "Kallang": 1},
            dict(Counter(row["proposed_area"] for row in rows)),
        )
        self.assertEqual(
            {
                "public_telegram_candidate",
                "merged_nlb_draft",
                "merged_activesg_draft",
                "public_web_candidate",
            },
            {row["source_kind"] for row in rows},
        )
        buckets = {
            bucket
            for row in rows
            for bucket in row["hobby_buckets"].split(" | ")
        }
        self.assertEqual({"sporty", "artistic", "chill", "explorative"}, buckets)
        self.assertTrue(all(not row["review_decision"] for row in rows))
        self.assertTrue(all(not row["reviewed_by"] for row in rows))
        self.assertTrue(all(row["source_url"].startswith("http") for row in rows))
        forbidden_flags = {
            "closed_or_cancelled_text",
            "all_detected_dates_expired",
            "not_a_hobby_activity",
            "official_source_says_unavailable",
            "stated_age_outside_13_17",
            "venue_outside_proposed_area",
        }
        for row in rows:
            self.assertTrue(
                forbidden_flags.isdisjoint(row["automated_flags"].split(" | "))
            )


if __name__ == "__main__":
    unittest.main()
