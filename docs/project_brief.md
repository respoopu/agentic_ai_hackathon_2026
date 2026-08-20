# Project Brief — Hobbi 

*Hackathon: "Design for a World in Transformation"*
*Version 1 · Synthesised from research conducted 18 Aug 2026*

---

## 1. Problem Statement

**Singaporean teenagers overwhelmingly want hobbies. Almost none of the system around them is designed to help them find one that sticks.**

The evidence is the government's own:

- Pursuing a hobby is the **third most common aspiration** among young people (National Youth Survey 2025).
- Only **42% of youths are satisfied** with the opportunities available to do so (NCSS Quality of Life Survey 2025).
- **8% of youths report having no close friends**; about **three in five** say dedicated youth spaces would encourage them to meet people from different backgrounds (MCCY/NYC engagements, 2026).

In July 2026 the government responded with the SG Youth Plan: **S$500 "Curiosity Credits"** for 13–17-year-olds in Self-Help Groups (Mendaki, SINDA, Eurasian Association, CDAC), **12 free "third spaces"** by end-2026, a **Somerset Belt youth precinct** by 2028, and **~20,000 hobby and interest opportunities per year by 2030**.

So money is arriving. Supply is arriving. **The matching layer is not.**

The gap is not information scarcity — it is a *conversion* problem. A teenager who wants a hobby has to independently:
1. figure out what they might like, with no reliable way to know before trying;
2. discover that an option exists, across a landscape split between commercial directories, Community Clubs, ActiveSG, NYC platforms, and a Telegram/Instagram long tail;
3. work out whether it fits their budget, schedule, and travel radius;
4. actually show up alone, repeatedly, until it becomes a habit — or quietly stop, with the money and the intent gone.

Every existing product solves step 2 for a *parent buying a class for a child*. Nothing solves the sequence, for a teenager, over time.

### The "change" dimension (hackathon criterion 3)

Two layers, and we should lead with the second:

- **Societal:** Singapore is deliberately restructuring how young people spend time outside school — a five-year, 20-initiative roadmap now in motion.
- **Individual (the strong version):** a teenager's interests, schedule, friend group and confidence change month to month. Any plan made in January is wrong by March. **A static recommendation decays; only a system that re-plans survives contact with a real 14-year-old.**

### What we are explicitly *not* claiming

We are **not** framing this as "teens are on screens too much." That premise is moralising, hard to evidence, positions our users as the problem, and every judge has heard it. The evidenced problem is an **aspiration-to-access gap** plus a **belonging gap**. Reduced screen time may be an outcome; it is not our thesis.

---

## 2. Who This Is For

**Primary persona (design for the hardest case):** a 14-year-old in an SHG family, with **S$0** of discretionary money, no parent free to drive them anywhere, no idea that free CC courses exist, and no friend already doing the thing.

**Everyone else is a strictly easier instance of the same system** — including a teen with the full S$500, or with a supportive, well-resourced parent. This is curb-cut design: build for the constrained case, serve all 13–17-year-olds.

**Secondary user:** a trusted adult — parent, SHG case worker, school counsellor — who holds approval authority over spend and over any unvetted provider. This is a safety requirement, not a nice-to-have (see §6).

**Framing note:** the Curiosity Credits are our **evidence that the problem is real and nationally recognised**, not our total addressable market. Lead with the scheme, scope to all teens.

---

## 3. Solution Overview

### The core reframe

Do **not** build: *assess personality → retrieve matching classes → present list.*
That is a recommender with a RAG backend. It runs once and stops. It fails criteria 1 and 2.

Do build: **an agent that manages a finite exploration budget as a portfolio of experiments over ~12 months.**

The unit of work is not a recommendation. It is a **trial loop**.

### The loop

```
DECLARE  →  PLAN  →  BROKER  →  OBSERVE  →  UPDATE  →  RE-PLAN
   ↑                                                      │
   └──────────────────────────────────────────────────────┘
```

1. **Declare** — user states what they have. Three currencies (§4).
2. **Plan** — sequence cheap experiments first. Tasters and one-off workshops before term-long commitments. Explore before exploit.
3. **Broker** — find the option, handle logistics: booking, reminders, travel time from home *or school*, whether a peer is going.
4. **Observe** — did they go? Did they go back? What did they say after? Signals are behavioural, not self-reported preference.
5. **Update** — revise the model of the user from *revealed* preference. No prediction, no typing.
6. **Re-plan** — reallocate remaining budget. Two no-shows triggers a **re-plan, not a nag**. Sustained repeat attendance triggers escalation from "try" to "commit."

