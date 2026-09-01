# Discrepancy Register

*Conflicts between the three things that currently define Hobbi: the **brief** (`project_brief.md` v1), the **architecture** (`architecture-diagram.png`), and the **hackathon requirements** (`deliverables.md`, from the official deck).*

*Opened 27 Aug 2026. This is a working document — close rows as they are resolved.*

**Severity:** 🔴 blocks a scoring criterion or ships a broken system · 🟠 weakens the pitch materially · 🟡 tidy-up.

*Rows below cite "Brief v1" throughout. It is not lost — v1 is the committed version at `eea58dd`. Read it with `git show eea58dd:docs/project_brief.md`, or compare both paths with `git diff eea58dd -- docs/project_brief.md docs/2-product/project_brief.md`.*

**Status:** `RESOLVED` — decided and already reflected in the v2 docs · `OPEN` — needs a team decision · `NOTED` — no action, recorded so nobody rediscovers it.

---

## Summary

| Class | 🔴 | 🟠 | 🟡 | Total |
|---|---|---|---|---|
| **A** — Brief ↔ Architecture | 4 | 4 | 3 | 11 |
| **B** — Architecture ↔ Hackathon requirements | 5 | 4 | 2 | 11 |
| **C** — Brief ↔ Hackathon requirements | 2 | 2 | 6 | 10 |
| **E** — Downstream artifacts | 0 | 1 | 0 | 1 |
| | **11** | **11** | **11** | **33** |

**All twelve decisions in §D closed on 31 Aug**, and every discrepancy in classes A, B and C with them. §F records the subsequent consistency reviews and their corrections; future mismatches remain defects to fix, not something this status line claims can never exist.

**One row is still open: E1** — the `feat/agent-system-prompts` branch. It is not a decision; **D6** scheduled it. The prompts get re-derived from `architecture.md` §3 once this branch merges to main.

Everything else that remains is work, not argument: the build, the deck, the video, the source-verification list below, and five teenagers.

**If you read one row, read B7** — and then **B11**, the trap inside B7's own fix. Both closed on 31 Aug; they are kept because the reasoning is the reasoning behind slide 2 and the headline metric.

---

## A. Brief ↔ Architecture

The brief's v1 agent table and the architecture diagram describe different systems. The diagram is newer, so it wins by default — but three things in the brief have no home in it, and two of those three are load-bearing for the pitch.

---

### A1 · The agent roster changed and nothing recorded it 🟠 `RESOLVED`

| Brief v1 §3 | Diagram | Verdict |
|---|---|---|
| Orchestrator | Orchestrator *(different job entirely)* | → recast, see **A2** |
| Planner | Planner Agent | unchanged |
| Broker | Broker Agent | unchanged |
| Observer | Feedback Capture *(narrowed)* | → see **A4** |
| Reallocator | — | **dropped** → see **A3** |
| Guardian *(optional)* | Guardian Agent | **promoted to mandatory in-pipeline gate** — an improvement |
| — | **Discovery Engine** | new → see **A7** |
| — | **Compliance Agent** | new → see **A8** |

**Resolution.** `architecture.md` §3 is now the canonical roster: **5 pipeline agents + Compliance (scheduled, off the request path) + the validation layer** — matching the roster shown in the current diagram subtitle. The brief's v1 table is retired, and `project_brief.md` links here instead of duplicating it. Guardian's promotion from optional to mandatory is the right call: it converts the child-safety constraint from a caveat into a visible feature, which is exactly what the deck's case studies do with their human-in-the-loop lines.

---

### A2 · "Orchestrator" now means the opposite of what it meant 🟠 `RESOLVED`

- **Brief v1:** *"Holds goal state, budget ledger, decides when to re-plan."* — a controller.
- **Diagram:** *"stands outside the pipeline — calls nothing, called by nothing; checks every subagent output at each gate before it advances."* — a validator.

Two problems. First, these are different components with the same name, which will confuse anyone reading both documents. Second, *"calls nothing, called by nothing"* is not implementable as stated — a component invoked by nothing cannot gate anything.

**Resolution.** Implementable reading, now in `architecture.md` §3.7: it is not a node in the business graph; it is a validation step applied **on every edge**. No agent calls it as a peer and it calls none as a peer, but nothing advances until it passes.

**Recommended rename: `Validator`.** "Orchestrator" carries the v1 meaning and will keep pulling readers back to a budget ledger this component no longer holds. Retained as "Orchestrator (validation layer)" in the docs for now so the diagram still matches — flip both together.

**Bonus.** Because it sees every payload, it is the natural instrumentation point for schema-validation pass rate, loop discipline and token cost. See **B3**.

---

### A3 · The budget ledger has no owner 🔴 `RESOLVED — D1, 31 Aug`

**This is the most consequential row in the register.**

The brief's answer to *"why must this be an agent?"* is the budget:

> *"The budget is finite and non-renewable. Spend is irreversible. The decision is sequential — each trial changes what should be tried next. It is a genuine explore/exploit problem under constraint, not a lookup."*

