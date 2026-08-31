# Hobbi — Documentation

*Source of truth for the SimplifyNext Agentic AI Hackathon 2026 submission. Last updated 31 Aug 2026.*

**Hobbi** helps a 13–17-year-old turn intent into a first session they actually walk into — and then keeps adapting as they do or don't turn up.

---

## Read in this order

The folders carry the order. Numbers are the reading sequence, not a priority ranking.

| # | Document | What it settles | Read it when |
|---|---|---|---|
| 1 | **[`1-requirements/deliverables.md`](./1-requirements/deliverables.md)** | What the hackathon requires, the full rubric, and how we maximise the score | Before anything. It constrains everything else. |
| 2 | **[`2-product/project_brief.md`](./2-product/project_brief.md)** | The problem, the person, the solution argument, the positioning | Writing slides 1–3, 6, 7, 9, 10 |
| 3 | **[`3-system/architecture.md`](./3-system/architecture.md)** | The system: 5 pipeline agents + Compliance + validation layer, 2 stores, 2 capped request loops + 1 ledger-bounded cycle, state, stack, scope | Writing code, or slide 5 |
| 4 | **[`3-system/evaluation.md`](./3-system/evaluation.md)** | Metrics, invariants, test data, the counterfactual baseline | Writing tests, or the evaluation slide |
| 5 | **[`3-system/seed-ckb.md`](./3-system/seed-ckb.md)** | The transcription contract for the seed listing set, and what "done" means | Filling the CKB — the one build task with no code dependency |
| 6 | **[`2-product/user_stories.md`](./2-product/user_stories.md)** | Every story mapped to the agent that owns it | Checking a feature has a home |
| 7 | **[`2-product/sources.md`](./2-product/sources.md)** | Every citation, with reliability marks | **Before any figure goes on a slide** |
| 8 | **[`4-decisions/discrepancies.md`](./4-decisions/discrepancies.md)** | 33 conflicts between the brief, the diagram and the requirements, and the 12 decisions that closed them | Deciding anything |
| 9 | **[`5-delivery/outstanding.md`](./5-delivery/outstanding.md)** | Canonical backlog: status, owner, target and acceptance test for every unfinished item | Planning the next piece of work |

### The folders

| | |
|---|---|
| **`1-requirements/`** | The hackathon's own constraints. Includes [`judging-criteria.pdf`](./1-requirements/judging-criteria.pdf) — the official deck, and the authority behind everything else here. |
| **`2-product/`** | What we are building and for whom, with the evidence behind it. |
| **`3-system/`** | How it works and how we prove it works. |
| **`4-decisions/`** | The register of every conflict found and every decision taken. |
| **`5-delivery/`** | What remains to validate, integrate, build and submit. [`outstanding.md`](./5-delivery/outstanding.md) is the only canonical task-status tracker. |
| **`assets/`** | [`architecture-diagram.png`](./assets/architecture-diagram.png) for slides, and [`architecture-diagram.html`](./assets/architecture-diagram.html) — its editable SVG source. Regenerate from the HTML, never redraw by hand. |

---

## Precedence

When two documents disagree:

```
judging-criteria.pdf  >  deliverables.md  >  architecture.md  >  project_brief.md  >  the diagram
```

The diagram is downstream of the spec, never upstream of it. It is **regenerable** — [`assets/architecture-diagram.html`](./assets/architecture-diagram.html) is the source and the PNG is its export. [`architecture.md`](./3-system/architecture.md) §13 is the 23-item synchronization checklist used before slide 5 is updated.

---

## The state of things right now

**Decided and written up.** Problem statement in POV format · six agents (five on the request path, one scheduled) with contracts, caps and failure behaviour · two capped request loops and one ledger-bounded longitudinal cycle · typed state and schemas · human-in-the-loop mapped to the IMDA framework · a PDPA position for minors' data · an evaluation plan with invariants and a counterfactual baseline · tech stack · PoC scope.

