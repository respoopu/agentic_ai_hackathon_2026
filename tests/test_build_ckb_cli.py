from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.build_ckb import COLUMNS, RowError, _bool, _money, parse_row
from scripts.fetch_activesg_free_play import to_row as activesg_to_row
from scripts.fetch_nlb_teen_events import stable_listing_id
from scripts.fetch_nlb_teen_events import to_row as nlb_to_row

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_ckb.py"
QUARANTINE = ROOT / "data" / "quarantine_listings.json"
AS_OF = "2026-09-01T09:00:00+08:00"


def write_sheet(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def complete_rows() -> list[dict[str, str]]:
    areas = ["Jurong West"] * 24 + ["Punggol"] * 4 + ["Bishan"] * 4
    providers = ["cc", "activesg", "third_space", "informal", "commercial"]
    vibes = ["sporty", "artistic", "chill", "explorative"]
    rows: list[dict[str, str]] = []
    for index, area in enumerate(areas, start=1):
        rows.append(
            {
                "listing_id": f"TEST-{index:03d}",
                "title": f"Test activity {index}",
                "provider": f"Test provider {index}",
                "provider_type": providers[(index - 1) % len(providers)],
                "source_url": f"https://example.org/activities/{index}",
                "verified_at": "2026-09-01",
                "verified_by": "Automated test fixture",
                "verification": "verified",
                "cost_one_off_sgd": "0",
                "cost_recurring_sgd": "0",
                "equipment_cost_sgd": "0",
                "venue_name": f"Test venue {index}",
                "postal_code": str(600000 + index),
                "planning_area": area,
                "nearest_mrt": "Test MRT",
                "age_min": "13",
                "age_max": "17",
                "beginner_friendly": "yes",
                "join_alone_ok": "yes",
                "guest_allowed": "no",
                "commitment": "one_off",
                "schedule_kind": "weekly",
                "weekday": "sat",
                "start_time": "10:00",
                "duration_min": "60",
                "first_session": "2026-09-05",
                "num_sessions": "4",
                "fixed_dates": "",
                "open_hours_note": "",
                "vibes": vibes[(index - 1) % len(vibes)],
                "in_incumbent_directory": "no" if index <= 16 else "yes",
                "notes": (
                    "#demo-retire" if index == len(areas) else "Synthetic test row"
                ),
                "weekday_evening_available": "",
                "weekend_available": "",
            }
        )
    return rows


class BuilderFieldTests(unittest.TestCase):
    def test_blank_cost_and_boolean_facts_are_rejected(self) -> None:
        with self.assertRaises(RowError):
            _money("", "cost_one_off_sgd")
        with self.assertRaises(RowError):
            _bool("", "in_incumbent_directory")

    def test_singapore_currency_prefix_is_accepted(self) -> None:
        self.assertEqual("5.50", _money("S$5.50", "cost_one_off_sgd"))

    def test_retired_csv_row_gets_dead_freshness_state(self) -> None:
        row = complete_rows()[0]
        row["verification"] = "retired"
        record = parse_row(
            row,
            as_of=datetime.fromisoformat(AS_OF),
        )
        self.assertEqual("dead", record["freshness_state"])


class BuilderCliTests(unittest.TestCase):
    def run_builder(
        self, *args: object, no_site: bool = True
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable]
        if no_site:
            command.append("-S")
        command.extend([str(BUILDER), *(str(arg) for arg in args)])
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_stdlib_cli_builds_a_complete_seed_atomically(self) -> None:
        canonical = ROOT / "data" / "seed_ckb.json"
        canonical_before = canonical.read_bytes() if canonical.exists() else None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sheet = root / "complete.csv"
            output = root / "seed.json"
            write_sheet(sheet, complete_rows())

            result = self.run_builder(
                "--sheet",
                sheet,
                "--quarantine",
                QUARANTINE,
                "--out",
                output,
                "--as-of",
                AS_OF,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("12/12 coverage checks pass", result.stdout)
            self.assertIn("pydantic not installed", result.stdout)
            records = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(42, len(records))
            self.assertTrue(records[0]["last_seen_at"].endswith("+08:00"))
            self.assertEqual([], list(root.glob(f".{output.name}.*.tmp")))

        canonical_after = canonical.read_bytes() if canonical.exists() else None
        self.assertEqual(canonical_before, canonical_after)

    @unittest.skipUnless(
        importlib.util.find_spec("pydantic"),
        "Full conformance test needs project dependencies",
    )
    def test_complete_artifact_passes_model_and_loader_contracts(self) -> None:
        from src.ckb.seed_loader import load_seed_records

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sheet = root / "complete.csv"
            output = root / "seed.json"
            write_sheet(sheet, complete_rows())
            result = self.run_builder(
                "--sheet",
                sheet,
                "--quarantine",
                QUARANTINE,
                "--out",
                output,
                "--as-of",
                AS_OF,
                no_site=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("pydantic conformance: OK", result.stdout)
            self.assertEqual(42, len(load_seed_records(output)))

    def test_stdlib_cli_rejects_malformed_quarantine_without_traceback(self) -> None:
        original = json.loads(QUARANTINE.read_text(encoding="utf-8"))
        mutations = {
            "missing listing_id": lambda row: row.pop("listing_id"),
            "fictional provider typed as cc": lambda row: row.update(
                provider_type="cc"
            ),
            "fictional marker removed": lambda row: row.update(is_fictional=False),
            "dead but unverified": lambda row: row.update(freshness_state="dead"),
            "unknown field": lambda row: row.update(unexpected="schema drift"),
            "non-string vibe": lambda row: row.update(vibes=[{"bad": "shape"}]),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sheet = root / "empty.csv"
            write_sheet(sheet, [])
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    payload = json.loads(json.dumps(original))
                    mutate(payload["listings"][0])
                    quarantine = root / "quarantine.json"
                    quarantine.write_text(json.dumps(payload), encoding="utf-8")
                    output = root / "should-not-exist.json"

                    result = self.run_builder(
                        "--sheet",
                        sheet,
                        "--quarantine",
                        quarantine,
                        "--out",
                        output,
                        "--allow-incomplete",
                        "--as-of",
                        AS_OF,
                    )

                    self.assertEqual(1, result.returncode)
                    self.assertIn("quarantine", result.stdout)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)
                    self.assertFalse(output.exists())

    def test_external_missing_sheet_has_a_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.csv"
            result = self.run_builder("--sheet", missing, "--coverage-only")
        self.assertEqual(1, result.returncode)
        self.assertIn(f"no sheet at {missing.resolve()}", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)


class DraftFetcherTests(unittest.TestCase):
    def test_fetchers_refuse_to_overwrite_drafts_without_force(self) -> None:
        scripts = (
            ROOT / "scripts" / "fetch_nlb_teen_events.py",
            ROOT / "scripts" / "fetch_activesg_free_play.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.csv"
            output.write_text("human-reviewed draft\n", encoding="utf-8")
            for script in scripts:
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        [sys.executable, "-S", str(script), "--out", str(output)],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(1, result.returncode)
                    self.assertIn("refusing to overwrite", result.stdout)
                    self.assertEqual(
                        "human-reviewed draft\n",
                        output.read_text(encoding="utf-8"),
                    )

    def test_nlb_ids_are_stable_and_unknown_cost_remains_blank(self) -> None:
        event = {
            "url": "https://nlb.libcal.com/event/5971203",
            "title": "A test event",
            "startdt": "2026-09-05T15:00:00+08:00",
            "registration_cost": "",
        }
        self.assertEqual("NLB-5971203", stable_listing_id(event))
        row = nlb_to_row(event)
        self.assertEqual("NLB-5971203", row["listing_id"])
        self.assertEqual("", row["cost_one_off_sgd"])
        self.assertEqual("yes", row["in_incumbent_directory"])

    def test_nlb_west_subset_uses_the_same_ids_as_the_full_draft(self) -> None:
        def url_to_id(path: Path) -> dict[str, str]:
            with path.open(newline="", encoding="utf-8") as handle:
                return {
                    row["source_url"]: row["listing_id"]
                    for row in csv.DictReader(handle)
                }

        full = url_to_id(ROOT / "data" / "draft_nlb.csv")
        west = url_to_id(ROOT / "data" / "draft_nlb_west.csv")
        self.assertTrue(set(west).issubset(full))
        self.assertTrue(
            all(full[url] == listing_id for url, listing_id in west.items())
        )

    def test_activesg_draft_does_not_invent_availability(self) -> None:
        row = activesg_to_row(
            {
                "slug": "test-field",
                "name": "Test School Field",
                "url": "https://example.org/test-field",
                "postal": "600001",
                "zone": "West",
                "address": "1 Test Street Singapore 600001",
            },
            hours="",
        )
        self.assertEqual("", row["open_hours_note"])
        self.assertEqual("", row["weekday_evening_available"])
        self.assertEqual("", row["weekend_available"])
        self.assertEqual("", row["beginner_friendly"])
        self.assertEqual("", row["join_alone_ok"])
        self.assertEqual("", row["guest_allowed"])
        self.assertEqual("yes", row["in_incumbent_directory"])


if __name__ == "__main__":
    unittest.main()
