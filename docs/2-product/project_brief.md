# Project Brief — Hobbi

*Hackathon: SimplifyNext Agentic AI Hackathon 2026 — **"Design for a World in Transformation"***
*Version 2.1 · 31 Aug 2026 · supersedes v1 (18 Aug 2026)*

**The doc set.** 
- [`deliverables.md`](../1-requirements/deliverables.md) — what the hackathon requires · **this** — problem, user, solution, positioning · 
- [`architecture.md`](../3-system/architecture.md) — the system spec · 
- [`evaluation.md`](../3-system/evaluation.md) — how we prove it works · 
- [`user_stories.md`](./user_stories.md) — stories mapped to agents · 
- [`sources.md`](./sources.md) — every citation · 
- [`discrepancies.md`](../4-decisions/discrepancies.md) — open conflicts and decisions.

> **What changed in v2.1 (31 Aug).** All twelve open decisions closed (§12). The problem statement now leads with **S$0** rather than S$500 of Curiosity Credits — narrow on outcome, broad on audience (§1.1). Belonging is built as **cohort presence, not a friend graph** (§3.7). The cohort is fixed at **13–17 at both ends** (§2, §6.4). The budget ledger has an owner (§4). §6.1 now states where the line falls between **seeding and typing**, because the cold start asks a short question.
>
> **What changed in v2 (27 Aug).** Problem statement rewritten into the required POV format and pressure-tested. **The "42% of youths satisfied" figure is removed — it does not survive verification** (see §1.2). The agent roster now lives in [`architecture.md`](../3-system/architecture.md) and matches the diagram. Evaluation, tech stack and build scope added. Criterion references corrected to the real rubric. All headline figures re-sourced to primary documents.

---

## 1. Problem Statement

### 1.1 The statement

> **A 14-year-old in Singapore with S$0 of their own to spend needs a way to get to a first hobby session this month without an adult driving the search — because the free and low-cost options are scattered across Community Clubs, ActiveSG, new third spaces and group chats that no directory indexes together, and nobody at home has the hours to go looking.**

**North star, for slide 9 and not for slide 2:** *the same teenager, twelve months later, still going.*

*Closed as [`discrepancies.md`](../4-decisions/discrepancies.md) **D3**, 31 Aug. This wording supersedes the Curiosity-Credits-led version.*

#### Why this is narrow without being small

Two things were being conflated, and separating them is what let the statement get sharper *and* wider at the same time:

| | Question | Where it is graded | Our answer |
|---|---|---|---|
| **Outcome** | What does the prototype have to close? | **Effectiveness** — top band is *"fully addresses and **resolves**"* | **One first attended session.** Bounded, demonstrable, closable in five minutes of video |
| **Audience** | Who has this problem? | **Benefits** — top band is *"scalable or easily adopted"* | **Every secondary student on limited discretionary money.** Not a niche |

The earlier draft led with S$500 of Curiosity Credits, which quietly made Self-Help Group members the whole audience. They are the **wedge**, not the market — a real, funded, nationally-announced cohort to start with, and the reason the problem is provably recognised. That is what §2.3 already said; the statement now agrees with it.

**Leading with S$0 is the stronger claim, not the humbler one.** S$0 is a *harder* constraint than S$500 — a system that solves it solves the funded case trivially — and it is already a tested invariant (**A3**), not a marketing line. Curiosity Credits move to slides 7 and 9, where a funded, government-announced cohort is an adoption argument rather than a ceiling.

The narrow *outcome* is what the Effectiveness rubric rewards. The deck's "Boiling Ocean" failure mode says *"cut one slice we can finish and demonstrate"*, and "teens need hobbies that stick" scores 1 no matter how good the build is. The twelve-month version is an asset on the roadmap slide and a liability on the problem slide.

### 1.2 Pressure test

The deck requires this, as a team, before writing code. Ours, honestly scored:

| # | Question | Verdict |
|---|---|---|
| 1 | **Can we name one person?** | ✅ Aisyah, 14 (§2.1) — S$0 of their own, nobody at home free to drive them, no friend already doing the thing. Not "youths." |
| 2 | **Can we cite the evidence?** | ✅ Now. Figure, source and date for every claim in §1.3 — after one of them failed verification. |
| 3 | **Would that person recognise themselves?** | ❌ **No. We have not spoken to a single teenager.** See below. |
| 4 | **Does it survive a different solution?** | ✅ The statement describes fragmentation and adult time-poverty. It holds if someone builds a directory, a WhatsApp bot, or nothing at all. |
| — | **Would this problem exist if agentic AI had never been invented?** | ✅ Yes. It is a matching and follow-through problem that predates all of it. |

**Question 3 is a real failure and the deck is explicit that any "no" sends us back to Empathise before we write code.** This is the deck's sixth failure mode — *"The Comfortable Guess: written from the team's imagination, with no contact with anyone who lives the problem"* — and right now we are in it. The whole brief is desk research.

**The fix is cheap and it is the highest-value hour available to us: talk to five teenagers this week.** Ask what they tried, what they quit, and what stopped them walking in. Two things follow:

