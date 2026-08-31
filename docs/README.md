# Hobbi — Documentation

*Source of truth for the SimplifyNext Agentic AI Hackathon 2026 submission. Last updated 27 Aug 2026.*

**Hobbi** helps a 13–17-year-old turn intent into a first session they actually walk into — and then keeps adapting as they do or don't turn up.

---

## Read in this order

| # | Document | What it settles | Read it when |
|---|---|---|---|
| 1 | **[`deliverables.md`](./deliverables.md)** | What the hackathon requires, the full rubric, and how we maximise the score | Before anything. It constrains everything else. |
| 2 | **[`project_brief.md`](./project_brief.md)** | The problem, the person, the solution argument, the positioning | Writing slides 1–3, 6, 7, 9, 10 |
| 3 | **[`architecture.md`](./architecture.md)** | The system: 5 pipeline agents + Compliance + validation layer, 2 stores, 3 bounded loops, state, stack, scope | Writing code, or slide 5 |
| 4 | **[`evaluation.md`](./evaluation.md)** | Metrics, invariants, test data, the counterfactual baseline | Writing tests, or the evaluation slide |
| 5 | **[`user_stories.md`](./user_stories.md)** | Every story mapped to the agent that owns it | Checking a feature has a home |
| 6 | **[`project_brief_sources.md`](./project_brief_sources.md)** | Every citation, with reliability marks | **Before any figure goes on a slide** |
| 7 | **[`discrepancies.md`](./discrepancies.md)** | 31 conflicts between the brief, the diagram and the requirements | Deciding anything |

**Assets:** [`teen-planner-architecture.png`](./teen-planner-architecture.png) — the diagram · [`info-judging-criteria-reqs.pdf`](./info-judging-criteria-reqs.pdf) — the official deck (the authority; `deliverables.md` is our reading of it)

---

## Precedence

When two documents disagree:

```
official deck  >  deliverables.md  >  architecture.md  >  project_brief.md  >  the PNG diagram
```

The diagram is a picture and lags the spec. `architecture.md` §13 lists every place they differ and why.

---

## The state of things right now

**Decided and written up.** Problem statement in POV format · six agents (five on the request path, one scheduled) with contracts, caps and failure behaviour · three bounded loops with hard caps · typed state and schemas · human-in-the-loop mapped to the IMDA framework · a PDPA position for minors' data · an evaluation plan with invariants and a counterfactual baseline · tech stack · PoC scope.

**Open, and needs the team** — [`discrepancies.md`](./discrepancies.md) §D:

| | Decision | Why it matters |
|---|---|---|
| **D3** | How narrow is the problem statement? | **Decide first.** Sets the Effectiveness ceiling and gates slide 2, slide 7, the video open, and the metrics. |
| **D1** | Keep the budget-as-portfolio thesis and add the ledger? | The Originality argument rests on it. Small fix, biggest return. |
| **D2** | Build the belonging tiebreak, or cut the claim? | Currently pitched and unbuilt — the worst of the three states. |
| **D3b** | Which metric is the headline once D3 narrows the claim? | Left alone, slide 2 and the evaluation slide argue for different products. |
| **D6** | When do we re-derive the system prompts on `feat/agent-system-prompts`? | That branch predates these docs and diverges on five points — including whether the user is a child or a 13–17-year-old. |
| **D4/D5** | Ask organisers: live Q&A? deadline and upload mechanism? | Neither appears in the deck. Project files are **one submission only**. |

**The one task that is not a decision:** talk to five teenagers. It closes the only pressure-test question we currently fail ([`project_brief.md`](./project_brief.md) §1.2), and it converts our best original insight into primary research. One afternoon.

---

## Nothing is built yet

There is no Hobbi implementation in this repository — `lab/` is unrelated workshop material. Every ✅ in [`user_stories.md`](./user_stories.md) and the repo layout in [`architecture.md`](./architecture.md) §11 are **scope, not progress**. Technical Quality is 20% of the score and is the one criterion no slide can earn, so this is the gap that matters most.

There is also an unmerged branch, `feat/agent-system-prompts`, carrying ~1,700 lines of earlier agent-prompt work. It predates this doc set and diverges from it — see [`discrepancies.md`](./discrepancies.md) **E1**. These documents are the source of truth; the prompts get re-derived from them, not the other way round.

---

## Two things worth knowing before you cite anything

1. **A figure was retracted.** *"Only 42% of youths satisfied with opportunities to pursue a hobby (NCSS QoL Survey 2025)"* does not survive verification — it traces to a single news sentence the primary record does not support. It was one of two numbers we planned to open with. [`project_brief_sources.md`](./project_brief_sources.md) §A.2.
2. **An AI summary of a source is a lead, not a citation.** That is how the 42% figure got in. Anything going on a slide gets opened, read, and quoted from the actual document. [`project_brief_sources.md`](./project_brief_sources.md) §0.

---

## Conventions

- 🟢 primary/official · 🟡 credible secondary · 🔴 weak · ⛔ retracted
- ✅ in the PoC · 🔶 partial/simulated · ⬜ roadmap
- 🔴 blocks a criterion · 🟠 weakens the pitch · 🟡 tidy-up *(severity, in `discrepancies.md`)*
- Every figure carries a **source and a date**. Every metric carries a **denominator and a date**.

> **One ID collision to know about.** `discrepancies.md` numbers its rows A1–A11 / B1–B10 / C1–C10, and `evaluation.md` numbers its invariants A1–A8 and its rates B1–B14. **The same label means different things in the two files.** References are always qualified — "Discrepancy A3" is the missing budget ledger, "invariant A3" is the S$0 viability test. If a reference is bare, check which file it points at.