The diagram does not contain that. `time · money · interest` enter Personal Data as **static filter inputs**. There is no spend tracking, no tries counter, no reallocation after an outcome, and the *Reallocator* agent that used to do the job is gone. Nothing holds the ledger — the Orchestrator that used to hold it has been recast as a validator (**A2**).

The gap is narrower than "the budget is missing" — money is present as a *constraint*. What is missing is the **portfolio management over time**, which is the entire differentiator.

**What it costs if we leave it.** The honest description of the system as drawn becomes *"a constrained planner with a safety gate and a preference learner."* That is a good system, and it is also roughly what a well-built recommender with filters does. Directly at risk:

- **Originality (20%)** — the 1→2 band is "unique" vs "based on existing ideas." Budget-as-portfolio is the unique part.
- **Effectiveness (20%)** — "what would a fixed workflow miss?" is much harder to answer without it.

**Recommended resolution — small change, big return.** No new agent:

1. `BudgetLedger` in typed state (`architecture.md` §5) — money total/spent/committed, hours/week and committed, **tries total/used/abandoned**.
2. Planner reads it. Broker decrements it. Observer reconciles it after each outcome.
3. Reallocation becomes a Planner responsibility, so the v1 *Reallocator* stays retired.

**The alternative,** if the team would rather not touch the architecture: drop the portfolio framing from the brief and re-derive "why agentic" from the two request loops plus longitudinal preference cycle alone. Defensible, and materially weaker.

**Closed as D1 on 31 Aug: the recommendation was adopted.** `architecture.md` §5 and §9.1 carry the ledger, and it is no longer conditional. The alternative below is recorded only so nobody re-opens the argument.

---

### A4 · Revealed vs self-reported preference — a direct contradiction 🔴 `RESOLVED`

The brief could not be clearer:

> *"Signals are behavioural, not self-reported preference."* … *"revise the model of the user from **revealed** preference. No prediction, no typing."*

The diagram's Feedback Capture collects *likes & dislikes · demographic fit · vibes · environment · travel · comfortability*, as audio + text transcribed to structured prefs. **That is entirely self-report.** And it hangs off a single edge labelled `teen attends session`, so a teen who does not show produces no signal at all.

This is not a small inconsistency. "We learn from what you actually did, not from a quiz" is the intellectual spine of the whole product and the reason the personality-assessment approach was rejected in §6.

**Resolution.** Keep both, ranked. Renamed **Observer** in `architecture.md` §3.5, with two inputs:

| Signal | Weight | Rationale |
|---|---|---|
| **Attendance** — did they go, did they go back | **Primary** | Behavioural, hard to fake, available even when the teen says nothing |
| **Debrief** — vibes, comfortability, environment | Secondary | Rich and human, but self-reported and subject to politeness bias |

The debrief is worth keeping regardless: text→structured extraction is a genuine Extraction-class showcase and it demos clearly. It cannot be the *only* input, and it must not outrank attendance. Audio remains a roadmap adapter subject to the consent, processor and deletion controls in `architecture.md` §8.

---

### A5 · "Two no-shows → re-plan, not a nag" has no path 🔴 `RESOLVED`

Follows from **A4**, but listed separately because it is the flagship adaptivity behaviour and the best beat in the demo.

The brief §9 and `architecture.md` §10 identify the "agent correctly decides to do nothing" moment as the strongest single signal of genuine adaptivity. The v1 diagram had **no non-attendance edge, no timer, and no do-nothing outcome** — so as drawn, the behaviour could not happen.

**Resolution.** `architecture.md` §6 adds the `did_not_attend` edge and a `hold_this_week` terminal outcome, with the rule: one no-show → note it; two → re-plan; sustained attendance → escalate try→commit and reallocate.

---

### A6 · The belonging objective is in the brief and nowhere in the system 🟠 `RESOLVED — D2, 31 Aug`

Brief §3: *"Optimise for interest fit **and** belonging. Prefer options where a peer from the same school or neighbourhood is also attending."* Backed by real evidence (8% of youths report no close friends; friendships outside school is a stated aim of the Curiosity Credits scheme).

The diagram has no peer data in Personal Data, no peer field on a listing, and no second scoring dimension in the Planner. Brief v1 §11 also flagged the privacy mechanism as unsolved — *"How do we detect 'a peer is going' without creating a privacy problem?"* — a question this row now carries, and which option (a) below is the answer to.

So we are pitching a two-objective system and have specified a one-objective system, with a known-unsolved privacy question underneath the missing half.

**Options:**

| | Cost | Risk |
|---|---|---|
| **(a) Build it small** — an opt-in field on `Listing`, resolved coarsely and never to a named individual, used as a **ranking tiebreak** not a filter | ~half a day | Low. Privacy-safe by construction. |
| **(b) Cut it from the brief** | Free | Loses a genuine, evidenced differentiator |
| **(c) Leave it as-is — pitched, not built** | Free | **A judge asks "show me where belonging is scored" and there is nothing to show.** Worst of the three. |

**Option (a), built as cohort presence (D2, 31 Aug).** The obvious implementation — a friend graph — is the wrong one twice over: it **reproduces the school social graph** Hobbi exists to get a teen out of, and it is **empty on day one**, so it would be dead exactly when the demo runs.