- It converts our best original insight — *"a teen wants a scene, not a class"* (§5.3) — from an assertion into primary research. *(Our impression from the winners reviewed in §10 is that small-n user research shows up often; that is our reading of a sample, not a measured pattern.)*
- It gives the pitch a line no other team will have: *"we spoke to five 14-year-olds, and four of them said the same thing."*

Until then, every claim about what teenagers feel is labelled as inference, not finding.

### 1.3 The evidence

All figures verified against primary documents on 27 Aug 2026. Full provenance in [`sources.md`](./sources.md).

| Figure | Source |
|---|---|
| **"Pursue interests/hobbies" is the #3 aspiration** among Singapore's youth — and a **brand-new category** in the 2025 survey wave | National Youth Survey 2025, reproduced in the official **SG Youth Plan Report**, p.14 🟢 |
| **8% of youths report having no close friends**; average close friends fell from 7.68 (2013) to 6.04 (2024) | SG Youth Plan Report, p.53 🟢 |
| **About 3 in 5** youths say dedicated youth spaces would encourage them to meet people from different backgrounds | SG Youth Plan Report, p.56 🟢 |
| **S$500 Curiosity Credits**, ages 13–17, via the Self-Help Groups — arts, sports, technology, culinary, sustainability | SG Youth Plan Report, Move 15, p.69 🟢 |
| **20,000 social, hobby and interest-based opportunities annually by 2030** | SG Youth Plan Report, p.9 🟢 |
| **12 new third spaces**, free for youths to use | SG Youth Plan Report, Move 12 🟢 |
| **Somerset Belt youth precinct by 2028** | SG Youth Plan Report, Move 11, p.58 🟢 |
| **Discover** named as the sign-up channel | SG Youth Plan Report, Enablers 🟢 |

> ### ⚠️ One figure was removed
>
> v1 led with *"only 42% of youths are satisfied with the opportunities available to pursue a hobby (NCSS Quality of Life Survey 2025)."* **It does not check out.**
>
> NCSS does not appear anywhere in the SG Youth Plan Report's own bibliography. No NCSS publication measuring youth hobby-opportunity satisfaction could be located. The only 42% in the primary report is *"recover well from stressful events (42%)"* — a resilience statistic on a different page about a different thing. The claim traces word-for-word to a single Mothership sentence that the primary record does not support.
>
> **It was one of our two headline numbers.** Had it gone on slide 2 and a judge checked it, it would have taken the rest of the evidence down with it. This is precisely what the deck's *"a figure, a source, and a date"* rule exists to catch, and the general lesson is in [`sources.md`](./sources.md) §0: an AI summary of a source is a lead, not a citation.

**Note on the surviving headline.** "Hobbies are the #3 aspiration" is *stronger* than the number we lost — it is the government's own survey, it is new in the 2025 wave, and it says the want is real and rising. We now lead with a verified figure instead of a broken one.

### 1.4 The gap

Money is arriving. Supply is arriving. **The matching layer is not.**

This is not information scarcity. It is a **conversion** problem. A teenager who wants a hobby has to independently:

1. work out what they might like, with no reliable way to know before trying;
2. discover that an option exists at all, across a landscape split between commercial directories, Community Clubs, ActiveSG, NYC platforms, and a Telegram/Instagram long tail;
3. check it against their budget, their timetable and their travel radius;
4. actually show up, alone, repeatedly, until it becomes a habit — or quietly stop, with the money and the intent gone.

Every existing product solves step 2, for a *parent buying a class for a child*. Nothing solves the sequence, for a teenager, over time.

### 1.5 The "transformation" dimension

The hackathon theme is *"Design for a World in Transformation"* and asks for a solution that **plans, acts, and adapts over time**. Two layers, and we lead with the second:

- **Societal** — Singapore is deliberately restructuring how young people spend time outside school: a five-year roadmap, 20+ initiatives, now in motion.
- **Individual (the strong version)** — a teenager's interests, schedule, friend group and confidence change month to month. Any plan made in January is wrong by March. **A static recommendation decays; only a system that re-plans survives contact with a real 14-year-old.**

### 1.6 What we are explicitly *not* claiming

We are **not** framing this as "teens are on screens too much." That premise moralises, is hard to evidence, positions our users as the problem, and every judge has heard it. The evidenced problem is an **aspiration-to-access gap** plus a **belonging gap**. Less screen time may be an outcome; it is not our thesis.

---

## 2. Who This Is For

### 2.1 Primary persona

**Aisyah, 14.** *(Name is a placeholder — swap it if someone has a better one, but use the same one everywhere: slide 2, the video, the simulation harness and the evaluation profiles. A judge should meet the same person three times.)*

Secondary 2. Has **S$0** of their own discretionary money. Nobody at home is free to drive them anywhere. Lives in an SHG family, and has just been told about S$500 of Curiosity Credits — the occasion that makes the problem urgent, not the thing that defines them. Does not know that free CC courses exist. Has no friend already doing the thing. Has walked into a room full of strangers exactly zero times by choice.

**Everyone else is a strictly easier instance of the same system** — including a teen with the full S$500 and a supportive, well-resourced parent. This is curb-cut design: build for the constrained case, serve all 13–17-year-olds. It is also why `S$0` is a first-class input rather than an edge case (§4).

