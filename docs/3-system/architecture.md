# Architecture — Hobbi

*Authoritative system spec. Companion to [`architecture-diagram.png`](../assets/architecture-diagram.png).*
*Version 2.2 · 31 Aug 2026 · supersedes the agent table in `project_brief.md` v1 §3. v2.2 folds in all twelve decisions — D1–D11 plus D3b — and the PR #2 review corrections (`discrepancies.md` §D).*

**Reading order:** [`deliverables.md`](../1-requirements/deliverables.md) → [`project_brief.md`](../2-product/project_brief.md) → this → [`evaluation.md`](./evaluation.md) → [`discrepancies.md`](../4-decisions/discrepancies.md).

The diagram is the picture. **This document is the contract.** The editable HTML and exported PNG are downstream renderings of this contract; any mismatch is a defect. §13 is the synchronization checklist.

---

## 1. Shape of the system

**5 pipeline agents · 1 scheduled agent · 1 detached validation layer · 1 deterministic intake/setup service · 2 data stores · 2 bounded request loops + 1 ledger-bounded longitudinal feedback cycle.**

The diagram's subtitle uses the same count: **Compliance is not a pipeline agent.** It runs on a schedule, off the request path, and never blocks a user-facing turn. There are seven agentic components in total; Intake/Setup is deterministic application code and is not counted as an agent.

```
Teen + parent ──▶ Intake/Setup ──I0 age boundary──▶ Planner ──◀──1──▶ Discovery Engine ──write──▶ CKB
                       │                                ▲
                       └──eligible setup + seeds──▶     │ external fetch
                                                        │
                                      approved plan     │
                                           ▼            │
                                        Guardian ──2──▶ (fail → Planner)
                                           │ pass
                                           ▼
                                        Broker ──G4 booking record──▶ teen attends / does not attend
                                           │
                                           ▼
                                        Observer ──3──▶ Personal Data ──▶ Planner (next cycle)

Compliance Agent ── scheduled, off the request path ──▶ CKB freshness
Orchestrator ───── validates G1–G4 on-edge, in-band ─────
```

Two stores, and the read/write asymmetry is the point:

| Store | Holds | Who reads | Who writes |
|---|---|---|---|
| **Central Knowledge Base (CKB)** | listings · activities · locations · simulated cohort buckets | Planner, Discovery, Guardian, Compliance | **Seed loader** (build time) · **Discovery** (plan path) · **Compliance** (scheduled freshness) · deterministic cohort aggregator (roadmap) |
| **Personal Data** | declared inputs · parental rules · consent records · budget ledger · plan-live flags · learned preferences | Planner, Guardian, Compliance | **Intake/Setup** (parent + teen inputs and cold-start seeds) · **Broker** (ledger commitments) · **Observer** (outcomes and preferences) · **Compliance** (dead-listing plan flags) |

**Planner is READ-ONLY on both stores.** It cannot write. That is deliberate: the component that reasons most freely is the one with no side effects, so a bad plan is discarded rather than persisted. Intake/Setup owns declared-input and cold-start seed writes after I0 passes; Broker owns commitments; Observer owns outcome reconciliation. Discovery remains the only runtime writer to CKB on the request path.

Broker and Observer use narrow transactional write commands rather than broad Personal Data reads. Broker submits the approved plan's `ledger_version` with its booking transaction; Observer submits an `AttendanceEvent` keyed to a booking. The storage layer rejects a stale version or duplicate transaction and applies the ledger update atomically. This is how they can reconcile the ledger without gaining read access to the rest of a minor's profile.

---

## 2. Actors

| Actor | Role | Touchpoints |
|---|---|---|
| **Teen** (13–17) | End user. Issues a session request with a hobby goal. Attends or does not attend. Gives a post-session debrief. | request in · plan out · debrief in |
| **Parent / Caregiver** | Sets time, money, interest, location, parental rules and consent. One-time setup plus ongoing edits. **Holds approval authority** over spend and over unverified providers. | writes Personal Data · answers Guardian escalations |
| **External sources** | Activity listings, provider sites, public APIs, web search, venue schedules and pricing. **Outside the system boundary** — fetched, never trusted. | read by Discovery |

The Parent is a **secondary user with veto power**, not an observer. See §7.

### 2.1 Deterministic Intake/Setup service

Intake/Setup is application code, not an agent. It collects the declared age, consent records, parent/teen constraints and optional cold-start chip taps; calls the pure `I0` validator; and terminates out-of-range requests before anything reaches Planner. For an eligible teen, it persists the setup inputs and any seed `Axis` records to Personal Data, then invokes Planner. The UI owns the fixed chip vocabulary and the setup handler owns the write, so Planner never has to mutate a store.

The diagram shows both human inputs entering Intake/Setup, its I0 path to Planner, and its write to Personal Data. The planned implementation is `src/intake.py` (§11).

