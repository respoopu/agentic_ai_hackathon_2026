# User Stories — Hobbi

*Version 2 · 27 Aug 2026. Every story now names the **agent that owns it** and whether it is in the prototype.*

Grouped by user. Each row: the story, what Hobbi needs to know, the feature it implies, and the owning agent from [`architecture.md`](./architecture.md) §3.

**Build status — nothing is implemented yet.** These marks are *scope*, not progress: ✅ planned for the PoC · 🔶 partial / simulated in the PoC · ⬜ deferred to roadmap · ⚠️ **pitched but not yet specified — see [`discrepancies.md`](./discrepancies.md)**

> There is no Hobbi code in this repository at the time of writing. Every ✅ below is a commitment we have made to ourselves, not a feature that exists. When implementation starts, this column becomes the checklist.

> A story with no owning agent is a feature nobody is building. That column is the point of this document — it is how we catch a slide promising something the graph cannot do.

---

## Teen — Discovery & Personalisation

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a teen, I want to discover hobbies that suit me, because I don't know what I would enjoy.** | Preference axes, prior attendance | Experiment sequencing, not a ranked list | **Planner** | ✅ |
| **As a teen, I want recommendations to improve when I tell Hobbi what I liked or disliked.** | Debrief content, attendance, return behaviour | Feedback-driven preference model | **Observer** → **Planner** | ✅ |
| **As a teen, I want to not be asked a personality quiz before I've tried anything.** | — | Absence of an assessment step | **Planner** *(by design)* | ✅ |

> ⚠️ **"Personality" input must never become left/right-brain or MBTI-style typing.** Hard, non-negotiable ([`project_brief.md`](./project_brief.md) §6.1). Use non-stigmatising preference axes — indoor/outdoor, team/solo, contact/non-contact, high/low intensity, competitive/social — each carried with a **confidence** that grows from attendance, not from a questionnaire.
>
> Feedback favours **revealed** (behavioural) preference over self-report. The debrief is real and useful, but attendance outranks it ([`architecture.md`](./architecture.md) §3.5). The theory behind refusing to diagnose is Hidi & Renninger's four-phase model — you cannot measure an interest in someone who has not yet had a trigger ([`project_brief.md`](./project_brief.md) §3.2).

---

## Teen — Practical Filters

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a teen, I want hobbies within my budget so I don't get recommended things I can't afford.** | One-time, recurring and equipment cost; money remaining | Hard budget constraint + estimated total cost | **Planner** *(reads ledger)* | ✅ |
| **As a teen, I want activities that fit my schedule.** | Free days, times, school and CCA commitments | Availability matching | **Planner** | ✅ |
| **As a teen, I want groups near me so travelling isn't a pain.** | Location, max travel time — **from home *and* from school** | Travel-time filtering on both origins | **Planner** | ✅ |
| **As a teen, I want to meet people around my age so I don't end up in a group of 40-year-olds.** | Participant age range | Age-range filtering | **Planner** | ✅ |

> ⚠️ **S$0 must be a fully viable input, not an edge case** ([`project_brief.md`](./project_brief.md) §4). Tested as invariant **A3** in [`evaluation.md`](./evaluation.md), not left to hope. If no plan exists at S$0, that is a **CKB coverage bug** for Discovery, not a "no results" screen.
>
> Travel time is computed **from school as well as from home** — a teen goes straight from school more often than from home, and every incumbent product models only the home origin.

---

## Teen — Confidence & First-Timers

*This whole block is the `tries` currency: how many times will a teen walk into a room alone before giving up? Every story here reduces the cost of one try.*

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a beginner, I want groups that welcome beginners so I don't feel embarrassed joining.** | Experience level, group requirements | `beginner_friendly` flag | **Planner** *(field on `Listing`)* | ✅ |
| **As someone joining alone, I want to know how welcoming a group is to newcomers.** | Whether people usually join alone; newcomer process | `join_alone_ok` — "good for first-timers" | **Planner** / **Discovery** | ✅ |
| **As a shy teen, I want to know what will happen before I arrive so I feel less anxious.** | Meeting format, group size, meeting point, activities | "What to expect" preview | **Broker** | ✅ |
| **As a teen, I want to know exactly what I need before joining.** | Equipment, clothing, prerequisites | Preparation checklist | **Broker** | ✅ |
| **As a teen, I want to bring a friend if I'm uncomfortable attending alone.** | Whether groups allow guests | `guest_allowed` + share | **Planner** / **Broker** | 🔶 |