### 2.2 Secondary user

A **trusted adult** — parent, SHG case worker, school counsellor — holding approval authority over spend and over any unvetted provider. This is a safety requirement and a legal one, not a nice-to-have (§6.3, [`architecture.md`](../3-system/architecture.md) §7).

### 2.3 Framing note

The Curiosity Credits are our **evidence that the problem is real and nationally recognised**, not our total addressable market. Lead with the scheme, scope to all teens. Note the scheme's own rules are *not yet finalised* — the report says *"more details will be shared when ready"* — so describe it as the occasion, never as a spec we depend on.

---

## 3. Solution Overview

*The full system spec is [`architecture.md`](../3-system/architecture.md). This section is the argument; that document is the contract.*

### 3.1 The core reframe

Do **not** build: *assess personality → retrieve matching classes → present list.*
That is a recommender with a RAG backend. It runs once and stops.

Do build: **an agent that manages a finite exploration budget as a portfolio of experiments.**

The unit of work is not a recommendation. It is a **trial loop**.

### 3.2 There is theory under this, and it is worth citing

The refusal to run an assessment is not squeamishness. It is the finding.

**Hidi & Renninger's four-phase model of interest development** (*Educational Psychologist*, 2006; updated by the same authors in *Learning and Individual Differences*, 2025) describes interest as a developmental trajectory, not a trait: *triggered situational interest → maintained situational interest → emerging individual interest → well-developed individual interest*. Interest is produced by repeated triggers and support, and it can be *"supported to develop"* in anyone.

**So an assessment is measuring the wrong object.** You cannot diagnose a phase-4 interest in someone who has not yet had a phase-1 trigger. The only way to move a teenager along that trajectory is to arrange triggers and see which ones survive contact — which is precisely a portfolio of cheap experiments under a budget.

*"Interest gets developed, not diagnosed"* was an assertion in v1. It is now a citation.

### 3.3 The three loops

v1 drew one six-step ring. The system has **three distinct bounded loops** — which is both truer and better for the deck, because bounded control flow is exactly what the deck's "Bound every loop" slide primed judges to look for.

| # | Loop | What it does | Cap |
|---|---|---|---|
| **1 · Plan-quality** | Planner ⇄ Discovery Engine | When the plan is thin, go and find supply that isn't indexed yet | 2 rounds |
| **2 · Safety** | Guardian → Planner | Reject unsafe or unapproved plans; replan with the reason | 2 rejections |
| **3 · Feedback** | Observer → Personal Data → Planner | Learn from what actually happened and reallocate | Longitudinal; bounded by `tries` |

Loop 3 is the one that makes this longitudinal instead of stateless. It is also invisible in a five-minute demo, which is why the simulation harness exists ([`architecture.md`](../3-system/architecture.md) §10).

`DECLARE` is not an agent — it is parent setup plus the teen's request.

### 3.4 The agents

Five pipeline agents, one scheduled agent, and a detached validation layer. **Full contracts, caps, failure behaviour and agent-class mapping in [`architecture.md`](../3-system/architecture.md) §3.** In brief:

| Agent | Job | Why nothing else can do it |
|---|---|---|
| **Planner** | Builds the plan under money/time/tries constraints. Read-only on both stores. | The only component that reasons about *sequence* |
| **Discovery Engine** | Searches external sources when the plan is thin; the only writer on the plan path | The only component that can grow the supply side |
| **Guardian** | Per-listing provider vetting **and** per-plan spend approval | The only component that can say no |
| **Broker** | Books, confirms, and produces the reassurance artefact for parent and teen | The only component that touches the real world |
| **Observer** | Ingests attendance first, debrief second. Updates from **revealed** preference | The only component that learns |
| **Compliance** | Scheduled freshness scans; retires dead listings | The only component that runs when nobody asked |
| **Orchestrator** *(validation layer)* | Validates every payload at every gate | Sees everything; belongs to no path |

> Multi-agent with named, distinct roles is near-universal among hackathon winners — but only counts if each agent does something the others can't. The right-hand column is the test, and it is worth reading down it sceptically.

**v1's *Reallocator* is retired**: reallocation is a Planner responsibility over the ledger, not a separate agent. **Discovery and Compliance are new** since v1 and are two of the strongest components in the system — see §5 and §6.4.

### 3.5 Why this must be an agent

The deck grades this separately from the problem statement, under **Solution Overview**: *"explains what a fixed workflow would miss."*

- The budget is **finite and non-renewable**, and spend is **irreversible**.
- The decision is **sequential** — each trial changes what should be tried next.
- It is a genuine **explore/exploit problem under constraint**, not a lookup.
- The supply side is **incomplete at query time**, so the system sometimes has to go and find options that do not exist in any index yet.
- The value is created **between sessions**, over months, not in a single query.

**What a fixed workflow misses, in one line:** a filter-and-rank pipeline returns the same answer to the same inputs forever. It cannot spend a budget down, cannot notice that nobody showed up, and cannot decide that this week the right move is to do nothing.

### 3.6 Why it is adaptive

