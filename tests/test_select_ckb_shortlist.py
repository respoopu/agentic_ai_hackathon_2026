from __future__ import annotations

import unittest

from scripts.select_ckb_shortlist import (
    _age_overlaps_target,
    _parse_hint_dates,
    automated_flags,
    hobby_buckets,
    infer_area,
)


class ShortlistSelectionTests(unittest.TestCase):
    def test_explicit_area_beats_channel_hint(self) -> None:
        row = {
            "source_name": "Bishan Connects",
            "title_hint": "Workshop at One Punggol",
            "venue_hint": "",
            "postal_hint": "",
            "excerpt_or_notes": "Meet at One Punggol",
        }
        self.assertEqual("Punggol", infer_area(row)[0])

    def test_local_channel_is_only_a_hint(self) -> None:
        row = {
            "source_name": "OneBoonLay",
            "title_hint": "Community workshop",
            "venue_hint": "",
            "postal_hint": "",
            "excerpt_or_notes": "",
        }
        area, evidence = infer_area(row)
        self.assertEqual("Jurong West", area)
        self.assertIn("hint only", evidence)

    def test_parses_iso_and_social_dates(self) -> None:
        self.assertEqual(
            ["2026-09-20", "2026-10-03"],
            [
                value.isoformat()
                for value in _parse_hint_dates("2026-09-20T10:00 | 3 October 2026")
            ],
        )

    def test_expired_and_closed_candidates_are_flagged(self) -> None:
        row = {
            "title_hint": "SOLD OUT workshop",
            "excerpt_or_notes": "Registration has closed",
            "date_hints": "22 August 2026",
            "age_hints": "",
            "cost_hints": "",
        }
        flags = automated_flags(row, "explicit row text")
        self.assertIn("closed_or_cancelled_text", flags)
        self.assertIn("all_detected_dates_expired", flags)

    def test_channel_hint_does_not_override_explicit_out_of_area_venue(self) -> None:
        row = {
            "title_hint": "Walk at Sembawang Hot Spring Park",
            "excerpt_or_notes": "Meet at Bishan CC for the bus",
            "date_hints": "20 September 2026",
            "age_hints": "all ages",
            "cost_hints": "Free",
        }
        flags = automated_flags(row, "local source-channel hint only; venue may differ")
        self.assertIn("venue_outside_proposed_area", flags)

    def test_cafe_and_thrift_candidates_are_hobbies(self) -> None:
        row = {
            "title_hint": "Coffee tasting and thrift swap",
            "topic_hints": "cafe hopping",
            "excerpt_or_notes": "community market workshop",
        }
        buckets = hobby_buckets(row)
        self.assertIn("chill", buckets)
        self.assertIn("explorative", buckets)

    def test_stated_age_must_overlap_13_to_17(self) -> None:
        self.assertTrue(_age_overlaps_target("Ages 13-17"))
        self.assertTrue(_age_overlaps_target("aged 17-24"))
        self.assertTrue(_age_overlaps_target("all ages"))
        self.assertTrue(_age_overlaps_target("aged 12 and above"))
        self.assertTrue(_age_overlaps_target("suitable for everyone"))
        self.assertFalse(_age_overlaps_target("aged 7-12"))
        self.assertFalse(_age_overlaps_target("aged 60"))


if __name__ == "__main__":
    unittest.main()
