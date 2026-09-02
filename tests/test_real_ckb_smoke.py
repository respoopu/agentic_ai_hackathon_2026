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

from src.api import HobbiService
from tests.helpers import NOW, listing_record
from tests.test_intake_and_gates import consents

assert "sim.catalogue" not in sys.modules
with tempfile.TemporaryDirectory() as directory:
    service = HobbiService(directory, guardian_token="guardian-smoke-token")
    try:
        service.ckb.seed(
            [
                listing_record("real-source-smoke-a"),
                listing_record("real-source-smoke-b"),
            ]
        )
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
                        "requested_at": NOW.isoformat(),
                    },
                    "ledger": {
                        "money_total_sgd": 0,
                        "hours_per_week": 2,
                        "tries_total": 2,
                    },
                    "consents": [
                        consent.model_dump(mode="json")
                        for consent in consents("real-smoke-teen")
                    ],
                },
            },
            authorization="guardian-smoke-token",
        )
        item_ids = [item["listing_id"] for item in response["state"]["approved_plan"]["items"]]
        print(json.dumps({
            "ready": health["ready_for_real_planning"],
            "outcome": response["state"]["outcome"],
            "item_ids": item_ids,
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
        result = json.loads(completed.stdout)
        self.assertTrue(result["ready"])
        self.assertEqual("escalated_to_adult", result["outcome"])
        self.assertEqual(
            ["real-source-smoke-a", "real-source-smoke-b"], result["item_ids"]
        )
        self.assertFalse(result["synthetic_imported"])


if __name__ == "__main__":
    unittest.main()