The user model is built from **outcomes, not from an assessment**. It changes every time the teen does or doesn't show up. There is no fixed profile to decay.

**The rule, and it is the most important behaviour in the product:**

- One no-show → note it, change nothing.
- **Two no-shows → re-plan, not a nag.** Something is wrong: wrong time, wrong travel, wrong intimidation level.
- Sustained attendance → escalate from **try** to **commit**, reallocate budget toward it.
- Some weeks the correct output is **hold**: no booking, no message. An agent that only ever escalates is not adapting, it is nagging.

### 3.7 Two objectives, not one

Optimise for **interest fit** *and* **belonging**. Prefer options where joining alone is normal, or where other teens from the same area already turn up.

The evidence is unusually good here:

- **8% of youths report no close friends**, and average close friends fell from 7.68 to 6.04 over eleven years (SG Youth Plan Report, p.53).
- **Peer support correlates with adolescent physical activity at r = 0.256** across 56 studies and 47,196 participants (Lin et al., 2024, meta-analysis).
- **Social pressures and lack of enjoyment are among the top drivers of youth sport dropout** — and interpersonal constraints are reported more often than structural ones (Crane & Temple, 2015, systematic review of 43 studies).
- Building friendships outside school is a stated aim of the Curiosity Credits scheme itself.

A hobby found alone is much less likely to stick, and the literature says the mechanism is social, not logistical.

> ✅ **Built as of 31 Aug — as cohort presence, not a friend graph** ([`discrepancies.md`](../4-decisions/discrepancies.md) **D2**; spec in [`architecture.md`](../3-system/architecture.md) §9.3).
>
> A friend system was the obvious implementation and the wrong one. It **reproduces the school social graph** — precisely what we are trying to get a teen out of — and it is empty on day one, so it would be dead exactly when the demo runs. `PeerCohort` carries **aggregate presence with no identity in it**: bucketed (`none/few/some/many`), suppressed below a k-anonymity floor of 5, resolved at planning-area level and **never at school level**, opt-in to contribute, used as a ranking tiebreak and never as a filter.
>
> **Absence is never shown.** *"Nobody is going"* is a discouraging screen that burns a `try`.
>
> The line for the slide: **3 in 5 youths say youth spaces would help them meet people from different backgrounds** (§1.3). A friend graph delivers the opposite of that; cohort presence delivers it. The privacy-preserving design is also the more effective one.

### 3.8 How long "sticks" actually takes

Worth knowing before we promise anything. **Lally et al. (2010)** measured habit automaticity in the field: reaching 95% of an individual's automaticity plateau took **18 to 254 days**, with wide individual variation. The popular "66 days" figure is a median from that same study, not a law.

Two consequences. First, our twelve-month horizon is the right order of magnitude and we can now say so with a citation. Second, **we should not claim a hobby is "formed" inside a demo**, or inside a term. What we can claim is the leading indicator: did they go back?

---

## 4. The Three Currencies

The budget is a **declared input**, never an assumption. It can be zero.

| Currency | Range | Notes |
|---|---|---|
| **Money** | S$0 → S$500 → parental allowance | Do not assume a lump sum exists. ST/Milieu 2024 puts children's pocket money at ~S$4–14/day, but that is food and transport money, and about **1 in 3 parents** say the child should use their own savings. *(See [`sources.md`](./sources.md) §D — the $4–14 range is for children generally, not secondary students. Soften the wording or drop the number.)* |
| **Time** | hours/week | Usually the **binding** constraint. School + compulsory CCA + tuition + travel. |
| **Tries** | count of "first sessions" | The scarcest resource. How many times will a teen walk into a room alone before giving up? **Nobody models this. We should.** |

**Hard requirement: the agent must produce a viable plan at S$0.** If it can't, we have built something exclusive and the whole broadening argument collapses. This is tested as an invariant, not a hope — [`evaluation.md`](../3-system/evaluation.md) A3.

> ✅ **The ledger has an owner as of 31 Aug ([`discrepancies.md`](../4-decisions/discrepancies.md) **D1**).** `BudgetLedger` sits in typed state ([`architecture.md`](../3-system/architecture.md) §5): Planner reads it, Broker decrements it, Observer reconciles it after each outcome. This is what separates the system we pitch from a recommender with filters — money, time and tries are spent down and reallocated, not matched against once.

---

## 5. Knowledge Base — What to Actually Index

### 5.1 Do NOT rebuild what exists

The formal, centre-based market is saturated. Scraping it produces Skoop-with-an-LLM.

| Existing | Coverage |
|---|---|
| **Skoop** | ~1,500–1,600 enrichment centres, filterable to postal code, **already has** an "answer a few questions → best-fit centre" recommender |
| **Serious About School** | 8,000+ listings with parent reviews (children 0–12) |
| **Flying Cape** | Booking platform, 18 months to 18 years |
| **LessonPlan, BYKidO, POSB Education Marketplace** | Aggregation + booking |
| **Discover (NYC/GovTech)** | Career portal, ages 15–35, static personalisation quiz. **Named as the sign-up channel for the 20,000 opportunities.** |

### 5.2 DO index the uncovered supply — where the free and cheap options live