`PeerCohort` on `Listing` instead: bucketed presence (`none/few/some/many`), suppressed below a k-anonymity floor of 5, resolved at planning-area or 2-digit postal-sector level and **never at school level**, opt-in to contribute, ranking tiebreak only, absence never surfaced. Spec in `architecture.md` §9.3 and §5, invariant **A12**.

---

### A7 · Discovery Engine is new and the brief never mentions it 🟠 `RESOLVED`

It is arguably the most differentiating component in the system — it is what indexes the long-tail supply the brief spends §5 arguing for — and it appears in no version of the brief.

**Resolution.** Specified in `architecture.md` §3.2 and written into `project_brief.md` v2 §3. Two design points recorded there that were implicit in the diagram:

- **It receives the plan, not the person.** Diagram says *"passes plan only to discovery."* That is a real privacy boundary — the only component touching the open internet never holds personal data — and it maps straight onto IMDA's *restricted tool access*. Worth saying out loud rather than leaving as an arrow label.
- **It is the only writer on the plan path**, so write-quality rules (verification state, `source_url`, `last_seen_at` on everything) live in exactly one place.

---

### A8 · Compliance Agent is new and the brief never mentions it 🟡 `RESOLVED`

Answers the existing user story *"detect outdated groups so users aren't sent to dead Telegram/Instagram communities."*

**Resolution.** In `architecture.md` §3.6. Two notes:

- It is what makes long-tail indexing **responsible** rather than reckless. Without it, the differentiating supply is also the supply most likely to send a shy 14-year-old to an empty room — which is the exact failure that ends the habit. Frame it that way in the pitch, not as a maintenance job.
- **Feasibility:** "scheduled scans" implies a deployed scheduler. For the PoC it is a manually-triggered script plus a demonstrated retire→replan cascade. Stated in `architecture.md` §10 so we are not implying infrastructure we did not build.

---

### A9 · Guardian's two jobs are conflated into one box 🔴 `RESOLVED`

The brief's hard constraint (§6) is **per-listing provider vetting**: an unverified private provider is never surfaced to the teen; it goes to a trusted adult first. The diagram's Guardian does *"safety check · parental approval"* on **the plan**.

Those are different checks at different granularities with different failure modes. A plan can pass spend approval while containing an unvetted provider, and vice versa. Collapsing them means one of the two silently does not happen.

**Resolution.** `architecture.md` §3.3 splits them explicitly: per-listing vetting (quarantine → trusted adult → bookable) and per-plan spend/attendance approval. Both required, both logged.

---

### A10 · The brief's six-step loop doesn't exist in the build 🟡 `RESOLVED`

Brief v1 draws `DECLARE → PLAN → BROKER → OBSERVE → UPDATE → RE-PLAN` as one ring. The system has **two capped request loops and one longitudinal feedback cycle** with different triggers, participants and bounds.

The three-cycle version is better for the deck as well as truer: it distinguishes request retries from post-session learning and shows where the system can get stuck. One big ring does not.

**Resolution.** `project_brief.md` adopts the two-request-loops-plus-longitudinal-cycle framing. `DECLARE` is not an agent — it is Parent setup + Teen request, recorded as such.

---

### A11 · `hold_this_week` is a required outcome that nothing produced 🟡 `RESOLVED`

Brief §9: *"Include at least one moment where the agent correctly decides to do nothing this week."* No such terminal state existed anywhere. Now a first-class outcome in `architecture.md` §5.

---

## B. Architecture ↔ Hackathon requirements

---

### B1 · Three loops, zero caps 🔴 `RESOLVED`

The deck says it twice, in two different places, in imperative mood:

> *"Bound every loop with a counter held in state."*
> *"Keep a hard iteration cap in state that ignores the model's judgement."*
> *"A refine loop that exits when the critic is satisfied will sometimes never be satisfied, and we discover it from the bill."*

The diagram's Planner *"replans until a gate passes."* That is, precisely and by name, the failure mode the deck warns about. **Loop Discipline** is also one of the six evaluation metrics the deck offers, and it cannot be reported at all without a cap to measure against.

**Resolution.** `MAX_REPLANS = 3`, `MAX_DISCOVERY_ROUNDS = 2`, `MAX_GUARDIAN_REJECTIONS = 2`, all in `constants.py`, all in typed state, all logged, each with a defined terminal behaviour at cap. `architecture.md` §4.

**Judges have been primed on this specific point.** A visible cap is cheap and reads as competence.

---

### B2 · No error or terminal states anywhere 🔴 `RESOLVED`

The diagram shows only the happy path. Nothing says what happens when Discovery finds nothing, when Guardian rejects three times, when a booking fails, or when a listing dies between planning and the session.

The deck grades this directly: *"Error Handling — baseline: functional resilience. Going further: how can you make it actionable for business users?"*

**Resolution.** `architecture.md` §6 defines every terminal state and error path, each producing a message a non-technical person can act on — *"nothing free within 30 min on a weekday evening; widening to Saturday opens 6 options"* rather than an empty result or a stack trace.

