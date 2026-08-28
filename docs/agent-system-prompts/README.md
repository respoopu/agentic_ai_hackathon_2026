# Agent System Prompts

This directory defines a lifelong activity and career-exploration system for children. It helps a child explore interests through real-world activities while preserving data-quality, safety, parental-approval, and execution boundaries.

## Architecture

```text
Planner
  ├─ missing facts → Discovery → Compliance → Central Knowledge Base ─┐
  └────────────────────────────────────────────────────────────────────┘
                                  ↓
                              Guardian
                                  ↓
                        Explicit parent approval
                                  ↓
                               Broker
                                  ↓
                     Activity and child feedback
                                  ↓
                     Planner and Child Profile
```

The [Shared Protocol](shared-protocol.md) is the normative contract for messages, identifiers, approvals, errors, retries, privacy, and side effects. This README is an overview; the shared protocol takes precedence if they conflict.

## Agents

| Agent | Primary function | Must not do |
|---|---|---|
| [Orchestrator](orchestrator-agent.md) | Routes work and maintains workflow state | Perform specialist reasoning or bypass a required stage |
| [Planner](planner-agent.md) | Selects useful exploratory activities from trusted facts and child context | Search externally, approve safety, or execute activities |
| [Discovery Engine](discovery-engine.md) | Collects raw external information with provenance | Validate, recommend, or trust retrieved information |
| [Compliance](compliance-agent.md) | Validates freshness, accuracy, and structure | Perform parental or safety approval |
| [Guardian](guardian-agent.md) | Reviews safety and records explicit parental approval | Infer consent or execute bookings |
| [Broker](broker-agent.md) | Executes the exact approved activity idempotently | Substitute activities or act without matching approval |

## Standard workflow

1. Planner proposes an activity using trusted knowledge, or requests missing information.
2. Orchestrator sends external-information requests to Discovery.
3. Discovery returns raw, provenance-preserving records.
4. Compliance validates the records and proposes Central Knowledge Base mutations.
5. Planner completes an immutable activity version and hash.
6. Guardian reviews safety and presents that exact version to an authenticated parent.
7. Explicit approval is recorded with an activity version, price ceiling, and expiry.
8. Broker verifies approval and its idempotency ledger before any external side effect.
9. Outcomes and child feedback return through Orchestrator to Planner and Child Profile.

Raw Discovery results are not trusted before Compliance validation. Activities never reach Broker without Guardian review and explicit parental approval. A material activity change creates a new version and requires new review and approval.

## Data boundaries

- **Central Knowledge Base:** validated external facts about activities, providers, schedules, prices, locations, and eligibility.
- **Child Profile:** minimum-necessary personal information such as interests, experiences, feedback, preferences, and constraints.

Agents receive only the data needed for their role. Child-identifying data must not enter external searches, provider messages, logs, or knowledge records unless required and parent-authorized.

## Testing the contracts

Scenarios live outside production prompts under [`tests/agent-system-prompts/fixtures`](../../tests/agent-system-prompts/fixtures). The [fixture contract](../../tests/agent-system-prompts/fixture-schema.md) explains their format. Fixtures cover duplicate-booking prevention, approval-version matching, unknown provider outcomes, stale evidence, and prompt injection.

```powershell
& tests/agent-system-prompts/validate-fixtures.ps1
```
