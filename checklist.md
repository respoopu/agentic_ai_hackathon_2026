# Backend implementation checklist

Branch: `codex/backend-implementation`
Base: `origin/main` at `ba44bb5`
Scope: implement `OW-05`, `OW-06`, `OW-15`, and `OW-16` without rebuilding the merged CKB or changing the merged agent prompts; any acceptance gap without executable evidence remains open.

Merged baseline: PR #4 and PR #5 are on `main`; the post-merge suite passes 140 tests. Active follow-up work is tracked in the appended OW-06 section on branch `codex/ow-06-executable-evaluation`.

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
| [x] | D-04 | Implement approval persistence and matching by plan/listing for provider, attendance, and spend authorization. | Reconciled | Trusted-adult approvals live in a separate table keyed to one teen and Plan; spend approval carries a tested amount ceiling and cannot authorize another Plan. |
| [x] | D-05 | Implement optimistic ledger versioning and an atomic Broker booking transaction. | Reconciled | Multi-item plans commit under one version; stale/budget/hour/tries paths fail before mutation. |
| [x] | D-06 | Derive/reserve a stable transaction ID per logical plan-item commitment and make retries exactly-once. | Reconciled | Sequential and concurrent duplicate tests apply one ledger effect and return the same stored booking (`OW-15` code path). |
| [x] | D-07 | Implement narrow Observer attendance/debrief reconciliation and preference updates. | Reconciled | Attendance, ledger reconciliation, optional debrief, and preferences commit atomically; exact replay is a no-op. |
| [x] | D-08 | Implement Compliance live-plan lookup and dead-listing flag writes. | Reconciled | Runtime and API cascade tests flag only live plans containing the retired listing. |
| [x] | D-09 | Review transaction rollback, concurrency, foreign keys, uniqueness, restart persistence, and store permission boundaries. | Reconciled | Temporary-file, reopen, stale-version, rollback, uniqueness, and concurrent replay tests pass. |

## 3. Deterministic intake and validation gates

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | V-01 | Implement pure I0 age/consent validation for ages below 13, 13–17, and 18+. | Reconciled | Runtime and fixture age matrices cover 11, 12, 13, 17, 18, and 19 with correct referrals. |
| [x] | V-02 | Implement Intake/Setup orchestration for eligible persistence, trusted-adult authority, constraints, ledger, and optional seeds. | Reconciled | Setup persists only after passing I0, rejects approval fields, and refuses any second setup that could replace identity, age, or parental rules. |
| [x] | V-03 | Implement detached G1 validation for PII-free Plans and sourced typed Discovery records with no raw page content. | Reconciled | Runtime privacy test and existing nested-page-dump mutation test both fail closed. |
| [x] | V-04 | Implement G2 validation for plan shape, CKB resolvability, session cost integrity, and remaining-budget arithmetic. | Reconciled | Runtime tests cover cost mismatch, missing/dead listings, stale ledger, and all three currencies. |
| [x] | V-05 | Implement G3 validation for a present approved verdict matching `plan_id`, verified/adult-approved providers, and required attendance/spend approvals. | Reconciled | Broker independently requires G3 before saving or committing (`OW-15` code path). |
| [x] | V-06 | Implement replay-safe G4 validation for well-formed bookings and exactly-once ledger application. | Reconciled | G4 validates durable transaction IDs, row count, and one ledger-version transition. Invalid row-count/version evidence fails during strict `CommitEvidence` construction inside the transaction and rolls back before a G4 result can be emitted; fresh/replay/concurrent paths are tested. |
| [x] | V-07 | Emit shape-only gate logs that never contain payloads, personal identifiers, or debrief text. | Reconciled | Serialized gate tests confirm verdict and transaction identifiers never enter the log. |
| [x] | V-08 | Enforce fixture-declared reads, writes, and traversed gates against a canonical matrix including Intake/Setup. | Reconciled | New boundary and required-gate mutation tests pass; Intake is explicit (`OW-16`). |