### Why this must be an agent (criterion 1)

- The budget is **finite and non-renewable**. Spend is irreversible.
- The decision is **sequential** — each trial changes what should be tried next.
- It is a genuine **explore/exploit** problem under constraint, not a lookup.
- The value is created **between sessions**, over months, not in a single query.

### Why it is adaptive (criterion 2)

The user model is **built from outcomes, not from an assessment**. It changes every time the teen does or doesn't show up. There is no fixed profile to decay.

### Suggested agent decomposition

Cut the agents around the *loop*, not the funnel. Naming should describe distinct jobs, not decorate a linear pipeline.

| Agent | Job |
|---|---|
| **Orchestrator** | Holds goal state, budget ledger, decides when to re-plan |
| **Planner** | Sequences experiments under money/time/tries constraints |
| **Broker** | Searches supply KB, checks fit, handles booking + logistics |
| **Observer** | Ingests attendance, check-ins, drop-off signals; detects disengagement early |
| **Reallocator** | Revises remaining budget allocation after each outcome |
| *(optional)* **Guardian** | Vetting queue for unverified providers; routes to trusted adult |

Multi-agent with named, distinct roles is near-universal among hackathon winners — but only counts if each agent does something the others can't.

### Two objectives, not one

Optimise for **interest fit** *and* **belonging**. Prefer options where a peer from the same school or neighbourhood is also attending. The scheme's stated aim includes *building friendships outside school*, and 8% of youths report no close friends. A hobby found alone is much less likely to stick.

---

## 4. The Three Currencies

The budget is a **declared input**, never an assumption. It can be zero.

| Currency | Range | Notes |
|---|---|---|
| **Money** | S$0 → S$500 → parental allowance | ST/Milieu 2024: secondary students get ~S$4–14/day, but that's food and transport money. ~1 in 3 parents would tell the child to use their own savings. **Do not assume a lump sum exists.** |
| **Time** | hours/week | Usually the *binding* constraint. School + compulsory CCA + tuition + travel. |
| **Tries** | count of "first sessions" | The scarcest resource. How many times will a teen walk into a room alone before giving up? Nobody models this. We should. |

**Hard requirement: the agent must produce a viable plan at S$0.** If it can't, we've built something exclusive and the whole broadening argument collapses.

---

## 5. Knowledge Base — What to Actually Index

### Do NOT rebuild what exists

The formal, centre-based market is saturated. Scraping it produces Skoop-with-an-LLM.

| Existing | Coverage |
|---|---|
| **Skoop** | ~1,500–1,600 enrichment centres, filterable to postal code, *already has* a "answer a few questions → best-fit centre" recommender |
| **Serious About School** | 8,000+ listings with parent reviews |
| **Flying Cape** | Booking platform, 18 months to 18 years |
| **LessonPlan, BYKidO, POSB Education Marketplace** | Aggregation + booking |
| **Discover (NYC/GovTech)** | Career portal, ages 15–35, static personalisation quiz, 460 mentors, 46 events. **Named as the sign-up channel for the 20,000 opportunities.** |

### DO index the uncovered supply — this is where the free and cheap options live

- **PA Community Clubs** — CC Courses across Education & Enrichment, Health & Wellness, Lifelong Learning, Lifestyle & Leisure, Sports & Fitness
- **PA Youth Movement** — 95 Youth Networks based at CCs
- **ActiveSG** — Academies, Clubs, and 100+ interest groups via MyActiveSG+
- **The 12 new third spaces** — free access; youths can run their own programmes there
- **Informal / community-shaped activity** — pickup sports, meetup groups, run clubs, jam sessions
- **Telegram / Instagram private coach long tail** — with mandatory vetting (§6)
- **One-off tasters and workshops** — the cheapest possible experiment; critical to the explore phase

### Conceptual point worth building around

For a 13–17-year-old, the thing they want is usually **not a class — it's a scene**. A group of people who do the thing. "Class" is the *parent's* mental model of enrichment; "community" is the *teen's*. Indexing community-shaped supply is more accurate to our user and far less competed.

