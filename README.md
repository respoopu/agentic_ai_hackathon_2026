# agentic_ai_hackathon_2026

## Run the Hobbi demo

The responsive frontend drives the real Python API through setup, planning,
trusted-adult approval, sandbox booking, attendance, debrief and an adapted next
plan. Python 3.11 or later and Node.js 20.9 or later are required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm --prefix frontend install
python scripts/run_demo.py
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The runner starts both
services, loads `.env` when present and otherwise creates a temporary local
trusted-adult key. It never sends that key to browser code. Each new journey
uses a fresh synthetic profile, and every booking is clearly labelled as a
sandbox action; no provider is contacted and no payment is made.

The browser contract is generated from the Pydantic display models and committed
at `contracts/frontend-api.openapi.json`. The Next.js server routes use that
contract as a protective layer over the agent-facing `POST /` API: the Guardian
credential remains server-only and the returned teen token is held in an
HttpOnly, same-site cookie.

To verify the frontend:

```bash
python scripts/export_frontend_contract.py --check
npm --prefix frontend run contract:types
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
npx --prefix frontend playwright install chromium  # first run only
npm --prefix frontend run test:e2e
```

`frontend/app` contains the page and same-origin server routes;
`frontend/components` contains the journey UI; `frontend/lib` contains generated
types and the server/browser clients. `scripts/run_demo.py` is the one-command
launcher, while `scripts/export_frontend_contract.py` regenerates the API
contract from `src/schema/api.py`.

## Hobbi backend

The backend implements architecture v2.2 without changing the merged agent prompts or rebuilding the merged CKB loader:

- strict Pydantic state, plan, approval, booking, event, preference, gate, and token contracts;
- SQLite Personal Data with consent, approvals, plans, attendance, preferences, optimistic ledger versions, and exactly-once booking transactions;
- deterministic Intake/I0 and detached G1–G4 validation;
- Planner, Discovery, Guardian, Broker, Observer, and off-path Compliance components with fail-closed tool boundaries;
- a bounded LangGraph pipeline with persistent SQLite checkpoints;
- an optional, not-yet-production-validated Bedrock structured-output adapter, cached Discovery replay, sandbox booking, and an authenticated local JSON API;
- twelve eligible runtime profiles and a one-command B1–B15 report that marks unsupported counterfactual metrics unmeasured.

The canonical CKB is now demo-ready. Its reproducible queue combines 157 merged NLB/ActiveSG drafts with public community previews and official organiser, park, sport and thrifting pages. Rayden attested the 46-row shortlist: 35 complete real activities were promoted, 11 incomplete or unsuitable leads were retained as documented rejections, and 10 clearly fictional rows remain isolated for the Guardian/quarantine demo. Evaluation uses a separate explicitly synthetic catalogue and never presents those rows as real activities.

### Rebuild and verify the real CKB

```bash
python scripts/fetch_public_social_candidates.py
python scripts/build_ckb_review_queue.py
python scripts/select_ckb_shortlist.py --as-of 2026-09-02
# Human decisions and confirmed fields are recorded in data/ckb_attestations.json.
python scripts/promote_ckb_shortlist.py --as-of 2026-09-02
python scripts/build_ckb.py --check-urls --as-of 2026-09-02T12:00:00+08:00
```

These commands reproduce the 2 Sep 2026 snapshot. Its first fixed-date session
is 6 Sep 2026 at 10:00 Asia/Singapore, so refresh and re-attest the catalogue
before using it for a later demo; see `docs/3-system/seed-ckb.md`.
The promotion command replaces generated `data/seed_ckb.csv`; use `--out` with
a scratch path for trial runs rather than treating that file as a shared sheet.

The collector reads public Telegram previews only, never joins or bypasses private/login-gated groups, and stores compact excerpts rather than page dumps. Instagram and Facebook pages are lead sources; stable official organiser pages are preferred as evidence. Promotion fails closed if any shortlist row is pending, a rejection lacks a reason, a reviewer is an automated actor, or an approved row fails the merged builder’s canonical validation.

To prove that the actual agents and LangGraph can plan from the canonical artifact without importing the synthetic evaluation catalogue, run:

```bash
.venv/bin/python -m unittest tests.test_real_ckb_smoke -v
```

The smoke starts a clean runtime, loads `data/seed_ckb.json`, checks `ready_for_real_planning=true`, calls the normal `intake_and_plan` operation, and reaches the trusted-adult checkpoint with only sourced canonical listing IDs.

### Install and verify

