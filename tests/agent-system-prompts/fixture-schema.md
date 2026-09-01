# Agent-system prompt fixture contract - v2.2

Fixtures are executable external examples derived from [architecture v2.2](../../docs/3-system/architecture.md) and [evaluation Family A](../../docs/3-system/evaluation.md#2-family-a--invariants). They are not embedded in prompts and do not create a production test mode.

## Format

Each `.yaml` file uses the JSON subset of YAML 1.2. This gives readable YAML-compatible fixtures and dependency-free parsing through Python's standard `json` module.

Required top-level fields:

| Field | Contract |
|---|---|
| `fixture_version` | Exactly `2.2` |
| `id` | Repository-wide unique scenario id |
| `name` | Human-readable scenario |
| `agent` | `intake`, `planner`, `discovery`, `guardian`, `broker`, `observer`, `compliance`, `validator` or `protocol` |
| `given` | Inputs, state and observations |
| `expect.output` | Required typed output or control result |
| `expect.tool_calls` | Exact/maximum boundary call evidence used by named invariants |
| `expect.store_reads` | Expected read boundary |
| `expect.store_writes` | Expected write boundary |
| `expect.gates` | Gates traversed by the scenario |
| `invariants` | One or more executable names registered by `validate_fixtures.py` |
| `covers` | Traceability ids from `A1`-`A12` and `ADV-1`-`ADV-8` |

Unknown invariant names fail. Duplicate fixture ids, malformed documents, unknown coverage ids and missing Family A/adversarial coverage also fail.

## Coverage map

| Requirement | Fixture |
|---|---|
| A1 / ADV-1 | `guardian/unverified-provider-quarantine.yaml` |
| A2, A4 / ADV-3 | `planner/budget-parental-age-travel.yaml` |
| A3, A10 | `planner/zero-budget-skipped-cold-start.yaml` |
| A5 | `planner/caps-and-terminal-outcomes.yaml` |
| A6 | `discovery/private-cached-replay.yaml` |
| A7 | `broker/missing-guardian-verdict.yaml` |
| A8 | `observer/audio-rejected.yaml` |
| A9 | `planner/ranking-signals-only.yaml` |
| A11 / ADV-7 | `intake/age-boundary-matrix.yaml` |
| A12 / ADV-8 | `planner/peer-cohort-suppressed.yaml` |
| ADV-2 | `planner/actionable-thin-plan.yaml` |
| ADV-4 | `compliance/dead-listing-cascade.yaml` |
| ADV-5 | `planner/no-listing-coverage-gap.yaml` |
| ADV-6 | `guardian/two-rejections-escalate.yaml` |

Additional fixtures exercise the two Guardian checks, sandbox/idempotent Broker path including duplicate replay, booking-failure regating, attended/no-show Observer paths, second-no-show adaptation, try-to-commit, hold, debrief cap, dislike attribution/decay, manual Compliance caps, exact cached/manual/sandbox/simulation boundaries, exact store permissions and shape-only I0/G1-G4 logs.

## Validation

Canonical repository suite:

```bash
python -m unittest discover -s tests -t .
```

Focused fixture and prompt validation:

```bash
python tests/agent-system-prompts/validate_fixtures.py
```

The repository no longer maintains a separate PowerShell validator; one executable Python contract prevents the two paths from drifting.