This is the **Discovery Engine**'s entire justification ([`architecture.md`](../3-system/architecture.md) §3.2), and it is measured: **long-tail coverage**, the share of our recommendations absent from the incumbent directories ([`evaluation.md`](../3-system/evaluation.md) B9).

- **PA Community Clubs** — CC Courses across Education & Enrichment, Health & Wellness, Lifelong Learning, Lifestyle & Leisure, Sports & Fitness
- **PA Youth Movement** — 95 Youth Networks based at CCs
- **ActiveSG** — Academies, Clubs, and interest groups via MyActiveSG+
- **The 12 new third spaces** — free access; youths can run their own programmes there
- **Informal / community-shaped activity** — pickup sports, meetup groups, run clubs, jam sessions
- **Telegram / Instagram private coach long tail** — with mandatory vetting (§6.3)
- **One-off tasters and workshops** — the cheapest possible experiment, and critical to the explore phase

### 5.3 The conceptual point worth building around

For a 13–17-year-old, the thing they want is usually **not a class — it's a scene**. A group of people who do the thing. "Class" is the *parent's* mental model of enrichment; "community" is the *teen's*. Indexing community-shaped supply is both more accurate to our user and far less competed.

> This is our sharpest original observation and it is currently **unsourced** — our inference, not a finding. It is also exactly what five teen interviews would confirm or kill in an afternoon (§1.2). Label it as a hypothesis until then.

### 5.4 The supply that dies quietly

The differentiating supply — Telegram groups, Instagram coaches, informal run clubs — is precisely the supply that goes stale without announcing it. **A dead link is worse than no result**: it sends a shy 14-year-old to an empty room, and that is the single failure most likely to end the habit and burn a `try` that cannot be recovered.

This is why the **Compliance Agent** exists, and it should be pitched that way — as what makes long-tail indexing responsible rather than reckless, not as a maintenance chore.

---

## 6. Hard Constraints — Non-Negotiable

### 6.1 ❌ No left-brain / right-brain assessment

A debunked neuromyth — the **second most pervasive in education** (Shin, Lee & Bong, *Theory Into Practice*, 2022). Hemispheres show dominance for certain functions, but individuals cannot be categorised as left- or right-brained. **Nielsen et al. (2013)**, imaging 1,011 people aged 7–29 across 7,266 brain regions, found lateralisation to be *"a local rather than global property"* — nobody has an overall dominant hemisphere.

It clusters with "we only use 10% of our brains" in neuromyth surveys: **64% of the general public, 49% of educators and 32% of a high-neuroscience-exposure group** endorsed the left/right-brained learner item (Macdonald et al., 2017).

Any judge with a psychology or education background will spot it, and because it would be the *foundation* of the agent's reasoning, the whole system falls with it.

**Also excluded:** learning styles (VAK), and MBTI-style typing for minors.

**Bonus:** a fixed personality type is a *static* label. It would actively break the adaptivity argument in §3.6. Removing it is the fix, not a loss — and §3.2 gives us something better to put in its place.

#### Where the line actually falls: seeding is allowed, typing is not

A teen with zero history has to start somewhere, so Hobbi does ask a short question at signup. That is not a contradiction of the rule above, but the docs have to say why, or a careful reader will find one.

| | **Typing** — forbidden | **Seeding** — permitted |
|---|---|---|
| Claims | who you *are* | where to *start* |
| Lifespan | stable, permanent | discarded as soon as behaviour arrives |
| Shown back to you | yes — a label, a type, a result | never |
| Used to | explain and predict you | order the first one or two experiments |

The permitted version is 4–6 vibe chips ("sporty", "artistic", "chill", "explorative"), multi-select, bound by five rules ([`architecture.md`](../3-system/architecture.md) §3.1, decision **D10**):

1. **Skippable** — *"Surprise me"* produces a real plan. An unskippable screen is a gate, and a gate is a quiz.
2. **No result screen** — the chips never produce a label. *"You're an Explorer!"* is typing.
3. **Lowest confidence, and it decays** — the first attended session outranks the entire cold-start screen.
4. **Biases, never excludes** — seeds order the first experiments; they never filter the candidate set. Tested as invariant **A9**.
5. **Asks where to start, not what you are like** — the wording is the whole distinction.

Under Hidi & Renninger (§3.2) this is the only defensible design anyway: you cannot measure an interest in someone who has not yet had a trigger, so the cold start's job is to *produce* a trigger, not to diagnose one.

### 6.2 ❌ No height / weight / body-composition inputs

Three independent reasons:

1. **Unreliable.** Adolescent talent identification is dominated by **maturation timing**, not ability. Selection in youth sport *"follows a maturity-related gradient largely during the interval of puberty and the growth spurt"* (Malina et al., 2015, *BJSM*) — which is why bio-banding exists at all (Cumming et al., 2017). Rankings reverse: the "underdog hypothesis" holds that later-maturing players develop superior technical and psychological skills to survive selection, advantages that *"become more salient in late adolescence and early adulthood"* (Cumming et al., 2018). We would encode a bias against late-maturing kids.
2. **Harmful.** Weight stigma and weight-related commentary are robustly linked to disordered-eating cognitions and behaviours in the systematic-review literature (Levinson et al., 2024, *Body Image*), and adolescent weight-teasing predicts disordered eating up to 15 years later. *(Honest caveat: no study isolates "an app gives a teen their body-composition number" as the exposure. The mechanism is inferred by analogy from a strong adjacent literature — say it that way if pressed.)* Telling a 14-year-old they are the wrong shape for a sport is the exact opposite of "discover your passion, build confidence."
3. **Inequitable.** It lands hardest on our primary cohort.

