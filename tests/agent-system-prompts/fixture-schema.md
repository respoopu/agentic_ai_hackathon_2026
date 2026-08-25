# Agent System Prompt Fixture Contract

Fixtures are external examples used to verify deterministic safety and workflow invariants. They are not embedded in production prompts and do not enable a production test mode.

## Format

Fixture files use the JSON subset of YAML 1.2. This keeps them valid YAML while allowing dependency-free parsing with PowerShell's built-in JSON parser.

Every `.yaml` fixture contains:

- `fixture_version`: fixture contract version, currently `1.0`.
- `id`: repository-wide unique scenario identifier.
- `name`: short human-readable scenario.
- `agent`: agent under test.
- `given`: input message, store state, and tool observations.
- `expect.output`: required output fields.
- `expect.tool_calls`: expected call counts by tool boundary.
- `invariants`: deterministic rules enforced by the validator.

Supported cross-cutting invariants are:

- `broker_replay_has_no_provider_call`
- `approval_mismatch_stops_execution`
- `unknown_outcome_requires_reconciliation`
- `unsafe_or_expired_approval_stops_execution`
- `untrusted_content_never_executes`

Agent-specific fixtures may also include descriptive invariants that will be exercised by a future runtime agent evaluator. Unknown invariant names are preserved rather than treated as validation errors.

## Validation

Run unit tests:

```powershell
& tests/agent-system-prompts/test_validate_fixtures.ps1
```

Run repository fixture and documentation validation:

```powershell
& tests/agent-system-prompts/validate-fixtures.ps1
```

Validate documentation without requiring fixtures:

```powershell
& tests/agent-system-prompts/validate-fixtures.ps1 -DocsOnly
```
