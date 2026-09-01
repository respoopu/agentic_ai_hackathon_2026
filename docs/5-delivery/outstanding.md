# Outstanding Work — Hobbi

*Canonical tracker for unfinished validation, integration, build and submission work. Last updated 1 Sep 2026.*

This file answers **what is still open, who owns it, and what “done” means**. The product, architecture, evaluation and source documents retain the reasoning; they link here for status rather than maintaining competing task lists.

## How to use this tracker

- Keep each unfinished item in exactly one row with a stable `OW-*` ID.
- Use only these statuses: **Not started · Next · In progress · Blocked · Done · Dropped**.
- Assign an owner when work starts. Do not use “team” when one person is accountable.
- Update the row after a material change, merge or verification result.
- Move completed or intentionally dropped rows to the dated history section; do not delete them.
- “Done when” is the acceptance test. Activity alone does not close a row.
- **P0** means submission-critical or immediately blocking; **P1** means important evidence or positioning work that must finish before the affected slide freezes.

**Current evidence policy:** PR #3 integration accepts the facts already present in its seed drafts as provisionally accurate so implementation can proceed. That assumption does not close OW-07–OW-11 or convert unsigned draft rows to `verified`; those checks remain due before the affected slides and final seed artifact freeze.

## Current backlog

| ID | Priority | Status | Item | Owner | Target | Done when | Detail |
|---|---|---|---|---|---|---|---|
| **OW-01** | P0 | **Next** | Interview five teenagers/caregivers | — | Before slide 2 freezes | Interview notes are recorded; the “scene, not class” observation and adult-coordination hypothesis are marked supported, weakened or rejected; the problem statement is updated if needed | [`project_brief.md`](../2-product/project_brief.md) §1.2 · [`sources.md`](../2-product/sources.md) §J items 1 and 8 |
| **OW-02** | P0 | **Next** | Ask organisers about submission logistics and live Q&A | — | Immediately | Deadline, upload mechanism, accepted formats, live-pitch/Q&A format and team rules are recorded in `deliverables.md` | [`deliverables.md`](../1-requirements/deliverables.md) §12 · [`sources.md`](../2-product/sources.md) §J item 6 |
| **OW-05** | P0 | **Not started** | Build the Hobbi PoC | — | Before demo recording | The canonical environment installs; Intake/Setup, I0, six agents, G1–G4, both stores, two request loops and the longitudinal cycle run through the documented happy and failure paths | [`architecture.md`](../3-system/architecture.md) §§3–11 · [`user_stories.md`](../2-product/user_stories.md) |
| **OW-06** | P0 | **Not started** | Implement tests, simulation and one-command report | — | Before slide 7 freezes | Family A invariants pass; eligible and boundary profiles stay separate; counterfactual and longitudinal runs execute; `python -m sim.report` emits every reported slide metric with denominators | [`evaluation.md`](../3-system/evaluation.md) §§2–8 |
| **OW-07** | P1 | **Not started** | Verify “100+ ActiveSG interest groups” | — | Before citing the number | A primary MyActiveSG+ source confirms it, or the number is removed | [`sources.md`](../2-product/sources.md) §J item 2 |
| **OW-08** | P1 | **Not started** | Confirm Flying Cape still operates | — | Before competitor slide freezes | A current primary source confirms operation, or the competitor is removed | [`sources.md`](../2-product/sources.md) §J item 3 |
| **OW-09** | P1 | **Not started** | Verify the “12 third spaces by end-2026” deadline | — | Before citing the deadline | A primary source supports the date, or the statement keeps only the verified count | [`sources.md`](../2-product/sources.md) §J item 4 |
| **OW-10** | P1 | **Not started** | Fetch the Ostojic 2014 abstract directly | — | Before using the reversal figure | The primary abstract is checked and the citation/claim is corrected if necessary | [`sources.md`](../2-product/sources.md) §J item 5 |
| **OW-11** | P1 | **Not started** | Verify Discover's role in the 20,000 opportunities | — | Before positioning slide freezes | A primary source establishes whether Discover is a sign-up channel; otherwise the docs continue to call it only a digital compass | [`sources.md`](../2-product/sources.md) §J item 7 |
| **OW-12** | P0 | **Not started** | Produce and verify the presentation deck | — | Before submission freeze | Deck is no more than 10 slides, reflects the built system, carries sourced figures and measured results, and passes the rubric/slide checklist | [`deliverables.md`](../1-requirements/deliverables.md) §§3, 7–10 |
| **OW-13** | P0 | **Not started** | Record and verify the demo video or simulation recording | — | Before submission freeze | Recording is no more than 5 minutes, shows the submitted prototype running, includes the adaptive counterfactual beat, and matches the deck and repository | [`deliverables.md`](../1-requirements/deliverables.md) §§3.3, 6 · [`architecture.md`](../3-system/architecture.md) §10 |
| **OW-14** | P0 | **Not started** | Freeze and validate the final submission | — | Submission deadline | Repository, deck and recording are mutually consistent; secrets are absent; documented commands run from a clean checkout; size/format/upload rules are satisfied; the one allowed submission is verified before upload | [`deliverables.md`](../1-requirements/deliverables.md) §§2, 8, 11.6 |

## Completed / dropped history

Move closed rows here under a dated heading, preserving their ID, final owner and outcome.

### 1 Sep 2026

| ID | Priority | Final status | Item | Owner | Outcome |
|---|---|---|---|---|---|
| **OW-04** | P0 | **Done** | Reconcile and integrate `feat/seed-ckb` through PR #3 | Rayden | Architecture v2.2, stored/hydrated schemas, deterministic build/load boundaries, drafts and fixtures were reconciled; Claude's follow-up review was remediated and independently re-audited; 27 tests passed; PR #3 merged. |
| **OW-03** | P0 | **Done** | Re-derive the agent-system prompts and validation fixtures | Jethro | Five pipeline prompts, scheduled Compliance, detached Validator, typed v2.2 protocol and 25 executable fixtures were regenerated; all four E1 divergences and obsolete design artifacts were removed; A1-A12 and adversarial 1-8 are traceable; the canonical unittest suite passed 34 tests. PR #1 remains open for review. |