**The age boundary is 13–17, both ends, and it is enforced before Planner runs (D7).** `I0` is a deterministic input validator, not an LLM decision and not one of the four inter-agent gates.

- **Floor — 13.** Under-13 requires parental consent under PDPC's guidance rather than the teen's own, and it is a materially different safety and design problem. A declared age below 13 is **refused at intake**: no plan is produced, and the response points to a trusted adult. Invariant **A11**.
- **Ceiling — 17.** There is no adult mode. A declared age of 18+ is also **refused at intake**: no plan is produced, and the response points to age-appropriate general activity services — not to a trusted adult. Adult mode remains a roadmap item.
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
| **Writes** | Nothing. Emits `Plan` into request state. |
| **Calls** | Discovery Engine — **and only passes it the plan**, never the raw stores |
| **Cap** | `MAX_REPLANS = 3` per request, held in state |
| **On cap** | Emit `no_viable_plan` with the binding constraint named, and escalate to the trusted adult. Never loop again. |

**What it does**

0. **Cold start only** — accepts either the low-confidence seeds written by Intake/Setup or an explicitly unseeded state when the teen chose *"Surprise me"*. Planner does not render the setup screen or write the selection. See "Cold start" below.
1. Reads the ledger and the preference model.
2. Retrieves candidate listings from CKB under hard filters: money remaining, hours free, travel radius, age range, parental rules.
3. Sequences them as **experiments, cheapest first** — tasters and one-off workshops before short courses before term commitments. Explore before exploit.
4. Scores on two objectives: **interest fit** and **belonging** — the latter as a tiebreak between otherwise-equivalent options, never as a filter (§9.3).
5. If the candidate set is thin, invokes Discovery (loop 1).
6. If Guardian rejects, replans with the rejection reason in context (loop 2).

**Why it cannot be a fixed workflow.** The sequence is state-dependent: what to try third depends on what happened at try one. Money and tries are finite and non-renewable, so every selection forecloses others. A ranked list recomputed from the same filters returns the same answer forever; this has to reason over what has already been spent.

**Cold start (D10).** A teen with zero history has no behaviour to learn from — under Hidi & Renninger you cannot measure an interest in someone who has not yet had a trigger, so the cold start's job is to *produce* a trigger, not to diagnose one. After I0 passes and before Planner is invoked, Intake/Setup offers a fixed set of 4–6 vibe chips ("sporty", "artistic", "chill", "explorative"), multi-select. Five rules keep this a **seed** and not a **type**, and they are constraints on the build, not guidance:

1. **Skippable.** *"Surprise me"* is a first-class option that produces a real plan. If it cannot be skipped it is a gate, and a gate is a quiz.
2. **No result screen.** The chips never render a label back to the teen. *"You're an Explorer!"* is typing and is forbidden by `project_brief.md` §6.1.
3. **Lowest confidence, and it decays.** Intake/Setup writes `Axis` with `provenance="seed"` only after I0 passes and before it invokes Planner. Planner only reads it. The **first attendance event outranks the entire cold-start screen.**
4. **Biases, never excludes.** Seeds shape the first one or two experiments. They never filter the candidate set — a mis-tap at signup must not narrow the world permanently. Invariant **A9**.
5. **Asks where to start, not what you are like.** The wording is the distinction §6.1 protects.

**Hard requirement.** For an intake-eligible user aged 13–17, the Planner must return a viable plan at **S$0**, and must return one for a teen who skipped the cold start entirely (invariants **A3**, **A10**). Out-of-range intake cases are tested separately by A11 and never reach Planner. If an eligible user receives no plan, the free/public supply in CKB is under-indexed and that is a Discovery bug, not a "no results" outcome.

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
| **On cap** | After the **second** rejection, escalate the whole plan to the trusted adult with both rejection reasons attached. No third Guardian attempt occurs. Do not silently drop. |

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
| **Writes** | Booking records · **Personal Data ledger** (money committed, tries used) |
| **Precondition** | Guardian pass. **Broker is unreachable without it.** |
| **On failure** | Booking failure returns an actionable message ("venue full on 3 Sep — two alternatives on the same night"), never a stack trace. Failure returns control to Planner with the slot marked unavailable. |

**Outputs, both of them:**
- To the **teen**: what to bring, where exactly to meet, what will happen, how long, whether people usually come alone, and whether `guest_allowed` permits bringing a friend. The "what to expect" preview lowers the cost of walking into a room alone. A generated share link is roadmap, not PoC scope.
- To the **parent**: organiser identity, venue, timings, contact. The reassurance artefact.

**In the PoC, Broker is sandboxed.** It writes booking records and generates confirmations against a seeded provider set; it does not transact with live provider systems. This is stated on the architecture slide, not buried — a judge asking "did you actually book anything?" should get the answer before they ask.