**Use instead:** preference axes — indoor/outdoor, team/solo, contact/non-contact, high/low intensity, competitive/social. Legitimate, non-stigmatising, and carried with a confidence that is **seeded low and grows from attendance**. A chip tapped at signup and a preference inferred from six attended sessions are not the same object, and the schema keeps them distinguishable (`provenance` on `Axis`).

### 6.3 ⚠️ Child safety — unvetted providers

We are connecting **minors** to activity providers. The Telegram/IG long tail is genuinely differentiating and genuinely risky.

**Rule: an unverified private provider is never surfaced directly to the youth.** It enters a vetting queue for a trusted adult and becomes bookable only after approval. Enforced at the Guardian gate, tested as invariant A1, and reported as an absolute count — *"0 of N reached a teen"* — because a 99% containment rate is a failure, not a score.

**Make this a visible feature, not a hidden limitation.** It maps directly onto the IMDA framework (§8.1).

### 6.4 ⚠️ Data protection is a design constraint, not a slide

Our users are 13–17 and one input channel is a **voice recording**. The position is set out in [`architecture.md`](../3-system/architecture.md) §8, against PDPC's *Advisory Guidelines on the PDPA for Children's Personal Data* (28 Mar 2024). The headline, which is more interesting than "get parental consent":

- **A 13–17-year-old may give valid consent themselves** — provided the policies are *"readily understandable by them"*, including how to withdraw it. Our consent copy is therefore a deliverable, written for a 13-year-old.
- **Under 13 requires parental consent**, which is why the product starts at 13 and refuses a declared age below it (**D7**, invariant **A11**). The ceiling is 17 — there is no adult mode, so the Guardian gate has no bypass.
- Children's data is *"generally considered to be **sensitive personal data**"* and gets the enhanced protection tier. Voice recordings sit squarely there — so: transcribe, extract, **discard the audio**.

Also address on slides: platform ToS for scraping.

---

## 7. Anticipated Objections — Have Answers Ready

The Presentation rubric's 1-point band is *"partially explained, with **some prompting or clarification needed**."* Answers that land before the judge has to ask are worth a full point. This section is how we get it.

### 7.1 "Don't they already have CCAs?"

**Every Singaporean judge will think this.** Now sourced to MOE directly rather than to Wikipedia, and the MOE detail makes the answer *stronger* than v1's:

> *"A CCA is **compulsory for all secondary school students**. Secondary school students may pursue their interests and participate in external activities, but **not in-lieu of a school-based CCA**."* — MOE

> Under **LEAPS 2.0**, participation in one school-based CCA is graded **Excellent / Good / Fair**, and *"the level of attainment will be converted to a bonus point(s) which can be used for admission to Junior Colleges/Polytechnics/Institutes of Technical Education."* — MOE

**The answer.** The CCA is Singapore's default hobby-allocation mechanism, and it is:

- **school-bound** — MOE's own wording forbids substituting an outside activity, so it structurally cannot deliver "friendships outside school," which is an explicit stated aim of the Curiosity Credits scheme;
- **graded, and convertible into admissions bonus points** — which makes it an *achievement instrument*. A thing you are scored on is not the same object as a thing you do because you like it, and this is the sharpest version of the argument;
- **capped** at whatever one school happens to offer;
- **terminal** — it ends at graduation.

We handle the outside-school half the CCA system cannot, by design rather than by omission.

*(v1 also claimed CCAs are "frequently assigned rather than freely chosen." That remains unsourced — drop it. The graded-and-bonus-pointed argument above is better evidenced and lands harder.)*

### 7.2 "Won't NYC just build this into Discover?"

Real risk — Discover is the named sign-up channel in the government's own plan. Two honest counters:

- Discover today is **career-framed, starts at 15, and personalises via a static quiz**. Our cohort — 13–17, hobbies, adaptive — falls in the gap.
- Our defensibility is **the budget-optimisation loop and the long-tail supply**, not the directory. If someone builds the directory better, we sit on top of it.

Say this out loud in the pitch. Pre-empting it reads as confidence.

### 7.3 "Isn't this just a recommender?"

Answer with the constraint: a recommender optimises *"find a class."* We optimise *"spend a fixed, non-renewable exploration budget to maximise the probability of long-term adherence."* That is a sequential decision problem, and it is why it must be an agent.

**Then show, don't argue:** the counterfactual panel ([`evaluation.md`](../3-system/evaluation.md) §5) runs a static recommender alongside the agent on the same data. Adaptation is only legible against a baseline.

### 7.4 "How do you know any of this is true — have you talked to a teenager?"

**Right now the honest answer is no** (§1.2). Fix it before demo day, then answer with a number.