## 4. Six agent implementations

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | A-01 | Implement Planner candidate filtering, cheapest/reversible sequencing, ranking-only preferences, peer-cohort tie-break seam, thin-plan handling, and S$0/skipped-seed support. | Reconciled | Runtime A3/A4/A9/A10/A12 tests pass; Planner receives read snapshots and has no store mutation method. The cohort tiebreak is unit-tested but no canonical or simulation runtime data currently populates cohort buckets. |
| [x] | A-02 | Implement Discovery cached replay plus whitelisted live fetch/extraction with typed CKB writes and request-level round caps. | Reconciled | Official ActiveSG replay validates as unverified; replay idempotency, live whitelist rejection, G1, and graph round caps are enforced. |
| [x] | A-03 | Implement Guardian’s distinct per-listing vetting and per-plan attendance/spend checks. | Reconciled | Verified, unverified, paid, missing-attendance, mismatch, and two-rejection paths are tested. |
| [x] | A-04 | Implement sandbox Broker availability checks, stable transaction IDs, booking/confirmation artifacts, actionable failures, and atomic commitment. | Reconciled | A seeded availability failure now drives Broker → Planner → fresh G2/Guardian/G3 → replacement booking; multi-item replay remains exactly once. |
| [x] | A-05 | Implement Observer attendance-first adaptation, optional text debrief extraction, dislike attribution/decay, two-no-show replan, repeat-attendance commit, and `hold_this_week`. | Reconciled | Instance dislikes down-rank the provider; activity dislikes move an axis only after two corroborating signals; unknown-listing signals are not persisted. |
| [x] | A-06 | Implement manually triggered Compliance scan with listing/domain caps and retire-to-replan flags. | Reconciled | Operator authorization and allow-listing are required; transient failures mark stale, only explicit missing responses retire, and replacements require fresh approval. |
| [x] | A-07 | Define centralized per-agent permission declarations, method-entry checks, and structured model-output seams. | Reconciled | Every production agent/Intake/Validator call executes the central fail-closed `ToolGuard`, and fixture reads/writes import that matrix. These assertions do not wrap every store/CKB capability; Bedrock remains an explicitly optional, unvalidated adapter. |

## 5. LangGraph, runtime, and API

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | R-01 | Build the typed LangGraph pipeline with Planner, optional Discovery loop, G2, Guardian/replan loop, G3, Broker, and G4. | Reconciled | Every new Planner output records G1 before optional Discovery and G2; every Guardian decision records G3; trusted-adult approval resumes the exact previously validated Plan at fresh G2. |
| [x] | R-02 | Enforce `MAX_REPLANS`, `MAX_DISCOVERY_ROUNDS`, and `MAX_GUARDIAN_REJECTIONS` in state independently of model judgment. | Reconciled | Constants drive routers; runtime second-rejection test and merged exact-cap fixtures pass. |
| [x] | R-03 | Implement Broker-failure and Compliance-retirement replacement paths through fresh G2 → Guardian → G3 authorization. | Reconciled | Real seeded Broker failure books a different Plan only after fresh G2/G3; Compliance replacement stops at the human checkpoint until a new plan-bound approval is issued. |
| [x] | R-04 | Add persistent SQLite thread checkpoints with an in-memory test option. | Reconciled | Test closes and reopens the runtime, resumes the same thread, and observes no duplicate append-only records. |
| [x] | R-05 | Add Bedrock model factory/configuration using fixed model IDs, region validation, token capture, and a deterministic offline model seam. | Reconciled | Imports/tests/simulation make no AWS call; live factory is lazy with fixed IDs and actionable region validation. |
| [x] | R-06 | Add local `POST localhost:8080` JSON entrypoint and AgentCore-ready callable seam without a front-end dependency. | Reconciled | Role-specific Bearer tokens protect setup/approval/Compliance; generated profile capabilities protect attendance; request bodies are capped and unknown errors are not leaked. |
| [x] | R-07 | Add `.env.example`, dependency pins/ranges, and README setup/run/API/module guidance. | Reconciled | Root README documents canonical commands, CKB publication boundary, API operations, and offline/live seams. |