---

### 3.5 Observer *(diagram: "Feedback Capture (post-session)")*

> **Ingests what actually happened: attendance first, debrief second. Updates the preference model from revealed behaviour.**

| | |
|---|---|
| **Class** | Extraction (*Parse & Transform*) — text + attendance → structured preferences |
| **Reads** | Booking records · attendance signal |
| **Writes** | **Personal Data** — updated preferences, attendance history, ledger reconciliation |
| **Cap** | One debrief per session. No re-prompting a teen who does not answer. |

**Two input channels, and the ordering matters:**

| Signal | Source | Weight |
|---|---|---|
| **Attendance** — did they go? did they go back? | Booking record + check-in | **Primary.** Behavioural, hard to fake, available even when the teen says nothing. |
| **Debrief** — likes & dislikes, demographic fit, vibes, environment, travel, comfortability | Text submitted in-app | Secondary. Rich and human, but self-reported and subject to politeness bias. |

**The channel is in-app, and the channel is an adapter (D9, revised 31 Aug).**

Observer does not know or care where a debrief came from. It takes a channel-agnostic `DebriefSubmission` (§5), so the transport is swappable. The PoC accepts text in the in-app form. Audio transcription and messaging adapters are roadmap items unless a local STT component is explicitly added and tested.

For the PoC that adapter is **an in-app text form**, for one reason that outranks convenience: **a third-party messaging platform would hold a minor's submission before we ever see it.** Text-only keeps the four-day build reproducible and removes an STT dependency that the stack does not otherwise provide. A future audio path has its own consent, processor and deletion requirements in §8.

**Keep the register, change the transport.** The form reads like texting a friend, not like a survey: one open question — *"how was it?"* — and one line of text. No star ratings, no matrices. A debrief nobody completes is worth nothing however well it is modelled, and that was the correct instinct behind the original decision.

*Original decision: a Telegram bot. Reversed because it added a second live network dependency to the demo (after D8 added a cached replay precisely to remove one), and because it put a minor's voice recording on a third party's infrastructure. Telegram remains where the long-tail **supply** lives — that is Discovery reading public groups (`project_brief.md` §5.2), an unrelated path.*

Both the diagram and event model route `attended` and `did_not_attend` into Observer. A no-show is one of the most informative signals in the system and must remain visible end to end (Discrepancy A4/A5).

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

**Privacy.** The PoC does not collect audio. A future audio adapter must transcribe locally or within an explicitly approved processor, extract structured preferences, **discard the audio**, and retain the transcript only with explicit consent. See §8.

---

### 3.6 Compliance Agent

> **Scheduled freshness scans. Verifies listings are still valid; refreshes or retires stale data.**

