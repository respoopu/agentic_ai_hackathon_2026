# agentic_ai_hackathon_2026

## Hobbi backend

The backend implements architecture v2.2 without changing the merged agent prompts or rebuilding the merged CKB loader:

- strict Pydantic state, plan, approval, booking, event, preference, gate, and token contracts;
- SQLite Personal Data with consent, approvals, plans, attendance, preferences, optimistic ledger versions, and exactly-once booking transactions;
- deterministic Intake/I0 and detached G1–G4 validation;
- Planner, Discovery, Guardian, Broker, Observer, and off-path Compliance components with fail-closed tool boundaries;
- a bounded LangGraph pipeline with persistent SQLite checkpoints;
- an optional, not-yet-production-validated Bedrock structured-output adapter, cached Discovery replay, sandbox booking, and an authenticated local JSON API;
- twelve eligible runtime profiles and a one-command B1–B15 report that marks unsupported counterfactual metrics unmeasured.

The canonical CKB sources are the merged transcription sheet, 157 sourced drafts, quarantine fixtures, builder, and loader. The runtime consumes `data/seed_ckb.json` when the existing builder can publish it. It does not silently promote unfinished drafts or invent verification metadata. Evaluation uses an explicitly synthetic catalogue and never presents those rows as real activities.

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

`sim.report` labels every result as simulated and keeps the scope of partial diagnostics visible. B1 lacks first-attempt parse instrumentation; B2 covers booking calls only; B9 is illustrative because its catalogue is authored; B10 covers eligible rather than adversarial runs; and B6 plus B11–B15 remain unmeasured until their required instrumentation, judge, executable baseline, Observer transitions, live-link checks, and attendance evidence exist.

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
| `health` | Runtime and CKB readiness |
| `discovery_replay` | Operator-authorized G1 replay of the typed, unverified ActiveSG capture |
| `intake_and_plan` | Trusted-adult-authorized, one-time I0/setup followed by bounded planning |
| `guardian_approve` | Store provider/attendance/spend approval against one exact Plan, then resume at G2 |
| `attendance` | Teen-profile-authorized booking outcome and optional in-app text debrief |
| `compliance_scan` | Operator-authorized, allow-listed, robots-aware freshness scan; denied/transient checks mark stale, while explicit listing 404/410 retires |

Protected operations use `Authorization: Bearer <token>`. Setup returns a one-time `teen_access_token` for that profile. Trusted-adult approval is a separate request and is bound to the exact `plan_id`; paid plans also require an amount ceiling. Setup refuses to replace an existing profile, declared age, or parental rules.

`HOBBI_GUARDIAN_API_TOKEN` is a deployment-wide PoC operator credential, not a teen- or household-specific identity. Plan and teen data ownership checks still apply, but anyone holding that token can act as the trusted-adult operator for every profile in that deployment. Production deployment therefore requires household-scoped identities and authorization in front of this API.

Peer-cohort ranking is implemented only as a privacy-preserving tiebreak seam. The current canonical CKB and simulation catalogue do not populate cohort buckets, so this objective does not affect normal runtime output or any reported metric yet. Agent `ToolGuard` checks are centralized method-entry assertions against declared permissions; they do not mediate every store or CKB call as capability wrappers.

The default runtime executes deterministic typed policies. `src.runtime.structured.invoke_structured` is an optional prompt-backed Bedrock adapter; it is not wired into the default LangGraph and has not been validated against a live AWS account.

The API and simulation do not need AWS. Live model use is lazy through `src.runtime.structured.invoke_structured`; model IDs are fixed constants and credentials come from the normal AWS chain.

Implementation progress and acceptance evidence are tracked in [`checklist.md`](checklist.md).

## Workshop lab

The original teaching material remains under `lab/`. Hobbi project documentation is in
[`docs/`](docs/) — start at [`docs/README.md`](docs/README.md) for its reading order.

---

Runnable lab for the Agentic AI hackathon workshop: LLM foundations → agents →
Amazon Bedrock → LangGraph → DeepAgents & the Claude Agent SDK → deploying to
Bedrock AgentCore.

Two sessions. **Day 1 needs no AWS account** — it runs on Groq's free tier.
Day 2 moves the same code to Bedrock by changing one line.

## Quick start

```bash
cd lab
uv sync
echo 'GROQ_API_KEY=gsk_...' > .env          # console.groq.com -> API Keys
uv run 00_check_env.py                      # offline preflight, no key needed
uv run section_1_foundation/00_check_groq.py
```

Then work through the sections in order. Each folder has its own README.

| | Folder | Covers | Runs on |
|---|---|---|---|
| §1 | `lab/section_1_foundation/` | what an LLM call actually is | Groq |
| §2 | `lab/section_2_agentic_ai_basic/` | memory, tools, planning, the loop, prompting & RAG | Groq |
| §3 | `lab/section_3_bedrock/` | the raw call, tools, cost, multimodal | Bedrock |
| §4 | `lab/section_4_langgraph/` | state, nodes, edges, tools × state | either |
| §5 | `lab/section_5_deepagents/` | the abstraction ladder, sub-agents, Agent SDK | Bedrock |
| §6 | `lab/section_6_agentcore/` | deploying the agent as an HTTPS service | Bedrock |

Full setup, keys and troubleshooting: [`lab/README.md`](lab/README.md).
AWS CLI and SSO setup: [`lab/AWS_SETUP.md`](lab/AWS_SETUP.md).

## Hands-on labs

Most files are demos to run and read. These are exercises with `TODO(student)`
blocks — the file runs before you touch it and gets the answer wrong in a
useful way:

- `lab/section_2_agentic_ai_basic/05_agent_lab.py` — the agent loop, 4 TODOs
- `lab/section_2_agentic_ai_basic/06d_rag.py` — retrieval from scratch, 2 TODOs
- `lab/section_2_agentic_ai_basic/prompt_engineering.py` — 4 prompt experiments to break
- `lab/section_4_langgraph/01_graph_lab.py` — state, nodes, edges

## ⚠ §6 creates real, billable AWS resources

Everything else is an API call that finishes. Deploying to AgentCore leaves a
runtime, an IAM role and an S3 upload in your account, and a runtime in READY
bills whether or not anything calls it.

```bash
uv run section_6_agentcore/03_teardown.py          # dry run
uv run section_6_agentcore/03_teardown.py --yes    # delete
uv run section_6_agentcore/03_teardown.py --list   # everything in the region
```

Run `--list` at the end of the session.

## Keys are never committed

`lab/.env` holds your Groq key and AWS profile, and is gitignored. If you fork
or clone this, create your own — there are no credentials in this repository.

## No client data

Everything is synthetic: fictional staff, fictional amounts, a fictional
company. The code patterns come from real projects; the data never does.
