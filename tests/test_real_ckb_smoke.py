from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RealCkbSmokeTests(unittest.TestCase):
    def test_real_row_planning_does_not_import_synthetic_catalogue(self) -> None:
        program = r'''
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from src.api import HobbiService
from src.ckb.seed_loader import load_seed_records
from src.schema.plan import ConsentRecord

assert "sim.catalogue" not in sys.modules
root = Path.cwd()
now = datetime.fromisoformat("2026-09-02T12:00:00+08:00")
consents = [
    ConsentRecord(
        consent_id="real-smoke-teen-personal",
        teen_id="real-smoke-teen",
        kind="personal_data",
        granted=True,
        granted_by="teen",
        recorded_at=now,
    ),
    ConsentRecord(
        consent_id="real-smoke-teen-adult",
        teen_id="real-smoke-teen",
        kind="trusted_adult_authority",
        granted=True,
        granted_by="trusted_adult",
        recorded_at=now,
    ),
]
records = load_seed_records(root / "data" / "seed_ckb.json")
real_ids = {
    record.listing_id
    for record in records
    if not record.is_fictional and record.verification != "retired"
}
with tempfile.TemporaryDirectory() as directory:
    service = HobbiService(
        directory, guardian_token="guardian-smoke-token", seed_artifact=None
    )
    try:
        service.ckb.seed(records)
        health = service.handle({"operation": "health"})
        response = service.handle(
            {
                "operation": "intake_and_plan",
                "setup": {
                    "teen_id": "real-smoke-teen",
                    "thread_id": "real-smoke-thread",
                    "declared_age": 15,
                    "request": {
                        "goal": "try a sourced nearby hobby",
                        "requested_at": datetime.fromisoformat("2026-09-02T12:00:00+08:00").isoformat(),
                    },
                    "ledger": {
                        "money_total_sgd": 0,
                        "hours_per_week": 2,
                        "tries_total": 2,
                    },
                    "consents": [
                        consent.model_dump(mode="json")
                        for consent in consents
                    ],
                },
            },
            authorization="guardian-smoke-token",
        )
        item_ids = [item["listing_id"] for item in response["state"]["approved_plan"]["items"]]
        print("REAL_CKB_RESULT=" + json.dumps({
            "ready": health["ready_for_real_planning"],
            "outcome": response["state"]["outcome"],
            "item_ids": item_ids,
            "all_items_are_canonical": set(item_ids) <= real_ids,
            "synthetic_imported": "sim.catalogue" in sys.modules,
        }))
    finally:
        service.close()
'''
        completed = subprocess.run(
            [sys.executable, "-c", program],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        result_line = next(
            line.removeprefix("REAL_CKB_RESULT=")
            for line in completed.stdout.splitlines()
            if line.startswith("REAL_CKB_RESULT=")
        )
        result = json.loads(result_line)
        self.assertTrue(result["ready"])
        self.assertEqual("escalated_to_adult", result["outcome"])
        self.assertTrue(result["item_ids"])
        self.assertTrue(result["all_items_are_canonical"])
        self.assertFalse(result["synthetic_imported"])


if __name__ == "__main__":
    unittest.main()