The "going further" answer is worth making explicit in the pitch: **our error messages name the binding constraint.** That is the difference between a dead end and a decision.

---

### B3 · Nothing captures evaluation data 🔴 `RESOLVED`

The deck **requires** testing/evaluation on the slides and offers six ready-made metrics. The architecture had no instrumentation point.

**Resolution.** The validation layer inspects every inter-agent payload, so schema-validation and loop data come from `gate_log`. Token usage comes from model-response metadata; tool outcomes come from the tool wrapper; terminal and attendance metrics come from their own events. `evaluation.md` names the source for every measure.

Most teams will skip evaluation entirely. This is the cheapest available separation on **Effectiveness (20%)**, and for us it costs almost nothing because the gate log already exists for other reasons.

---

### B4 · No tech stack named 🟠 `RESOLVED`

Slide 5 of the required deck structure is *"Technical Architecture — high-level system design, components, **tech stack**."* The diagram names no framework, model or library.

**Resolution.** `architecture.md` §11. LangGraph for two capped request loops, one ledger-bounded longitudinal cycle and typed state with reducers; Pydantic; `ChatBedrockConverse`; Claude Haiku 4.5 by default with Sonnet 4.5 where reasoning quality demands it; a SQLite-backed checkpointer + `thread_id` for the longitudinal thread (`InMemorySaver` is test-only); and a local-first, AgentCore-ready entrypoint. Staying on the taught stack also makes the code legible to judges who sat through the same sessions.

---

### B5 · Agent classes not claimed 🟡 `RESOLVED`

Topic #2 of the deck is an eight-class taxonomy, and it states outright that agents commonly span several. Naming ours costs one line on the architecture slide and is free evidence for *"showcase your knowledge of Agentic AI."*

**Resolution.** `architecture.md` §12. We claim five: Decision-Support, Personalized, Information, Extraction, Transaction, Orchestration. We deliberately do **not** claim Embedded or Creative/Generative — nothing generates content or lives inside another product, and claiming a class we do not occupy is worse than claiming five accurately.

---

### B6 · Human-in-the-loop present but not labelled 🟡 `RESOLVED`

Every case study in the deck carries an explicit *"Human-in-the-loop:"* line. Ours has it — parent setup, Guardian approval — and never names it.

**Resolution.** `architecture.md` §7 names all four checkpoints and maps them to the IMDA framework dimensions. Free credibility with a Singapore panel, and our risk profile (minors + irreversible spend) is exactly what that framework anticipates.

---

### B7 · Scope of the claim vs what the prototype resolves 🔴 `RESOLVED — D3, 31 Aug`

**This is the highest-leverage decision in the register.**

The Effectiveness rubric bands are:
- **2 pts** — "Fully addresses and **resolves** the problem"
- **1 pt** — "**Partially** addresses the problem, but not fully resolved"

The brief pitches a **12-month adaptive portfolio**. The prototype demonstrates a plan→approve→book→observe cycle plus a simulated longitudinal replay. If the stated problem is *"teens in Singapore can't find hobbies that stick over a year,"* then by our own honest account we partially address it, and we are **capped at 1** on a 20% criterion.

The deck's "Boiling Ocean" failure mode says the same thing from the other side: *"cut one slice we can finish and demonstrate."*

**Recommendation.** Write the problem statement narrow enough that the prototype demonstrably closes it, and put the 12-month vision on slide 9 (Roadmap & Future Potential) where it is an asset rather than an unmet promise.

A narrow statement that survives the deck's POV test and that we can actually close — proposed in `project_brief.md` v2 §1, for the team to sharpen:

> *A 14-year-old on S$500 of Curiosity Credits needs a way to spend a first S$0 try without an adult driving the search, because the free options are split across CCs, ActiveSG and group chats that no single directory indexes.*

That is closable in a demo. "Teens need hobbies that stick" is not.

**Resolution (D3).** Narrowed — and widened at the same time, because two things were being conflated. The **outcome** is narrow (one first attended session, graded under Effectiveness); the **audience** is broad (every secondary student on limited discretionary money, graded under Benefits). The earlier draft leaked the audience into the outcome by leading with Curiosity Credits, which quietly made SHG members the whole market.

Final wording, now in `project_brief.md` §1.1:

> *A 14-year-old in Singapore with S$0 of their own to spend needs a way to find and reach a first hobby session this month — because Singapore is expanding to 20,000 social, hobby and interest opportunities a year and 12 free youth spaces, while finding an option still requires searching separate Community Club, ActiveSG and youth-space channels.*

**S$0 is the harder constraint, not the humbler one.** A system that closes it closes the funded case trivially, and it is already invariant **A3** rather than a marketing line. Curiosity Credits move to slides 7 and 9 as a funded, nationally-announced beachhead — an adoption argument instead of a ceiling.

---

### B8 · The demo cannot show the thing being pitched 🟠 `RESOLVED`

The value accrues over months. The video is five minutes and the deck allocates two of them to the demo. Loop 3 — the longitudinal one, the only thing that makes this more than a recommender — is invisible in a single session.

