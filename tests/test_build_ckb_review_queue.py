from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_ckb_review_queue import build_queue


class ReviewQueueTests(unittest.TestCase):
    def test_deduplicates_by_stable_source_url_and_keeps_both_source_families(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft = root / "draft_nlb.csv"
            fields = [
                "listing_id",
                "title",
                "provider",
                "source_url",
                "verified_at",
                "verified_by",
                "cost_one_off_sgd",
                "planning_area",
                "postal_code",
                "age_min",
                "age_max",
                "beginner_friendly",
                "join_alone_ok",
                "guest_allowed",
                "fixed_dates",
                "weekday",
                "start_time",
                "open_hours_note",
                "vibes",
                "notes",
            ]
            with draft.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for listing_id in ("NLB-1", "NLB-duplicate"):
                    writer.writerow(
                        {
                            "listing_id": listing_id,
                            "title": "Teen workshop",
                            "provider": "NLB",
                            "source_url": "https://example.test/event/1",
                            "age_min": "13",
                            "age_max": "17",
                            "fixed_dates": "2026-09-20T10:00",
                            "vibes": "artistic",
                        }
                    )
            social = root / "social.json"
            social.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "candidate_id": "SOC-1",
                                "source_name": "Community",
                                "source_url": "https://t.me/community/1",
                                "title_hint": "Cycling workshop",
                                "registration_urls": [],
                                "detected": {
                                    "dates": ["20 September 2026"],
                                    "times": ["2pm"],
                                    "costs": ["Free"],
                                    "ages": ["Ages 13-17"],
                                    "postal_codes": ["579799"],
                                },
                                "area_hints": ["Bishan"],
                                "topic_hints": ["cycling"],
                                "excerpt": "Public event excerpt",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rows, summary = build_queue([draft], social)
        self.assertEqual(2, summary["total"])
        self.assertEqual(1, summary["merged_drafts"])
        self.assertEqual(1, summary["public_candidates"])
        self.assertEqual(1, summary["duplicates_removed"])
        self.assertEqual("SOC-1", rows[0]["candidate_id"])
        self.assertEqual("Bishan", rows[0]["area_hints"])

    def test_distinct_web_activities_can_share_an_official_evidence_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft = root / "draft.csv"
            draft.write_text("listing_id,source_url\n", encoding="utf-8")
            social = root / "social.json"
            social.write_text('{"candidates": []}', encoding="utf-8")
            web = root / "web.json"
            candidates = []
            for candidate_id, title in (("WEB-1", "Cycle"), ("WEB-2", "Walk")):
                candidates.append(
                    {
                        "candidate_id": candidate_id,
                        "source_name": "Official source",
                        "source_url": "https://example.test/venue",
                        "registration_urls": [],
                        "title_hint": title,
                        "detected": {},
                        "area_hints": ["Jurong West"],
                        "topic_hints": [],
                    }
                )
            web.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
            rows, summary = build_queue([draft], social, web)

        self.assertEqual(2, len(rows))
        self.assertEqual(2, summary["public_candidates"])
        self.assertEqual(0, summary["duplicates_removed"])

    def test_social_reposts_with_same_external_registration_link_are_deduped(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft = root / "draft.csv"
            draft.write_text("listing_id,source_url\n", encoding="utf-8")
            social = root / "social.json"
            candidates = []
            for number in (1, 2):
                candidates.append(
                    {
                        "candidate_id": f"SOC-{number}",
                        "source_name": "Community",
                        "source_url": f"https://t.me/community/{number}",
                        "registration_urls": [
                            f"https://t.me/community/{number}",
                            "https://go.gov.sg/same-event?tracking=different",
                        ],
                        "title_hint": "Same event repost",
                        "detected": {},
                        "area_hints": ["Bishan"],
                        "topic_hints": [],
                    }
                )
            social.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
            rows, summary = build_queue([draft], social)

        self.assertEqual(1, len(rows))
        self.assertEqual(1, summary["duplicates_removed"])

    def test_distinct_social_events_can_share_a_programme_registration_link(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft = root / "draft.csv"
            draft.write_text("listing_id,source_url\n", encoding="utf-8")
            social = root / "social.json"
            candidates = []
            for number, title, event_date in (
                (1, "Punggol trial", "20 September 2026"),
                (2, "Bukit Canberra trial", "27 September 2026"),
            ):
                candidates.append(
                    {
                        "candidate_id": f"SOC-{number}",
                        "source_name": "Programme",
                        "source_url": f"https://t.me/programme/{number}",
                        "registration_urls": ["https://go.gov.sg/standing-link"],
                        "title_hint": title,
                        "detected": {"dates": [event_date]},
                        "area_hints": [],
                        "topic_hints": [],
                    }
                )
            social.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
            rows, summary = build_queue([draft], social)

        self.assertEqual(2, len(rows))
        self.assertEqual(0, summary["duplicates_removed"])


if __name__ == "__main__":
    unittest.main()
