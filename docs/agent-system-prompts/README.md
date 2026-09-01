# Hobbi agent-system prompts

These prompts are downstream interfaces derived from [architecture v2.2](../3-system/architecture.md). Hobbi helps ages 13-17 discover a hobby and reach a first attended session under finite money, time and tries.

## Topology

```text
Teen + parent -> deterministic Intake/Setup -> I0 -> Planner <-> G1 <-> Discovery -> CKB
                                                   |
                                                   G2
                                                   v
                                                Guardian
                                                   |
                                                   G3
                                                   v
                                                 Broker
                                                   |
                                                   G4
                                                   v
                                                Observer -> Personal Data -> next-cycle Planner

Compliance -> scheduled, off the request path -> CKB freshness + Personal Data plan-live flags
Validator  -> detached on-edge validation at I0 and G1-G4; calls no business agent
```

The five pipeline agents are Planner, Discovery, Guardian, Broker and Observer. Compliance is a scheduled monitor, not a request-path stage. Validator is the detached validation layer formerly called Orchestrator; it does not route work or own workflow state. Intake/Setup and I0 are deterministic application code.

## Prompt roster

| Component | Contract | Store boundary |
|---|---|---|
| [Planner](planner-agent.md) | Builds and replans a multi-item `Plan`; cheapest reversible experiments first | Reads CKB and Personal Data; writes neither |
| [Discovery](discovery-engine.md) | Receives a `Plan` only; finds and directly stores typed `ListingRecord` rows | Reads/writes CKB; never receives Personal Data |
| [Guardian](guardian-agent.md) | Per-listing provider vetting plus per-plan attendance/spend approval | Reads approved Plan, CKB and Personal Data; writes neither store |
| [Broker](broker-agent.md) | Sandboxed booking and atomic, idempotent ledger commitment | Reads Guardian-passed Plan; narrowly writes booking records and Personal Data ledger |
| [Observer](observer-agent.md) | Records attendance first, optional text debrief second, then adapts | Narrowly writes Personal Data attendance, preferences and ledger reconciliation |
| [Compliance](compliance-agent.md) | Scheduled freshness monitor | Reads both stores; writes CKB freshness and Personal Data plan-live flags |
| [Validator](validator-agent.md) | Shape, safety and arithmetic checks at I0/G1-G4 | Writes shape-only `gate_log`; no business calls |

The [shared protocol](shared-protocol.md) is normative. Role prompts narrow it but cannot weaken it.

## Control flow

1. Intake/Setup collects teen-readable consent, declared constraints, trusted-adult rules and optional cold-start seeds. I0 refuses ages below 13 with trusted-adult guidance and ages 18+ with general-services guidance; only ages 13-17 persist setup and reach Planner.
2. Planner reads both stores. If its candidate plan is thin, it sends the `Plan` alone through G1 to Discovery. Discovery deduplicates against CKB, searches a whitelist or cached replay, and writes small typed records directly to CKB. After two rounds Planner proceeds thin and names the binding constraint.
3. The candidate `Plan` passes G2. Guardian runs its two distinct checks and emits `GuardianVerdict`. After the second rejection it returns `escalated_to_adult` with both reasons and no third attempt.
4. A Guardian-passed Plan crosses G3 to sandboxed Broker. Broker commits the ledger once using `ledger_version` plus a unique `ledger_transaction_id`, emits `BookingRecord` and both teen/parent artefacts, then crosses G4 to Observer.
5. Both `attended` and `did_not_attend` reach Observer. Attendance outweighs the optional text debrief. Two consecutive no-shows trigger replan; sustained attendance can move try to commit; doing nothing can correctly return `hold_this_week`.
6. Booking failures and Compliance dead-listing replacements return to Planner and must traverse G2, Guardian and G3 before Broker is reachable again.

## Consent, privacy and PoC boundary

- Ages 13-17 may give teen-readable consent for preferences, attendance and plan history. Trusted-adult approval is a separate product control for spend, physical attendance and unverified providers.
- Discovery never receives identity, address, school or parental rules. This boundary is absolute.
- `PeerCohort` is opt-in contribution, bucketed, planning-area or two-digit postal-sector only, suppressed below k=5, identity-free and a ranking tiebreak only. It is simulated in the PoC.
- The PoC accepts in-app text `DebriefSubmission` only. Audio and messaging adapters are roadmap; future audio requires teen plus parent consent, an approved/local processor and deletion after extraction.
- Discovery offers live whitelisted search plus a cached replay with the same typed shape. Compliance is manually triggered over the seeded CKB. Broker has zero live provider/payment calls. Attendance and the 9-12 month longitudinal history are simulation-fed.

## Fixture validation

Fixtures use the JSON subset of YAML and every invariant name maps to executable Python. The canonical command is:

```bash
python -m unittest discover -s tests -t .
```

For the prompt corpus alone:

```bash
python tests/agent-system-prompts/validate_fixtures.py
```

See the [fixture contract](../../tests/agent-system-prompts/fixture-schema.md) for Family A and adversarial traceability.