---

## 6. Hard Constraints — Non-Negotiable

### ❌ No left-brain / right-brain assessment

This is a debunked neuromyth — the **second most pervasive in education**, per a 2022 *Theory Into Practice* review. Hemispheres show dominance for certain functions, but individuals cannot be categorised as left- or right-brained. Rejected by the APA and Harvard. It clusters with "we only use 10% of our brains" in neuromyth surveys.

Any judge with a psychology or education background will spot it, and because it would be the *foundation* of the agent's reasoning, the whole system falls with it.

**Also excluded:** learning styles (VAK), MBTI-style typing for minors.

**Bonus:** a fixed personality type is a *static* label and would actively break criterion 2. Removing it is the fix, not a loss.

### ❌ No height / weight / body-composition inputs

Three independent reasons:

1. **Unreliable.** Adolescent anthropometric talent ID is dominated by maturation timing. Early developers look talented; late developers look unsuited; rankings often reverse by adulthood. We'd encode a bias against late-maturing kids.
2. **Harmful.** Body-composition feedback to 13–17-year-olds carries real body-image and disordered-eating risk. Telling a 14-year-old they're the wrong shape for a sport is the exact opposite of "discover your passion, build confidence."
3. **Inequitable.** It lands hardest on our primary cohort.

**Use instead:** preference signals — indoor/outdoor, team/solo, contact/non-contact, high/low intensity, competitive/social. Self-reported, legitimate, non-stigmatising.

### ⚠️ Child safety — unvetted providers

We are connecting **minors** to activity providers. The Telegram/IG long tail is genuinely differentiating and genuinely risky.

**Rule: an unverified private provider is never surfaced directly to the youth.** It goes into a vetting queue for a trusted adult (parent / SHG case worker / school counsellor) and only becomes bookable after approval.

Make this a **visible feature**, not a hidden limitation. It maps directly onto IMDA's framework (§8).

Also address in slides: platform ToS for scraping, and PDPA handling of minors' data.

---

## 7. Anticipated Objections — Have Answers Ready

### "Don't they already have CCAs?"

**Every Singaporean judge will think this.** CCAs are compulsory in all secondary schools — at least one core activity, graded under LEAPS.

**Answer:** The CCA is Singapore's default hobby-allocation mechanism, and it is:
- **school-bound** — so it structurally cannot deliver "friendships outside school," which is an explicit stated aim of the Curiosity Credits scheme;
- **frequently assigned rather than freely chosen**;
- **capped** at whatever one school happens to offer;
- **terminal** — it ends at graduation.

We handle the outside-school half the CCA system cannot.

### "Won't NYC just build this into Discover?"

Real risk — Discover is already the named sign-up channel. Two honest counters:

- Discover today is **career-framed, starts at 15, and personalises via a static quiz**. Our cohort (13–17, hobbies, adaptive) falls in the gap.
- Our defensibility is **the budget-optimisation loop and the long-tail supply**, not the directory. If someone builds the directory better, we sit on top of it.

Say this out loud in the pitch. Pre-empting it reads as confidence.

### "Isn't this just a recommender?"

Answer with the constraint: a recommender optimises "find a class." We optimise "spend a fixed, non-renewable exploration budget to maximise the probability of long-term adherence." That's a sequential decision problem, and it's why it must be an agent.

---

## 8. Positioning Levers

### IMDA Model AI Governance Framework for Agentic AI

Launched 22 Jan 2026 at Davos — **the world's first** agentic-AI-specific governance framework, from Singapore. Effective 20 May 2026. Emphasises:
- humans remain **ultimately accountable**;
- **approval checkpoints** for actions with material real-world impact;
- risk assessment on **autonomy, data access, and action reversibility**;
- design-level limits — **restricted tool access, sandboxing**.

One slide mapping our human-in-the-loop design (spend approval + provider vetting) to these dimensions is nearly free and will land hard with a Singaporean panel. Our users are minors and our actions spend real money — this is exactly the risk profile the framework anticipates.

### Timeliness

The SG Youth Plan launched 25 July 2026. This is three weeks old. Judges reward projects anchored to live policy.

---

## 9. Demo Strategy — The Hard Part

