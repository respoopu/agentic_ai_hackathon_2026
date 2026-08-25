# Agent Shared Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the multi-agent prompt set conform to a shared, testable protocol with version-bound parental approval and idempotent Broker execution.

**Architecture:** The README is the human entry point, while `shared-protocol.md` is the normative cross-agent contract. Role prompts reference that contract and contain only role-specific rules. JSON-compatible YAML fixtures plus a dependency-free Python validator test structural and safety invariants without embedding test cases in production prompts.

**Tech Stack:** Markdown, JSON-compatible YAML 1.2 fixtures, Python 3.11 standard library, Git.

---

### Task 1: Architecture overview and normative protocol

**Files:**
- Modify: `docs/agent-system-prompts/README.md`
- Create: `docs/agent-system-prompts/shared-protocol.md`

- [ ] **Step 1: Expand the README**

Document the purpose, six agent roles, end-to-end workflow, external-knowledge and personal-data trust boundaries, distinction between overview and normative protocol, prompt links, and test-fixture links.

- [ ] **Step 2: Define the shared protocol**

Add normative sections for message envelopes, agent and status enums, activity identity and material changes, approval records, Broker execution records, errors, retry stop conditions, external-content isolation, privacy, timestamps, and schema evolution.

- [ ] **Step 3: Verify documentation structure**

Run:

```powershell
python tests/agent-system-prompts/validate_fixtures.py --docs-only
```

Before the validator exists, verify manually that every README link resolves and every required protocol heading appears once.

- [ ] **Step 4: Commit**

```powershell
git add docs/agent-system-prompts/README.md docs/agent-system-prompts/shared-protocol.md
git commit -m "docs(agents): define shared workflow protocol"
```

### Task 2: Role prompt conformance and Broker idempotency

**Files:**
- Modify: `docs/agent-system-prompts/orchestrator-agent.md`
- Modify: `docs/agent-system-prompts/planner-agent.md`
- Modify: `docs/agent-system-prompts/discovery-engine.md`
- Modify: `docs/agent-system-prompts/compliance-agent.md`
- Modify: `docs/agent-system-prompts/guardian-agent.md`
- Modify: `docs/agent-system-prompts/broker-agent.md`

- [ ] **Step 1: Add protocol conformance to all prompts**

Require every input and output to use the shared envelope. Require preservation of workflow, correlation, activity-version, and authorization identifiers. Replace incompatible routing values and error shapes with shared enums.

- [ ] **Step 2: Harden trust boundaries**

Add Discovery rules treating retrieved instructions as untrusted data. Add minimum-necessary child-data rules to all agents. Require Compliance to propose a knowledge mutation rather than silently persisting unvalidated data.

- [ ] **Step 3: Bind Guardian approval to activity state**

Require approval records to contain `approval_id`, `activity_id`, `activity_version`, `activity_hash`, `approved_by`, `approved_at`, `expires_at`, `maximum_total_cost`, and `status`. Define expiry, revocation, and material-change behavior.

- [ ] **Step 4: Add Broker execution state machine**

Require `execution_request_id`, an operation-scoped `idempotency_key`, approval matching, and ledger lookup before side effects. Define `IN_PROGRESS`, `SUCCEEDED`, `FAILED_RETRYABLE`, `FAILED_FINAL`, and `UNKNOWN`, including replay and reconciliation behavior.

- [ ] **Step 5: Verify prompt structure**

Run a PowerShell check confirming every prompt contains `SHARED PROTOCOL`, exactly one opening and closing fence, and no unsupported legacy routing enum.

- [ ] **Step 6: Commit**

```powershell
git add docs/agent-system-prompts/*-agent.md docs/agent-system-prompts/discovery-engine.md
git commit -m "docs(agents): enforce shared protocol invariants"
```

### Task 3: Fixture schema and validator using test-first development

**Files:**
- Create: `tests/agent-system-prompts/fixture-schema.md`
- Create: `tests/agent-system-prompts/validate_fixtures.py`
- Create: `tests/agent-system-prompts/test_validate_fixtures.py`