---

## 8. Positioning Levers

### 8.1 The IMDA framework

**Model AI Governance Framework for Agentic AI** — v1.0 announced 22 Jan 2026 at WEF Davos, **v1.5 published 20 May 2026** (updated 5 Jun 2026). The world's first agentic-AI-specific governance framework, from Singapore.

*Get the version and the status right:* it is a **voluntary Model Framework** and a "living document", not legislation. Say "aligned with", never "compliant with". A Singaporean judge will know the difference, and v1 got both the version story and the "effective date" framing wrong.

Its four dimensions and our mapping are in [`architecture.md`](../3-system/architecture.md) §7. The reason it is nearly free marks: the framework's own risk-factor table reads like a description of our system — **persistent memory**, **write access**, **irreversible actions**, **autonomy level** — and it names *"making payments"* and *"sending communications"* explicitly among the actions that require a human approval checkpoint. Our Broker does both, on behalf of a minor.

One slide. It will land hard with a Singaporean panel.

### 8.2 Timeliness

The SG Youth Plan launched **25 July 2026** — five weeks ago. Judges reward projects anchored to live policy, and this one is live enough that the scheme's own rules are still being written.

---

## 9. Demo Strategy — The Hard Part

The value accrues over months; the demo is five minutes, and the deck allocates two of them to the demo itself. Three tactics, all now build items in [`architecture.md`](../3-system/architecture.md) §10 rather than aspirations:

1. **Build a time machine.** A simulation harness replaying a synthetic 9–12 month history, showing the plan and the budget mutating at each decision point. Adaptation has to be seen as a *sequence*.
2. **Show the diff, not the output.** A "what changed and why" panel: old plan → trigger signal → reasoning → new plan. Reasoning traces were the explicitly stated differentiator for multiple 2025–26 hackathon winners.
3. **Log the counterfactual.** Show what a static recommender would have suggested alongside what the agent did.

**Include at least one moment where the agent correctly decides to do nothing this week.** It is the strongest single signal of genuine adaptivity, and no ranked-list product can produce it. It is a first-class terminal outcome (`hold_this_week`) and a reported metric ([`evaluation.md`](../3-system/evaluation.md) B12), not a demo trick.

**Quantify.** Winning projects lead with a measured figure. Ours are specified in [`evaluation.md`](../3-system/evaluation.md) §7 — and the two most valuable are zeros: *0 unverified providers reached a teen*, *0 constraint violations*. A zero with a denominator is a safety claim a judge can check.

---

## 10. What Wins Agentic Hackathons

*From 11 comparable hackathons reviewed — Google Cloud Agentic AI Day, Microsoft AI Agents, AWS AI Agent Global, IBM watsonx/Call for Code, MIT CSAIL, UC Berkeley, HackUSF, NUS–GURU, Elastic Singapore, Google Gen AI Exchange, and this one's own 2025 edition. Sources in [`sources.md`](./sources.md) §H.*

**Five archetypes recur:** Navigator (collapse a fragmented system), Sentinel (detect → act on live signals), Researcher, Guardian (verify/explain), Coach (persistent companion).

**The gap:** of ~40 winners reviewed, **fewer than five are genuinely longitudinal**. Almost all are stateless within a session. The Coach archetype is the rarest — and every clear example won:

- *Kovai Shines* (Google, farming) — persistent memory + continuous feedback loop
- *Team Jiaye* (NUS–GURU, joint champion, S$20k) — ADHD productivity coach using behavioural science + real-time feedback
- *Bit2Brain* (Microsoft, Java category) — evolving knowledge map

**Our shape — Navigator + Coach — does not appear in any winner found.**

**Avoid the Sentinel archetype.** Most-attempted, and reactive: it responds to events, but its policy never changes.

> Both the archetype taxonomy and the "fewer than five" count are **our analysis of a real sample**, not published statistics. Present them as *"we reviewed 11 hackathons and ~40 winning projects and found…"* — which is honest, and actually more impressive than citing someone else.

---

## 11. What We Actually Build

Full component-by-component scope in [`architecture.md`](../3-system/architecture.md) §10. The one-line version, and it needs to be said on a slide:

**In the prototype:** all six agents (five on the request path, plus Compliance on a schedule) and the validation layer, real bounded loops, a seeded CKB of real Singapore listings including a quarantined unverified set, live web search over a whitelisted domain set, **sandboxed** booking, a manually-triggered freshness scan, and a simulation harness driving a 9–12 month replay.

**Deferred:** live provider integrations, a deployed scheduler, real check-in channels, real users over real months.

Two reasons to be explicit rather than vague. Technical Quality's top band is *"minimal work needed for production"*, which is only assessable against a stated scope. And the deck's first execution criterion is *"whether the solution can run as demonstrated in video"* — so anything shown must be reproducible from the repo. Being caught implying a live booking costs more than the honesty does.

---

## 12. Decisions

**All twelve closed on 31 Aug.** [`discrepancies.md`](../4-decisions/discrepancies.md) §D is the register of record, with the reasoning behind each.