**Resolution.** The simulation harness is now a named build item (`architecture.md` §10), not a demo afterthought, and it doubles as the evaluation substrate. Three things it must show:

1. **The diff, not the output** — old plan → trigger → reasoning → new plan.
2. **The counterfactual** — what a static recommender would have returned alongside what the agent did. Adaptation is only legible against a baseline.
3. **At least one `hold_this_week`** — the agent correctly doing nothing. No ranked-list product can produce that moment.

---

### B9 · Broker spends real money on behalf of a minor 🟠 `RESOLVED`

*"Makes bookings"* is an irreversible action with material real-world impact, taken on behalf of a 13–17-year-old. Guardian precedes it, which is correct. Two things were unstated.

**Resolution.**
- The architecture now says explicitly that **Broker is sandboxed in the PoC** — real booking records and confirmations, no live transactions. A judge asking *"did you actually book anything?"* should get the answer before they ask; being caught implying otherwise costs more than the honesty does.
- Ordering is now a stated invariant, not an accident of layout: **Broker is unreachable without a Guardian pass.**

---

### B10 · Voice recordings of minors 🟠 `RESOLVED`

Feedback Capture records audio from 13–17-year-olds. The brief mentions PDPA once, in passing, as something to *"also address in slides."* That is not a position.

**Resolution.** PDPC guidance is fetched and quoted in `sources.md` §G2. The PoC is now text-only. A future audio adapter must name its STT processor, obtain teen + parent consent, transcribe → extract structured preferences → **discard the audio**, retain the transcript only on explicit opt-in, and pass a deletion test.

---

### B11 · The evaluation measures a wider claim than the problem statement 🔴 `RESOLVED — D3b, 31 Aug`

Spotted on review, and it is the trap inside **B7**'s own recommendation.

B7 says: narrow the problem statement so the prototype can *"fully address and resolve"* it — a first S$0 try, not twelve months of adherence. Sensible. But `evaluation.md`'s headline metrics are all measurements of the **wide** claim:

| Metric | What it measures | Horizon |
|---|---|---|
| **B14 · adherence delta vs static baseline** — labelled *"the headline number"* | Whether the teen keeps going | 9–12 month replay |
| **B11 · adaptation latency** | Cycles between signal and re-plan | Multi-cycle |
| **B12 · hold rate** | Is it adapting or nagging | Multi-cycle |

So narrowing the problem statement does not resolve the tension — **it relocates it into the gap between slide 2 and the evaluation slide.** A judge reads "we help a teen get to one first session", then sees a headline metric about twelve-month adherence, and asks which one we are claiming.

**Recommended resolution — one metric moves, nothing is lost.** Promote a metric that measures the *narrow* claim to headline, and keep the longitudinal set as supporting evidence for the roadmap:

- **New headline:** *first attendance within 30 days at S$0*, including calendar time and teen-side actions, agent vs static baseline. It measures exactly what the narrow statement promises, and the counterfactual arm still does the work.
- **Demoted to supporting:** B14, B11, B12 — reframed on the slide as *"and here is what the same policy does over twelve months"*, which is the roadmap argument rather than the effectiveness claim.

**Resolution (D3b).** Adopted and made calendar-bound after PR review. **B15 — first attendance within 30 days at S$0, including time and teen-side actions** is the headline; B14, B11 and B12 stay in the report as supporting evidence for the roadmap slide. `evaluation.md` §3.3, §5 and §7 all updated. Slide 2 and the headline metric now measure the same thing.

---

## C. Brief ↔ Hackathon requirements

---

### C1 · The problem statement is not in the required format 🔴 `RESOLVED`

The deck mandates POV: `[User] needs [a way to ...] because [insight].` Brief v1 opens with:

> *"Singaporean teenagers overwhelmingly want hobbies. Almost none of the system around them is designed to help them find one that sticks."*

Good rhetoric, wrong artefact. It also trips two of the deck's six named failure modes:

- **The Everyone Problem** — "Singaporean teenagers" is a population, not a person at a moment. The deck: *"'Users' and 'people' will not pass."*
- **The Boiling Ocean** — as scoped, not resolvable in four days. See **B7**.

The brief already contains everything needed to fix it: §2's persona is sharp (a 14-year-old in an SHG family, S$0 discretionary, no parent free to drive them, no idea free CC courses exist, no friend already doing the thing). It just never got compressed into one sentence.

**Resolution.** `project_brief.md` v2 §1 leads with a POV statement, pressure-tested against all four of the deck's questions, with the narrative moved underneath it. Final wording settled by **D3** on 31 Aug.

---

### C2 · Criterion numbers reference a rubric that doesn't exist 🟡 `RESOLVED`

Brief v1 cites *"hackathon criterion 3"*, *"criterion 1"* and *"criterion 2"* in §1 and §3. The actual criteria are Benefits / Originality / Effectiveness / Technical Quality / Presentation, and none of the numbers line up. Looks like a holdover from an earlier brief. In a source-of-truth document this is actively misleading — someone will optimise for the wrong thing.