> The Broker's teen-facing output is not a confirmation email. It is an **anxiety-reduction artefact** — where exactly to meet, what happens in the first ten minutes, whether people usually come alone. It exists because a burnt `try` cannot be recovered.

---

## Teen — Decision Support

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a teen, I want to try a hobby without committing lots of money.** | Trial sessions, rentals, free groups | Cheapest-reversible-first sequencing | **Planner** | ✅ |
| **As a teen, I want to see actual upcoming sessions rather than just reading about a hobby.** | Group calendars, `next_sessions` | Upcoming events feed | **Discovery** → **Planner** | ✅ |
| **As a teen, I want to save interesting hobbies and come back later.** | Favourites | Saved hobbies | **Planner** *(reads a favourites list in Personal Data)* | ⬜ |
| **As a teen, I want to compare different activities before deciding.** | Cost, distance, time, social level, equipment | Comparison view | **Planner** | 🔶 |
| **As a teen, I want to be left alone when there's nothing worth telling me.** | Whether anything actually changed | `hold_this_week` | **Observer** → **Planner** | ✅ |

> "Try it first" is the product surface for the loop's **explore** phase — cheapest experiments before term-long commitments ([`project_brief.md`](./project_brief.md) §3.1).
>
> **The last story is the one no competitor has.** An agent that only ever escalates is a nag with a planner attached. `hold_this_week` is a first-class terminal outcome and a reported metric ([`evaluation.md`](./evaluation.md) B12).

---

## Teen — Trust Signals

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a teen, I want to know whether a group is active before travelling there.** | Recent posts, events, `last_seen_at` | Freshness / last-verified indicator | **Compliance** | ✅ |
| **As a teen, I want to know whether the information is trustworthy.** | `source_url`, `verified_at` | Source attribution + verified badge | **Discovery** *(writes)* / **Compliance** *(maintains)* | ✅ |

> Every row Discovery writes carries `source_url` and `last_seen_at`, so provenance is always attributable. This is not bookkeeping — it is what lets us surface long-tail supply at all without being reckless ([`project_brief.md`](./project_brief.md) §5.4).

---

## Parent / Trusted Adult

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As a parent, I want to understand where my child is going and who is running the activity.** | Organiser identity, venue, timings, contact | Reassurance artefact | **Broker** | ✅ |
| **As a parent, I want potentially unsafe activities or groups to be flagged.** | Moderation signals, venue type, organiser verification | Vetting queue | **Guardian** | ✅ |
| **As a parent, I want to approve anything that costs money before it happens.** | Plan cost vs ledger | Per-plan spend approval | **Guardian** | ✅ |
| **As a parent, I want to know *what changed* rather than approving the same thing repeatedly.** | Diff against the last approved plan | Escalations state what changed and why | **Guardian** | ✅ |
| **As a parent, I want to set rules once and not be pestered.** | Parental rules, consent, thresholds | One-time setup + ongoing edits | **Guardian** *(enforces the rules the parent writes to Personal Data)* | ✅ |
| **As a parent, I want to know what the agent is allowed to do on its own.** | Agent scope and limits | Plain-language scope statement | **Broker** *(parent artefact)* | 🔶 |

> The vetting queue is the mandatory requirement for unverified providers — hard and non-negotiable ([`project_brief.md`](./project_brief.md) §6.3). **An unverified private provider is never surfaced directly to the youth**; it goes to a trusted adult first. Tested as invariant **A1** and reported as an absolute count, because 99% containment is a failure.
>
> The fourth row exists because of **automation bias**, which the IMDA framework names explicitly: a parent who approves twenty plans in a row will approve the twenty-first without reading it. The last row is IMDA dimension 4, *"enable end-user responsibility."*