Python 3.11 or later is required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -t .
python -m sim.harness --profiles eligible
python -m sim.counterfactual
python -m sim.report
```

`sim.report` labels every result as simulated and keeps the scope of partial diagnostics visible. B10 reports both the eight-case adversarial set and the 12-profile eligible runtime diagnostic. B11 and B14 come from a 12-cycle executable production-component replay against an immutable static policy; B15 runs both policies over the same four eligible S$0 profiles and applies its 30-day censor to the planned session date, not the request date. Planner and G1 execute directly once per simulated cycle; G2–G4 execute inside LangGraph after the harness auto-issues synthetic per-Plan approvals. The fixture supplies environment inputs, while plans, attendance and replan results are generated at runtime.

The B12 row is intentionally narrower: it proves that the deterministic text-classifier hold branch is reachable twice, not that 16.7% is a behavioral hold rate or that two bookings were prevented. Observer runs after a booked session in this harness, so the hold is a post-session next-cycle decision; production scheduling that suppresses the next booking remains follow-up work. All results are deterministic policy evidence, not participant evidence. B1 still lacks live-model first-attempt parse instrumentation; B2 covers booking calls only; B9 remains illustrative because its catalogue is authored; B6 requires an LLM judge plus human double-scoring; and B13 needs a dated live-link sample.

### Run the local API

```bash
export HOBBI_RUNTIME_DIR=.hobbi
export HOBBI_GUARDIAN_API_TOKEN='replace-with-a-random-guardian-secret'
export HOBBI_COMPLIANCE_API_TOKEN='replace-with-a-random-compliance-secret'
python -m src.api --port 8080
curl -s http://127.0.0.1:8080/ \
  -X POST -H 'content-type: application/json' \
  -d '{"operation":"health"}'
```

The single `POST /` endpoint accepts these operations:

| Operation | Purpose |
|---|---|
| `health` | Runtime and CKB readiness, split into usable real, verified, unverified, fictional and unusable counts |
| `discovery_replay` | Operator-authorized G1 replay of the typed, unverified ActiveSG capture |
| `intake_and_plan` | Trusted-adult-authorized, one-time I0/setup followed by bounded planning |
| `guardian_approve` | Store provider/attendance/spend approval against one exact Plan, then resume at G2 |
| `attendance` | Teen-profile-authorized booking outcome and optional in-app text debrief |
| `next_plan` | Teen-profile-authorized next-cycle planning after attendance evidence is recorded |
| `compliance_scan` | Operator-authorized, allow-listed, robots-aware freshness scan; denied/transient checks mark stale, while explicit listing 404/410 retires |

Protected operations use `Authorization: Bearer <token>`. Setup returns a one-time `teen_access_token` for that profile. Trusted-adult approval is a separate request and is bound to the exact `plan_id`; paid plans also require an amount ceiling. Setup refuses to replace an existing profile, declared age, or parental rules. Planning responses also include a display-ready `plan_view` and `approval_requirements`; approval adds sandbox `bookings`, and attendance adds an `adaptation` view. The original typed state remains available for agent/runtime integrations.

`HOBBI_GUARDIAN_API_TOKEN` is a deployment-wide PoC operator credential, not a teen- or household-specific identity. Plan and teen data ownership checks still apply, but anyone holding that token can act as the trusted-adult operator for every profile in that deployment. Production deployment therefore requires household-scoped identities and authorization in front of this API.

Peer-cohort ranking is implemented only as a privacy-preserving tiebreak seam. The current canonical CKB and simulation catalogue do not populate cohort buckets, so this objective does not affect normal runtime output or any reported metric yet. Agent `ToolGuard` checks are centralized method-entry assertions against declared permissions; they do not mediate every store or CKB call as capability wrappers.

The default runtime executes deterministic typed policies. `src.runtime.structured.invoke_structured` is an optional prompt-backed Bedrock adapter; it is not wired into the default LangGraph and has not been validated against a live AWS account.

The API and simulation do not need AWS. Live model use is lazy through `src.runtime.structured.invoke_structured`; model IDs are fixed constants and credentials come from the normal AWS chain.

Implementation progress and acceptance evidence are tracked in [`checklist.md`](checklist.md).

## Documentation

Project documentation is in [`docs/`](docs/) — start at [`docs/README.md`](docs/README.md)
for its reading order. Outstanding work and its acceptance tests are tracked in
[`docs/5-delivery/outstanding.md`](docs/5-delivery/outstanding.md).

## Secrets are never committed

Copy [`.env.example`](.env.example) to `.env` and fill in your own values. `.env` is
gitignored and there are no credentials in this repository.
`HOBBI_GUARDIAN_API_TOKEN` and `HOBBI_COMPLIANCE_API_TOKEN` must be independent
high-entropy secrets.

## No real personal data

Every teen profile, history and reported metric here is synthetic. The evaluation
catalogue is authored and labelled as such, and the canonical CKB holds real sourced
activities but no participant data. Nothing in this repository is evidence from a
real teenager.
