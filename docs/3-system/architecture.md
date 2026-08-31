# Architecture — Hobbi

*Authoritative system spec. Companion to [`architecture-diagram.png`](../assets/architecture-diagram.png).*
*Version 2.1 · 31 Aug 2026 · supersedes the agent table in `project_brief.md` v1 §3. v2.1 folds in decisions D1–D11 (`discrepancies.md` §D).*

**Reading order:** [`deliverables.md`](../1-requirements/deliverables.md) → [`project_brief.md`](../2-product/project_brief.md) → this → [`evaluation.md`](./evaluation.md) → [`discrepancies.md`](../4-decisions/discrepancies.md).

The diagram is the picture. **This document is the contract.** Where they differ, this document is newer, and every difference is listed in §13 (with reasoning in §9) and cross-referenced in [`discrepancies.md`](../4-decisions/discrepancies.md).

---

## 1. Shape of the system

**5 pipeline agents · 1 scheduled agent · 1 detached validation layer · 2 data stores · 3 bounded loops.**

The diagram's own subtitle says *"5 pipeline agents + 1 detached validation layer"*, and the count is worth being precise about: **Compliance is not a pipeline agent.** It runs on a schedule, off the request path, and never blocks a user-facing turn. Seven components in total.

```
Teen ──request──▶ Planner ──◀──1──▶ Discovery Engine ──write──▶ CKB
                     │                      ▲
                     │ approved plan        │ external fetch
                     ▼                      │
                  Guardian ──2──▶ (fail → Planner)
                     │ pass
                     ▼
                  Broker ──booking──▶ teen attends / does not attend
                     │
                     ▼
                  Observer ──3──▶ Personal Data ──▶ Planner (next cycle)

Compliance Agent ── scheduled, off the request path ──▶ CKB freshness
Orchestrator ───── validates every ◆ gate, in-band ─────
```

Two stores, and the read/write asymmetry is the point:

| Store | Holds | Who reads | Who writes |
|---|---|---|---|
| **Central Knowledge Base (CKB)** | listings · activities · locations | Planner, Discovery, Compliance | **Discovery** (plan path) · **Compliance** (scheduled) |
| **Personal Data** | declared inputs · parental rules · budget ledger · learned preferences | Planner, Guardian | **Parent** (setup) · **Observer** (post-session) |

**Planner is READ-ONLY on both stores.** It cannot write. That is deliberate: the component that reasons most freely is the one with no side effects, so a bad plan is discarded rather than persisted. Discovery is the only writer on the plan path.

---

## 2. Actors

| Actor | Role | Touchpoints |
|---|---|---|
| **Teen** (13–17) | End user. Issues a session request with a hobby goal. Attends or does not attend. Gives a post-session debrief. | request in · plan out · debrief in |
| **Parent / Caregiver** | Sets time, money, interest, location, parental rules and consent. One-time setup plus ongoing edits. **Holds approval authority** over spend and over unverified providers. | writes Personal Data · answers Guardian escalations |
| **External sources** | Activity listings, provider sites, public APIs, web search, venue schedules and pricing. **Outside the system boundary** — fetched, never trusted. | read by Discovery |

The Parent is a **secondary user with veto power**, not an observer. See §7.

**The age boundary is 13–17, both ends, and it is enforced (D7).**

- **Floor — 13.** Under-13 requires parental consent under PDPC's guidance rather than the teen's own, and it is a materially different safety and design problem. A declared age below 13 is **refused at intake**: no plan is produced, and the response points to a trusted adult. Invariant **A11**.
- **Ceiling — 17.** There is no adult mode. 18+ is a roadmap item, not a build item.
- **A trusted adult is mandatory for every user**, because every user is a minor. There is no configuration in which the Guardian gate is skipped.

**Why the ceiling matters technically, not just editorially.** An adult mode would mean a second path through Broker — the one agent that commits money — and would turn `Broker is unreachable without a Guardian pass` (invariant **A7**) from an unconditional property into a conditional one. Keeping the cohort at 13–17 keeps that a single code path with a single test.

**Two different things that look alike, and must not be merged:**

| | **PDPA consent** | **Guardian approval** |
|---|---|---|
| What it governs | Collection and use of personal data | Spend, and exposure to unvetted providers |
| Who holds it | **The teen**, 13–17, may self-consent (§8) — parent additionally for voice | **The trusted adult**, always |
| Why | Legal basis under PDPC guidance | Our own product and safety control |

The trusted adult is not there because the law requires them to consent on the teen's behalf — for 13–17 it generally does not. They are there because money is irreversible and unvetted providers are a child-safety risk. Saying it the other way round on a slide would be wrong, and a judge with a privacy background would notice.

---

## 3. Agents