| | Decision |
|---|---|
| **D1** | The budget ledger is in typed state — Planner reads, Broker decrements, Observer reconciles (§4) |
| **D2** | Belonging is **cohort presence, not a friend graph**: bucketed, k-anonymised, planning-area level, tiebreak only (§3.7) |
| **D3** | The statement is **narrow on outcome, broad on audience**, leading with S$0 (§1.1) |
| **D3b** | The headline metric is **B15** — actions to a first attended session at S$0 |
| **D4** | Prepare a Q&A, at second priority behind the idea and the deck |
| **D5** | Organiser questions handled directly by the team |
| **D6** | System prompts re-derived after this branch merges to main |
| **D7** | The cohort is **13–17 at both ends, enforced**; a trusted adult is mandatory for every user (§2, §6.4) |
| **D8** | Seed CKB from real listings · live whitelisted Discovery · sandboxed Broker · a cached replay for the demo |
| **D9** | The observation channel is an **in-app form** behind a channel-agnostic `DebriefSubmission` — reads like texting a friend, keeps a minor's voice note off third-party servers *(revised from Telegram, 31 Aug)* |
| **D10** | Cold start is 4–6 skippable vibe chips — **seeding, not typing** (§6.1) |
| **D11** | Dislike is modelled, with decay and attribution, **never as a blocklist** |

What is left is not a decision. It is the build, the deck, the video — and one task below.

**The one that is not a decision but a task: talk to five teenagers (§1.2).** It closes the only pressure-test question we currently fail.

---

## Appendix — Figures Cleared for Slides

Every row verified against a primary source on 27 Aug 2026. 🟢 primary · 🟡 credible secondary · ⛔ do not use.

| Figure | Source | |
|---|---|---|
| "Pursue interests/hobbies" = **#3 youth aspiration**, new category in 2025 | National Youth Survey 2025 via SG Youth Plan Report, p.14 | 🟢 |
| **8%** of youths have no close friends; average fell 7.68 → 6.04 (2013→2024) | SG Youth Plan Report, p.53 | 🟢 |
| **3 in 5** say youth spaces would help them meet people from different backgrounds | SG Youth Plan Report, p.56 | 🟢 |
| **S$500** Curiosity Credits, ages 13–17, via Self-Help Groups | SG Youth Plan Report, Move 15, p.69 | 🟢 |
| **20,000** social/hobby/interest opportunities annually by 2030 | SG Youth Plan Report, p.9 | 🟢 |
| **12** new third spaces, free to use | SG Youth Plan Report, Move 12 | 🟢 |
| Somerset Belt precinct by **2028** | SG Youth Plan Report, Move 11, p.58 | 🟢 |
| CCA **compulsory** in secondary school; not substitutable by outside activities | MOE, CCA Overview | 🟢 |
| LEAPS 2.0 grades CCA **Excellent/Good/Fair** → admissions **bonus points** | MOE, LEAPS 2.0 brochure | 🟢 |
| Left/right-brain = **2nd most pervasive** education neuromyth | Shin, Lee & Bong, *Theory Into Practice* 61(3), 2022 | 🟢 |
| **64% / 49% / 32%** endorse the left-brain myth (public / educators / neuroscience-trained) | Macdonald et al., *Frontiers in Psychology* 8:1314, 2017 | 🟢 |
| Hemispheric lateralisation is *"local rather than global"* — n=1,011 | Nielsen et al., *PLoS ONE* 8(8):e71275, 2013 | 🟢 |
| Habit automaticity takes **18–254 days** | Lally et al., *EJSP* 40(6), 2010 | 🟢 |
| Peer support ↔ adolescent physical activity, **r = 0.256**, n = 47,196 | Lin et al., meta-analysis, 2024 | 🟢 |
| Interest develops in **four phases**; it is not a fixed trait | Hidi & Renninger, *Educational Psychologist* 41(2), 2006 | 🟢 |
| Youth talent ID confounded by **maturation timing** | Malina et al., *BJSM* 49(13), 2015 | 🟢 |
| World's first agentic-AI governance framework, **v1.0 Jan 2026 / v1.5 May 2026**, voluntary | IMDA | 🟢 |
| 13–17-year-olds **may self-consent** if policies are readily understandable | PDPC Advisory Guidelines, 28 Mar 2024 | 🟢 |
| 95 PA Youth Networks at Community Clubs | People's Association | 🟢 |
| Skoop: ~1,500–1,600 enrichment centres | Skoop (self-reported) | 🟡 |
| Secondary students receive ~S$4–14/day pocket money | ST / Milieu Insight, 2024 — **range is for children generally; soften or drop** | 🟡 |
| ~1 in 3 parents say "use your own savings" | ST / Milieu Insight, 2024 | 🟡 |
| "100+ ActiveSG interest groups" | Listicle only — verify in MyActiveSG+ before quoting | 🔴 |
| **"Only 42% of youths satisfied with opportunities" (NCSS QoL 2025)** | **Unverifiable. Not in NCSS material or the SG Youth Plan bibliography.** | ⛔ |
| "70% of kids quit sport by 13" | Widely circulated, contested and unattributed | ⛔ |
| "96% of children receive regular pocket money" | Prudential 2017 — nine years old | ⛔ |