## 6. Evaluation and simulation

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | E-01 | Add synthetic eligible profiles, separate age-boundary profiles, adversarial cases, and 9–12 month synthetic history. | Reconciled | 12 eligible profiles, a separate six-age matrix, merged adversarial fixtures, and a 12-cycle labelled replay are committed. |
| [x] | E-02 | Implement Family A executable invariants against runtime behavior, including caps, S$0, vetting, reachability, idempotency, privacy, and ranking-only signals. | Reconciled | Dedicated runtime invariant tests plus merged fixture invariants cover A1–A12; full suite passes. |
| [x] | E-03 | Implement eligible-profile harness and collect Family B system/product rates with denominators and zero-denominator handling. | Reconciled | Twelve profiles execute the real graph before and after plan-bound approval. Full and partial metrics carry explicit scopes; B1, full B2, B9, and full B10 are not presented as measured. |
| [ ] | E-04 | Implement longitudinal replay showing old plan → signal → reasoning → new plan diffs. | Open | Scripted 12-cycle input remains illustrative only; a measured result must execute runtime plans and Observer transitions. |
| [ ] | E-05 | Implement static-recommender counterfactual and compute B14/B15 for both arms. | Open | Hand-authored outcomes were removed. B14/B15 stay unmeasured until both executable policies run against the same observations. |
| [x] | E-06 | Include at least one correct `hold_this_week` decision in the replay. | Reconciled | The fixture contains two scripted holds, now labelled as illustrative input rather than measured product performance. |
| [x] | E-07 | Implement `python -m sim.report` as the one-command reproducible metrics report. | Reconciled | Runtime-derived completion, booking, loop, S$0, free-share, and A1 diagnostics emit; partial B1/B2/B9/B10 and unmeasured B6/B11–B15 state their evidence limits. |

