# Outstanding Work — Hobbi

*Canonical tracker for unfinished validation, integration, build and submission work. Last updated 3 Sep 2026.*

This file answers **what is still open, who owns it, and what “done” means**. The product, architecture, evaluation and source documents retain the reasoning; they link here for status rather than maintaining competing task lists.

## How to use this tracker

- Keep each unfinished item in exactly one row with a stable `OW-*` ID.
- Use only these statuses: **Not started · Next · In progress · Blocked · Done · Dropped**.
- Assign an owner when work starts. Do not use “team” when one person is accountable.
- Update the row after a material change, merge or verification result.
- Move completed or intentionally dropped rows to the dated history section; do not delete them.
- “Done when” is the acceptance test. Activity alone does not close a row.
- **P0** means submission-critical or immediately blocking; **P1** means important evidence or positioning work that must finish before the affected slide freezes.

**Current evidence policy:** PR #5 published a separately attested canonical CKB for runtime and demo use. That attestation covers the promoted listing fields only; it does not verify the unrelated presentation claims in OW-07–OW-11, which remain due before the affected slides freeze.

## Current backlog

| ID | Priority | Status | Item | Owner | Target | Done when | Detail |
|---|---|---|---|---|---|---|---|
| **OW-12** | P0 | **Not started** | Produce and verify the presentation deck | — | After OW-24 demo flow freezes | Deck is no more than 10 slides, reflects the built system, carries sourced figures and measured results, and passes the rubric/slide checklist | [`deliverables.md`](../1-requirements/deliverables.md) §§3, 7–10 |
| **OW-13** | P0 | **Not started** | Record and verify the demo video or simulation recording | — | After OW-24 demo flow freezes | Recording is no more than 5 minutes, shows the submitted prototype running, includes the adaptive counterfactual beat, and matches the deck and repository | [`deliverables.md`](../1-requirements/deliverables.md) §§3.3, 6 · [`architecture.md`](../3-system/architecture.md) §10 |
| **OW-14** | P0 | **Not started** | Freeze and validate the final submission | — | Submission deadline | The confirmed organiser deadline, upload mechanism, accepted formats and presentation format are transcribed into `deliverables.md` §12; repository, deck and recording are mutually consistent; secrets are absent; documented commands run from a clean checkout; size/format/upload rules are satisfied; the one allowed submission is verified before upload | [`deliverables.md`](../1-requirements/deliverables.md) §§2, 8, 11.6 |
| **OW-18** | P1 | **Not started** | Replace the deployment-wide Guardian credential with household-scoped authorization | — | Before any shared or production deployment | Every trusted-adult identity is authorized only for its linked teen profiles; cross-household setup and approval attempts fail; credential rotation and revocation are documented and tested | `HOBBI_GUARDIAN_API_TOKEN` is an explicit PoC operator credential and can act for every profile in one deployment. |
| **OW-19** | P1 | **Not started** | Populate and evaluate privacy-preserving peer-cohort buckets | — | Before claiming the belonging objective | A documented k-anonymous source populates pre-bucketed cohorts without peer identity; canonical or simulation runtime exercises the Planner tiebreak; and any reported effect has a measured denominator | Hydration and ranking support exist, but current CKB and simulation inputs leave the seam unused. |
| **OW-20** | P1 | **Not started** | Mediate agent data/tool access through enforceable capabilities | — | Before claiming tool allow-lists as a security boundary | Personal Data, CKB and runtime tool calls require component-scoped capabilities; a component cannot bypass its declared matrix by calling a store directly; and negative integration tests fail closed | Current `ToolGuard` checks are centralized method-entry assertions, not wrappers around each store or CKB capability. |
| **OW-21** | P1 | **Not started** | Make exactly-once evidence failures observable at the G4 boundary | — | Before operational monitoring is finalized | Row-count and ledger-version violations roll back and surface as typed G4/operational events with tests, without leaking transaction or profile identifiers | Strict `CommitEvidence` construction currently enforces these invariants inside the transaction, so two G4 reason codes are not externally reachable. |
| **OW-22** | P1 | **Not started** | Validate and integrate the Bedrock structured-output path | — | Before presenting live-model cost or quality claims | The selected model resolves in the deployment region/account; typed output, retry/error handling and token capture pass an integration test; and measured cost/quality evidence replaces deterministic-path placeholders | The canonical JSON adapter is optional, is not wired into the default graph and has not been tested against a live AWS account. |
| **OW-23** | P1 | **Not started** | Turn Observer holds into a structured pre-booking next-cycle decision | — | Before reporting B12 as product performance | Temporary constraints are classified through a typed, evaluated output rather than a fixed phrase list; a hold suppresses the next booking/message; held events break the disengagement streak; and precision/recall or human-reviewed scenario evidence supports the reported rate | PR #7 proves deterministic hold-branch reachability and prevents held events from triggering a two-no-show replan, but Observer still runs post-session and the PoC classifier matches a small English phrase list. |
| **OW-07** | P1 | **Not started** | Verify “100+ ActiveSG interest groups” | — | Before citing the number | A primary MyActiveSG+ source confirms it, or the number is removed | [`sources.md`](../2-product/sources.md) §J item 2 |
| **OW-08** | P1 | **Not started** | Confirm Flying Cape still operates | — | Before competitor slide freezes | A current primary source confirms operation, or the competitor is removed | [`sources.md`](../2-product/sources.md) §J item 3 |
| **OW-09** | P1 | **Not started** | Verify the “12 third spaces by end-2026” deadline | — | Before citing the deadline | A primary source supports the date, or the statement keeps only the verified count | [`sources.md`](../2-product/sources.md) §J item 4 |
| **OW-10** | P1 | **Not started** | Fetch the Ostojic 2014 abstract directly | — | Before using the reversal figure | The primary abstract is checked and the citation/claim is corrected if necessary | [`sources.md`](../2-product/sources.md) §J item 5 |
| **OW-11** | P1 | **Not started** | Verify Discover's role in the 20,000 opportunities | — | Before positioning slide freezes | A primary source establishes whether Discover is a sign-up channel; otherwise the docs continue to call it only a digital compass | [`sources.md`](../2-product/sources.md) §J item 7 |

