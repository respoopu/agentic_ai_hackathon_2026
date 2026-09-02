from __future__ import annotations

import csv
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CkbReviewArtifactTests(unittest.TestCase):
    def test_public_candidate_capture_is_compact_unverified_and_nonfictional(self) -> None:
        payload = json.loads(
            (ROOT / "data" / "draft_social_candidates.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(0, payload["summary"]["error_count"])
        self.assertEqual(197, payload["summary"]["candidate_count"])
        self.assertEqual(11, payload["summary"]["lead_only_sources"])
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
        self.assertEqual(45, len(rows))
        self.assertEqual(
            {"Jurong West": 25, "Punggol": 10, "Bishan": 10},
            dict(Counter(row["proposed_area"] for row in rows)),
        )
        self.assertEqual(
            {
                "public_telegram_candidate": 13,
                "merged_nlb_draft": 10,
                "merged_activesg_draft": 8,
                "public_web_candidate": 14,
            },
            dict(Counter(row["source_kind"] for row in rows)),
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