## 7. Final reconciliation and pull request

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | F-01 | Run focused tests after each implementation group and the complete canonical test suite at the end. | Reconciled | PR #4 passed its 98-test post-follow-up suite; after PR #5 merged, the clean `main` baseline passes 140 tests. |
| [x] | F-02 | Run the eligible simulation, counterfactual, one-command report, and local API smoke test. | Reconciled | All three modules exit 0; health reports empty-CKB readiness false, protected access returns 401, oversized input returns 413, and malformed JSON returns 400 without internal details. |
| [x] | F-03 | Perform a final code review for correctness, authorization, privacy, concurrency, loop bounds, error handling, and accidental scope drift. | Reconciled | Both Claude review passes were independently checked; the initial blocker/high findings and follow-up R-1 regression were corrected, while partial capabilities and unsupported evaluation claims are explicitly scoped. |
| [x] | F-04 | Reconcile code, tests, README, tracker status, and this checklist with architecture v2.2 and merged prompt contracts. | Reconciled | PR #4 merged and closed `OW-05` and `OW-16`; `OW-06` remains active for executable evaluation, while `OW-15` still needs narrow source-contract reconciliation. |
| [x] | F-05 | Inspect the complete diff and repository for secrets, generated junk, and unrelated changes. | Reconciled | Secret scan is clean; ignored runtime/venv artifacts are absent from the diff; no merged prompt or CKB source-data file changed. |
| [x] | F-06 | Commit and push `codex/backend-implementation`, then open a PR to `main` with summary, validation evidence, risks, and scope boundaries. | Reconciled | Opened [PR #4](https://github.com/respoopu/agentic_ai_hackathon_2026/pull/4) to `main`; its description records validation evidence and the CKB/prompt boundaries. |

## 8. PR #4 review remediation

| Done | ID | Review finding | Status | Reconciliation evidence |
|---|---|---|---|---|
| [x] | CR-01 | BL-1 / H-5: caller-issued, reusable approvals and profile takeover | Reconciled | Setup approval keys are forbidden; setup is immutable; API roles are authenticated; approvals are per-Plan with spend ceilings; attendance checks a profile capability and booking owner. |
| [x] | CR-02 | BL-2 / M-1 / M-2 / M-3: ineffective replanning, gate order, lost reasons and binding constraint | Reconciled | G1 precedes G2; rejected G3 decisions and reason history are retained; provider/dead-listing and parental-rule reasons alter Planner inputs. Missing attendance/spend approval preserves the exact Plan at the trusted-adult checkpoint. Binding constraints persist and failed planning declares notification required. |
| [x] | CR-03 | BL-3 / BL-4: constants presented as measured counterfactual and autonomous completion | Reconciled | All profiles traverse the real graph and approval continuation; 12/12 are human checkpoints. Unsupported counterfactuals are removed, and incomplete B1/B2/B9/B10 plus B6/B11–B15 are labelled partial, illustrative, or unmeasured. |
| [x] | CR-04 | H-1: empty canonical CKB hidden behind successful health/planning semantics | Reconciled | Health exposes `ready_for_real_planning=false`; empty-CKB planning returns `ok=false`, `no_viable_plan`, and its binding constraint. |
| [x] | CR-05 | H-2: tautological G4 | Reconciled | `CommitEvidence` carries transaction rows and before/after ledger versions from SQLite; G4 independently matches booking transactions. Strict evidence construction enforces row count and exactly-one version transition inside the transaction, so those violations roll back rather than becoming G4 reason codes. |
| [x] | CR-06 | H-3: unauthorised Compliance and transient failures retired listings | Reconciled | Compliance requires its own Bearer token and allow-list, honors robots.txt, and marks denied/transient/403/timeout checks stale; only explicit listing 404/410 retires. |
| [x] | CR-07 | H-4: unreachable Broker failure | Reconciled | Injected sandbox availability can fail after selection; the graph test observes fresh G2/G3 on a different replacement Plan. |
| [x] | CR-08 | M-4 / M-5: dead peer-cohort and dislike attribution | Reconciled | Hydration can consume strict pre-bucketed cohorts and a ranking test proves the seam, but current runtime/simulation data does not populate it. Instance/provider and corroborated activity-axis behavior are executable and tested. |
| [x] | CR-09 | M-6 / M-7: unenforced/divergent permission matrices | Reconciled | Production components run centralized method-entry `ToolGuard` assertions; fixture read/write validation imports the same matrix. Store/CKB calls are not capability-mediated, and scenario gate paths remain fixture-specific. |
| [x] | CR-10 | M-8 / M-9 / M-10: CKB exports, replay host, stale live plans | Reconciled | Merged loader exports are restored/tested; cached replay validates the expanded official allow-list; successful replacement atomically retires prior live plans. |
| [x] | CR-11 | M-11 / L-1–L-8: optional Bedrock overclaim and API/runtime hardening | Reconciled | Bedrock payload is canonical JSON and the seam is optional/unvalidated; service init is locked, requests capped, graph boundary asserts are explicit errors, HTTP errors are narrowed, Python 3.11 is required, and the checkpoint serializer dependency is direct. |

## 9. PR #4 follow-up review

| Done | ID | Review finding | Status | Reconciliation evidence |
|---|---|---|---|---|
| [x] | FR-01 | R-1: missing spend approval incorrectly forced a free replan and discarded a valid paid Plan | Reconciled | Missing attendance/spend authority now stops at the trusted-adult checkpoint with the paid Plan intact. Only an actual `parental_rule:no_paid_activities` refusal tightens the Planner to free options; a paid-only regression pins the distinction. |
| [x] | FR-02 | M-4 partial: peer-cohort seam has no populated runtime source | Reconciled | README and A-01/CR-08 now state that hydration/ranking support exists but current canonical and simulation inputs do not exercise it or produce a metric. |
| [x] | FR-03 | M-6 partial: `ToolGuard` assertions are not store/CKB capability wrappers | Reconciled | A-07/CR-09 and README explicitly scope the implementation to centralized method-entry assertions and no longer claim full mediated enforcement. |
| [x] | FR-04 | H-2 residual: malformed durable evidence rolls back before G4 can emit two reason codes | Reconciled | V-06/CR-05 distinguish transactional schema enforcement from G4 result reporting; the exactly-once invariant remains enforced without claiming every reason code is externally reachable. |
| [x] | FR-05 | Deployment-wide Guardian token can act for every teen | Reconciled | README identifies it as a PoC operator credential and requires household-scoped identity/authorization before production deployment. |

## 10. OW-17 canonical CKB and demo readiness

Branch: `codex/ow-17-canonical-ckb-demo`
Base: merged `main` after PR #4

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | CKB-01 | Inventory synthetic fixtures, existing sourced drafts, publication rules, runtime readiness semantics, and target-area coverage. | Reconciled | Synthetic evaluation rows are isolated in `sim/catalogue.py`; the fictional Guardian queue is in `data/quarantine_listings.json`; 157 sourced NLB/ActiveSG drafts were inventoried separately from the promotion boundary. The builder and runtime acceptance boundaries were rechecked before the canonical CSV was populated. |
| [x] | CKB-02 | Create a diverse, allow-listed source catalogue spanning public Telegram channels, public social pages, organisers' event pages, community venues, sport, arts, performance, volunteering, nature, thrifting, and low-pressure self-guided hobbies. | Reconciled | `data/public_activity_sources.json` covers nine public Telegram previews and eleven public social/organiser leads. Private/login-gated groups are excluded; stable organiser pages are preferred for Facebook/Instagram evidence. |
| [x] | CKB-03 | Implement reproducible, polite source acquisition that emits unverified candidate data with stable source URLs and never invents missing fields. | Reconciled | The public-preview collector produced 197 compact unverified candidates with zero fetch errors; it stores stable links, hashes, short excerpts and detected evidence tokens—not raw pages or guessed CKB values. Parser/change-detection tests and Ruff pass. |
| [x] | CKB-04 | Reconcile and deduplicate social candidates against the 157 merged NLB/ActiveSG drafts; select a hobby-diverse 40–50-row real seed across the three target areas. | Reconciled | The queue contains 356 unique candidates: 157 merged drafts and 199 public leads after 34 duplicate rows/reposts were removed. The deterministic 46-row shortlist is split 25/10/10 across Jurong West/Punggol/Bishan plus one commercial thrifting supplement, with 13 social, 10 NLB, 8 ActiveSG-draft and 15 official-web candidates spanning all four hobby buckets. |
| [x] | CKB-05 | Provide a human verification queue/attestation flow and promote only rows whose source, date, price, age, venue, participation, and schedule were actually checked. | Reconciled | Rayden's 2 Sep attestation is recorded separately in `data/ckb_attestations.json` under `respoopu`; 35 complete rows promote and 11 rows remain documented rejections. Promotion fails closed on pending/unknown rows, automated reviewers, undocumented rejections and schema-invalid approvals. |
| [x] | CKB-06 | Build and commit `data/seed_ckb.json` with the merged builder; reconcile quarantine, freshness, URL, provenance, provider, vibe, regional, and long-tail coverage. | Reconciled | The committed artifact contains 35 real plus 10 quarantine rows. All 12 coverage gates pass: 4 areas with Jurong West densest, 2 free weekday evenings/7 free weekends there, 60% long-tail, 24/35 free, full provider/vibe spread and fresh provenance. |
| [x] | CKB-07 | Make health readiness require usable sourced non-fictional rows, not merely any CKB record, and add regression coverage. | Reconciled | Health now reports total, usable real, verified real, unverified real, fictional and unusable counts. Empty, quarantine-only and retired-only stores are not ready; a sourced unverified real row is ready for the Guardian flow. |
| [x] | CKB-08 | Add a clean-runtime real-row planning smoke test that imports no synthetic evaluation catalogue. | Reconciled | A clean subprocess loads the committed canonical artifact, reports real-planning readiness, calls the normal intake/agent/LangGraph path, reaches the trusted-adult checkpoint with canonical IDs and proves `sim.catalogue` was never imported. |
| [x] | CKB-09 | Run CKB URL checks, focused tests, full tests, clean-runtime/API smoke, and a final provenance/privacy/copyright review. | Reconciled | PR #5 initially passed 125 tests; its merged review follow-ups raise the clean `main` baseline to 140 passing tests. All 12 CKB gates and Pydantic conformance pass. URL checking found no dead links; one ActiveSG booking URL returned expected bot-blocking HTTP 403 and had already been opened by the human reviewer. Public-only compact excerpts contain no secrets or personal data. |
| [x] | CKB-10 | Reconcile `README.md`, `seed-ckb.md`, `outstanding.md`, and this checklist; then commit, push, and open a PR to `main`. | Reconciled | README includes the canonical real-agent smoke command; the seed runbook records the attestation ledger and final counts; OW-17 is closed in the tracker; PR #5 is the publication unit to `main`. |

## 11. OW-06 executable evaluation follow-up

Branch: `codex/ow-06-executable-evaluation`
Base: merged `main` after PR #5

| Done | ID | Task | Status | Acceptance and evidence |
|---|---|---|---|---|
| [x] | EV-01 | Sync the merged baseline and reconcile stale tracker/checklist evidence. | Reconciled | Branch created from clean `origin/main` at `8d0287e`; the baseline passes 140 tests and `sim.report` runs. The tracker now distinguishes the attested CKB from unrelated open slide claims. |
| [x] | EV-02 | Replace hand-authored Hobbi/static outcomes with a shared synthetic environment and executable policies. | Reconciled | `data/synthetic_teen.json` now contains only profile, date, context, availability and preferred-vibe inputs. Tests reject authored attendance, action, selected-listing or static-result fields. Both policies use the same catalogue and attendance rule. |
| [x] | EV-03 | Execute longitudinal Hobbi cycles through Planner, Guardian, Broker and Observer persistence. | Reconciled | Twelve generated Plans traverse G1→G2→G3→G4, commit through Broker, reconcile through Observer and retain listing, attendance, action, reason and ledger-version evidence. Runtime output includes intentional hold, two-no-show replan and sustained-attendance `try_to_commit`. |
| [x] | EV-04 | Execute the immutable static baseline and compute B11, B12, B14 and B15 with explicit populations. | Reconciled | The static arm repeats one immutable declared-preference recommendation while Hobbi changes listings from stored outcomes. B11 resolves 1/2 triggers in one cycle with one right-censored; B12 is 2/12; B14 is 8/12 vs 2/12; B15 is 4/4 vs 3/4 across the S$0 cohort. All are labelled deterministic synthetic evidence. |
| [x] | EV-05 | Instrument the adversarial constraint rate and any other deterministic-path metrics that can be measured honestly. | Reconciled | `sim.adversarial` executes all eight documented scenarios through production validators/components, including the real two-rejection graph path. B10 reports 0/8 violations. Live-model B1/B4, full tool B2, human-scored B6 and dated B13 remain visibly outside deterministic evidence. |
| [x] | EV-06 | Update tests, report output, README/evaluation guidance and evidence labels. | Reconciled | Four new/expanded tests pin input-only fixtures, policy independence, real gate traversal, Observer action semantics, denominators and the eight-case adversarial set. README and evaluation methodology state the population, five-opportunity B15 horizon and non-participant boundary. |
| [x] | EV-07 | Run focused/full verification and perform final correctness/evidence review. | Reconciled | 144 tests pass; all 25 architecture fixtures pass; changed-file Ruff and whitespace checks pass; harness, counterfactual and report commands exit 0. Final review found no authored result leakage or unsupported participant/live-model claim. |