**Resolution.** All references renamed to the real criteria in v2.

---

### C3 · The brief lists our own hackathon as a competitor 🟠 `RESOLVED`

Brief v1 §10, under "Competitive Context":

> *"Local competition note: the SimplifyNext Agentic AI Hackathon (NUS/NTU) asks students to tackle 'mental health, student success, financial inclusion, sustainable cities' and its 2026 edition is running now."*

**That is the hackathon we are in.** And those are the 2025 themes — the 2026 theme is *"Design for a World in Transformation."* Reading our own source of truth as if we were outside it is a small thing that reads badly.

**Resolution.** In v2, §10 keeps the winner analysis (which is genuinely useful — the Navigator + Coach shape argument is good) and drops the framing of SimplifyNext as external competition. The 2026 theme now sits at the top of the brief where it belongs.

---

### C4 · No evaluation or testing anywhere in the brief 🔴 `RESOLVED`

Explicitly required (*"Testing/Evaluation should be covered in your slides"*), and the brief's only gesture at it is §9's *"quantify one number."* Right instinct, no methodology — and the deck asks specifically that we **justify the testing methodology** and derive metrics *"in translation to the Problem Statement & Solution Objective."*

**Resolution.** New `evaluation.md`, referenced from the brief.

---

### C5 · No tech stack in the brief 🟡 `RESOLVED`

Required for slide 5. Now in `architecture.md` §11, referenced from the brief rather than duplicated.

---

### C6 · No "what we build in four days" line 🟠 `RESOLVED`

Nothing in v1 distinguishes the vision from the build. Both the Boiling Ocean failure mode and the Effectiveness rubric demand the distinction, and Technical Quality's 1→2 band ("minimal work needed for production") is only assessable against a stated scope.

**Resolution.** `architecture.md` §10 — in-PoC vs deferred, per component, including which parts are sandboxed or simulated.

---

### C7 · The sources doc points at a file that doesn't exist 🟡 `RESOLVED`

`sources.md` opens *"Companion to `hobby-agent-project-brief.md`."* No such file. It is `project_brief.md`. Fixed.

---

### C8 · The persona has no name 🟡 `RESOLVED`

The deck's own DO/DON'T list gives *"Meet Jane, a university student who struggles to access timely support"* as the model for a user story slide. Our persona is sharper than Jane and anonymous.

**Resolution.** Named in v2 §2 and used consistently across the deck, the video and the simulation harness, so slide 2, the demo and the evaluation data are all visibly about the same person.

---

### C9 · Objection-handling is a strength — keep it 🟡 `NOTED`

Brief v1 §7 pre-empts *"don't they already have CCAs?"*, *"won't NYC just build this into Discover?"* and *"isn't this just a recommender?"* This is genuinely good work and it maps directly onto the Presentation rubric, whose 1-point band is *"partially explained, with some prompting or clarification needed."* Answers that land without prompting are worth a full point.

**Kept verbatim in v2**, with one addition: the CCA argument currently rests on a Wikipedia citation, which is the weakest source behind the objection judges are most likely to raise. See §D.

---

### C10 · Version metadata stale 🟡 `RESOLVED`

*"Version 1 · Synthesised from research conducted 18 Aug 2026."* Bumped to v2, 27 Aug 2026, with a changelog.

---

## E. Downstream artifacts now out of sync

### E1 · `origin/feat/agent-system-prompts` predates this doc set and diverges from it 🟠 `OPEN — scheduled: re-derive once this branch merges (D6)`

An unmerged branch (10 commits, 25–28 Aug 2026, forked after `eea58dd`) contains ~1,700 lines of real work: six agent system prompts, a normative `shared-protocol.md`, a design spec and plan, and nine test fixtures with a validator.

**It is downstream of these documents, not an input to them.** The source of truth is being set here; the prompts are an output of it. Nothing in this register changes the architecture because of that branch. What follows is a **re-derivation checklist** for whoever realigns it.

Where the branch and [`architecture.md`](../3-system/architecture.md) currently disagree:

| # | Branch says | These docs say |
|---|---|---|
| 1 | **Compliance sits in the plan path**: Discovery → Compliance → CKB, validating before any write | Discovery writes to CKB directly and is *"the only writer on the plan path"*; Compliance runs **scheduled, off the request path** |
| 2 | **Orchestrator is an active router** — *"routes work and maintains workflow state"* | Orchestrator is a **passive on-edge validator**; the controller reading was explicitly retired in **A2** |
| 3 | **No Observer / feedback agent** — outcomes return "through Orchestrator to Planner" | **Observer** is one of the five pipeline agents and is the only component that learns (**A4**) |
| 4 | Store is called **Child Profile** | Store is called **Personal Data** |
| 5 | Framed as a system for **children**, *"lifelong activity and career-exploration"* | Framed for **13–17-year-olds**, hobby discovery. This one is not cosmetic — it moves the PDPA consent basis (under-13 requires parental consent; 13–17 may self-consent) and it changes the product |