| | |
|---|---|
| **Class** | Information + Extraction, run as a monitor |
| **Reads** | CKB · Personal Data (to know which listings are live in someone's plan) |
| **Writes** | **CKB** (`freshness_state`, `last_seen_at`, `verification`) · **Personal Data** (flags a plan whose listing died) |
| **Trigger** | Scheduled, **off the request path**. Never blocks a user-facing turn. |
| **Cap** | `MAX_LISTINGS_PER_SCAN = 50`, plus `MAX_FETCHES_PER_DOMAIN = 5` per scan. |

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

Concretely, in LangGraph, it is a validation function applied at each gate (`G1`–`G4`), not a routed node. **Recommended rename: `Validator`** — "Orchestrator" implies it holds control flow and a budget ledger, which is what `project_brief.md` v1 said it did and what it no longer does. (Discrepancy A2.)

**What it checks at intake and at each inter-agent gate:**

| Gate | Between | Checks |
|---|---|---|
| **I0** *(deterministic intake boundary)* | Intake/Setup → Planner | Declared age is 13–17 · required consent records exist · out-of-range requests terminate before planning or persistence |
| **G1** | Planner ⇄ Discovery | Outbound `Plan` is valid, non-empty and stripped of personal data; returned `Listing` records are valid, carry source/verification fields, and contain no raw page dump |
| **G2** | Planner → Guardian | Plan schema valid · every listing resolvable in CKB · ledger arithmetic balances · **cost ≤ money remaining** |
| **G3** | Guardian → Broker | `GuardianVerdict` present · every listing `verified` or trusted-adult-approved · required provider, attendance and spend approval ids present |
| **G4** | Broker → Observer | `BookingRecord` well-formed · `ledger_transaction_id` unique · ledger commitment applied exactly once |

**This is one instrumentation point, not the only one.** Gate results provide schema-validation and loop data; model responses provide token usage; tool wrappers provide tool-call outcomes; attendance records and the evaluation harness provide product metrics and judge scores. [`evaluation.md`](./evaluation.md) §3 names the source for each metric. (Discrepancy B3.)

---

## 4. Two request loops and one longitudinal cycle

The deck is unambiguous: *"Bound every loop with a counter held in state"* and *"keep a hard iteration cap in state that ignores the model's judgement."* The two within-request loops use hard `MAX_*` caps. The longitudinal feedback cycle is not a retry loop; it advances at most once per attended or missed session and is bounded by the declared `tries_total` ledger. **These bounds are not optional.** (Discrepancy B1.)

| # | Loop | Path | Trigger | Cap | Terminal behaviour at cap |
|---|---|---|---|---|---|
| **1** | **Plan-quality** | Planner ⇄ Discovery | Candidate set too thin under the declared constraints | `MAX_DISCOVERY_ROUNDS = 2` | Proceed with the thin plan and **name the binding constraint** to the user |
| **2** | **Safety** | Guardian → Planner | Guardian rejects on vetting or spend | `MAX_GUARDIAN_REJECTIONS = 2` | Escalate the plan to the trusted adult with reasons attached |
| **3** | **Feedback** | Observer → Personal Data → Planner | Session outcome recorded | Not a within-request retry loop — one turn per session | Stops when the finite ledger reaches `tries_total` |

Loop 3 is the one that makes this longitudinal rather than stateless. It is also the one that is invisible in a five-minute demo, which is why the simulation harness in §10 exists.

Overall request bound: `MAX_REPLANS = 3`. All caps live in typed state, are logged, and are reported as **Loop Discipline** in [`evaluation.md`](./evaluation.md).

---

## 5. Typed state

One state object per request thread, carried across sessions by `thread_id` in a persistent SQLite checkpointer for the PoC. Reducers apply to append-only fields. CKB writes use store-level transactions rather than request-state reducers.

```python
MAX_REPLANS = 3
MAX_DISCOVERY_ROUNDS = 2
MAX_GUARDIAN_REJECTIONS = 2
MAX_LISTINGS_PER_SCAN = 50
MAX_FETCHES_PER_DOMAIN = 5

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
    thread_id:          str                      # persistent checkpointer key
    declared_age:       int
    intake_result:      IntakeResult
    request:            SessionRequest
    ledger:             BudgetLedger
    candidate_plan:     Plan | None
    approved_plan:      Plan | None
    guardian_verdict:   GuardianVerdict | None
    booking_records:    Annotated[list[BookingRecord], operator.add]

    replan_count:       int                      # ≤ MAX_REPLANS
    discovery_rounds:   int                      # ≤ MAX_DISCOVERY_ROUNDS
    guardian_rejects:   int                      # ≤ MAX_GUARDIAN_REJECTIONS

    gate_log:           Annotated[list[GateResult], operator.add]
    token_usage:        Annotated[list[TokenUsage], operator.add]

    outcome:            Literal["booked", "escalated_to_adult",
                                "no_viable_plan", "hold_this_week"] | None
```

Four terminal outcomes, and **`hold_this_week` is a first-class success**, not a failure. Terminal state and completion class are separate: `escalated_to_adult` after the second permitted Guardian rejection is a designed-checkpoint success; an attempted iteration beyond any configured bound (`cap_breached`) or `no_viable_plan` is a failed completion even when a human is notified. Reaching a designed escalation bound is not itself a breach. See [`evaluation.md`](./evaluation.md) §3.2.

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

class SessionRequest(BaseModel):
    goal:              str
    requested_at:      datetime

class IntakeResult(BaseModel):
    eligible:          bool
    reason:            Literal["eligible", "under_13", "adult_mode_unavailable"]
    referral:          Literal["trusted_adult", "general_activity_services"] | None

class PlanItem(BaseModel):
    listing_id:        str
    session_at:        datetime
    cost_sgd:          Decimal

class Plan(BaseModel):
    plan_id:           str
    items:             list[PlanItem]
    total_cost_sgd:    Decimal
    ledger_version:    int              # optimistic-concurrency token read by Planner

class GuardianVerdict(BaseModel):
    plan_id:                 str
    approved:                bool
    provider_approval_ids:   dict[str, str]  # listing_id → trusted-adult approval id
    attendance_approval_id:  str | None
    spend_approval_id:       str | None
    reason_codes:            list[str]
    reviewed_at:             datetime

class BookingRecord(BaseModel):
    booking_id:            str
    plan_id:               str
    listing_id:            str
    status:                Literal["booked", "failed"]
    ledger_transaction_id: str | None    # idempotency key; unique when booked
    committed_sgd:         Decimal
    created_at:            datetime

class GateResult(BaseModel):
    gate:              Literal["I0", "G1", "G2", "G3", "G4"]
    passed:            bool
    schema_id:         str
    payload_size:      int
    reason_codes:      list[str]
    checked_at:        datetime

class TokenUsage(BaseModel):
    agent:             str
    input_tokens:      int
    output_tokens:     int
    recorded_at:       datetime

class AttendanceEvent(BaseModel):
    booking_id:        str
    attended:          bool
    occurred_at:       datetime

class DebriefRecord(BaseModel):
    booking_id:        str
    text:              str
    submitted_at:      datetime

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
    text:         str
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
    debriefs:            list[DebriefRecord]     # self-reported — weighted lower
    seeded_at:           datetime | None         # None when the teen skipped the cold start
```

**Confidence is ordered by provenance: `seed` < `debrief` < `attendance`.** A preference inferred from one attended session is not the same object as one inferred from six, and a chip tapped at signup is not the same object as either. This ordering is A4's revealed-over-self-reported rule applied at *t=0*, where there is no behaviour yet.

**Dislike decays and never filters (D11).** Effective strength is `strength × 0.5 ** (days_elapsed / half_life_days)`; below a floor of 0.15 it stops influencing ranking at all. Three rules make this a preference signal rather than a ban:

- **Ranking only, never membership.** A dislike moves an option down the list. It never removes it from the candidate set. Tested as invariant **A9** in [`evaluation.md`](./evaluation.md).
- **Attribution matters more than valence.** *"Pottery is boring"* and *"the studio was 50 minutes away and everyone there was 40"* are different findings. Observer attributes which one it was (§3.5). An `instance` dislike down-ranks that provider and that listing; it does not touch the axis, because the activity was never the problem.
- **One negative is n=1.** An axis only moves materially on **two** corroborating `activity`-attributed dislikes. A single bad Tuesday should not close off a category.

The specific `listing_id` remains in the candidate set but is down-ranked while the signal is active. Both the listing and its category can return to their unbiased position as the signal decays. Safety, availability and hard-constraint filters remain independent of dislike.

---

## 6. Control flow, including the paths the diagram omits

```
request
  │
  ▼ I0
age 13–17? ──no──▶ under_13: trusted-adult guidance
  │                 18+: general activity services
  │ yes             (both terminal; no plan)
  ▼
Planner ──── plan thin? ───yes──▶ Discovery ──▶ CKB ──▶ Planner   [loop 1, ≤2]
  │ no                                                      │
  │◀─────────────────────────────────────────────────────────┘
  ▼ G2
Guardian
  ├── unverified provider in plan ──▶ vetting queue ──▶ trusted adult
  │                                        ├── approved ──▶ continue
  │                                        └── rejected ──▶ Planner  [loop 2, ≤2]
  ├── spend requires approval ────▶ parent ──┬── approved ──▶ continue
  │                                          └── declined ──▶ Planner [loop 2, ≤2]
  └── caps hit ─────────────────────────────────────▶ escalated_to_adult (terminal)
  │ pass G3
  ▼
Broker ──┬── booking ok ──▶ confirmations ──▶ ledger decrement ──▶ G4
         └── booking fails ──▶ actionable message ──▶ Planner, slot marked unavailable
                                                        │
                                                        └── replacement traverses G2 → Guardian → G3 again
  │ G4
  ▼ (time passes)
  ├── teen attends ────────▶ Observer: attendance + debrief
  └── teen does NOT attend ─▶ Observer: no-show recorded
  │
  ▼
Observer ──▶ Personal Data ──▶ next cycle Planner                  [loop 3, longitudinal]
             │
             └── 2nd consecutive no-show ──▶ trigger re-plan (NOT a nag)
             └── sustained attendance ─────▶ escalate try → commit, reallocate budget
             └── nothing changed ──────────▶ hold_this_week (terminal, and correct)
```

**Error and terminal states (Discrepancy B2):**

| Condition | Behaviour |
|---|---|
| Discovery finds nothing new | Proceed thin; name the binding constraint ("nothing free within 30 min on a weekday evening — widening to Saturday would open 6 options") |
| Planner cannot build any plan at S$0 for an eligible user | `no_viable_plan` + notify the trusted adult. **Failed completion**, treated as a CKB coverage bug and logged as such. |
| Guardian rejects 2× | `escalated_to_adult` with both reasons; no third attempt |
| Broker booking fails | Actionable alternative → Planner → G2 → Guardian → G3 before any replacement booking |
| Listing dies between plan and session | Compliance flags → Planner re-plans that slot → G2 → Guardian → G3 → Broker; teen and parent notified before travel |
| Intake age outside 13–17 | Refuse before Planner. Under-13 gets trusted-adult guidance; 18+ gets general-services guidance |
| Any attempted iteration beyond a configured cap | Reject the transition, log `cap_breached`, and hand to a human. Never "try once more." Each permitted cap hit follows the loop-specific terminal behaviour in §4. |

Every one of these produces a message a non-technical person can act on. The deck grades error handling on exactly that: *"Going further: how can you make it actionable for business users?"*

---

## 7. Human-in-the-loop

Both software case studies in the deck label their human checkpoint explicitly. Ours, named:

| Checkpoint | Who | What they hold | Where |
|---|---|---|---|
| **Setup** | Parent / caregiver | Time, money, interest, location, parental rules, consent | Personal Data, before any request |
| **Provider vetting** | Trusted adult (parent / SHG case worker / school counsellor) | Whether an unverified private provider is ever shown to the teen | Guardian, per listing |
| **Spend approval** | Parent | Whether money is committed | Guardian, per plan |
| **Escalation** | Trusted adult | Every terminal state that is not `booked` or `hold_this_week` | Guardian at its configured bound / failure handler on `cap_breached` |

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
| *"Agent's access to sensitive data… the risk increases if the agent has **persistent memory** and can store sensitive data across sessions"* | **High.** Personal Data is persistent by design — the longitudinal loop is the product | Minimised scope; no audio in the PoC; Discovery firewalled from personal data |
| *"Scope of agent's actions — read from, or also modify… **Read vs write**"* | Mixed | Planner read-only; every other writer is allow-listed by store and field in §1 |
| *"**Reversibility** — whether such modifications are easily reversed… downstream obligations e.g. entering into a contract"* | **High.** Bookings and spend are irreversible | Both sit behind the strictest gate. Sandboxed in the PoC |
| *"Agent's **level of autonomy** — whether the agent can define the entire workflow or must follow a well-defined procedure"* | Bounded | Fixed graph, hard caps, defined terminal states |

The framework names **"making payments"** and **"sending communications"** explicitly among the irreversible actions that require a human approval checkpoint. Our Broker does both, on behalf of a minor. That is not an incidental alignment — it is the exact case the framework anticipates, and it is why the Guardian gate is a feature we lead with rather than a constraint we apologise for.

One more the framework raises and most teams will not have thought about: **automation bias**. It warns that *"'human-in-the-loop' has to be adapted to address automation bias"* — a parent who approves twenty plans in a row will approve the twenty-first without reading it. Our mitigation: Guardian escalations state **what changed and why**, not just "approve?", and unverified-provider approvals are visually distinct from routine spend approvals.

---

## 8. Data protection

Governed by the PDPC **Advisory Guidelines on the PDPA for Children's Personal Data in the Digital Environment** (issued 28 Mar 2024).

**The consent position, and it is more nuanced than "get parental consent".** PDPC's actual line:

> *"The PDPC considers that a child between 13 and 17 may give valid consent, when the policies on the collection, use and disclosure of the child's personal data, as well as the withdrawal of consent, are readily understandable by them… However, where an organisation has reason to believe that a child does not have sufficient understanding of the nature and consequences of giving consent, the organisation should obtain consent from the child's parent or guardian."*

Our entire cohort is 13–17, so **the teen can legally consent for themselves** — provided our consent language is readable by a 13-year-old. PDPC also notes that an organisation may reasonably set a higher bar in its context, giving an education setting as the example. The PoC is text-only; a future audio adapter takes the higher bar below:

| Data | Consent basis |
|---|---|
| Preferences, attendance, plan history | **Teen's own consent**, in language a 13-year-old can actually read. Withdrawal explained in the same words. |
| **Voice recordings (roadmap only)** | **Teen + parent.** Higher bar taken deliberately before an audio adapter can be enabled. |
| Anything triggering spend or physical attendance | **Parental approval**, via the Guardian gate — a product control, separate from the consent basis |

PDPC further states that children's personal data *"is generally considered to be **sensitive personal data** and must be accorded a higher standard of protection under the PDPA"*, pointing to the **Enhanced Practices** tier of its Guide to Data Protection Practices for ICT Systems. Voice recordings of minors sit squarely there.

| Concern | Position |
|---|---|
| **Voice recordings (roadmap only)** | Not collected by the PoC. A future adapter must name the local or approved STT processor, transcribe → extract structured preferences → **discard the audio**, and retain the transcript only on explicit opt-in. Enhanced Practices tier. |
| **Readable consent** | The consent copy is a deliverable, written for a 13-year-old and tested on one. Not boilerplate. |
| **Withdrawal** | Explained in the same readable language, and actually implemented — required by the guidance, not optional |
| **Peer signal** | **Aggregate only — there is no identity in the payload.** Bucketed presence, k-anonymity floor of 5, resolved at planning-area or 2-digit postal-sector level and **never at school level**. Opt-in to contribute. See §9.3. |
| **Scraping / external fetch** | Discovery respects `robots.txt` and provider ToS. Anything fetched carries `source_url` + `last_seen_at`, so provenance is always attributable. |
| **Blast radius** | Discovery — the only component touching the open internet — never holds personal data. |
| **The gate log is the second custodian** | The validation layer reads *every* inter-agent payload, including gate G3 where approval references cross from Guardian to Broker. So it sees more metadata than any single agent. **`gate_log` therefore records payload *shape* — schema id, validity, size and loop counters — never payload content.** Token usage stays in `token_usage`; content is referenced by id and stays in state. |
| **Consent survives majority** | PDPC: consent obtained while a child *"remains valid when the individual reaches 18"*. No forced re-consent at 18, but we offer a review. The **account** is a separate question: at 18 the Guardian approval requirement is what would need to change, which is precisely the 18+ roadmap item (D7). |

---

## 9. Structural decisions carried by both spec and diagram

These three decisions originated as corrections to v1. They are now requirements of both this contract and the v2.2 diagram. Full reasoning remains in [`discrepancies.md`](../4-decisions/discrepancies.md).

### 9.1 The budget ledger *(Discrepancy A3 — highest impact)*

The ledger turns `time · money · interest` from static filters into a *finite, non-renewable exploration budget managed as a portfolio of experiments over months*: spend tracked, tries counted, remainder reallocated after each outcome.

Without it, the system would only be a constrained planner with a safety gate and a preference learner. That is not the product the brief pitches, and *"why must this be an agent?"* would be much harder to answer.

`BudgetLedger` lives in typed state (§5); Planner reads it; Broker decrements it; Observer reconciles it after each outcome. No new agent is required — reallocation is a Planner responsibility, which is why `project_brief.md` v1's separate *Reallocator* agent is retired rather than reinstated.

### 9.2 The no-show edge *(Discrepancy A4/A5)*

Observer is reachable through both `attended` and `did_not_attend`. A no-show is the trigger for the flagship adaptivity behaviour ("two no-shows → re-plan, not a nag") and must never disappear from the event model.

### 9.3 The belonging objective *(Discrepancy A6)*

`project_brief.md` states two objectives — interest fit **and** belonging — on the evidence that 8% of youths report no close friends and that building friendships outside school is a stated aim of the Curiosity Credits scheme. A hobby found alone is much less likely to stick. Nothing in the diagram scores for it.

**Built as cohort presence, not a friend graph (D2, 31 Aug).** The obvious implementation is a friend system, and it is the wrong one for two independent reasons:

1. **It reproduces the school social graph** — which is the thing Hobbi exists to get a teen out of. A recommender that preferentially sends you where your existing friends already are cannot deliver the outcome the evidence asks for.
2. **It is empty on day one.** A friend graph needs users before it does anything, so the feature would be dead exactly when the demo runs.

What we build instead is `PeerCohort` on `Listing` (§5) — **aggregate presence with no identity in it**:

> Never *"Jian is going."* For an underlying count of four, show **nothing**. At or above k=5, show a bucket such as *"Some teens from your area usually attend"* — never an exact count.

Four rules, and they are what make it privacy-safe by construction rather than by policy:

| Rule | Why |
|---|---|
| **Bucketed, never a count** — `none / few / some / many` | An exact number plus a small area is a re-identification vector |
| **k-anonymity floor (k = 5)** — below it, `suppressed = True` and nothing is shown | *"1 teen from your area is going"* identifies that teen. Showing nothing is the correct output |
| **Planning area or 2-digit postal sector — never school** | School is the graph we are deliberately crossing. Resolving at school level would rebuild it |
| **Opt-in to contribute, and a ranking tiebreak only** | A teen chooses whether their own attendance feeds the aggregate; default off. The signal moves an option up between otherwise-equivalent options, and **absence is never surfaced as a negative** — *"nobody is going"* is a discouraging screen that burns a `try` |

**The slide line.** *3 in 5 youths say youth spaces would help them meet people from different backgrounds* (SG Youth Plan Report, p.56). A friend graph delivers the opposite of what that number asks for; cohort presence delivers it. This is the rare case where the privacy-preserving design is also the more effective one, and it is worth saying in exactly those terms.

**In the PoC, `PeerCohort` is simulated** and labelled as such — the seed loader writes pre-bucketed fixtures into CKB, and no runtime agent infers them from real attendance. A production system would use a deterministic, privacy-reviewed cohort aggregator over opt-in attendance events; it would write only bucket + suppression fields to CKB, never identities or raw counts. Tested as invariant **A12**.

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
| **Observer** | Attendance events fed by the simulation harness; **in-app text debrief form** | Local/approved audio transcription and messaging adapters behind the same `DebriefSubmission` contract |
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
| **Orchestrate** | **LangGraph** | Nodes, edges and routers map 1:1 onto the 5 pipeline agents, two capped request loops and the ledger-bounded longitudinal cycle; Compliance runs as a separate scheduled entrypoint. Typed state with reducers is exactly what concurrent CKB writes need. |
| **Schema** | **Pydantic** | Every inter-agent payload in §5 is a model. Schema descriptions are the prompt. |
| **Access** | `ChatBedrockConverse` | Unified message shape, LangChain-native, token usage on every response — which Loop Discipline and Token Cost Per Run both need |
| **Model** | **Claude Haiku 4.5** (global profile) default; **Sonnet 4.5** for Planner and Guardian if reasoning quality demands it | Model ids read from a constant, never built |
| **Memory** | SQLite-backed LangGraph checkpointer + `thread_id` | Persists the 12-month thread across process restarts; `InMemorySaver` is test-only |
| **Deploy** | Local first (`POST localhost:8080`); `@app.entrypoint` seam ready for AgentCore | The entrypoint is the seam a UI calls |
| **Interface** | Own front end / CLI + the simulation harness | No framework required |
| **Guardrails** | Per-agent `allowed_tools` allow-list; region-verified model access; caps in state | `allowed_tools` is a security boundary, not a convenience |

### Repo layout

*Target structure. **None of this exists yet** — there is no Hobbi code in the repository at the time of writing; `lab/` is unrelated workshop material. This is the shape to build into, chosen so the deck's structure suggestion (`src/`, `docs/`, `data/`, `tests/`) is satisfied and every agent on the architecture slide is findable as a module.*

```
src/
  agents/      planner.py  discovery.py  guardian.py  broker.py  observer.py  compliance.py
  validation/  orchestrator.py         # the gate checks of §3.7
  schema/      state.py  listing.py  preferences.py  plan.py  events.py  gates.py
  intake.py                            # deterministic I0 + setup/seed writes
  graph.py                             # nodes, edges, routers, caps
  constants.py                         # MODEL_ID, all MAX_* caps
data/          seed_ckb.json  synthetic_teen.json  discovery_replay.json
sim/           harness.py  counterfactual.py  report.py
tests/         test_caps.py  test_s0_plan.py  test_guardian_vetting.py  test_schema.py
               test_age_boundary.py  test_peer_cohort.py  test_cold_start.py
docs/
README.md      run instructions + purpose of every file
requirements.txt
.env.example
```

The deck's requirement that *"presentation methodology is reflected at code level"* is the reason `constants.py` holds the request-loop caps as named constants and `graph.py` names its loops. Every agent on the architecture slide is findable as a module; the two request loops show their `MAX_*` caps and the longitudinal cycle shows its finite `tries_total` bound.

---

## 12. Agent-class map

For the architecture slide. Free evidence that we know the taxonomy, and it costs one line.

| Agent | Classes |
|---|---|
| Planner | **Decision-Support** · **Personalized** |
| Discovery Engine | **Information** · **Extraction** |
| Guardian | **Decision-Support** (+ human-in-the-loop checkpoint) |
| Broker | **Transaction** |
| Observer | **Extraction** (attendance + text → structured) |
| Compliance | **Information** · **Extraction** |
| Orchestrator / Validator | **Orchestration** |

Patterns used, in the deck's own vocabulary: **Multi-Agent (A2A) pipeline** with a **Reflection Pattern (feedback loop)** on plan quality, a **safety gate**, and **human-in-the-loop** at spend and vetting.

We do **not** claim Embedded or Creative/Generative. Nothing in the system generates content or lives inside another product, and claiming a class we do not occupy is worse than claiming five accurately.

---

## 13. Diagram synchronization checklist

| # | Contract item checked against the diagram | Type | Origin |
|---|---|---|---|
| 1 | Hard caps on both request loops; `tries_total` bound on the longitudinal cycle | **Required** | B1 |
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
| 14 | Text-only PoC debrief; audio consent, processor and deletion policy on roadmap | **Required** (minors) | B10 |
| 15 | Cold-start seeding — 4–6 skippable vibe chips, `provenance` on `Axis` | New behaviour | D10 |
| 16 | `DislikeSignal` — decaying, attributed, ranking-only | New behaviour | D11 |
| 17 | Age boundary 13–17 enforced at I0; both under-13 and 18+ refused with distinct guidance | **Required** (safety/consent) | D7 |
| 18 | Observation channel: in-app form behind a channel-agnostic `DebriefSubmission` | Decision | D9 |
| 19 | Cached Discovery replay fixture for the demo path | **Required for demo** | D8 |
| 20 | Four inter-agent gates G1–G4, including Broker → Observer | **Required** | PR #2 review |
| 21 | Guardian reads Personal Data + CKB; Compliance writes dead-listing flags to Personal Data | **Required** | PR #2 review |
| 22 | Every booking-failure or dead-listing replacement re-enters G2 and G3 | **Required** | PR #2 review |
| 23 | Guardian escalates after two rejections, never three | **Required** | PR #2 review |

The editable HTML and exported PNG must visibly show every structural flow, boundary, store, gate and bound above, and must not contradict any behavioural row. Prose-only details such as full schema fields, agent-class labels and stack rationale stay here rather than overcrowding the slide asset. The PNG is regenerated from the HTML; it is never maintained independently.
