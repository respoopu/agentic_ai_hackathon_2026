# Backend implementation checklist

Branch: `codex/backend-implementation`
Base: `origin/main` at `ba44bb5`
Scope: complete `OW-05`, `OW-06`, `OW-15`, and `OW-16` without rebuilding the merged CKB or changing the merged agent prompts.

## How this checklist is maintained

Each task moves through `Planned` → `Implemented` → `Reviewed` → `Reconciled`.

- **Implemented** means the code or artifact exists.
- **Reviewed** means its diff, failure paths, permissions, and relevant tests were inspected.
- **Reconciled** means it agrees with architecture v2.2, the merged prompt contracts, adjacent modules, and the full test suite.
- A checkbox is marked only at `Reconciled`. Evidence is recorded in the final column.

## 0. Branch and baseline

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | B-01 | Refresh `origin/main` and create `codex/backend-implementation` from the merged tip. | Reconciled | Branch created from `origin/main` at `ba44bb5`; clean starting tree. |
| [x] | B-02 | Inventory the merged architecture, prompt contracts, CKB schemas/loader, fixtures, tests, and open implementation tracker items. | Reconciled | Confirmed PRs #1–#3 foundations; identified `OW-05`, `OW-06`, `OW-15`, and `OW-16` as the backend scope. |
| [x] | B-03 | Avoid rebuilding merged CKB/prompt work; review the final diff for accidental duplication or prompt drift. | Reconciled | No prompt, seed loader/builder, draft, or quarantine file changed. The only merged CKB-schema edit is the reviewed A12 fix that makes `PeerCohort` reject identity extras. |

## 1. Canonical state and schemas

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | S-01 | Add named runtime/model/loop constants for all architecture caps. | Reconciled | `src/constants.py` is the single source for request, Discovery, and Compliance caps and fixed model IDs. |
| [x] | S-02 | Implement strict `BudgetLedger`, `SessionRequest`, `IntakeResult`, `PlanItem`, and `Plan` models with non-negative values and balanced totals. | Reconciled | Schema tests reject over-commitment, altered totals, duplicates, empty plans, and unnamed thin plans. |
| [x] | S-03 | Implement `GuardianVerdict`, `BookingRecord`, `AttendanceEvent`, `DebriefRecord`, and `DebriefSubmission`. | Reconciled | Booking authorization is required structurally; debrief schema is strict in-app text only. |
| [x] | S-04 | Implement `Axis`, `DislikeSignal`, and `PreferenceModel`, including provenance confidence ordering and dislike decay. | Reconciled | Seed confidence is capped, attendance evidence is stronger, and the 0.15 decay floor is tested. |
| [x] | S-05 | Implement strict `GateResult`, `TokenUsage`, and `HobbiState` contracts with append-only event fields and exact terminal outcomes. | Reconciled | LangGraph reducers append bookings/gates/tokens; gate payload content and token usage remain separate. |
| [x] | S-06 | Review schema serialization, timezone handling, Decimal behavior, unknown-field rejection, and compatibility with existing `ListingRecord`/`Listing`. | Reconciled | Dependency-backed CKB/schema suite passes; `PeerCohort` now structurally rejects identity extras. |

## 2. Personal Data SQLite store

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | D-01 | Create idempotent SQLite migrations for profiles, consent, rules/constraints, preferences, approvals, plans, bookings, attendance, debriefs, ledger transactions, and plan-live flags. | Reconciled | Reopening initialized file databases is tested; migrations are idempotent `CREATE TABLE IF NOT EXISTS` statements. |
| [x] | D-02 | Implement eligible-profile setup and read APIs, including optional cold-start seed persistence after I0 only. | Reconciled | Ages 12/18 and missing authority produce zero writes; eligible and skipped-seed setup tests pass. |
| [x] | D-03 | Implement narrow Planner/Guardian read views without exposing write capabilities. | Reconciled | Separate Planner and Guardian snapshots expose only their documented read surfaces. |
| [x] | D-04 | Implement approval persistence and matching by plan/listing for provider, attendance, and spend authorization. | Reconciled | Verdict identity includes all approval IDs; G3 and the store reject absent/rejected/mismatched authorization. |
| [x] | D-05 | Implement optimistic ledger versioning and an atomic Broker booking transaction. | Reconciled | Multi-item plans commit under one version; stale/budget/hour/tries paths fail before mutation. |
| [x] | D-06 | Derive/reserve a stable transaction ID per logical plan-item commitment and make retries exactly-once. | Reconciled | Sequential and concurrent duplicate tests apply one ledger effect and return the same stored booking (`OW-15` code path). |
| [x] | D-07 | Implement narrow Observer attendance/debrief reconciliation and preference updates. | Reconciled | Attendance, ledger reconciliation, optional debrief, and preferences commit atomically; exact replay is a no-op. |
| [x] | D-08 | Implement Compliance live-plan lookup and dead-listing flag writes. | Reconciled | Runtime and API cascade tests flag only live plans containing the retired listing. |
| [x] | D-09 | Review transaction rollback, concurrency, foreign keys, uniqueness, restart persistence, and store permission boundaries. | Reconciled | Temporary-file, reopen, stale-version, rollback, uniqueness, and concurrent replay tests pass. |