---

## Hobbi (the Platform)

| User story | What Hobbi needs to know | Feature | Agent | |
|---|---|---|---|---|
| **As Hobbi, we want to detect outdated groups so users aren't sent to dead Telegram/Instagram communities.** | Last activity, link validity, event recency | Automated freshness checking | **Compliance** | 🔶 |
| **As Hobbi, we want to find supply that isn't in any directory yet.** | What CKB already holds; external sources | Gap-driven external search | **Discovery** | ✅ |
| **As Hobbi, we want to never leak personal data to the open internet.** | — | Discovery receives the plan, not the person | **Orchestrator** *(gate ◆1)* | ✅ |
| **As Hobbi, we want to know whether the agent is converging or circling.** | Loop counts vs caps | Loop discipline logging | **Orchestrator** | ✅ |
| **As Hobbi, we want every claim on our slides to be reproducible.** | Gate log, token usage | One-command evaluation report | **Orchestrator** → [`evaluation.md`](./evaluation.md) | ✅ |

> Compliance is 🔶 because the PoC runs a **manually-triggered** scan plus a demonstrated retire→replan cascade, not a deployed scheduler ([`architecture.md`](./architecture.md) §10). Say so on the slide.

---

## ⚠️ Pitched but unowned

Two commitments in [`project_brief.md`](./project_brief.md) have no agent and no field behind them. Both are open decisions in [`discrepancies.md`](./discrepancies.md) §D.

| Story | Why it has no owner | Decision |
|---|---|---|
| **As a teen, I want to go somewhere a friend or someone from my school is going, so I don't walk in alone.** | Belonging is stated as a second objective in the brief, but nothing in the architecture scores for it — no peer field, no scoring dimension. The privacy mechanism is also unsolved. | **A6 / D2** — build the opt-in `peer_going` tiebreak, or cut the claim. Do not present it unbuilt. |
| **As a teen, I want the money to last across several tries, not be spent on the first thing.** | The architecture carries money as a static filter, not as a ledger that is spent down and reallocated. **This is the story the entire "why agentic" argument rests on.** | **A3 / D1** — add `BudgetLedger` to typed state. Small change, highest impact in the project. |

---

## Coverage by agent

A quick read on whether each agent is carrying its weight — the deck's test is that a multi-agent design *"only counts if each agent does something the others can't."* Counts are of the 30 owned story rows above; a story naming two agents counts for both.

| Agent | Stories | Verdict |
|---|---|---|
| **Planner** | 15 | The core, and by a wide margin. Owns every constraint and all sequencing. Worth watching: if Planner owns half the stories, check it is one agent and not four wearing a trenchcoat. |
| **Broker** | 5 | Two distinct audiences — the teen's anxiety artefact and the parent's reassurance artefact. Earns its place. |
| **Discovery** | 4 | The only component that grows the supply side. Our differentiator. |
| **Guardian** | 4 | The only component that can say no. Two granularities: per-listing vetting, per-plan spend. |
| **Compliance** | 3 | Small but load-bearing: it is what makes long-tail indexing responsible rather than reckless. |
| **Orchestrator** | 3 | Not a business agent — validation and instrumentation. All are platform stories. |
| **Observer** | 2 | The only component that learns. Attendance first, debrief second. Thin on stories because most of its value is *longitudinal* and shows up as Planner behaviour next cycle. |

No agent is idle, and no two agents overlap. **Both unowned stories belong to Planner** and need state, not a new agent — which is why v1's *Reallocator* stays retired.

> ⚠️ Planner owning 15 of 30 is the one number here worth arguing about. If it turns out to be doing constraint-filtering, sequencing *and* reallocation as three unrelated jobs, the deck's own advice — *"build short, single-purpose agents that do one job and exit"* — says split it. Revisit once the ledger decision (**D1**) lands.