**All twelve decisions in [`discrepancies.md`](./4-decisions/discrepancies.md) §D closed on 31 Aug.** In brief: **D3** the statement is narrow on outcome and broad on audience, leading with S$0 · **D3b** B15 measures attendance within 30 days, with actions and elapsed time · **D2** belonging is simulated cohort presence, not a friend graph · **D7** the cohort is 13–17 at both ends, enforced at I0 · **D1** the budget ledger is in typed state · **D8** seed CKB from real listings + live whitelisted Discovery + sandboxed Broker + cached replay · **D9** the PoC observation channel is an in-app text form; audio and messaging adapters are roadmap · **D10** cold start is skippable vibe chips, *seeding not typing* · **D11** dislike decays and never blocklists · **D4** Q&A prep at second priority · **D5** organiser questions handled directly · **D6** prompts re-derived after this branch merges.

Every discrepancy in classes A, B and C is resolved. Cross-document consistency is checked against [`architecture.md`](./3-system/architecture.md) §13 and the audit notes in [`discrepancies.md`](./4-decisions/discrepancies.md) §F; any future mismatch is treated as a defect rather than covered by an absolute “nothing contradicts” claim.

One register row stays open — **E1**, the `feat/agent-system-prompts` branch — but it is scheduled rather than undecided: D6 re-derives it from [`architecture.md`](./3-system/architecture.md) §3 once this branch merges. The status, owner and acceptance test for E1 and every other unfinished item now live in the canonical [`outstanding.md`](./5-delivery/outstanding.md) tracker.

**The highest-priority validation task:** talk to five teenagers. It closes the pressure-test question we currently fail ([`project_brief.md`](./2-product/project_brief.md) §1.2), tests the adult-coordination hypothesis, and converts our best original insight into primary research. One afternoon. Track it as **OW-01** in [`outstanding.md`](./5-delivery/outstanding.md); [`sources.md`](./2-product/sources.md) §J retains the research detail.

---

## Nothing is built yet

There is no Hobbi implementation in this repository — `lab/` is unrelated workshop material. Every ✅ in [`user_stories.md`](./2-product/user_stories.md) and the repo layout in [`architecture.md`](./3-system/architecture.md) §11 are **scope, not progress**. Technical Quality is 20% of the score and is the one criterion no slide can earn, so this is the gap that matters most.

There is also an unmerged branch, `feat/agent-system-prompts`, carrying ~1,700 lines of earlier agent-prompt work. It predates this doc set and diverges from it — see [`discrepancies.md`](./4-decisions/discrepancies.md) **E1**. These documents are the source of truth; the prompts get re-derived from them, not the other way round.

---

## Two things worth knowing before you cite anything

1. **A figure was retracted.** *"Only 42% of youths satisfied with opportunities to pursue a hobby (NCSS QoL Survey 2025)"* does not survive verification — it traces to a single news sentence the primary record does not support. It was one of two numbers we planned to open with. [`sources.md`](./2-product/sources.md) §A.2.
2. **An AI summary of a source is a lead, not a citation.** That is how the 42% figure got in. Anything going on a slide gets opened, read, and quoted from the actual document. [`sources.md`](./2-product/sources.md) §0.

---

## Conventions

- 🟢 primary/official · 🟡 credible secondary · 🔴 weak · ⛔ retracted
- ✅ in the PoC · 🔶 partial/simulated · ⬜ roadmap
- 🔴 blocks a criterion · 🟠 weakens the pitch · 🟡 tidy-up *(severity, in `discrepancies.md`)*
- Every figure carries a **source and a date**. Every metric carries a **denominator and a date**.

> **One ID collision to know about.** `discrepancies.md` numbers its rows A1–A11 / B1–B11 / C1–C10, and `evaluation.md` numbers its invariants A1–A12 and its rates B1–B15. **The same label means different things in the two files.** References are always qualified — "Discrepancy A3" is the budget ledger, "invariant A3" is the S$0 viability test; "Discrepancy B7" is the scope-of-claim question, "metric B7" is the S$0 viability rate. If a reference is bare, check which file it points at.
