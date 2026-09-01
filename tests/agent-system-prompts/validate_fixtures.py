"""Dependency-free validator for architecture-v2.2 prompt fixtures.

Fixture files use the JSON subset of YAML 1.2 so the canonical judge path does
not need a YAML package.  Every named invariant is executable; unknown names
are errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.tools import COMPONENT_PERMISSIONS

DEFAULT_FIXTURES = Path(__file__).resolve().parent / "fixtures"
PROMPTS = ROOT / "docs" / "agent-system-prompts"
REQUIRED_COVERAGE = {
    *(f"A{i}" for i in range(1, 13)),
    *(f"ADV-{i}" for i in range(1, 9)),
}
REQUIRED_AGENTS = {
    "planner",
    "discovery",
    "guardian",
    "broker",
    "observer",
    "compliance",
    "validator",
    "intake",
    "protocol",
}

# Runtime-enforceable boundaries. Scenario fixtures may exercise any subset;
# anything outside the set is a contract violation. Intake is explicit here
# even though it is deterministic application code rather than an agent.
COMPONENT_BOUNDARIES = {
    component: {
        "reads": set(boundary["reads"]),
        "writes": set(boundary["writes"]),
    }
    for component, boundary in COMPONENT_PERMISSIONS.items()
}
COMPONENT_BOUNDARIES["protocol"] = {"reads": set(), "writes": set()}

REQUIRED_GATES_BY_FIXTURE = {
    "broker-actionable-failure-regated": {"G2", "G3"},
    "broker-duplicate-transaction-replay": {"G4"},
    "broker-missing-guardian-verdict": {"G3"},
    "broker-sandbox-idempotent-booking": {"G4"},
    "compliance-dead-listing-cascade": {"G2", "G3"},
    "discovery-private-cached-replay": {"G1"},
    "guardian-two-distinct-checks": {"G3"},
    "guardian-two-rejections-escalate": {"G3"},
    "guardian-unverified-provider-quarantine": {"G2"},
    "intake-age-boundary-matrix": {"I0"},
    "planner-budget-parental-age-travel": {"G2"},
    "planner-zero-budget-skipped-cold-start": {"G2"},
    "validator-shape-only-gates": {"I0", "G1", "G2", "G3", "G4"},
    "compliance-manual-scan-caps": set(),
    "observer-attendance-paths": set(),
    "observer-audio-rejected": set(),
    "observer-dislike-attribution-decay": set(),
    "observer-no-show-and-adaptation": set(),
    "planner-actionable-thin-plan": set(),
    "planner-caps-and-terminal-outcomes": set(),
    "planner-no-listing-coverage-gap": set(),
    "planner-peer-cohort-suppressed": set(),
    "planner-ranking-signals-only": set(),
    "protocol-poc-boundaries": set(),
    "protocol-store-permissions": set(),
}


def _fail(errors: list[str], source: str, message: str) -> None:
    errors.append(f"{source}: {message}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _expect(errors: list[str], source: str, condition: bool, message: str) -> None:
    if not condition:
        _fail(errors, source, message)


Invariant = Callable[[dict[str, Any], str, list[str]], None]
INVARIANTS: dict[str, Invariant] = {}


def invariant(name: str) -> Callable[[Invariant], Invariant]:
    def register(function: Invariant) -> Invariant:
        INVARIANTS[name] = function
        return function

    return register


@invariant("intake_age_matrix_enforced")
def _intake_age_matrix(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    cases = fixture["expect"]["output"].get("cases", [])
    by_age = {case.get("age"): case for case in cases}
    _expect(errors, source, set(by_age) == {11, 12, 13, 17, 18, 19}, "age matrix must contain 11, 12, 13, 17, 18 and 19")
    for age in (11, 12):
        case = by_age.get(age, {})
        _expect(errors, source, case.get("eligible") is False and case.get("referral") == "trusted_adult", f"age {age} must terminate with trusted-adult guidance")
    for age in (13, 17):
        case = by_age.get(age, {})
        _expect(errors, source, case.get("eligible") is True and case.get("planner_calls") == 1, f"age {age} must proceed to Planner")
    for age in (18, 19):
        case = by_age.get(age, {})
        _expect(errors, source, case.get("eligible") is False and case.get("referral") == "general_activity_services", f"age {age} must terminate with general-services guidance")
    for age in (11, 12, 18, 19):
        case = by_age.get(age, {})
        _expect(errors, source, case.get("planner_calls") == 0 and case.get("personal_data_writes") == 0, f"age {age} must terminate before planning or persistence")


@invariant("unverified_provider_quarantined")
def _unverified_quarantined(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("teen_visible") is False, "unverified private provider must not be teen-visible")
    _expect(errors, source, output.get("vetting_queue") == "trusted_adult", "unverified private provider must enter trusted-adult vetting")
    _expect(errors, source, calls.get("broker") == 0, "unverified private provider must not reach Broker")


@invariant("ledger_budget_balances")
def _ledger_budget(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    ledger = fixture["given"]["ledger"]
    total = fixture["expect"]["output"]["plan"]["total_cost_sgd"]
    remaining = ledger["money_total_sgd"] - ledger["money_spent_sgd"] - ledger["money_committed_sgd"]
    _expect(errors, source, total <= remaining, "plan cost exceeds money remaining")


@invariant("eligible_s0_plan")
def _eligible_s0(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    ledger = fixture["given"]["ledger"]
    plan = fixture["expect"]["output"]["plan"]
    _expect(errors, source, fixture["given"].get("declared_age") in range(13, 18), "S$0 case must be intake-eligible")
    _expect(errors, source, ledger.get("money_total_sgd") == 0, "S$0 fixture must declare a zero budget")
    _expect(errors, source, bool(plan.get("items")), "eligible S$0 fixture must produce a non-empty plan")
    _expect(errors, source, plan.get("total_cost_sgd") == 0 and all(item.get("cost_sgd") == 0 for item in plan.get("items", [])), "S$0 plan must be free")


@invariant("parental_age_travel_rules_hard_filtered")
def _hard_filters(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("parental_rule_won") is True, "parental rule must override teen preference")
    _expect(errors, source, output.get("age_ok") is True and output.get("travel_ok") is True, "plan must satisfy age and travel constraints")


@invariant("configured_caps_and_outcomes_exact")
def _caps_and_outcomes(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    counters = output.get("counters", {})
    _expect(errors, source, counters == {"replan_count": 3, "discovery_rounds": 2, "guardian_rejects": 2}, "counter boundaries must be exactly 3/2/2")
    outcomes = {case.get("case"): case for case in output.get("outcomes", [])}
    expected = {
        "booked": "autonomous_success",
        "hold_this_week": "autonomous_success",
        "escalated_to_adult": "designed_checkpoint_success",
        "no_viable_plan": "failed",
        "cap_breached": "failed",
    }
    for outcome, completion in expected.items():
        _expect(errors, source, outcomes.get(outcome, {}).get("completion") == completion, f"{outcome} must classify as {completion}")
    _expect(errors, source, outcomes.get("escalated_to_adult", {}).get("cap_hit") is True and outcomes.get("escalated_to_adult", {}).get("cap_breached") is False, "designed escalation is a cap hit, not a breach")
    _expect(errors, source, outcomes.get("cap_breached", {}).get("attempted_counter") == 3, "Guardian cap breach fixture must attempt a third rejection")


@invariant("discovery_payload_absolute_pii_isolation")
def _discovery_pii(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    payload = fixture["given"].get("discovery_payload")
    _expect(
        errors,
        source,
        isinstance(payload, Mapping),
        "given.discovery_payload must be present and be an object",
    )
    if not isinstance(payload, Mapping):
        return
    for key in ("teen_id", "address", "school", "parental_rule", "parental_rules"):
        _expect(errors, source, not _contains_key(payload, key), f"Discovery payload contains forbidden personal field {key}")


@invariant("typed_discovery_ckb_write")
def _typed_discovery_write(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    writes = fixture["expect"]["store_writes"]
    _expect(errors, source, writes == ["CKB.ListingRecord"], "Discovery must write only typed ListingRecord rows to CKB")
    for key in ("listing_id", "verification", "source_url", "last_seen_at"):
        _expect(errors, source, key in output.get("listing", {}), f"Discovery ListingRecord missing {key}")
    for key in ("raw_html", "page_dump"):
        _expect(errors, source, not _contains_key(output, key), f"Discovery output must not contain raw page content field {key}")


@invariant("cached_replay_matches_live_shape")
def _cached_replay(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("mode") == "cached_replay", "PoC replay must be explicitly labelled cached_replay")
    _expect(errors, source, output.get("schema_id") == "ListingRecord", "cached replay must match the live typed record shape")


@invariant("untrusted_content_never_executes")
def _untrusted_content(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, calls.get("untrusted_instruction") == 0, "retrieved instructions must remain inert")
    _expect(errors, source, output.get("suspected_prompt_injection") is True, "prompt injection must be flagged")


@invariant("broker_requires_guardian_verdict")
def _broker_guardian(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    calls = fixture["expect"]["tool_calls"]
    _expect(errors, source, fixture["given"].get("guardian_verdict_id") is None, "negative reachability fixture must omit Guardian verdict id")
    _expect(errors, source, calls.get("sandbox_provider") == 0 and calls.get("ledger_commit") == 0, "Broker must be unreachable without Guardian pass")


@invariant("poc_rejects_audio")
def _reject_audio(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("status") == "rejected" and output.get("reason") == "audio_not_supported_in_poc", "PoC must reject audio")
    _expect(errors, source, calls.get("persist_debrief") == 0, "rejected audio must not persist")


@invariant("ranking_signals_preserve_membership")
def _ranking_only(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    given = fixture["given"]
    base, seeded, disliked = map(set, (given["base_candidates"], given["seeded_candidates"], given["disliked_candidates"]))
    _expect(errors, source, base == seeded == disliked, "seeds and dislikes may reorder but never filter candidates")


@invariant("skipped_cold_start_supported")
def _skipped_cold_start(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    _expect(errors, source, fixture["given"].get("seeded_at") is None, "skipped cold-start fixture must use seeded_at=None")
    _expect(errors, source, bool(fixture["expect"]["output"].get("plan", {}).get("items")), "skipped cold start must still produce a plan")


@invariant("peer_cohort_k5_private_tiebreak_only")
def _peer_cohort(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    given, output = fixture["given"], fixture["expect"]["output"]
    peer = output.get("peer_cohort", {})
    _expect(errors, source, given.get("underlying_count", 99) < 5 and peer.get("suppressed") is True, "cohort below k=5 must be suppressed")
    for key in ("teen_id", "school", "count"):
        _expect(errors, source, not _contains_key(peer, key), f"PeerCohort must not contain {key}")
    _expect(errors, source, set(given.get("without_peer_signal", [])) == set(given.get("with_peer_signal", [])), "PeerCohort must not filter candidates")
    _expect(errors, source, output.get("display") is None, "suppressed cohort must display nothing")


@invariant("thin_plan_names_binding_constraint")
def _thin_plan(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("status") == "thin_plan" and bool(output.get("binding_constraint")), "thin plan must name an actionable binding constraint")


@invariant("no_listing_is_coverage_failure")
def _no_listing(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("outcome") == "no_viable_plan" and output.get("completion") == "failed", "no-listing result must be a failed no_viable_plan completion")
    _expect(errors, source, output.get("reason_code") == "ckb_coverage_gap", "no-listing result must identify the CKB coverage gap")


@invariant("dead_listing_replacement_rechecks_g2_g3")
def _dead_listing(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("path") == ["retire", "Planner", "G2", "Guardian", "G3", "Broker"], "dead-listing replacement must traverse Planner/G2/Guardian/G3")
    _expect(errors, source, set(output.get("notified", [])) == {"teen", "parent"}, "dead-listing cascade must notify teen and parent")
    for agent in ("planner", "guardian", "broker"):
        _expect(errors, source, calls.get(agent) == 0, f"Compliance must not call {agent.title()} directly")


@invariant("exactly_two_guardian_rejections_escalate")
def _guardian_rejections(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("guardian_rejects") == 2 and output.get("outcome") == "escalated_to_adult", "second Guardian rejection must escalate")
    _expect(errors, source, len(output.get("reason_codes", [])) == 2, "escalation must carry both rejection reasons")
    _expect(errors, source, calls.get("guardian_third_attempt") == 0, "a third Guardian attempt is forbidden")


@invariant("guardian_runs_two_distinct_checks")
def _guardian_two_checks(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    checks = fixture["expect"]["output"].get("checks", [])
    _expect(errors, source, checks == ["per_listing_provider_vetting", "per_plan_attendance_spend"], "Guardian must run the two v2.2 checks at distinct granularities")


@invariant("sandbox_booking_has_no_live_calls")
def _sandbox_booking(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("mode") == "sandbox" and output.get("status") == "booked", "PoC Broker must emit a sandboxed BookingRecord")
    _expect(errors, source, calls.get("live_provider") == 0 and calls.get("payment") == 0, "PoC Broker must make zero live-provider/payment calls")
    _expect(errors, source, bool(output.get("teen_preparation")) and bool(output.get("parent_reassurance")), "Broker must emit teen and parent artefacts")


@invariant("ledger_transaction_applies_exactly_once")
def _ledger_once(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, bool(output.get("booking_record", {}).get("ledger_transaction_id")), "booked record needs a ledger_transaction_id")
    _expect(errors, source, output.get("ledger_version_checked") is True and calls.get("ledger_commit") == 1, "ledger commit must be version-checked and applied once")
    _expect(errors, source, calls.get("duplicate_ledger_commit") == 0, "duplicate ledger commit must be suppressed")


@invariant("duplicate_transaction_replays_without_side_effects")
def _duplicate_transaction(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    given, output, calls = fixture["given"], fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    existing = given.get("existing_booking_record", {})
    _expect(errors, source, given.get("ledger_transaction_id") == existing.get("ledger_transaction_id"), "duplicate fixture must reuse the same ledger_transaction_id")
    _expect(errors, source, output.get("replayed") is True and output.get("booking_record") == existing, "duplicate must return the stored BookingRecord")
    _expect(errors, source, calls.get("sandbox_provider") == 0 and calls.get("ledger_commit") == 0, "duplicate must make no provider or ledger side effect")


@invariant("booking_failure_rechecks_g2_g3")
def _booking_failure(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, bool(output.get("actionable_reason")), "booking failure must be actionable")
    _expect(errors, source, output.get("slot_marked_unavailable") is True, "failed slot must be marked unavailable")
    _expect(errors, source, output.get("replacement_path") == ["Planner", "G2", "Guardian", "G3", "Broker"], "replacement booking must re-enter G2/G3")
    _expect(errors, source, calls.get("planner") == 0, "Broker must return a failure result rather than call Planner directly")


@invariant("observer_handles_attended_and_no_show")
def _observer_paths(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    paths = fixture["expect"]["output"].get("paths", {})
    _expect(errors, source, set(paths) == {"attended", "did_not_attend"}, "both attendance paths must reach Observer")
    _expect(errors, source, all(value.get("observer_calls") == 1 and value.get("attendance_written") is True for value in paths.values()), "each attendance path must be recorded by Observer")
    _expect(errors, source, paths.get("attended", {}).get("weight") == "primary", "attendance must be weighted above debrief")


@invariant("two_no_shows_trigger_replan")
def _two_no_shows(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("consecutive_no_shows") == 2 and output.get("action") == "replan", "second consecutive no-show must replan")
    _expect(errors, source, output.get("message_sent") is False, "second no-show must not nag")


@invariant("observer_try_commit_hold_and_debrief_cap")
def _observer_adaptation(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output, calls = fixture["expect"]["output"], fixture["expect"]["tool_calls"]
    _expect(errors, source, output.get("sustained_attendance_action") == "try_to_commit", "sustained attendance must support try-to-commit")
    _expect(errors, source, output.get("hold_outcome") == "hold_this_week", "Observer must support hold_this_week")
    _expect(errors, source, calls.get("debrief_prompt") == 1 and calls.get("debrief_reprompt") == 0, "Observer permits one debrief and no re-prompt")


@invariant("dislike_is_attributed_decaying_and_ranking_only")
def _dislike(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, set(output.get("attributions", [])) == {"activity", "instance", "unattributed"}, "DislikeSignal must support all attribution values")
    _expect(errors, source, output.get("half_life_days") == 90 and output.get("floor") == 0.15, "dislikes must decay with 90-day half-life and 0.15 floor")
    _expect(errors, source, output.get("membership_changed") is False and output.get("axis_moves_after_signals") == 2, "dislikes must be ranking-only and require two corroborating activity signals")


@invariant("manual_compliance_scan_obeys_caps")
def _compliance_caps(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    output = fixture["expect"]["output"]
    _expect(errors, source, output.get("trigger") == "manual_poc", "PoC Compliance must be manually triggered")
    _expect(errors, source, output.get("request_path_blocked") is False, "Compliance must stay off the request path")
    _expect(errors, source, output.get("listings_scanned", 99) <= 50 and output.get("max_fetches_for_any_domain", 99) <= 5, "Compliance scan exceeds 50 listings or 5 fetches/domain")


@invariant("shape_only_gate_log")
def _shape_gate_log(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    logs = fixture["expect"]["output"].get("gate_log", [])
    _expect(errors, source, [log.get("gate") for log in logs] == ["I0", "G1", "G2", "G3", "G4"], "Validator must check exactly I0 and G1-G4")
    for log in logs:
        _expect(errors, source, {"gate", "passed", "schema_id", "payload_size", "reason_codes", "checked_at"} <= set(log), "GateResult missing shape metadata")
        for key in ("payload", "content", "teen_id", "text"):
            _expect(errors, source, not _contains_key(log, key), f"gate log must not contain payload content field {key}")


@invariant("store_permission_matrix_exact")
def _store_matrix(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    matrix = fixture["expect"]["output"].get("matrix", {})
    expected = {
        "planner": {"reads": ["CKB", "Personal Data"], "writes": []},
        "discovery": {"reads": ["CKB", "external_sources"], "writes": ["CKB"]},
        "guardian": {"reads": ["approved_plan", "CKB", "Personal Data"], "writes": []},
        "broker": {"reads": ["guardian_passed_plan"], "writes": ["Personal Data.ledger", "booking_records"]},
        "observer": {"reads": ["AttendanceEvent", "BookingRecord", "DebriefSubmission"], "writes": ["Personal Data.attendance", "Personal Data.ledger", "Personal Data.preferences"]},
        "compliance": {"reads": ["CKB", "Personal Data"], "writes": ["CKB.freshness", "Personal Data.plan_live_flags"]},
        "validator": {"reads": ["inter_agent_payload_shape"], "writes": ["gate_log"]},
    }
    _expect(errors, source, matrix == expected, "store permission matrix does not match architecture v2.2")


@invariant("poc_boundaries_exact")
def _poc_boundaries(fixture: dict[str, Any], source: str, errors: list[str]) -> None:
    boundaries = fixture["expect"]["output"].get("boundaries", {})
    expected = {
        "discovery": "live_whitelist_plus_cached_replay",
        "compliance": "manual_seeded_ckb_scan",
        "broker": "sandbox_zero_live_provider_payment_calls",
        "observer": "in_app_text_with_simulated_attendance",
        "longitudinal": "simulated_9_to_12_month_replay",
        "peer_cohort": "simulated_prebucketed_k5",
    }
    _expect(errors, source, boundaries == expected, "PoC cached/manual/sandbox/simulation boundaries are not exact")


def validate_fixture(fixture: Any, source: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(fixture, dict):
        return [f"{source}: fixture root must be an object"]
    required = {"fixture_version", "id", "name", "agent", "given", "expect", "invariants", "covers"}
    missing = required - set(fixture)
    if missing:
        _fail(errors, source, f"missing required fields: {', '.join(sorted(missing))}")
        return errors
    _expect(errors, source, fixture["fixture_version"] == "2.2", "fixture_version must be 2.2")
    _expect(errors, source, fixture["agent"] in REQUIRED_AGENTS, f"unsupported agent {fixture['agent']!r}")
    _expect(errors, source, isinstance(fixture["given"], dict), "given must be an object")
    _expect(errors, source, isinstance(fixture["expect"], dict), "expect must be an object")
    _expect(errors, source, isinstance(fixture["invariants"], list) and bool(fixture["invariants"]), "invariants must be a non-empty list")
    _expect(errors, source, isinstance(fixture["covers"], list), "covers must be a list")
    for key in ("output", "tool_calls", "store_reads", "store_writes", "gates"):
        _expect(errors, source, key in fixture["expect"], f"expect missing {key}")
    if errors:
        return errors
    for key in ("store_reads", "store_writes", "gates"):
        _expect(
            errors,
            source,
            isinstance(fixture["expect"][key], list),
            f"expect.{key} must be a list",
        )
    if errors:
        return errors
    boundary = COMPONENT_BOUNDARIES[fixture["agent"]]
    for declared_key, allowed_key in (
        ("store_reads", "reads"),
        ("store_writes", "writes"),
    ):
        unexpected = set(fixture["expect"][declared_key]) - boundary[allowed_key]
        _expect(
            errors,
            source,
            not unexpected,
            f"forbidden {declared_key}: {', '.join(sorted(unexpected))}",
        )
    required_gates = REQUIRED_GATES_BY_FIXTURE.get(fixture["id"])
    if required_gates is not None:
        _expect(
            errors,
            source,
            set(fixture["expect"]["gates"]) == required_gates,
            "required scenario gates were skipped or changed",
        )
    if errors:
        return errors
    for name in fixture["invariants"]:
        check = INVARIANTS.get(name)
        if check is None:
            _fail(errors, source, f"unknown invariant {name!r}")
        else:
            try:
                check(fixture, source, errors)
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                _fail(errors, source, f"invariant {name!r} could not evaluate: {exc}")
    return errors


def validate_fixture_directory(root: Path, require_coverage: bool = True) -> list[str]:
    errors: list[str] = []
    ids: dict[str, Path] = {}
    coverage: set[str] = set()
    files = sorted(root.rglob("*.yaml")) if root.is_dir() else []
    if not files:
        return [f"{root}: no fixture files found"]
    for path in files:
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: not JSON-compatible YAML: {exc}")
            continue
        errors.extend(validate_fixture(fixture, str(path)))
        fixture_id = fixture.get("id") if isinstance(fixture, dict) else None
        if fixture_id in ids:
            errors.append(f"{path}: duplicate fixture id {fixture_id!r}; first seen in {ids[fixture_id]}")
        elif fixture_id:
            ids[fixture_id] = path
        if isinstance(fixture, dict) and isinstance(fixture.get("covers"), list):
            coverage.update(fixture["covers"])
    if require_coverage:
        unknown_coverage = coverage - REQUIRED_COVERAGE
        missing_coverage = REQUIRED_COVERAGE - coverage
        if unknown_coverage:
            errors.append(f"{root}: unknown coverage ids: {', '.join(sorted(unknown_coverage))}")
        if missing_coverage:
            errors.append(f"{root}: missing coverage ids: {', '.join(sorted(missing_coverage))}")
    return errors


def validate_docs() -> list[str]:
    errors: list[str] = []
    required = {
        "README.md", "shared-protocol.md", "planner-agent.md", "discovery-engine.md",
        "guardian-agent.md", "broker-agent.md", "observer-agent.md",
        "compliance-agent.md", "validator-agent.md",
    }
    missing = [name for name in sorted(required) if not (PROMPTS / name).is_file()]
    if missing:
        errors.append(f"{PROMPTS}: missing prompt files: {', '.join(missing)}")
    for path in PROMPTS.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        if (
            path.name.endswith("-agent.md") or path.name == "discovery-engine.md"
        ) and sum(1 for line in content.splitlines() if line.startswith("```")) != 2:
            errors.append(f"{path}: role prompt must contain exactly one fenced prompt")
        for match in re.finditer(r"\]\(([^)]+)\)", content):
            link = match.group(1).split("#", 1)[0]
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / link).resolve().exists():
                errors.append(f"{path}: broken link {link!r}")
    return errors


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--no-docs", action="store_true", help="validate fixtures only")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    custom_root = args.fixtures.resolve() != DEFAULT_FIXTURES.resolve()
    errors = validate_fixture_directory(args.fixtures, require_coverage=not custom_root)
    if not args.no_docs:
        errors.extend(validate_docs())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(list(args.fixtures.rglob('*.yaml')))} architecture-v2.2 fixtures; all named invariants executable")
    if not args.no_docs:
        print("PASS: agent prompt documentation validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