## 3. Deterministic intake and validation gates

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | V-01 | Implement pure I0 age/consent validation for ages below 13, 13–17, and 18+. | Reconciled | Runtime and fixture age matrices cover 11, 12, 13, 17, 18, and 19 with correct referrals. |
| [x] | V-02 | Implement Intake/Setup orchestration for eligible persistence, trusted-adult authority, constraints, ledger, and optional seeds. | Reconciled | Setup persists only after a passing I0 and preserves learned preferences on later setup edits. |
| [x] | V-03 | Implement detached G1 validation for PII-free Plans and sourced typed Discovery records with no raw page content. | Reconciled | Runtime privacy test and existing nested-page-dump mutation test both fail closed. |
| [x] | V-04 | Implement G2 validation for plan shape, CKB resolvability, session cost integrity, and remaining-budget arithmetic. | Reconciled | Runtime tests cover cost mismatch, missing/dead listings, stale ledger, and all three currencies. |
| [x] | V-05 | Implement G3 validation for a present approved verdict matching `plan_id`, verified/adult-approved providers, and required attendance/spend approvals. | Reconciled | Broker independently requires G3 before saving or committing (`OW-15` code path). |
| [x] | V-06 | Implement replay-safe G4 validation for well-formed bookings and exactly-once ledger application. | Reconciled | Fresh commit and legitimate replay pass; transaction reuse is rejected by the store. |
| [x] | V-07 | Emit shape-only gate logs that never contain payloads, personal identifiers, or debrief text. | Reconciled | Serialized gate tests confirm verdict and transaction identifiers never enter the log. |
| [x] | V-08 | Enforce fixture-declared reads, writes, and traversed gates against a canonical matrix including Intake/Setup. | Reconciled | New boundary and required-gate mutation tests pass; Intake is explicit (`OW-16`). |

## 4. Six agent implementations

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | A-01 | Implement Planner candidate filtering, cheapest/reversible sequencing, ranking-only preferences, peer-cohort tie-break, thin-plan handling, and S$0/skipped-seed support. | Reconciled | Runtime A3/A4/A9/A10/A12 tests pass; Planner receives read snapshots and has no store mutation method. |
| [x] | A-02 | Implement Discovery cached replay plus whitelisted live fetch/extraction with typed CKB writes and request-level round caps. | Reconciled | Official ActiveSG replay validates as unverified; replay idempotency, live whitelist rejection, G1, and graph round caps are enforced. |
| [x] | A-03 | Implement Guardian’s distinct per-listing vetting and per-plan attendance/spend checks. | Reconciled | Verified, unverified, paid, missing-attendance, mismatch, and two-rejection paths are tested. |
| [x] | A-04 | Implement sandbox Broker availability checks, stable transaction IDs, booking/confirmation artifacts, actionable failures, and atomic commitment. | Reconciled | Multi-item and concurrent replay tests prove zero duplicate effects; implementation exposes no live provider/payment/message client. |
| [x] | A-05 | Implement Observer attendance-first adaptation, optional text debrief extraction, dislike attribution/decay, two-no-show replan, repeat-attendance commit, and `hold_this_week`. | Reconciled | Runtime no-show test plus replay data cover text debrief, replan, commit, hold, audio rejection, and one-event idempotency. |
| [x] | A-06 | Implement manually triggered Compliance scan with listing/domain caps and retire-to-replan flags. | Reconciled | Caps are model-enforced; runtime and API tests prove off-path scan, flagging, and application-owned cascade. |
| [x] | A-07 | Define and enforce per-agent tool allow-lists and structured model-output seams. | Reconciled | Fail-closed permission matrix includes Intake/Validator; optional Bedrock runner binds merged prompts to Pydantic output schemas. |

