from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, time
from pathlib import Path

from scripts.build_ckb import coverage

try:
    from pydantic import ValidationError
except ImportError:
    HAS_PYDANTIC = False
else:
    from src.ckb.seed_loader import (
        expand_next_sessions,
        hydrate_listing,
        load_seed_records,
    )
    from src.schema.listing import SG_TZ, ListingRecord, Schedule

    HAS_PYDANTIC = True

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_PYDANTIC, "Pydantic model tests need project dependencies")
class ListingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads((ROOT / "data" / "quarantine_listings.json").read_text())
        cls.quarantine = payload["listings"]

    def test_every_quarantine_fixture_matches_listing_record(self) -> None:
        records = [ListingRecord.model_validate(row) for row in self.quarantine]
        self.assertEqual(10, len(records))
        self.assertTrue(all(record.is_fictional for record in records))

    def test_unknown_fields_are_rejected(self) -> None:
        row = {**self.quarantine[0], "unexpected": "schema drift"}
        with self.assertRaises(ValidationError):
            ListingRecord.model_validate(row)

    def test_derived_first_session_cost_cannot_drift(self) -> None:
        row = {**self.quarantine[0], "cost_total_first_session": "999"}
        with self.assertRaises(ValidationError):
            ListingRecord.model_validate(row)

    def test_seed_load_is_atomic(self) -> None:
        rows = [self.quarantine[0], {**self.quarantine[1], "postal_code": "bad"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_seed_records(path)

    def test_seed_load_rejects_duplicate_ids(self) -> None:
        rows = [self.quarantine[0], self.quarantine[0]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate listing IDs"):
                load_seed_records(path)

    def test_seed_load_keeps_quarantine_for_guardian_vetting(self) -> None:
        rows = self.quarantine[:2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            records = load_seed_records(path)
        self.assertEqual(2, len(records))
        self.assertTrue(all(record.is_fictional for record in records))


@unittest.skipUnless(HAS_PYDANTIC, "Pydantic model tests need project dependencies")
class HydrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads((ROOT / "data" / "quarantine_listings.json").read_text())
        cls.record = ListingRecord.model_validate(payload["listings"][0])

    def test_weekly_schedule_expands_from_first_matching_weekday(self) -> None:
        schedule = Schedule(
            kind="weekly",
            weekday="sat",
            start_time=time(10, 0),
            duration_min=60,
            first_session=date(2026, 9, 5),
            num_sessions=3,
        )
        sessions = expand_next_sessions(schedule, as_of=datetime(2026, 9, 1))
        self.assertEqual(
            [
                datetime(2026, 9, 5, 10, 0, tzinfo=SG_TZ),
                datetime(2026, 9, 12, 10, 0, tzinfo=SG_TZ),
                datetime(2026, 9, 19, 10, 0, tzinfo=SG_TZ),
            ],
            sessions,
        )

    def test_weekly_schedule_rejects_mismatched_first_day(self) -> None:
        with self.assertRaises(ValidationError):
            Schedule(
                kind="weekly",
                weekday="sat",
                start_time=time(10, 0),
                duration_min=60,
                first_session=date(2026, 9, 1),
                num_sessions=3,
            )

    def test_weekly_schedule_requires_duration(self) -> None:
        with self.assertRaises(ValidationError):
            Schedule(
                kind="weekly",
                weekday="sat",
                start_time=time(10, 0),
                first_session=date(2026, 9, 5),
                num_sessions=3,
            )

    def test_aware_fixed_dates_are_normalised_to_singapore(self) -> None:
        schedule = Schedule(
            kind="fixed_dates",
            fixed_dates=["2026-09-05T02:00:00Z"],
        )
        sessions = expand_next_sessions(
            schedule,
            as_of=datetime.fromisoformat("2026-09-05T09:00:00+08:00"),
        )
        self.assertEqual(
            [datetime.fromisoformat("2026-09-05T10:00:00+08:00")],
            sessions,
        )

    def test_hydration_keeps_relative_fields_out_of_stored_record(self) -> None:
        listing = hydrate_listing(
            self.record,
            travel_min_home=12,
            travel_min_school=8,
            as_of=datetime(2026, 9, 1),
        )
        self.assertEqual(12, listing.travel_min_home)
        self.assertEqual(8, listing.travel_min_school)
        self.assertFalse(hasattr(self.record, "travel_min_home"))

    def test_negative_travel_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            hydrate_listing(
                self.record,
                travel_min_home=-1,
                travel_min_school=8,
                as_of=datetime(2026, 9, 1),
            )


class CoverageTests(unittest.TestCase):
    def test_quarantine_only_seed_is_not_complete(self) -> None:
        payload = json.loads((ROOT / "data" / "quarantine_listings.json").read_text())
        results = coverage(payload["listings"])
        self.assertFalse(all(passed for _, passed, _ in results))

    def test_empty_real_seed_does_not_pass_freshness(self) -> None:
        payload = json.loads((ROOT / "data" / "quarantine_listings.json").read_text())
        results = dict(
            (label, passed) for label, passed, _ in coverage(payload["listings"])
        )
        self.assertFalse(results["freshness · verified within 30 days"])

    def test_drop_in_availability_is_explicit(self) -> None:
        if not HAS_PYDANTIC:
            self.skipTest("Pydantic model tests need project dependencies")
        schedule = Schedule(
            kind="drop_in",
            open_hours_note="Weekends only",
            weekday_evening_available=False,
            weekend_available=True,
        )
        self.assertFalse(schedule.is_weekday_evening())
        self.assertTrue(schedule.is_weekend())

    def test_drop_in_without_availability_flags_is_rejected(self) -> None:
        if not HAS_PYDANTIC:
            self.skipTest("Pydantic model tests need project dependencies")
        with self.assertRaises(ValidationError):
            Schedule(kind="drop_in", open_hours_note="Open when posted")


if __name__ == "__main__":
    unittest.main()
