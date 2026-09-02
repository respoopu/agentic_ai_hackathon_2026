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
VALIDATOR = ROOT / "tests" / "agent-system-prompts" / "validate_fixtures.py"


class AgentPromptContractTests(unittest.TestCase):
    def run_fixture_validator(self, fixtures: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            for filename, fixture in fixtures.items():
                Path(temporary, filename).write_text(json.dumps(fixture), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "--fixtures", temporary, "--no-docs"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

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

    def test_broker_authorization_and_idempotency_docs_match_runtime(self) -> None:
        sources = {
            "architecture": (ROOT / "docs/3-system/architecture.md").read_text(
                encoding="utf-8"
            ),
            "protocol": (PROMPTS / "shared-protocol.md").read_text(encoding="utf-8"),
            "broker": (PROMPTS / "broker-agent.md").read_text(encoding="utf-8"),
            "validator": (PROMPTS / "validator-agent.md").read_text(encoding="utf-8"),
        }
        for name, source in sources.items():
            with self.subTest(source=name):
                self.assertIn("guardian_verdict_id", source)
                self.assertIn("logical commitment", source)
                self.assertIn("replay", source.lower())

    def test_fixture_validator_is_canonical_python_and_complete(self) -> None:
        self.assertTrue(VALIDATOR.is_file())
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_unknown_fixture_invariant_is_rejected(self) -> None:
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
        result = self.run_fixture_validator({"unknown.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unknown invariant", result.stdout + result.stderr)

    def test_discovery_payload_is_required_for_pii_isolation(self) -> None:
        fixture = json.loads(
            (FIXTURES / "discovery" / "private-cached-replay.yaml").read_text(encoding="utf-8")
        )
        del fixture["given"]["discovery_payload"]
        result = self.run_fixture_validator({"missing-payload.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("given.discovery_payload must be present", result.stdout + result.stderr)

    def test_nested_discovery_page_dump_is_rejected(self) -> None:
        fixture = json.loads(
            (FIXTURES / "discovery" / "private-cached-replay.yaml").read_text(encoding="utf-8")
        )
        fixture["expect"]["output"]["listing"]["raw_html"] = "<html>private page</html>"
        result = self.run_fixture_validator({"nested-page-dump.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("raw page content field raw_html", result.stdout + result.stderr)

    def test_fixture_forbidden_store_write_is_rejected(self) -> None:
        fixture = json.loads(
            (FIXTURES / "planner" / "actionable-thin-plan.yaml").read_text(encoding="utf-8")
        )
        fixture["expect"]["store_writes"] = ["Personal Data.preferences"]
        result = self.run_fixture_validator({"forbidden-write.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("forbidden store_writes", result.stdout + result.stderr)

    def test_fixture_skipped_or_extra_gate_is_rejected(self) -> None:
        fixture = json.loads(
            (FIXTURES / "discovery" / "private-cached-replay.yaml").read_text(encoding="utf-8")
        )
        fixture["expect"]["gates"] = []
        result = self.run_fixture_validator({"wrong-gate.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("required scenario gates were skipped", result.stdout + result.stderr)

    def test_intake_permission_boundary_is_enforced(self) -> None:
        fixture = json.loads(
            (FIXTURES / "intake" / "age-boundary-matrix.yaml").read_text(encoding="utf-8")
        )
        fixture["expect"]["store_reads"] = ["Personal Data"]
        result = self.run_fixture_validator({"intake-read.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("forbidden store_reads", result.stdout + result.stderr)

    def test_non_object_fixture_is_reported_without_crashing(self) -> None:
        result = self.run_fixture_validator({"array.yaml": []})
        combined = result.stdout + result.stderr
        self.assertNotEqual(0, result.returncode)
        self.assertIn("fixture root must be an object", combined)
        self.assertNotIn("Traceback", combined)

    def test_malformed_nested_value_is_reported_without_crashing(self) -> None:
        fixture = json.loads(
            (FIXTURES / "discovery" / "private-cached-replay.yaml").read_text(encoding="utf-8")
        )
        fixture["expect"]["output"] = []
        result = self.run_fixture_validator({"malformed-output.yaml": fixture})
        combined = result.stdout + result.stderr
        self.assertNotEqual(0, result.returncode)
        self.assertIn("could not evaluate", combined)
        self.assertNotIn("Traceback", combined)

    def test_cascade_fixtures_forbid_direct_business_agent_calls(self) -> None:
        cases = (
            ("compliance", "dead-listing-cascade.yaml", "planner"),
            ("broker", "actionable-failure-regated.yaml", "planner"),
        )
        for directory, filename, direct_call in cases:
            with self.subTest(filename=filename):
                fixture = json.loads((FIXTURES / directory / filename).read_text(encoding="utf-8"))
                fixture["expect"]["tool_calls"][direct_call] = 1
                result = self.run_fixture_validator({filename: fixture})
                self.assertNotEqual(0, result.returncode)
                self.assertIn("call Planner directly", result.stdout + result.stderr)

    def test_broker_fixture_requires_guardian_verdict_binding(self) -> None:
        fixture = json.loads(
            (FIXTURES / "broker" / "sandbox-idempotent-booking.yaml").read_text(
                encoding="utf-8"
            )
        )
        del fixture["expect"]["output"]["booking_record"]["guardian_verdict_id"]
        result = self.run_fixture_validator({"missing-verdict-binding.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("bind the matching Guardian verdict id", result.stdout + result.stderr)

    def test_broker_fixture_requires_stable_transaction_identity(self) -> None:
        fixture = json.loads(
            (FIXTURES / "broker" / "sandbox-idempotent-booking.yaml").read_text(
                encoding="utf-8"
            )
        )
        fixture["expect"]["output"]["booking_record"]["ledger_transaction_id"] = (
            "caller_supplied_tx"
        )
        result = self.run_fixture_validator({"changed-transaction-id.yaml": fixture})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("derive the stable transaction id", result.stdout + result.stderr)

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

    def test_e1_completion_language_and_evidence_are_current(self) -> None:
        discrepancies = (ROOT / "docs/4-decisions/discrepancies.md").read_text(
            encoding="utf-8"
        )
        tracker = (ROOT / "docs/5-delivery/outstanding.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("re-derivation checklist", discrepancies)
        self.assertNotIn("other four rows still need re-deriving", discrepancies)
        self.assertNotIn("canonical unittest suite passed 34 tests", discrepancies)
        self.assertNotIn("canonical unittest suite passed 34 tests", tracker)
        self.assertIn("agent-system contract tests passed", discrepancies)
        self.assertNotIn("PR #1 remains open for review", tracker)


if __name__ == "__main__":
    unittest.main()
