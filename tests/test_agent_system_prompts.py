"""Contract tests for the architecture-v2.2 agent prompts and fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "docs" / "agent-system-prompts"
FIXTURES = ROOT / "tests" / "agent-system-prompts" / "fixtures"


class AgentPromptContractTests(unittest.TestCase):
    def test_v22_agent_roster_and_topology_are_documented(self) -> None:
        readme = (PROMPTS / "README.md").read_text(encoding="utf-8")
        for filename in (
            "planner-agent.md",
            "discovery-engine.md",
            "guardian-agent.md",
            "broker-agent.md",
            "observer-agent.md",
            "compliance-agent.md",
            "validator-agent.md",
        ):
            self.assertTrue((PROMPTS / filename).is_file(), filename)
        self.assertIn("Intake/Setup", readme)
        self.assertIn("scheduled, off the request path", readme)
        self.assertIn("detached", readme)
        self.assertNotIn("Discovery -> Compliance", readme)

    def test_legacy_protocol_vocabulary_is_absent(self) -> None:
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for path in PROMPTS.glob("*.md")
        )
        for forbidden in (
            "Child Profile",
            "activity_version",
            "activity_hash",
            "RAW_DATA_COLLECTED",
            "lifelong activity and career",
        ):
            self.assertNotIn(forbidden, corpus)

    def test_shared_protocol_carries_canonical_records_caps_and_outcomes(self) -> None:
        protocol = (PROMPTS / "shared-protocol.md").read_text(encoding="utf-8")
        required = (
            "BudgetLedger",
            "HobbiState",
            "ListingRecord",
            "GuardianVerdict",
            "BookingRecord",
            "AttendanceEvent",
            "DebriefSubmission",
            "GateResult",
            "PreferenceModel",
            "MAX_REPLANS = 3",
            "MAX_DISCOVERY_ROUNDS = 2",
            "MAX_GUARDIAN_REJECTIONS = 2",
            "booked",
            "escalated_to_adult",
            "no_viable_plan",
            "hold_this_week",
            "cap_breached",
        )
        for marker in required:
            self.assertIn(marker, protocol)

    def test_fixture_validator_is_canonical_python_and_complete(self) -> None:
        validator = ROOT / "tests" / "agent-system-prompts" / "validate_fixtures.py"
        self.assertTrue(validator.is_file())
        result = subprocess.run(
            [sys.executable, str(validator)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_unknown_fixture_invariant_is_rejected(self) -> None:
        validator = ROOT / "tests" / "agent-system-prompts" / "validate_fixtures.py"
        with tempfile.TemporaryDirectory() as temporary:
            fixture = {
                "fixture_version": "2.2",
                "id": "unknown-invariant",
                "name": "Unknown invariant is not silently accepted",
                "agent": "validator",
                "given": {},
                "expect": {
                    "output": {},
                    "tool_calls": {},
                    "store_reads": [],
                    "store_writes": [],
                    "gates": [],
                },
                "invariants": ["not_a_real_invariant"],
                "covers": [],
            }
            Path(temporary, "unknown.yaml").write_text(
                json.dumps(fixture), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(validator), "--fixtures", temporary, "--no-docs"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unknown invariant", result.stdout + result.stderr)

    def test_fixture_corpus_traces_family_a_and_adversarial_sets(self) -> None:
        coverage: set[str] = set()
        invariants: set[str] = set()
        for path in FIXTURES.rglob("*.yaml"):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            coverage.update(fixture.get("covers", []))
            invariants.update(fixture.get("invariants", []))
        expected = {*(f"A{i}" for i in range(1, 13)), *(f"ADV-{i}" for i in range(1, 9))}
        self.assertEqual(set(), expected - coverage)
        self.assertIn("poc_boundaries_exact", invariants)
        self.assertIn("duplicate_transaction_replays_without_side_effects", invariants)

    def test_superseded_pre_v22_design_artifacts_are_removed(self) -> None:
        for relative in (
            "docs/superpowers/plans/2026-08-25-agent-shared-protocol.md",
            "docs/superpowers/specs/2026-08-25-agent-shared-protocol-design.md",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