## Completed / dropped history

Move closed rows here under a dated heading, preserving their ID, final owner and outcome.

### 3 Sep 2026

| ID | Priority | Final status | Item | Owner | Outcome |
|---|---|---|---|---|---|
| **OW-24** | P0 | **Done** | Build and verify the demo frontend | Codex | A responsive youth-focused Next.js interface starts with a documented fake login, keeps preferences on a dedicated profile screen, and provides a returning-user home before driving the real API through planning, exact-plan trusted-adult approval, sandbox booking, attendance/debrief and an adapted next plan. Pydantic display models generate the OpenAPI contract and TypeScript types; server routes keep the Guardian credential out of browser code and hold the teen token in an HttpOnly cookie. Safe loading, empty and error states are present; `scripts/run_demo.py` starts both services; Python contract tests, React tests, a production build, Playwright end-to-end flow and desktop/mobile visual checks pass. |

### 2 Sep 2026

| ID | Priority | Final status | Item | Owner | Outcome |
|---|---|---|---|---|---|
| **OW-02** | P0 | **Done** | Ask organisers about submission logistics and live Q&A | Rayden | Rayden confirmed on 2 Sep that the organiser response has been received, closing the research dependency. The row's original acceptance test — transcribing the deadline, upload mechanism, accepted formats and presentation format into `deliverables.md` §12 — is not yet met; that obligation is carried by **OW-14** rather than left implicit here. |
| **OW-06** | P0 | **Done** | Implement tests, simulation and one-command report | Codex | PR #7 merged the executable longitudinal and counterfactual evaluation. The 149-test suite passes; `python -m sim.report` emits scoped B1–B15 results with denominators and explicit evidence limits, including B10 0/8 adversarial plus 0/12 eligible diagnostics, B11 1/1, B14 8/12 vs 2/12 and B15 4/4 vs 3/4. B12 remains branch reachability and is separately bounded by OW-23. |
| **OW-15** | P0 | **Done** | Resolve Broker authorization and idempotency contract | Codex | Runtime and source contracts now agree: `BookingRecord` binds `guardian_verdict_id`; G3 requires the approved verdict for the exact Plan; Broker derives a stable transaction id from each logical commitment; exact replay returns the stored record without a second side effect; and G4 accepts durable first-commit or replay evidence while enforcing exactly-once application. Architecture, prompts, fixtures and contract tests were reconciled. |
| **OW-05** | P0 | **Done** | Build the Hobbi backend PoC | Codex | PR #4 implemented Intake/I0, six agents, detached G1–G4, Personal Data SQLite, bounded LangGraph loops, protected API, durable approvals/bookings and 98 passing tests. Missing canonical CKB publication and unsupported evaluation/live-model evidence remain separately tracked as OW-17, OW-06 and OW-22. |
| **OW-16** | P0 | **Done** | Enforce fixture store and gate boundaries | Codex | PR #4 added Intake to the canonical permission matrix, reused that matrix in fixture validation, and added forbidden-read/write and required-gate mutation coverage; all 25 architecture-v2.2 fixtures pass. |
| **OW-17** | P0 | **Done** | Publish the canonical CKB runtime artifact | Codex + Rayden | Rayden attested the 46-row shortlist; 35 complete sourced activities were promoted and 11 unsuitable/incomplete leads retained as documented rejections. The 45-record artifact (35 real + 10 quarantine) passes all 12 coverage gates, Pydantic conformance, URL checking with no dead links, and a clean-runtime agent/LangGraph smoke without `sim.catalogue`. |

### 1 Sep 2026

| ID | Priority | Final status | Item | Owner | Outcome |
|---|---|---|---|---|---|
| **OW-04** | P0 | **Done** | Reconcile and integrate `feat/seed-ckb` through PR #3 | Rayden | Architecture v2.2, stored/hydrated schemas, deterministic build/load boundaries, drafts and fixtures were reconciled; Claude's follow-up review was remediated and independently re-audited; 27 tests passed; PR #3 merged. |
| **OW-03** | P0 | **Done** | Re-derive the agent-system prompts and validation fixtures | Jethro | Five pipeline prompts, scheduled Compliance, detached Validator, typed v2.2 protocol and 25 executable fixtures were regenerated; all E1 divergences and obsolete design artifacts were removed; A1-A12 and adversarial 1-8 are traceable; all 25 fixtures and the agent-system contract tests pass. Repository-wide discovery remains environment-dependent where optional project dependencies are unavailable; PR status and review evidence are tracked in GitHub. |
| **OW-01** | P0 | **Dropped** | Interview five teenagers/caregivers | Rayden | Primary interviews were de-scoped for the hackathon. Five [`modelled user journeys`](../2-product/modelled_user_journeys.md) now expose the product assumptions and one counterexample for design/testing; they are not participant evidence, so adult coordination and “scene, not class” remain explicitly labelled hypotheses. |