**Item 5 is settled: D7, 31 Aug — the cohort is 13–17, hobby discovery.** The branch's "children / lifelong activity and career exploration" framing is superseded, and the PDPA consent basis follows from the 13–17 boundary (`architecture.md` §8). The other four rows still need re-deriving.

**Also worth noting for whoever picks it up:** the branch's tests are PowerShell (`validate-fixtures.ps1`, `test_validate_fixtures.ps1`) while its own README invokes `python tests/agent-system-prompts/validate_fixtures.py`. The deck says **"Python is strongly recommended"** and judges will run what the README says. Whatever survives re-derivation should be Python.

**Action:** PR #2 has merged. Regenerate the system prompts from [`architecture.md`](../3-system/architecture.md) §3 — where the agent descriptions are already written to be the source text for prompts — rather than editing the old branch in place. Status and acceptance are tracked as **OW-03** in [`outstanding.md`](../5-delivery/outstanding.md).

---

## D. Decisions

### All twelve closed — 31 Aug 2026

| # | Question | Decision | Consequence |
|---|---|---|---|
| **D1** | **A3** — keep the budget-as-portfolio thesis and add the ledger? | **Yes.** `BudgetLedger` in typed state; Planner reads it, Broker decrements it, Observer reconciles it after each outcome. The v1 *Reallocator* stays retired — this needs state, not an agent. | `architecture.md` §5 and §9.1 already carry it; the "assumed pending decision" hedges come out. **A3 closes.** The Originality argument now rests on something that exists in the schema. |
| **D2** | **A6** — belonging: by what mechanism? | **Cohort presence, not a friend graph.** Aggregate `PeerCohort` on `Listing`: bucketed counts, k-anonymity floor of 5, planning-area level and never school, opt-in to contribute, ranking tiebreak only, absence never shown. | `architecture.md` §9.3 and §5; `project_brief.md` §3.7; invariant **A12**. **A6 closes.** A friend graph would have rebuilt the school social graph the product exists to cross — the privacy-preserving design is also the more effective one. |
| **D3** | **B7** — how narrow is the problem statement? | **Narrow on outcome, broad on audience** — they are different questions, graded under different criteria. The outcome is *one first attended session*; the audience is every secondary student on limited discretionary money. Statement now leads with **S$0** instead of S$500 of Curiosity Credits, which become the wedge on slides 7 and 9. | `project_brief.md` §1.1 rewritten with the audience/outcome table; §1.2 and §2.1 realigned. **B7 and C1 close.** |
| **D3b** | **B11** — which metric is the headline? | **B15 — first attendance within 30 days at S$0**, including calendar time and teen-side actions, agent vs static baseline. B14 (12-month adherence), B11 and B12 demoted to supporting evidence on the roadmap slide. | `evaluation.md` §3.3, §5, §7. **B11 closes.** Slide 2 and the headline metric now measure the same thing. |
| **D4** | Is there a live pitch and Q&A? | **Prepare for one regardless, at second priority.** It only happens if we are promoted, so the order is: sharpen the idea → build the deck → prep Q&A *against* the deck. | Objection sheet comes from `project_brief.md` §7, which already answers the three most likely questions. Rehearsal stays item 7 in `deliverables.md` §11.5. |
| **D5** | Deadline, upload mechanism, formats | **Team settles directly with the organisers.** No doc dependency. | Still gates the final freeze: project files are **one submission only**, no re-uploads. |
| **D6** | When do we re-derive the system prompts on `feat/agent-system-prompts`? | **After this source-of-truth branch is reviewed and merged to main.** Team owns the merge flow. | E1's re-derivation checklist stands as written. Regenerate from `architecture.md` §3 rather than editing the branch in place. |
| **D7** | Trusted adult — and who is the user? | **13–17, both ends, enforced at I0.** No adult mode; 18+ is roadmap. Under-13 gets trusted-adult guidance; 18+ gets general-services guidance. A trusted adult is mandatory for every eligible user, because every eligible user is a minor. | `architecture.md` §2 carries the boundary and enforcement; §8 carries consent. Invariant **A11** tests both bounds. **Closes E1 item 5** — the branch's "children / career exploration" framing is definitively wrong. |
| **D8** | Real integrations, or seed KB + simulated booking? | **Hybrid.** Seed CKB from **real** listings, hand-transcribed, every row carrying `source_url` and a real `verified_at` · Discovery **searches live** over a whitelisted domain set · Broker **sandboxed**, stated on slide 5 · a **cached replay fixture** so the demo never depends on a live call succeeding. No real provider integrations — there is no public booking API for CC courses or ActiveSG, and the payer is a minor. | `architecture.md` §10 confirmed, plus a replay row. **Tripwire below.** |
| **D9** | Observation channel | **In-app text form, behind a channel-agnostic `DebriefSubmission`.** *Revised 31 Aug — the original decision was a Telegram bot; narrowed after PR review.* The interaction still reads like texting a friend. Audio is roadmap until an STT processor, consent path and deletion test are specified. | `architecture.md` §3.5, §5, §8, §10. **Reversal reasoning below.** The text debrief is a build item; audio is not. |
| **D10** | Cold start | **4–6 vibe chips, multi-select, skippable** — "sporty", "artistic", "chill", "explorative". Five binding rules: skippable with *"Surprise me"* first-class · no label ever shown back · lowest confidence, outranked by the first attended session · biases ranking but never filters · asks *where to start*, not *what you are like*. | **Reconciles the collision with §6.1.** The line is now stated in the docs rather than implied: **seeding is permitted, typing is not.** `project_brief.md` §6.1 carries the distinction table, `architecture.md` §3.1 the five rules, `user_stories.md` the reworded story. New invariants **A9** (seeds and dislikes never change candidate-set membership) and **A10** (a skipped cold start still yields a viable plan). |
| **D11** | Model *dislike* explicitly? | **Yes, with decay.** A dislike is a signed, timestamped, confidence-weighted signal on a preference axis — **never a blocklist entry.** Something disliked at 14 can be liked at 16, and the model has to allow that. | **Specified 31 Aug.** `DislikeSignal` in `architecture.md` §5 with a 90-day half-life and a 0.15 floor; Observer attributes `activity` / `instance` / `unattributed` (§3.5); an axis moves only on **two** corroborating `activity` signals. Ranking-only, tested as invariant **A9**. |