## 5. LangGraph, runtime, and API

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | R-01 | Build the typed LangGraph pipeline with Planner, optional Discovery loop, G2, Guardian/replan loop, G3, Broker, and G4. | Reconciled | Happy/API paths traverse I0 → G2 → optional G1 → G2 → G3 → per-booking G4. |
| [x] | R-02 | Enforce `MAX_REPLANS`, `MAX_DISCOVERY_ROUNDS`, and `MAX_GUARDIAN_REJECTIONS` in state independently of model judgment. | Reconciled | Constants drive routers; runtime second-rejection test and merged exact-cap fixtures pass. |
| [x] | R-03 | Implement Broker-failure and Compliance-retirement replacement paths through fresh G2 → Guardian → G3 authorization. | Reconciled | API cascade test proves a dead slot gets a new Plan and verdict through fresh G2/G3 before Broker. |
| [x] | R-04 | Add persistent SQLite thread checkpoints with an in-memory test option. | Reconciled | Test closes and reopens the runtime, resumes the same thread, and observes no duplicate append-only records. |
| [x] | R-05 | Add Bedrock model factory/configuration using fixed model IDs, region validation, token capture, and a deterministic offline model seam. | Reconciled | Imports/tests/simulation make no AWS call; live factory is lazy with fixed IDs and actionable region validation. |
| [x] | R-06 | Add local `POST localhost:8080` JSON entrypoint and AgentCore-ready callable seam without a front-end dependency. | Reconciled | Service tests cover health, full intake/plan, and compliance; attendance/debrief is typed through Observer. |
| [x] | R-07 | Add `.env.example`, dependency pins/ranges, and README setup/run/API/module guidance. | Reconciled | Root README documents canonical commands, CKB publication boundary, API operations, and offline/live seams. |

## 6. Evaluation and simulation

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | E-01 | Add synthetic eligible profiles, separate age-boundary profiles, adversarial cases, and 9–12 month synthetic history. | Reconciled | 12 eligible profiles, a separate six-age matrix, merged adversarial fixtures, and a 12-cycle labelled replay are committed. |
| [x] | E-02 | Implement Family A executable invariants against runtime behavior, including caps, S$0, vetting, reachability, idempotency, privacy, and ranking-only signals. | Reconciled | Dedicated runtime invariant tests plus merged fixture invariants cover A1–A12; full suite passes. |
| [x] | E-03 | Implement eligible-profile harness and collect Family B system/product rates with denominators and zero-denominator handling. | Reconciled | Twelve eligible runs emit measured schema/tool/completion/safety/product numerators and denominators. |
| [x] | E-04 | Implement longitudinal replay showing old plan → signal → reasoning → new plan diffs. | Reconciled | Replay carries text debrief, two no-shows, one-cycle replan, recovery, commit, holds, and 10/12 finite tries used. |
| [x] | E-05 | Implement static-recommender counterfactual and compute B14/B15 for both arms. | Reconciled | `sim.counterfactual` reports both arms for first attendance and 12-cycle adherence. |
| [x] | E-06 | Include at least one correct `hold_this_week` decision in the replay. | Reconciled | Two of twelve cycles hold; report classifies the 16.7% hold rate as adaptive behavior. |
| [x] | E-07 | Implement `python -m sim.report` as the one-command reproducible metrics report. | Reconciled | B1–B15 all emit; B6 is explicitly unmeasured pending real judge/human scoring rather than invented. |

## 7. Final reconciliation and pull request

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | F-01 | Run focused tests after each implementation group and the complete canonical test suite at the end. | Reconciled | Final dependency-backed command: 83 tests passed in 1.2 seconds; dependency integrity and diff checks pass. |
| [x] | F-02 | Run the eligible simulation, counterfactual, one-command report, and local API smoke test. | Reconciled | All three module commands exit 0; HTTP smoke returned `{"ok":true,"service":"hobbi","ckb_records":0}`. |
| [x] | F-03 | Perform a final code review for correctness, authorization, privacy, concurrency, loop bounds, error handling, and accidental scope drift. | Reconciled | Fixed multi-item versioning, strict peer privacy, checkpoint allow-listing, and cross-profile ID ownership; targeted Ruff pass is clean. |
| [x] | F-04 | Reconcile code, tests, README, tracker status, and this checklist with architecture v2.2 and merged prompt contracts. | Reconciled | `OW-05`, `OW-06`, and `OW-16` are implementation-complete pending merge; `OW-15` code is complete while source-document closure stays visible because merged prompts were kept final. |
| [x] | F-05 | Inspect the complete diff and repository for secrets, generated junk, and unrelated changes. | Reconciled | Secret scan is clean; ignored runtime/venv artifacts are absent from the diff; no merged prompt or CKB source-data file changed. |
| [x] | F-06 | Commit and push `codex/backend-implementation`, then open a PR to `main` with summary, validation evidence, risks, and scope boundaries. | Reconciled | Opened [PR #4](https://github.com/respoopu/agentic_ai_hackathon_2026/pull/4) to `main`; its description records validation evidence and the CKB/prompt boundaries. |