- [ ] **Step 1: Write failing validator tests**

Use `unittest` and temporary JSON-compatible YAML files. Cover a valid fixture, a missing required field, a Broker replay that incorrectly permits a provider call, an approval mismatch that fails to stop, duplicate fixture IDs, missing documentation links, and unbalanced prompt fences.

- [ ] **Step 2: Run tests and confirm RED**

```powershell
python -m unittest tests/agent-system-prompts/test_validate_fixtures.py -v
```

Expected: failure because `validate_fixtures.py` does not exist.

- [ ] **Step 3: Implement the minimal validator**

Use only `argparse`, `json`, `pathlib`, and `sys`. Parse `.yaml` files as JSON, validate required keys and types, enforce named deterministic invariants, detect duplicate IDs, check documentation links, and check prompt fence balance.

- [ ] **Step 4: Run tests and confirm GREEN**

```powershell
python -m unittest tests/agent-system-prompts/test_validate_fixtures.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Document the fixture contract**

Explain that fixtures use the JSON subset of YAML 1.2, list required fields, define tool-call expectations and supported invariants, and provide the validator command.

- [ ] **Step 6: Commit**

```powershell
git add tests/agent-system-prompts/fixture-schema.md tests/agent-system-prompts/validate_fixtures.py tests/agent-system-prompts/test_validate_fixtures.py
git commit -m "test(agents): add fixture contract validator"
```

### Task 4: Initial safety and idempotency fixtures

**Files:**
- Create: `tests/agent-system-prompts/fixtures/broker/duplicate-booking-request.yaml`
- Create: `tests/agent-system-prompts/fixtures/broker/execution-in-progress.yaml`
- Create: `tests/agent-system-prompts/fixtures/broker/unknown-provider-outcome.yaml`
- Create: `tests/agent-system-prompts/fixtures/broker/activity-version-mismatch.yaml`
- Create: `tests/agent-system-prompts/fixtures/guardian/expired-parental-approval.yaml`
- Create: `tests/agent-system-prompts/fixtures/guardian/missing-supervision-information.yaml`
- Create: `tests/agent-system-prompts/fixtures/compliance/conflicting-prices.yaml`
- Create: `tests/agent-system-prompts/fixtures/compliance/stale-schedule.yaml`
- Create: `tests/agent-system-prompts/fixtures/discovery/prompt-injection-content.yaml`

- [ ] **Step 1: Add fixtures one scenario at a time**

Each fixture must define `fixture_version`, `id`, `name`, `agent`, `given`, `expect.output`, `expect.tool_calls`, and `invariants`. Broker replay fixtures must expect zero provider calls; mismatch and expired-approval fixtures must expect a stop status.

- [ ] **Step 2: Run the validator after each fixture group**

```powershell
python tests/agent-system-prompts/validate_fixtures.py
```

Expected: all fixtures and prompt documentation pass.

- [ ] **Step 3: Commit**

```powershell
git add tests/agent-system-prompts/fixtures
git commit -m "test(agents): add protocol safety fixtures"
```

### Task 5: Final documentation and verification

**Files:**
- Modify: `docs/agent-system-prompts/README.md`
- Modify: `tests/agent-system-prompts/fixture-schema.md`

- [ ] **Step 1: Confirm run instructions and links**

Ensure the README links to the protocol, every prompt, the fixture contract, and the fixture directory. Ensure the fixture contract contains the exact local validation command.

- [ ] **Step 2: Run the complete verification suite**

```powershell
python -m unittest tests/agent-system-prompts/test_validate_fixtures.py -v
python tests/agent-system-prompts/validate_fixtures.py
git diff --check HEAD~4..HEAD
git status --short --branch
```

Expected: unit tests pass, fixture validation passes, no whitespace errors, and the worktree is clean on `feat/agent-system-prompts`.

- [ ] **Step 3: Commit only if final documentation changed**

```powershell
git add docs/agent-system-prompts/README.md tests/agent-system-prompts/fixture-schema.md
git commit -m "docs(agents): document protocol validation workflow"
```
