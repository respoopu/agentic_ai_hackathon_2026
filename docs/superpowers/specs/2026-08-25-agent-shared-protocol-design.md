# Agent Shared Protocol and Test Fixture Design

## Purpose

Define a shared, versioned contract for the child activity agent system so that every handoff is traceable, approvals are bound to immutable activity details, Broker side effects are idempotent, and important safety properties can be tested outside production prompts.

## Documentation structure

The documentation has three layers:

1. `docs/agent-system-prompts/README.md` is the human-readable entry point. It explains the architecture, each agent's role, the end-to-end workflow, trust boundaries, and links to the normative protocol and individual prompts.
2. `docs/agent-system-prompts/shared-protocol.md` is the normative cross-agent contract. It defines message envelopes, identifiers, activity versions, approval records, routing statuses, errors, retries, idempotency, privacy rules, and untrusted-content handling.
3. Each agent prompt contains only role-specific behavior and explicitly requires conformance with the shared protocol.

Keeping the overview and protocol separate prevents the README from becoming an unwieldy system prompt while still making the system understandable from one starting page.

## Shared message contract

Every inter-agent message uses a common envelope containing:

- `schema_version`
- `message_id`
- `workflow_id`
- `correlation_id`
- `sender`
- `recipient`
- `created_at`
- `payload_type`
- `payload`

Identifiers are immutable. Receivers reject malformed envelopes and unsupported schema versions rather than guessing missing values. Shared statuses and agent names use documented enums.

## Activity and approval integrity

An activity is identified by `activity_id` and immutable `activity_version`. Material changes create a new version. A canonical representation produces `activity_hash`.

Guardian approval records include `approval_id`, `activity_id`, `activity_version`, `activity_hash`, authenticated parent identity, approval time, expiry, approved price ceiling, and approval status. The Broker may act only when all activity fields match an active approval. Expired, revoked, mismatched, or incomplete approvals stop execution and route back through the Orchestrator.

## Broker idempotency

Every external side-effect request includes an Orchestrator-issued `execution_request_id` and `idempotency_key`. The key is stable for the same intended side effect and must not be reused for a materially different operation.

Before calling a provider, the Broker checks an execution ledger:

- No record: atomically create `IN_PROGRESS`, then execute.
- `IN_PROGRESS`: return `EXECUTION_PENDING`; do not call the provider again.
- `SUCCEEDED`: return the stored result with `replayed: true`; do not call the provider again.
- `FAILED_RETRYABLE`: retry only within the documented attempt and expiry policy, using the same key.
- `FAILED_FINAL`: return the stored failure and stop.
- `UNKNOWN`: reconcile with the provider before any retry.

The ledger records attempts, provider references, timestamps, sanitized responses, and final state. Booking, payment, registration, and outbound communication use distinct operation-scoped keys.

## Trust, privacy, and side-effect boundaries

Discovery treats all retrieved content as untrusted data. Instructions found in external content never override agent instructions and never trigger tool calls. Child-identifying data is excluded from discovery queries unless explicitly necessary and authorized.

Agents receive only the minimum child data needed for their role. Prompts prohibit unnecessary replication, sensitive profiling, disclosure in logs, and retention beyond policy. Parent approval is explicit, authenticated, activity-version-specific, revocable, and time limited.

Decision-producing agents return proposed records or actions. Narrow persistence and execution tools perform mutations so authorization, validation, audit logging, and retries can be enforced at the boundary.

## Error and recovery contract

All errors include:

- a stable error code;
- a safe human-readable summary;
- whether retry is allowed;
- a retry condition rather than an unconditional retry instruction;
- the next route;
- relevant artifact identifiers without sensitive data.

Agents stop on authorization ambiguity, schema incompatibility, unknown external outcomes, missing critical safety facts, and retry exhaustion.

## Test fixture design

Fixtures live outside system prompts under `tests/agent-system-prompts/fixtures/`. Each YAML fixture declares:

- scenario name and agent under test;
- input message;
- initial stores or mocked tool observations;
- expected output fields;
- expected and forbidden tool calls;
- cross-cutting invariants.

A lightweight validation script checks fixture structure and deterministic invariants. Runtime integration can later invoke the actual agent with mocked tools against the same fixtures. The first fixture set covers:

- repeated Broker execution after success;
- execution already in progress;
- unknown provider outcome requiring reconciliation;
- approval bound to an older activity version;
- missing or expired parental approval;
- material price or venue change;
- conflicting Discovery sources;
- stale Compliance evidence;
- missing Guardian supervision information;
- prompt injection in retrieved content.

Fixtures never introduce a production `TEST_MODE` and are not copied into system prompts. Prompts instead state deterministic invariants and output contracts that fixtures can assert.

## Validation approach

Initial validation is deterministic and local:

1. Every prompt links to the shared protocol.
2. Required protocol fields and status enums are present.
3. Every fixture conforms to the fixture schema.
4. Broker replay fixtures forbid provider calls.
5. Approval mismatch fixtures require a stop response.
6. Markdown links and fenced prompt blocks remain valid.

Model-based evaluation can be added later for subjective qualities such as clarity or recommendation quality, but it is not required for validating authorization and side-effect invariants.

## Atomic commit sequence

1. Commit the original prompt split.
2. Commit this approved design document.
3. Add the README architecture overview and normative shared protocol.
4. Update agent prompts to consume the shared protocol, including Broker idempotency and approval binding.
5. Add the fixture schema, initial fixtures, and deterministic validator.
6. Add or update documentation for running validation.