The value accrues over months; the demo is five minutes. Three tactics that work:

1. **Build a time machine.** A simulation harness replaying a synthetic 9–12 month user history, showing plan and budget allocation mutating at each decision point. Adaptation must be seen as a *sequence*.
2. **Show the diff, not the output.** A "what changed and why" panel: old plan → trigger signal → reasoning → new plan. Reasoning traces were the explicit stated differentiator for multiple 2025–26 hackathon winners.
3. **Log the counterfactual.** Show what a static recommender would have suggested alongside what the agent actually did. Adaptation is only legible against a baseline.

**Include at least one moment where the agent correctly decides to do nothing this week.** An agent that only ever escalates isn't adapting, it's nagging. This is the strongest single signal of genuine adaptivity.

**Quantify one number.** Winning projects consistently lead with a measured figure (70% prep time reduction; 90% accuracy; 100% form accuracy). Vague impact claims lose to a single measured claim. Even a simulated adherence-rate delta beats prose.

---

## 10. Competitive Context — What Wins Agentic Hackathons

From 11 comparable hackathons reviewed (Google Cloud Agentic AI Day, Microsoft AI Agents, AWS AI Agent Global, IBM watsonx/Call for Code, MIT CSAIL, UC Berkeley, HackUSF, NUS–GURU, SimplifyNext, Elastic Singapore, Google Gen AI Exchange):

**Five archetypes recur:** Navigator (collapse a fragmented system), Sentinel (detect→act on live signals), Researcher, Guardian (verify/explain), Coach (persistent companion).

**The gap:** of ~40 winners reviewed, **fewer than five are genuinely longitudinal**. Almost all are stateless within a session. The Coach archetype is rarest — and every clear example won:
- *Kovai Shines* (Google, farming) — persistent memory + continuous feedback loop
- *Team Jiaye* (NUS–GURU, joint champion, S$20k) — ADHD productivity coach using behavioural science + real-time feedback
- *Bit2Brain* (Microsoft, Java category) — evolving knowledge map

**Our shape — Navigator + Coach — does not appear in any winner found.**

**Avoid the Sentinel archetype.** Most-attempted, and it's reactive: it responds to events but its policy never changes.

**Local competition note:** the SimplifyNext Agentic AI Hackathon (NUS/NTU) asks students to tackle "mental health, student success, financial inclusion, sustainable cities" and its 2026 edition is running now. 2025 drew ~400 students / 100 teams. Expect crowding in adjacent lanes.

---

## 11. Open Decisions

- [ ] Where does the trusted adult sit in the flow — mandatory co-user, or approval-only?
- [ ] Do we build real integrations (ActiveSG, CC courses) or a curated seed KB + simulated booking?
- [ ] How do we detect "a peer is going" without creating a privacy problem? (School? Postal sector? Opt-in only?)
- [ ] What is the observation channel — app check-in, SMS, Telegram bot? (Telegram is where the teens are.)
- [ ] Cold start: what does the very first experiment look like for a user with zero history?
- [ ] Do we model *dislike* explicitly? A teen who hates their first pottery class tells us a lot.

---

## Appendix — Key Figures for Slides

| Figure | Source |
|---|---|
| Hobby = 3rd most common youth aspiration | National Youth Survey 2025 |
| Only 42% satisfied with opportunities to pursue one | NCSS Quality of Life Survey 2025 |
| 8% of youths have no close friends | MCCY/NYC engagements, 2026 |
| 3 in 5 say youth spaces would help them meet others | MCCY/NYC engagements, 2026 |
| S$500 Curiosity Credits, ages 13–17, SHG members | SG Youth Plan, 25 Jul 2026 |
| ~20,000 hobby opportunities/year by 2030 | SG Youth Plan |
| 12 free third spaces by end-2026 | SG Youth Plan |
| 95 PA Youth Networks at Community Clubs | People's Association |
| 100+ ActiveSG interest groups | ActiveSG / MyActiveSG+ |
| Secondary students receive ~S$4–14/day pocket money | ST / Milieu Insight, 2024 |
| ~1 in 3 parents say use your own savings | ST / Milieu Insight, 2024 |
| World's first agentic AI governance framework | IMDA, 22 Jan 2026 |

*Verify each figure against the primary source before it goes on a slide.*