Each agent below states its job, its agent class (per the deck's taxonomy — see [`deliverables.md`](../1-requirements/deliverables.md) §11.2), what it reads and writes, its hard limits, and what it does when it fails. **Descriptions here are the source text for the tool/sub-agent descriptions in code** — the deck is explicit that descriptions are the interface.

---

### 3.1 Planner Agent

> **Builds the candidate plan under declared constraints. Read-only. Replans when a gate rejects.**

| | |
|---|---|
| **Class** | Decision-Support (*Guide & Recommend*) + Personalized (*Adapt & Learn*) |
| **Reads** | Personal Data (preferences, constraints, parental rules, **ledger**) · CKB (listings, activities, locations) |
| **Writes** | Nothing. Emits `CandidatePlan` into state. |
| **Calls** | Discovery Engine — **and only passes it the plan**, never the raw stores |
| **Cap** | `MAX_REPLANS = 3` per request, held in state |
| **On cap** | Emit `no_viable_plan` with the binding constraint named, and escalate to the trusted adult. Never loop again. |

**What it does**

0. **Cold start only** — if `seeded_at` is `None` and there is no attendance history, offers 4–6 vibe chips (multi-select, skippable). See "Cold start" below.
1. Reads the ledger and the preference model.
2. Retrieves candidate listings from CKB under hard filters: money remaining, hours free, travel radius, age range, parental rules.
3. Sequences them as **experiments, cheapest first** — tasters and one-off workshops before short courses before term commitments. Explore before exploit.
4. Scores on two objectives: **interest fit** and **belonging** — the latter as a tiebreak between otherwise-equivalent options, never as a filter (§9.3).
5. If the candidate set is thin, invokes Discovery (loop 1).
6. If Guardian rejects, replans with the rejection reason in context (loop 2).

**Why it cannot be a fixed workflow.** The sequence is state-dependent: what to try third depends on what happened at try one. Money and tries are finite and non-renewable, so every selection forecloses others. A ranked list recomputed from the same filters returns the same answer forever; this has to reason over what has already been spent.

**Cold start (D10).** A teen with zero history has no behaviour to learn from — under Hidi & Renninger you cannot measure an interest in someone who has not yet had a trigger, so the cold start's job is to *produce* a trigger, not to diagnose one. Planner offers 4–6 vibe chips ("sporty", "artistic", "chill", "explorative"), multi-select. Five rules keep this a **seed** and not a **type**, and they are constraints on the build, not guidance:

1. **Skippable.** *"Surprise me"* is a first-class option that produces a real plan. If it cannot be skipped it is a gate, and a gate is a quiz.
2. **No result screen.** The chips never render a label back to the teen. *"You're an Explorer!"* is typing and is forbidden by `project_brief.md` §6.1.
3. **Lowest confidence, and it decays.** Seeds write `Axis` with `provenance="seed"`. The **first attendance event outranks the entire cold-start screen.**
4. **Biases, never excludes.** Seeds shape the first one or two experiments. They never filter the candidate set — a mis-tap at signup must not narrow the world permanently. Invariant **A9**.
5. **Asks where to start, not what you are like.** The wording is the distinction §6.1 protects.

**Hard requirement.** The Planner must return a viable plan at **S$0**, and must return one for a teen who skipped the cold start entirely (invariants **A3**, **A10**). If it cannot, the free/public supply in CKB is under-indexed and that is a Discovery bug, not a "no results" outcome.

---

### 3.2 Discovery Engine

> **Invoked when the plan is thin. Reads CKB to see what already exists, searches external sources, writes only genuinely new options back.**

| | |
|---|---|
| **Class** | Information (*Answer & Advise*) + Extraction (*Parse & Transform*) |
| **Reads** | CKB (to avoid duplicates) · external sources |
| **Writes** | **CKB** — new `Listing` rows, always with `verification`, `source_url`, `last_seen_at` |
| **Receives** | The plan only. Not the user's personal data. |
| **Cap** | `MAX_DISCOVERY_ROUNDS = 2` per request |
| **On cap** | Return whatever was found. Planner proceeds with a thin plan and says so, rather than looping. |

**Why it exists.** The formal, centre-based market is already covered by Skoop, Serious About School and Flying Cape. Rebuilding it produces Skoop-with-an-LLM. Discovery targets the **uncovered supply** where the free and cheap options actually live: PA Community Club courses, the 95 PA Youth Networks, ActiveSG academies and interest groups, the new third spaces, informal community activity, and the Telegram/Instagram long tail. See `project_brief.md` §5.

**Privacy boundary.** Discovery receives the plan, not the person. It never sees the teen's identity, address, school or parental rules — only the shape of what is needed ("beginner-friendly, free, indoor, north-east, weekday evening"). This is a deliberate blast-radius limit and maps directly to IMDA's *restricted tool access* dimension.

**Anything it writes with `verification = unverified` is quarantined** — visible to Planner for ranking, never bookable until a trusted adult approves it. See §3.3.

**Payload discipline.** Returns small typed `Listing` records, never page dumps. Raw fetched HTML is held in state and discarded, never passed back into a prompt.

---

### 3.3 Guardian Agent

> **Reads the approved plan. Runs the safety check and the parental approval. On fail, the Planner replans.**

| | |
|---|---|
| **Class** | Decision-Support + the human-in-the-loop checkpoint |
| **Reads** | The approved plan · Personal Data (parental rules, consent) · CKB (`verification` state of every listing in the plan) |
| **Writes** | Nothing to the stores. Emits a verdict + reasons. |
| **Cap** | `MAX_GUARDIAN_REJECTIONS = 2` |
| **On cap** | Escalate the whole plan to the trusted adult with the rejection reasons attached. Do not silently drop. |

**Two distinct checks, and they run at different granularities:**

| Check | Granularity | Rule |
|---|---|---|
| **Provider vetting** | Per listing | An **unverified private provider is never surfaced directly to the teen**. It goes to a vetting queue for a trusted adult (parent / SHG case worker / school counsellor) and becomes bookable only after approval. |
| **Spend & plan approval** | Per plan | Any plan that commits money, or that books a minor into a venue, requires parental sign-off before Broker acts. |

These were one box on the diagram. They are separate rules with separate failure modes and both must exist. (Discrepancy A9.)

**This is a visible feature, not a hidden limitation.** It is the direct answer to IMDA's *approval checkpoints for actions with material real-world impact*, and our actions are: spending a minor's money, and sending a minor to a physical address.

---

### 3.4 Broker Agent

> **Makes bookings, sends details and confirmations, and produces the reassurance artefact for parent and teen.**

| | |
|---|---|
| **Class** | Transaction (*Do & Automate*) |
| **Reads** | Approved, Guardian-passed plan |
| **Writes** | Booking records · **decrements the ledger** (money committed, tries used) |
| **Precondition** | Guardian pass. **Broker is unreachable without it.** |
| **On failure** | Booking failure returns an actionable message ("venue full on 3 Sep — two alternatives on the same night"), never a stack trace. Failure returns control to Planner with the slot marked unavailable. |

**Outputs, both of them:**
- To the **teen**: what to bring, where exactly to meet, what will happen, how long, whether people usually come alone. The "what to expect" preview that lowers the cost of walking into a room alone.
- To the **parent**: organiser identity, venue, timings, contact. The reassurance artefact.

**In the PoC, Broker is sandboxed.** It writes booking records and generates confirmations against a seeded provider set; it does not transact with live provider systems. This is stated on the architecture slide, not buried — a judge asking "did you actually book anything?" should get the answer before they ask.

---

### 3.5 Observer *(diagram: "Feedback Capture (post-session)")*

> **Ingests what actually happened: attendance first, debrief second. Updates the preference model from revealed behaviour.**

| | |
|---|---|
| **Class** | Extraction (*Parse & Transform*) — multimodal: audio + text → structured preferences |
| **Reads** | Booking records · attendance signal |
| **Writes** | **Personal Data** — updated preferences, attendance history, ledger reconciliation |
| **Cap** | One debrief per session. No re-prompting a teen who does not answer. |

**Two input channels, and the ordering matters:**

| Signal | Source | Weight |
|---|---|---|
| **Attendance** — did they go? did they go back? | Booking record + check-in | **Primary.** Behavioural, hard to fake, available even when the teen says nothing. |
| **Debrief** — likes & dislikes, demographic fit, vibes, environment, travel, comfortability | Audio + text, transcribed to structured prefs | Secondary. Rich and human, but self-reported and subject to politeness bias. |

**The channel is in-app, and the channel is an adapter (D9, revised 31 Aug).**

Observer does not know or care where a debrief came from. It takes a channel-agnostic `DebriefSubmission` (§5), so the transport is swappable and *"this moves to WhatsApp"* is an adapter, not a rewrite.

For the PoC that adapter is **an in-app form**, for one reason that outranks convenience: **a third-party messaging platform would hold the voice note before we ever see it.** §8 builds our entire minors-data position on transcribe → extract → **discard the audio**, and invariant **A8** asserts no audio artefact survives. Routed through someone else's servers, A8 stays technically true and becomes misleading about the real data flow — which is worse than not claiming it. In-app, we own the whole path and the claim means what it appears to mean.

**Keep the register, change the transport.** The form reads like texting a friend, not like a survey: one open question — *"how was it?"* — an optional voice note, a line of text. No star ratings, no matrices. A debrief nobody completes is worth nothing however well it is modelled, and that was the correct instinct behind the original decision.

*Original decision: a Telegram bot. Reversed because it added a second live network dependency to the demo (after D8 added a cached replay precisely to remove one), and because it put a minor's voice recording on a third party's infrastructure. Telegram remains where the long-tail **supply** lives — that is Discovery reading public groups (`project_brief.md` §5.2), an unrelated path.*

The diagram shows only the debrief, reachable only along the `teen attends session` edge. **A no-show therefore produces no signal at all**, which discards the most informative event in the system. The `did_not_attend` edge is a required addition (Discrepancy A4/A5).

**The adaptation rule:**

- One no-show → note it, change nothing.
- **Two no-shows → re-plan, not a nag.** Something in the plan is wrong: wrong time, wrong travel, wrong intimidation level.
- Sustained repeat attendance → escalate that thread from **try** to **commit**, and reallocate remaining budget toward it.
- Some weeks the correct output is **hold** — no new booking, no message. An agent that only ever escalates is not adapting, it is nagging.

**Attributing a negative (D11).** When the debrief is negative, Observer's job is to decide *what* was disliked before writing anything. It emits a `DislikeSignal` with an `attribution`:

| Attribution | Example | Effect |
|---|---|---|
| `activity` | "Pottery is boring" | Down-weights the axis — but only on a **second** corroborating signal |
| `instance` | "Everyone there was 40 and it was 50 minutes away" | Down-ranks that provider and listing. **Leaves the axis untouched** — the activity was never the problem |
| `unattributed` | "It was fine I guess" | Recorded, decays, moves nothing on its own |

Most quits are instance-level, not activity-level. Collapsing them is how a recommender concludes a teen hates sport when what they hated was the bus ride.

**Privacy.** The audio debrief is a voice recording of a minor. Transcribe, extract structured preferences, **discard the audio**. Retain the transcript only with explicit consent. See §8.

---

### 3.6 Compliance Agent

> **Scheduled freshness scans. Verifies listings are still valid; refreshes or retires stale data.**

| | |
|---|---|
| **Class** | Information + Extraction, run as a monitor |
| **Reads** | CKB · Personal Data (to know which listings are live in someone's plan) |
| **Writes** | **CKB** (`freshness_state`, `last_seen_at`, `verification`) · **Personal Data** (flags a plan whose listing died) |
| **Trigger** | Scheduled, **off the request path**. Never blocks a user-facing turn. |
| **Cap** | `MAX_LISTINGS_PER_SCAN`, and a per-domain fetch budget. |

**Why it earns its place.** The differentiating supply — Telegram groups, Instagram coaches, informal run clubs — is exactly the supply that dies quietly. A dead link is worse than no result: it sends a shy 14-year-old to an empty room, and that is the failure that ends the habit. This agent is what makes long-tail indexing responsible rather than reckless.

**PoC scope:** a manually-triggered scan script over the seeded CKB, plus a demonstrated retire→replan cascade. Not a deployed cron. Say so.

---

### 3.7 Orchestrator Agent *(validation layer)*

> **Stands outside the pipeline. Checks every subagent output at every gate before it advances.**

| | |
|---|---|
| **Class** | Orchestration (*Coordinate & Integrate*) |
| **Reads** | Every inter-agent payload |
| **Writes** | `gate_log` in state |
| **Calls** | Nothing in the business pipeline |

The diagram says *"calls nothing, called by nothing."* Taken literally that cannot gate anything. The intended and implementable reading:

> The Orchestrator is **not a node in the business graph**. It is invoked on every edge, as a validation step between nodes. No agent calls it as a peer, and it calls no agent as a peer — but nothing advances until it passes.

Concretely, in LangGraph, it is a validation function applied at each gate (◆), not a routed node. **Recommended rename: `Validator`** — "Orchestrator" implies it holds control flow and a budget ledger, which is what `project_brief.md` v1 said it did and what it no longer does. (Discrepancy A2.)

**What it checks at each gate:**

| Gate | Between | Checks |
|---|---|---|
| ◆1 | Planner ⇄ Discovery | Plan schema valid · **no personal data in the payload** · plan non-empty |
| ◆2 | Planner → Guardian | Plan schema valid · every listing resolvable in CKB · ledger arithmetic balances · **cost ≤ money remaining** |
| ◆3 | Guardian → Broker | Verdict present · every listing `verified` or adult-approved · parental consent recorded |
| ◆4 | Broker → Observer | Booking record well-formed · ledger decremented exactly once |

**This is also the instrumentation point.** Because it sees every payload, schema-validation pass rate, loop counts and token usage fall out of it for free. That is where [`evaluation.md`](./evaluation.md) gets its numbers, and it is the cheapest way to satisfy the deck's testing requirement. (Discrepancy B3.)

---

## 4. The three loops — and their caps

The deck is unambiguous: *"Bound every loop with a counter held in state"* and *"keep a hard iteration cap in state that ignores the model's judgement."* The diagram draws three loops and caps none of them. Planner "replans until a gate passes" is precisely the unbounded refine loop the deck warns about by name. **These caps are not optional.** (Discrepancy B1.)

| # | Loop | Path | Trigger | Cap | Terminal behaviour at cap |
|---|---|---|---|---|---|
| **1** | **Plan-quality** | Planner ⇄ Discovery | Candidate set too thin under the declared constraints | `MAX_DISCOVERY_ROUNDS = 2` | Proceed with the thin plan and **name the binding constraint** to the user |
| **2** | **Safety** | Guardian → Planner | Guardian rejects on vetting or spend | `MAX_GUARDIAN_REJECTIONS = 2` | Escalate the plan to the trusted adult with reasons attached |
| **3** | **Feedback** | Observer → Personal Data → Planner | Session outcome recorded | Not a within-request loop — it is the **longitudinal** loop, one turn per session | n/a; bounded by the ledger (`tries_total`) |

Loop 3 is the one that makes this longitudinal rather than stateless. It is also the one that is invisible in a five-minute demo, which is why the simulation harness in §10 exists.

Overall request bound: `MAX_REPLANS = 3`. All caps live in typed state, are logged, and are reported as **Loop Discipline** in [`evaluation.md`](./evaluation.md).

---

## 5. Typed state

One state object per request thread, carried across sessions by `thread_id`. Reducers on the append-only fields, because Discovery and Compliance can both write CKB references concurrently.

```python
MAX_REPLANS = 3
MAX_DISCOVERY_ROUNDS = 2
MAX_GUARDIAN_REJECTIONS = 2

class BudgetLedger(BaseModel):
    """Three currencies. All three are declared inputs, never assumptions."""
    money_total_sgd:      Decimal   # may be 0 — S$0 is a supported input, not an edge case
    money_spent_sgd:      Decimal
    money_committed_sgd:  Decimal
    hours_per_week:       float     # usually the binding constraint
    hours_committed:      float
    tries_total:          int       # first-sessions the teen will tolerate. The scarcest currency.
    tries_used:           int
    tries_abandoned:      int       # no-shows — the signal the diagram had no edge for

class HobbiState(TypedDict):
    teen_id:            str
    thread_id:          str                      # InMemorySaver key; carries the 12-month thread
    request:            SessionRequest
    ledger:             BudgetLedger
    candidate_plan:     Plan | None
    approved_plan:      Plan | None

    replan_count:       int                      # ≤ MAX_REPLANS
    discovery_rounds:   int                      # ≤ MAX_DISCOVERY_ROUNDS
    guardian_rejects:   int                      # ≤ MAX_GUARDIAN_REJECTIONS

    gate_log:           Annotated[list[GateResult], operator.add]
    token_usage:        Annotated[list[TokenUsage], operator.add]

    outcome:            Literal["booked", "escalated_to_adult",
                                "no_viable_plan", "hold_this_week"] | None
```

Four terminal outcomes, and **`hold_this_week` is a first-class success**, not a failure. See §10.

### Core records

```python
class Listing(BaseModel):
    listing_id:        str
    title:             str
    provider:          str
    provider_type:     Literal["cc", "activesg", "third_space", "school",
                               "commercial", "informal", "private_unverified"]
    verification:      Literal["verified", "unverified", "retired"]
    verified_at:       date | None
    cost_one_off_sgd:  Decimal        # 0 is common and is the point
    cost_recurring_sgd:Decimal
    equipment_cost_sgd:Decimal
    postal_sector:     str
    travel_min_home:   int
    travel_min_school: int            # a teen goes straight from school more often than from home
    age_min:           int
    age_max:           int
    beginner_friendly: bool
    join_alone_ok:     bool
    guest_allowed:     bool
    commitment:        Literal["taster", "one_off", "short_course", "term"]
    next_sessions:     list[datetime]
    peer_cohort:       PeerCohort | None   # aggregate presence, never identity. See §9.3
    source_url:        HttpUrl
    last_seen_at:      datetime
    freshness_state:   Literal["fresh", "stale", "dead"]

class Axis(BaseModel):
    """One preference dimension, with how much we trust it and where it came from."""
    value:       float      # -1..1
    confidence:  float      # 0..1
    provenance:  Literal["seed", "debrief", "attendance"]
    updated_at:  datetime

class DislikeSignal(BaseModel):
    """A negative signal that decays. Never a blocklist entry — see D11."""
    axis:            str
    listing_id:      str
    attribution:     Literal["activity", "instance", "unattributed"]
    strength:        float          # 0..1 as recorded
    recorded_at:     datetime
    half_life_days:  int = 90       # disliked at 14 can be liked at 16

class DebriefSubmission(BaseModel):
    """Channel-agnostic. Observer does not know where this came from.
    PoC channel is an in-app form; WhatsApp/Telegram adapters are roadmap."""
    booking_id:   str
    text:         str | None
    audio_ref:    str | None      # local handle only; discarded after transcription (A8)
    channel:      Literal["in_app", "whatsapp", "telegram"]
    submitted_at: datetime

class PeerCohort(BaseModel):
    """Aggregate presence. There is no identity in here to leak. See §9.3."""
    same_age_band:  Literal["none", "few", "some", "many"]   # bucketed, never a count
    same_area:      bool          # planning area / 2-digit postal sector. NEVER school
    suppressed:     bool          # True when the underlying count is below k

class PreferenceModel(BaseModel):
    """Preference axes only. No personality type, no learning style, no body metrics.
    See project_brief.md §6 — these exclusions are non-negotiable.

    Cold-start values are SEEDS, not a diagnosis: lowest confidence, never
    exclusionary, outranked by the first attendance event. See §3.1."""
    indoor_outdoor:      Axis
    team_solo:           Axis
    contact_noncontact:  Axis
    intensity:           Axis
    competitive_social:  Axis
    dislikes:            list[DislikeSignal]     # decaying, ranking-only
    attendance:          list[AttendanceEvent]   # revealed — weighted higher
    debriefs:            list[Debrief]           # self-reported — weighted lower
    seeded_at:           datetime | None         # None when the teen skipped the cold start
```

**Confidence is ordered by provenance: `seed` < `debrief` < `attendance`.** A preference inferred from one attended session is not the same object as one inferred from six, and a chip tapped at signup is not the same object as either. This ordering is A4's revealed-over-self-reported rule applied at *t=0*, where there is no behaviour yet.

**Dislike decays and never filters (D11).** Effective strength is `strength × 0.5 ** (days_elapsed / half_life_days)`; below a floor of 0.15 it stops influencing ranking at all. Three rules make this a preference signal rather than a ban:

- **Ranking only, never membership.** A dislike moves an option down the list. It never removes it from the candidate set. Tested as invariant **A9** in [`evaluation.md`](./evaluation.md).
- **Attribution matters more than valence.** *"Pottery is boring"* and *"the studio was 50 minutes away and everyone there was 40"* are different findings. Observer attributes which one it was (§3.5). An `instance` dislike down-ranks that provider and that listing; it does not touch the axis, because the activity was never the problem.
- **One negative is n=1.** An axis only moves materially on **two** corroborating `activity`-attributed dislikes. A single bad Tuesday should not close off a category.

The specific `listing_id` that was disliked is not re-surfaced. The category returns as the signal decays.

---

## 6. Control flow, including the paths the diagram omits

```
request
  │
  ▼
Planner ──── plan thin? ───yes──▶ Discovery ──▶ CKB ──▶ Planner   [loop 1, ≤2]
  │ no                                                      │
  │◀─────────────────────────────────────────────────────────┘
  ▼ ◆2
Guardian
  ├── unverified provider in plan ──▶ vetting queue ──▶ trusted adult
  │                                        ├── approved ──▶ continue
  │                                        └── rejected ──▶ Planner  [loop 2, ≤2]
  ├── spend requires approval ────▶ parent ──┬── approved ──▶ continue
  │                                          └── declined ──▶ Planner [loop 2, ≤2]
  └── caps hit ─────────────────────────────────────▶ escalated_to_adult (terminal)
  │ pass ◆3
  ▼
Broker ──┬── booking ok ──▶ confirmations ──▶ ledger decrement
         └── booking fails ──▶ actionable message ──▶ Planner, slot marked unavailable
  │
  ▼ (time passes)
  ├── teen attends ────────▶ Observer: attendance + debrief
  └── teen does NOT attend ─▶ Observer: no-show recorded          ◀── MISSING FROM DIAGRAM
  │
  ▼
Observer ──▶ Personal Data ──▶ next cycle Planner                  [loop 3, longitudinal]
             │
             └── 2nd consecutive no-show ──▶ trigger re-plan (NOT a nag)
             └── sustained attendance ─────▶ escalate try → commit, reallocate budget
             └── nothing changed ──────────▶ hold_this_week (terminal, and correct)
```

**Error and terminal states, all of which the diagram lacks (Discrepancy B2):**

| Condition | Behaviour |
|---|---|
| Discovery finds nothing new | Proceed thin; name the binding constraint ("nothing free within 30 min on a weekday evening — widening to Saturday would open 6 options") |
| Planner cannot build any plan at S$0 | `no_viable_plan` + escalate. **Treated as a CKB coverage bug**, logged as such. |
| Guardian rejects 3× | `escalated_to_adult` with all three reasons |
| Broker booking fails | Actionable alternative, return to Planner |
| Listing dies between plan and session | Compliance flags → Planner re-plans that slot → teen and parent notified before travel |
| Any cap reached | Log it, exit the loop, hand to a human. Never "try once more." |

Every one of these produces a message a non-technical person can act on. The deck grades error handling on exactly that: *"Going further: how can you make it actionable for business users?"*

---

## 7. Human-in-the-loop

Both software case studies in the deck label their human checkpoint explicitly. Ours, named:

| Checkpoint | Who | What they hold | Where |
|---|---|---|---|
| **Setup** | Parent / caregiver | Time, money, interest, location, parental rules, consent | Personal Data, before any request |
| **Provider vetting** | Trusted adult (parent / SHG case worker / school counsellor) | Whether an unverified private provider is ever shown to the teen | Guardian, per listing |
| **Spend approval** | Parent | Whether money is committed | Guardian, per plan |
| **Escalation** | Trusted adult | Every terminal state that is not `booked` or `hold_this_week` | Guardian / cap breach |

Mapped to the **IMDA Model AI Governance Framework for Agentic AI** (v1.0, 22 Jan 2026, WEF Davos; **v1.5 published 20 May 2026**, updated 5 Jun 2026). It is a *voluntary* Model Framework and a "living document", not legislation — so we say "aligned with", never "compliant with".

Its **four dimensions**, and where each lands in Hobbi:

| IMDA dimension | Framework's own language | Where it lands in Hobbi |
|---|---|---|
| **1 · Assess and bound the risks upfront** | *"limit their agents' scope of impact by designing appropriate boundaries at the planning stage, such as limiting access to tools and external systems"* | Per-agent `allowed_tools` allow-list; Planner read-only; Discovery never holds personal data; hard loop caps |
| **2 · Make humans meaningfully accountable** | *"defining significant checkpoints in the agentic workflow that require human approval, such as high-stakes or irreversible actions"* | The four checkpoints above. Parent holds spend and vetting authority; **no autonomous spend exists** |
| **3 · Implement technical controls and processes** | testing for *"overall execution accuracy, policy adherence, and tool use"* | [`evaluation.md`](./evaluation.md) — Families A, B and C map onto exactly those three |
| **4 · Enable end-user responsibility** | *"users should be informed of the agent's range of actions, access to data, and the user's own responsibilities"* | Broker's parent-facing artefact states what the agent did, what it can do, and what the parent controls |

The framework's **risk-factor table** under dimension 1 reads almost as a description of our system, which is why this is worth a slide:

| Framework risk factor | Hobbi's exposure | Our control |
|---|---|---|
| *"Agent's access to sensitive data… the risk increases if the agent has **persistent memory** and can store sensitive data across sessions"* | **High.** Personal Data is persistent by design — the longitudinal loop is the product | Minimised scope; audio discarded; Discovery firewalled from personal data |
| *"Scope of agent's actions — read from, or also modify… **Read vs write**"* | Mixed | Planner read-only; exactly two writers, each with one job |
| *"**Reversibility** — whether such modifications are easily reversed… downstream obligations e.g. entering into a contract"* | **High.** Bookings and spend are irreversible | Both sit behind the strictest gate. Sandboxed in the PoC |
| *"Agent's **level of autonomy** — whether the agent can define the entire workflow or must follow a well-defined procedure"* | Bounded | Fixed graph, hard caps, defined terminal states |

The framework names **"making payments"** and **"sending communications"** explicitly among the irreversible actions that require a human approval checkpoint. Our Broker does both, on behalf of a minor. That is not an incidental alignment — it is the exact case the framework anticipates, and it is why the Guardian gate is a feature we lead with rather than a constraint we apologise for.

One more the framework raises and most teams will not have thought about: **automation bias**. It warns that *"'human-in-the-loop' has to be adapted to address automation bias"* — a parent who approves twenty plans in a row will approve the twenty-first without reading it. Our mitigation: Guardian escalations state **what changed and why**, not just "approve?", and unverified-provider approvals are visually distinct from routine spend approvals.

---

## 8. Data protection

Governed by the PDPC **Advisory Guidelines on the PDPA for Children's Personal Data in the Digital Environment** (issued 28 Mar 2024).

**The consent position, and it is more nuanced than "get parental consent".** PDPC's actual line:

> *"The PDPC considers that a child between 13 and 17 may give valid consent, when the policies on the collection, use and disclosure of the child's personal data, as well as the withdrawal of consent, are readily understandable by them… However, where an organisation has reason to believe that a child does not have sufficient understanding of the nature and consequences of giving consent, the organisation should obtain consent from the child's parent or guardian."*

Our entire cohort is 13–17, so **the teen can legally consent for themselves** — provided our consent language is readable by a 13-year-old. PDPC also notes that an organisation may reasonably set a higher bar in its context, giving an education setting as the example. Ours involves voice recordings and money, so:

| Data | Consent basis |
|---|---|
| Preferences, attendance, plan history | **Teen's own consent**, in language a 13-year-old can actually read. Withdrawal explained in the same words. |
| **Voice recordings (debrief)** | **Teen + parent.** Higher bar taken deliberately. |
| Anything triggering spend or physical attendance | **Parental approval**, via the Guardian gate — a product control, separate from the consent basis |

PDPC further states that children's personal data *"is generally considered to be **sensitive personal data** and must be accorded a higher standard of protection under the PDPA"*, pointing to the **Enhanced Practices** tier of its Guide to Data Protection Practices for ICT Systems. Voice recordings of minors sit squarely there.

| Concern | Position |
|---|---|
| **Voice recordings (debrief)** | Transcribe → extract structured preferences → **discard the audio**. Transcript retained only on explicit opt-in. Enhanced Practices tier. **The debrief is collected in-app precisely so this is true end-to-end** — a third-party messaging channel would hold the recording before we saw it, and the claim would be true of our system while misleading about the data flow (D9). |
| **Readable consent** | The consent copy is a deliverable, written for a 13-year-old and tested on one. Not boilerplate. |
| **Withdrawal** | Explained in the same readable language, and actually implemented — required by the guidance, not optional |
| **Peer signal** | **Aggregate only — there is no identity in the payload.** Bucketed presence, k-anonymity floor of 5, resolved at planning-area or 2-digit postal-sector level and **never at school level**. Opt-in to contribute. See §9.3. |
| **Scraping / external fetch** | Discovery respects `robots.txt` and provider ToS. Anything fetched carries `source_url` + `last_seen_at`, so provenance is always attributable. |
| **Blast radius** | Discovery — the only component touching the open internet — never holds personal data. |
| **The gate log is the second custodian** | The validation layer reads *every* inter-agent payload, including gate ◆3 where parental rules and consent cross from Guardian to Broker. So it sees more personal data than any single agent. **`gate_log` therefore records payload *shape* — schema id, validity, size, loop counters, token usage — never payload content.** Content is referenced by id and stays in state. Without this rule the privacy story we lead with has a hole in the middle of it. |
| **Consent survives majority** | PDPC: consent obtained while a child *"remains valid when the individual reaches 18"*. No forced re-consent at 18, but we offer a review. The **account** is a separate question: at 18 the Guardian approval requirement is what would need to change, which is precisely the 18+ roadmap item (D7). |

---

## 9. Additions to the diagram

Three things this spec adds that the diagram does not show. Each is here because the pitch or the rubric requires it; each is a small, concrete change. Full reasoning in [`discrepancies.md`](../4-decisions/discrepancies.md).

### 9.1 The budget ledger *(Discrepancy A3 — highest impact)*

The diagram carries `time · money · interest` into Personal Data as **static filter inputs**. The pitch claims something stronger: a *finite, non-renewable exploration budget managed as a portfolio of experiments over months*. That claim needs a **ledger**, not a filter — spend tracked, tries counted, remainder reallocated after each outcome.

Without it, the honest description of the system as drawn is "a constrained planner with a safety gate and a preference learner." That is a good system. It is not the one the brief pitches, and *"why must this be an agent?"* is much harder to answer without it.

**Minimum change:** `BudgetLedger` in typed state (§5); Planner reads it; Broker decrements it; Observer reconciles it after each outcome. No new agent required — reallocation is a Planner responsibility, which is why `project_brief.md` v1's separate *Reallocator* agent is retired rather than reinstated.

### 9.2 The no-show edge *(Discrepancy A4/A5)*

Feedback Capture is reachable only via `teen attends session`. A teen who does not show produces no signal. That is the most informative event in the system and the trigger for the flagship adaptivity behaviour ("two no-shows → re-plan, not a nag"). Add the `did_not_attend` edge into Observer.

### 9.3 The belonging objective *(Discrepancy A6)*

`project_brief.md` states two objectives — interest fit **and** belonging — on the evidence that 8% of youths report no close friends and that building friendships outside school is a stated aim of the Curiosity Credits scheme. A hobby found alone is much less likely to stick. Nothing in the diagram scores for it.

**Built as cohort presence, not a friend graph (D2, 31 Aug).** The obvious implementation is a friend system, and it is the wrong one for two independent reasons:

1. **It reproduces the school social graph** — which is the thing Hobbi exists to get a teen out of. A recommender that preferentially sends you where your existing friends already are cannot deliver the outcome the evidence asks for.
2. **It is empty on day one.** A friend graph needs users before it does anything, so the feature would be dead exactly when the demo runs.

What we build instead is `PeerCohort` on `Listing` (§5) — **aggregate presence with no identity in it**:

> Never *"Jian is going."* Always *"4 teens from your area usually come to this."*

Four rules, and they are what make it privacy-safe by construction rather than by policy:

| Rule | Why |
|---|---|
| **Bucketed, never a count** — `none / few / some / many` | An exact number plus a small area is a re-identification vector |
| **k-anonymity floor (k = 5)** — below it, `suppressed = True` and nothing is shown | *"1 teen from your area is going"* identifies that teen. Showing nothing is the correct output |
| **Planning area or 2-digit postal sector — never school** | School is the graph we are deliberately crossing. Resolving at school level would rebuild it |
| **Opt-in to contribute, and a ranking tiebreak only** | A teen chooses whether their own attendance feeds the aggregate; default off. The signal moves an option up between otherwise-equivalent options, and **absence is never surfaced as a negative** — *"nobody is going"* is a discouraging screen that burns a `try` |

**The slide line.** *3 in 5 youths say youth spaces would help them meet people from different backgrounds* (SG Youth Plan Report, p.56). A friend graph delivers the opposite of what that number asks for; cohort presence delivers it. This is the rare case where the privacy-preserving design is also the more effective one, and it is worth saying in exactly those terms.

**In the PoC, `PeerCohort` is simulated** and labelled as such — it cannot come from a real source at this stage (D8). Tested as invariant **A12**.

---

## 10. What we actually build

The deck's "Boiling Ocean" failure mode and the Effectiveness rubric band ("**fully** addresses and resolves") push the same way: **claim the narrow thing the prototype closes, and roadmap the wide thing.**

| | In the PoC | Deferred to roadmap |
|---|---|---|
| **Agents** | All 6 + validation layer | — |
| **CKB** | Seeded set of real listings across CC courses, ActiveSG, third spaces, informal, and a quarantined unverified set | Live provider integrations |
| **Discovery** | Live web search over a whitelisted domain set, **plus a cached replay fixture captured from a real run** | Full crawl + ToS negotiation |
| **Broker** | Sandboxed — real booking records and confirmations, no live transactions | Real provider APIs |
| **Compliance** | Manually-triggered scan + a demonstrated retire→replan cascade | Deployed scheduler |
| **Observer** | Attendance events fed by the simulation harness; **in-app debrief form** with real audio transcription | WhatsApp / Telegram adapters behind the same `DebriefSubmission` contract |
| **Longitudinal loop** | **Simulation harness** replaying 9–12 months of one synthetic teen | Real users over real months |

**The cached replay is not optional (D8).** Requirement 8.4.1 is that the submitted solution *"can run as demonstrated in the video."* A live search that 404s during judging — or a site that changed the week before — costs Technical Quality *and* Effectiveness. So Discovery's live path is real, one real run is captured to `data/discovery_replay.json`, and the demo path runs from the fixture. Both are reproducible; only one depends on the network being cooperative on the day.

### The simulation harness *(required build item — Discrepancy B8)*

The value accrues over months and the demo is five minutes, so the longitudinal loop has to be made visible or it will not be believed. The harness is not a demo trick; it is also the evaluation substrate ([`evaluation.md`](./evaluation.md)).

It replays a synthetic teen's 9–12 month history and shows, at each decision point:

1. **The diff, not the output** — old plan → trigger signal → reasoning → new plan.
2. **The counterfactual** — what a static recommender would have returned, alongside what the agent actually did. Adaptation is only legible against a baseline.
3. **At least one `hold_this_week`** — the moment the agent correctly decides to do nothing. This is the strongest single signal of genuine adaptivity, and it is the one thing no ranked-list product can produce.

---

## 11. Tech stack

Staying on the taught stack (deck: *"so what you learn from the technical sessions transfers into the submission"*) is the low-risk path and makes the code legible to judges.

| Layer | Choice | Why |
|---|---|---|
| **Orchestrate** | **LangGraph** | Nodes, edges, routers and loops map 1:1 onto the 5 pipeline agents and 3 bounded loops; Compliance runs as a separate scheduled entrypoint. Typed state with reducers is exactly what concurrent CKB writes need. |
| **Schema** | **Pydantic** | Every inter-agent payload in §5 is a model. Schema descriptions are the prompt. |
| **Access** | `ChatBedrockConverse` | Unified message shape, LangChain-native, token usage on every response — which Loop Discipline and Token Cost Per Run both need |
| **Model** | **Claude Haiku 4.5** (global profile) default; **Sonnet 4.5** for Planner and Guardian if reasoning quality demands it | Model ids read from a constant, never built |
| **Memory** | `InMemorySaver` + `thread_id` | Carries the 12-month thread across sessions — this is what makes loop 3 real |
| **Deploy** | Local first (`POST localhost:8080`); `@app.entrypoint` seam ready for AgentCore | The entrypoint is the seam a UI calls |
| **Interface** | Own front end / CLI + the simulation harness | No framework required |
| **Guardrails** | Per-agent `allowed_tools` allow-list; region-verified model access; caps in state | `allowed_tools` is a security boundary, not a convenience |

### Repo layout

*Target structure. **None of this exists yet** — there is no Hobbi code in the repository at the time of writing; `lab/` is unrelated workshop material. This is the shape to build into, chosen so the deck's structure suggestion (`src/`, `docs/`, `data/`, `tests/`) is satisfied and every agent on the architecture slide is findable as a module.*

```
src/
  agents/      planner.py  discovery.py  guardian.py  broker.py  observer.py  compliance.py
  validation/  orchestrator.py         # the gate checks of §3.7
  schema/      state.py  listing.py  preferences.py  plan.py
  graph.py                             # nodes, edges, routers, caps
  constants.py                         # MODEL_ID, all MAX_* caps
data/          seed_ckb.json  synthetic_teen.json  discovery_replay.json
sim/           harness.py  counterfactual.py
tests/         test_caps.py  test_s0_plan.py  test_guardian_vetting.py  test_schema.py
               test_age_boundary.py  test_peer_cohort.py  test_cold_start.py
docs/
README.md      run instructions + purpose of every file
requirements.txt
.env.example
```

The deck's requirement that *"presentation methodology is reflected at code level"* is the reason `constants.py` holds the caps as named constants and `graph.py` names its loops. Every agent on the architecture slide is findable as a module; every loop drawn has a visible cap.

---

## 12. Agent-class map

For the architecture slide. Free evidence that we know the taxonomy, and it costs one line.

| Agent | Classes |
|---|---|
| Planner | **Decision-Support** · **Personalized** |
| Discovery Engine | **Information** · **Extraction** |
| Guardian | **Decision-Support** (+ human-in-the-loop checkpoint) |
| Broker | **Transaction** |
| Observer | **Extraction** (multimodal: audio + text → structured) |
| Compliance | **Information** · **Extraction** |
| Orchestrator / Validator | **Orchestration** |

Patterns used, in the deck's own vocabulary: **Multi-Agent (A2A) pipeline** with a **Reflection Pattern (feedback loop)** on plan quality, a **safety gate**, and **human-in-the-loop** at spend and vetting.

We do **not** claim Embedded or Creative/Generative. Nothing in the system generates content or lives inside another product, and claiming a class we do not occupy is worse than claiming five accurately.

---

## 13. Delta from the diagram — quick reference

| # | Change | Type | Discrepancy |
|---|---|---|---|
| 1 | Hard caps on all three loops, held in state | **Required** | B1 |
| 2 | `BudgetLedger` in typed state; Broker decrements; Observer reconciles | **Required** | A3 |
| 3 | `did_not_attend` edge into Observer | **Required** | A4/A5 |
| 4 | Error and terminal states throughout | **Required** | B2 |
| 5 | Guardian's two checks separated (per-listing vetting vs per-plan spend) | **Required** | A9 |
| 6 | Orchestrator recast as an on-edge validator; recommended rename to `Validator` | Clarification | A2 |
| 7 | "Feedback Capture" renamed **Observer**, attendance weighted above debrief | Rename + rule | A4 |
| 8 | `Reallocator` from brief v1 formally retired into Planner | Retirement | A1 |
| 9 | `PeerCohort` on `Listing` — bucketed, k-anonymised, planning-area level, opt-in, tiebreak only | Scoped-down addition | A6 / D2 |
| 10 | Simulation harness as a named build item | **Required for demo** | B8 |
| 11 | Tech stack named | **Required by rubric** | B4 |
| 12 | Agent classes claimed | Free marks | B5 |
| 13 | Broker declared sandboxed in PoC | Honesty | B9 |
| 14 | Voice-recording retention policy | **Required** (minors) | B10 |
| 15 | Cold-start seeding — 4–6 skippable vibe chips, `provenance` on `Axis` | New behaviour | D10 |
| 16 | `DislikeSignal` — decaying, attributed, ranking-only | New behaviour | D11 |
| 17 | Age boundary 13–17 enforced at intake, under-13 refused | **Required** (safety/consent) | D7 |
| 18 | Observation channel: in-app form behind a channel-agnostic `DebriefSubmission` | Decision | D9 |
| 19 | Cached Discovery replay fixture for the demo path | **Required for demo** | D8 |

The diagram should be regenerated to include items **1, 2, 3, 5 and 17** before it goes on slide 5 — those are structural. The rest are text.