**D8 tripwire.** If live Discovery is not reliable by demo day, the fallback is a pure seed CKB — **but then B9 (long-tail coverage) comes off the evaluation slide, or is relabelled illustrative.** A metric computed over data we authored ourselves is not evidence, and it is the metric the Originality argument leans on. Decide that now, not at 2am on the last night.

**D9 reversal, recorded rather than rewritten.** The first decision on 31 Aug was a Telegram bot, on the reasoning that a message gets answered and an app has to be opened. Three things overturned it the same day:

1. **It would have undermined invariant A8.** A third-party messenger would hold a minor's submission before our code sees it. The review then exposed a second problem: the PoC stack named no STT component at all. A8 now enforces a text-only PoC; audio remains roadmap until its full processor and deletion path exists.
2. **It added a second live network dependency to the demo**, immediately after **D8** added a cached replay specifically to remove one. Two network paths at judging time, for a non-core feature, against requirement 8.4.1.
3. **A third-party platform sets its own minimum age**, and **D7** fixed our cohort at 13–17. That is a compliance question, not a preference. *(Unverified — check the ToS before any future adapter ships.)*

**What was not lost.** "Telegram is where the teens are" was about *supply* — Discovery reading public groups (`project_brief.md` §5.2) — which is a different path and unaffected. Attendance, no-shows and `hold_this_week` never depended on the debrief channel. The response-rate bet is real but unmeasurable in four days, so it belongs on the roadmap slide either way.

**The good part survived:** the register. One open text question, no star ratings. The instinct was right; the transport and audio scope were wrong.

---

**Source verification** — the original priority list is closed; `sources.md` §J records the remaining tasks. The two review-triggered items are verifying whether Discover is actually the sign-up channel for the 20,000 opportunities and validating the adult-coordination insight in interviews.

---

## F. PR #2 review follow-up

The external review on PR #2 found a second layer of cross-document defects after the original 33-row register closed. These are corrections to the chosen design, not new product decisions.

| Review findings | Resolution |
|---|---|
| 1, 12–14 | v2.2 HTML/PNG and prose use I0 plus G1–G4; consent and approval are separate; prose no longer describes v1 |
| 2, 4, 7–9, 15–16, 24–25 | Eligible and boundary test populations split; Guardian cap fixed at two; B15 has a 30-day window; metric sources and completion classes named |
| 3, 5–6, 26 | Replacement plans re-enter Guardian; store ACL added; Intake/Setup and the build-time seed loader are shown as writers; simulated cohort producer named |
| 10, 17, 20–22 | Problem evidence and official-deck attribution corrected; stale source rows and citation errors removed |
| 11, 18, 23 | Text-only PoC debrief; pip-based judge path; comparison/share scope reduced or deferred |
| 19 and review nits | Severity totals, schema names, persistent checkpointer, decision count, slide count and hackathon-source count corrected |

The review's positive link check remains true: every relative documentation link resolved at that review point. The follow-up audit rechecks link integrity after the latest edits without freezing a count that changes whenever documentation links are added.

### Final-pass review of the fixes

The second PR review found no reopened decision, but correctly identified consistency drift introduced by the first correction pass. The follow-up standardizes all gate references on **I0 + G1–G4**; adds Intake/Setup and the build-time seed loader to the prose, planned layout and diagram; distinguishes a permitted cap hit from an invariant-breaking cap breach; corrects the remaining evidence, audio, slide, branch and reproduction references; and refreshes the PR description.

The subsequent audit also tightened two items not raised in that review: G1 now specifies its different outbound and return payload checks, and G3/G4 now have explicit `GuardianVerdict` and `BookingRecord` schemas with idempotent ledger fields. PR #3 reconciles the former `feat/seed-ckb` follow-up: `ListingRecord` is now the shared stored contract, `Listing` is the teen-relative Planner view, the deterministic build/load seam is executable, and the former “nothing built yet” wording has been retired.
