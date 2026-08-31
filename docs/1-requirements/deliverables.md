# Deliverables & Judging — SimplifyNext Agentic AI Hackathon 2026

*Source of truth: `docs/judging-criteria.pdf` (official slide deck, 39 pages, © 2026 SimplifyNext). Compiled 27 Aug 2026.*

**Part I is the working brief:** the immediate submission requirements, hard limits, judging criteria, and recommended structure. **Part II is the reference section:** detailed guidance, examples, failure modes, technical notes, our scoring plan, and ambiguities.

Content stated as official comes from the deck. Anything read from a rendered diagram is labelled as such; our interpretations are marked *ours*.

---

# Part I — Key deliverables

## 1. Submission checklist

| # | Item | Hard limit / requirement | Owner | Status |
|---|---|---|---|---|
| 1 | Project files / workflow | **≤ 5 GB · one submission only** | | ☐ |
| 2 | Presentation deck | **≤ 10 slides** | | ☐ |
| 3 | Demo video **or** simulation recording | **≤ 5 minutes** | | ☐ |
| 4 | `README.md` | Run instructions + overview and purpose of each script/file | | ☐ |
| 5 | Environment setup | `requirements.txt` or Docker setup | | ☐ |
| 6 | Secrets | Use a `.env` pattern; commit no secrets | | ☐ |
| 7 | Testing / evaluation | Results **must be covered in the slides** | | ☐ |
| 8 | Reproducibility | Submitted solution runs as shown in the video | | ☐ |
| 9 | Deck/code consistency | Methodology presented is reflected at code level | | ☐ |

Item 3 is one five-minute artifact: either a digital solution video or, for a physical/simulated system, a recording of the simulation. Submit one, not both.

## 2. The brief we must answer

> **Design for a World in Transformation.**
> Change is everywhere — in how we live, learn, and relate to one another. Transformation takes time, effort, and the right support at the right moment.
> This is your chance to build something that helps. We envision a solution that **plans, acts, and adapts over time**.
> Your team will choose the problem and decide who it serves. You will design a solution that thinks ahead, takes action, and leaves people genuinely better off.

The three essential capabilities are **plan · act · adapt over time**. The deck repeats them in the Solution Overview and demo-video guidance. The deck, video, and code should each make it easy to identify where all three happen.

Together, the deliverables must:

1. **Answer the question** — explain the problem and the innovative solution clearly.
2. **Showcase Agentic AI knowledge** — demonstrate technical soundness and functionality.
3. **Create business impact** — show that the solution addresses the problem statement.

## 3. What to submit

| Deliverable | Limit | Immediate requirement |
|---|---|---|
| **Project Files / Workflow** | Max 5 GB; **one submission only** | A simple, runnable proof of concept demonstrating the Agentic AI component. Python is strongly recommended. |
| **Presentation Deck** | Max 10 slides | Explain the problem, solution, methodology, architecture, differentiation, evidence, benefits, and adoption potential. |
| **Digital Solution Video** | Max 5 minutes | Show the working solution making a decision or taking an action. |
| **OR Simulation Recording** | Max 5 minutes | Alternative video deliverable for physical/simulated systems. |

### 3.1 Project files — minimum contents

- A concise `README.md` with:
  1. Instructions to run the code.
  2. An overview of the code and purpose of each script/file.
- `requirements.txt` or an acceptable Docker setup.
- Path variables and secrets handled through `.env` files; no committed secrets.
- A logical structure; the deck suggests `src/`, `docs/`, `data/`, and `tests/`.
- Readable, consistently formatted code with relevant inline documentation.
- Actionable error handling suitable for business users.

The judges will look for three things:

1. The solution **can run as demonstrated in the video**.
2. The **presentation methodology is reflected at code level**.
3. **Testing/evaluation is covered in the slides**; extensive test data is not required.

### 3.2 Presentation deck — recommended 10-slide flow

| # | Slide | What goes on it |
|---|---|---|
| 1 | **Title & Team** | Names, roles, and a one-line mission statement |
| 2 | **Problem Statement / Why It Matters** | A specific real-world issue, backed by data, and why it matters for the public good |
| 3 | **Solution Overview** | What the Agentic AI does, why an agent is warranted, and why it is different |
| 4 | **Methodology** | Functional flow, including planning, acting, adapting, and evaluation |
| 5 | **Technical Architecture** | High-level system design, components, tech stack, guardrails, and human checkpoints |
| 6 | **Innovation & Uniqueness** | How the approach differs from existing solutions |
| 7 | **Benefits Delivered** | Quantified improvements, test results, or other evidence |
| 8 | **Demo Preview** | Screenshots or flow of the live/recorded demo or simulation |
| 9 | **Roadmap & Future Potential** | Scale, adoption, and next steps |
| 10 | **Conclusion & Call to Action** | Recap the value and invite adoption |

The original slide bolds slides **3, 4, 5, 7, and 9**: Solution Overview, Methodology, Technical Architecture, Benefits Delivered, and Roadmap. Testing/evaluation has no dedicated slide in the sample flow but is required, so place it on slide 4, 7, or 8.

For every slide: use one core message, prefer evidence and visuals over generic claims, maintain consistent branding, and connect the content to a judging criterion.

### 3.3 Demo video — recommended five-minute flow

| Time | Section | Content |
|---|---|---|
| 0:00–0:30 | **Opening hook** | Start with a relatable story or strong fact |
| 0:30–1:00 | **Problem explanation** | Show the problem in action |
| 1:00–1:30 | **Solution overview** | State how the solution addresses it |
| 1:30–3:30 | **Live / recorded demo** | Show the working prototype, including a decision or action |
| 3:30–4:15 | **Impact & benefits** | Show before/after evidence or metrics |
| 4:15–5:00 | **Closing & call to action** | End with the adoption case and vision |

The working demonstration gets two of the five minutes. Explicitly show where the agent **plans, acts, and adapts**. Use a clear voiceover or captions, avoid unexplained jargon, and ensure the submitted project can reproduce what appears in the video.

## 4. Judging criteria and the 2-point target

Five criteria are weighted **20% each** and scored **0 / 1 / 2**, for a maximum of 10 raw points. The deck gives no tie-breaker or bonus criterion.

| Criterion | Weight | To earn 2 points | Evidence to foreground |
|---|---:|---|---|
| **Benefits delivered** | 20% | Clear benefits that are **scalable or easily adopted** | Quantified improvement plus an adoption/scale path |
| **Original / Innovative idea** | 20% | A **unique and innovative** approach | A specific comparison showing what existing solutions do not do |
| **Effectiveness** | 20% | The solution **fully addresses and resolves** the stated problem | Data, tests, and scenarios against a deliberately narrow claim |
| **Technical Quality and Superiority** | 20% | A technically advanced, **fully functional** prototype needing **minimal work for production** | A reproducible demo, robust code, guardrails, and consistent architecture |
| **Presentation** | 20% | The problem and benefits are clear without prompting | A tight problem → solution → impact story and rehearsed delivery |

The critical gaps between 1 and 2 are:

1. Clear benefit → clear benefit **plus scale or easy adoption**.
2. Existing idea applied well → a **specific, defensible uniqueness claim**.
3. Partial solution → **fully resolves a tightly scoped problem**.
4. Functional with minor production work → **fully functional with minimal work**.
5. Some prompting needed → the story **lands without prompting**.

The alignment slide marks the presentation deck as the key evidence for Benefits, Originality, Effectiveness, and Presentation. Technical Quality is evidenced primarily through the project files and solution video/demo. This makes the deck central to four of five criteria, while the working prototype keeps those claims credible.

## 5. Final pre-submission check

- [ ] Problem statement names one user, one need, and a supported insight.
- [ ] Solution clearly demonstrates **planning, acting, and adapting**.
- [ ] Benefits include at least one measured result with a denominator and date.
- [ ] Originality names a concrete difference from existing solutions.
- [ ] Scale or easy adoption is addressed.
- [ ] Test/evaluation methodology and results appear in the deck.
- [ ] Every agent, loop, and guardrail shown in the deck is identifiable in the code.
- [ ] Every loop has a hard cap held in state.
- [ ] A fresh user can run the project from the `README.md`.
- [ ] The submitted build reproduces the recorded demo.
- [ ] Deck is at most 10 slides; video is at most 5 minutes; files are at most 5 GB.
- [ ] Final package has been verified before the one allowed project-file submission.

---

# Part II — Detailed guidance, examples, and notes

This section preserves the slide deck's supporting guidance, negative examples, technical reference material, our scoring plan, and items to confirm with the organisers.

## 6. Writing the problem statement

The deck spends seven slides on this. It is graded twice — under Presentation (articulating the problem) and under Effectiveness (does the solution resolve *that* problem).

### 6.1 Required format

**POV format:** `[User] needs [a way to ...] because [insight].`

Worked example from the deck: *"A caregiver needs a reliable way to track daily medication because missed doses lead to avoidable hospital visits."*

A finished statement:
- ✅ Names a real user, a real need, and the evidence
- ❌ Names a tool, a feature, or a technology

### 6.2 The six ways a problem statement fails

Every one of these "reads well in the room and collapses under a judge's first question." Check ours against all six **before writing any code**.

| Failure | What it looks like | The fix |
|---|---|---|
| **The Solution in Disguise** | Describes the thing we already decided to build, so the design work has been skipped. ✗ *"Students need an AI chatbot for course advice."* | Name the person and the moment they are stuck. |
| **The Everyone Problem** | The user is all of humanity, so no design decision follows and every feature seems justified. ✗ *"People need better access to mental health support."* | Choose one person we can picture and describe. |
| **The Missing Because** | A need asserted with nothing behind it, so we are designing from a feeling. ✗ *"Elderly residents need companionship."* | Find the evidence, then write the insight it supports. |
| **The Boiling Ocean** | True, enormous, and beyond what any team can move in four days. ✗ *"Singapore needs a sustainable food supply chain."* | Cut one slice we can finish and demonstrate. |
| **The Solved Problem** | A mature product already does this well, so the bar sits impossibly high. ✗ *"Commuters need to know when the next bus arrives."* | Look for what the existing tools still leave undone. |
| **The Comfortable Guess** | Written from the team's imagination, with no contact with anyone who lives the problem. ✗ *"Job seekers need help writing resumes."* | Talk to two real users this week and rewrite after. |

> **The fastest check:** read the statement aloud to someone outside the team. If they ask what we are building, the statement is still doing its job.

### 6.3 The pressure test

Any answer of "no" sends us back to Empathise **before we write code**.

1. **Can we name one person?** A role at a moment, specific enough that we could picture them walking into the room. "Users" and "people" will not pass.
2. **Can we cite the evidence?** A figure, a source, and a date. If the only support is that it feels true, we have an assumption to go and test.
3. **Would that person recognise themselves?** We have spoken with at least one of them. A statement written entirely from our own imagination ends up describing the team.
4. **Does it survive a different solution?** It should still hold if another team builds something completely unlike ours. It describes the problem and belongs to no design.

> **Question 4 is the sharpest one.** A statement that only makes sense once we describe our own build has quietly become a product pitch.

### 6.4 Problem statement vs Solution overview — both are graded

The deck is explicit that these are two different artifacts answering two different questions, and that **both points are graded**.

| The Problem Statement | The Solution Overview |
|---|---|
| Describes a person, a need and an insight, in language the person themselves would use. | Describes what we built and argues why an agentic approach **earns its place** in that problem. |
| Names a role at a specific moment | Names the **planning, acting and adapting** |
| Carries evidence with a source | Explains **what a fixed workflow would miss** |
| Stays true whatever anyone builds | Shows the reasoning a judge can follow |
| Reads as plainly as a sentence spoken aloud | Connects each capability to the person above |

> **The test that separates them: "Would this problem still exist if agentic AI had never been invented?"**
> A **yes** means we have written a problem statement. A **no** means we have written a solution — go back to the person and start again.

The corollary is that "why agentic AI" must appear, just not in the problem statement. Keep the problem statement technology-free and put the justification in the Solution Overview slide.

### 6.5 Weak → sharp, from the deck

Note the square brackets: the deck's own sharpened examples leave `[N weeks, cite source]` placeholders and states that **every bracket needs a source and a date before the statement is finished**.

| Weak | What is missing | Sharper |
|---|---|---|
| "People need better access to mental health support." | No named user, no moment, no evidence | "A polytechnic student in their first semester needs a way to reach a counsellor the same day, because the wait for a first appointment runs [N weeks, cite source] and distress peaks in the fortnight before exams." |
| "Elderly residents need an AI companion robot." | Names the technology, so the solution is already assumed | "An older adult living alone needs someone to notice within the hour that they have fallen, because [cite: share of lasting harm attributed to delay before help arrives]." |
| "Businesses need to be more efficient with documents." | The user is a category, the need is abstract | "A claims officer needs the matriculation number and incident date lifted from scanned forms automatically, because keying them by hand takes [N minutes per claim] and the errors surface [N weeks] later." |
| "Students need help with career planning." | True of almost everyone, so it guides no decision | "A final-year student two months from graduation needs to see which roles their electives qualify them for, because [cite: proportion graduating into unrelated work]." |

---

## 7. Full judging rubric and artifact alignment

### 7.1 Rubric, verbatim

| Criterion | Weight | Question asked | 2 points | 1 point | 0 points |
|---|---|---|---|---|---|
| **Benefits delivered by the solution** | 20% | What positive impact does the solution bring to users, the organization, or the community? Benefits may include increased revenue, productivity, quality, compliance, or quality of life. | Clear benefits; **scalable or easily adopted** | Clear benefits | No or limited benefits |
| **Original / Innovative idea** | 20% | How original and creative is this solution? | **Unique and innovative** approach to the problem | Based on existing ideas but addresses the problem | Not unique; existing solutions address it effectively |
| **Effectiveness of the Solution** | 20% | How effective is the solution in addressing the problem or opportunity? | **Fully addresses and resolves** the problem | Partially addresses the problem, but not fully resolved | Minimal effectiveness in solving the problem |
| **Technical Quality and Superiority of Solution** | 20% | Is the prototype functional and technically sound? | Technically advanced, **fully functional** prototype with **minimal work needed for production** | Functional prototype with **minor work** needed for production | Partially functional or does not meet core requirements |
| **Presentation** | 20% | How effective is the team in articulating the problem statement and explaining how the solution tackles the problem and delivers the benefits? | Clearly explained the problem **and demonstrated the solution's benefits** | Partially explained, with **some prompting or clarification needed** | Unable to clearly explain the problem or demonstrate benefits |

### 7.2 What each criterion wants and where it is evidenced

The "Judging Criteria Alignment" slide maps each criterion to an instruction, then draws arrows to the **slide deck** (marked with a ★), **Solution Video / Demo**, and **Project Files**.

| Criterion | Instruction from the deck | Arrow points at |
|---|---|---|
| Benefits delivered | "Clearly link your features to **measurable** improvements." | Slide deck ★ |
| Original / Innovative | "Point out what makes your approach **different from existing solutions**." | Slide deck ★ |
| Effectiveness | "Use **evidence (data, tests, scenarios)** to prove it works." | Slide deck ★ — and probably a second line into the Video / Demo |
| **Technical Quality** | "Show a **functional prototype** and explain how it is **robust**." | **Project Files + Solution Video / Demo — not the deck** |
| Presentation | "Structure your story well, **rehearse delivery**." | Slide deck ★ |

*(Arrow topology read from the rendered slide because it does not survive text extraction. Four red arrows converge on the starred deck. Black arrows run from Technical Quality to Project Files and Video / Demo. A further black line reaches Video / Demo from higher in the list; Effectiveness is the most likely origin, but the exact fan-out is uncertain.)*

Two conclusions are unambiguous:

- **The slide deck is the starred artifact and carries four of the five criteria.** Eighty per cent of the score is argued on ten slides.
- **"Scalable or easily adopted" is the difference between 1 and 2 for Benefits.** A clear benefit alone is not enough for the top band.

A narrower problem statement is strategically stronger than a broad one because the top Effectiveness band requires the solution to **fully address and resolve** the stated problem.

---

## 8. Project files — detailed requirements

Verbatim requirements from the "Project Files – Key Points" slide.

**Build a simple proof-of-concept to demonstrate your Agentic AI component.**

### 8.1 Documentation
Keep it concise. **A good README will suffice**, covering:
1. Instructions to run your code
2. Overview of your code, and the purpose of each script/file

### 8.2 Environment setup
- Virtual environments. Provide **`requirements.txt`**. Docker setup is also acceptable.
- Path variables
- Secrets and keys — **use `.env` files**

### 8.3 Language / stack
- **Python is strongly recommended.**

### 8.4 Execution — the three things they look at
> No extensive test data is required. What we will look at:
> 1. Whether the solution **can run as demonstrated in the video**.
> 2. Whether the **presentation methodology is reflected at code level**. In-line documentation where relevant would be helpful.
> 3. **Testing/Evaluation should be covered in your slides.**

Item 2 is the sleeper requirement. If the deck says "three loops with a hard iteration cap" then a judge opening the repo expects to find a named iteration cap in the state, not a `while True`. **The deck and the code have to describe the same system.** *(That sentence is the deck's requirement. The next one is ours: this strikes us as the easiest place for an otherwise strong pitch to lose Technical Quality points, because the deck and the repo are usually written by different people on different nights.)*

### 8.5 Development best practices (graded indirectly via Technical Quality)

- **Code readability** — clean, commented code; clear variable names; consistent formatting. Organise code to *showcase application of Agentic AI techniques*.
- **Folder structure** — a logical hierarchy. The deck's suggestion: `src/`, `docs/`, `data/`, `tests/`.
- **Documentation** — concise and clean; a good `README.md` is sufficient.
- **Error handling** — baseline is functional resilience. Going further: *"How can you make it actionable for business users?"* — i.e. a failure should produce a message a non-engineer can act on, not a stack trace.

---

## 9. Presentation deck — detailed guidance and examples

### 9.1 The sample flow

| # | Slide | What goes on it |
|---|---|---|
| 1 | **Title & Team** | Names, roles, and a one-line mission statement |
| 2 | **Problem Statement / Why It Matters** | The real-world issue, backed by data, and why solving it matters for the public good |
| 3 | **Solution Overview** | What your agentic AI does and why it's different |
| 4 | **Methodology** | Functional overview of your solution |
| 5 | **Technical Architecture** | High-level system design, components, tech stack |
| 6 | **Innovation & Uniqueness** | How your approach stands out |
| 7 | **Benefits Delivered** | Quantified improvements or advantages |
| 8 | **Demo Preview** | Screenshots or flow of your live/recorded demo or simulation |
| 9 | **Roadmap & Future Potential** | Where the solution can go next |
| 10 | **Conclusion & Call to Action** | Recap and inspire adoption |

**Five of the ten are bolded on the original slide: 3, 4, 5, 7 and 9** — Solution Overview, Methodology, Technical Architecture, Benefits Delivered, Roadmap & Future Potential. The bolding does not survive text extraction, and it is a direct signal of where the organisers expect the weight to sit. Four of those five are the "what did you actually build, and what is it worth" slides.

The flow otherwise maps almost 1:1 onto the rubric: slide 2 → Presentation, slides 3 + 6 → Originality, slide 5 → Technical Quality, slide 7 → Benefits, slides 4 + 8 → Effectiveness. **Testing/evaluation has no slide of its own** in the sample flow but is *required* to be covered (§8.4) — fold it into slide 4, 7 or 8.

### 9.2 Content rules

- **One core message per slide.** Do not overcrowd.
- Use visuals — diagrams, icons, infographics.
- Consistent branding: colours, fonts, style.
- **Tie each slide to a judging criterion.**
- Avoid generic claims; use data or real examples. *"Instead of 'Improves efficiency', say 'Reduces processing time by 30%'."*

### 9.3 Problem & Impact slide — DOs and DON'Ts

Include: a clear concise problem statement · evidence (data, statistics, credible reports showing urgency) · a relatable user story or persona · why solving this is important.

| ✅ DO | ❌ DON'T |
|---|---|
| "1 in 4 adults experience mental health issues annually, but only 40% receive treatment." *(clear statement)* | "Mental health is a big problem everywhere." *(too vague)* |
| "WHO reports depression costs the global economy $1 trillion yearly in lost productivity." *(credible data)* | "This issue affects everyone in the world." *(too broad, no focus)* |
| "Meet Jane, a university student who struggles to access timely support." *(user story)* | "Our solution will change the world." *(buzzwords, no evidence)* |
| "Lack of early intervention leads to worsening conditions and higher healthcare costs." *(connects to public good)* | |

### 9.4 Solution & Technical Flow slide — DOs and DON'Ts

Include: a short plain description of what it does · **agentic capabilities: planning, acting, adapting** · a diagram of `inputs → reasoning → actions → feedback` · key tech stack.

| ✅ DO | ❌ DON'T |
|---|---|
| Plain language: "Our AI agent detects early signs of stress from daily mood check-ins." | "We built a GPT-4 + RLHF + custom neural net…" *(jargon-heavy, no context)* |
| Show flow: Inputs (check-ins, wearable data) → reasoning (detect patterns) → actions (recommend exercises, alert counsellor) → feedback (track improvements). | Only listing features: "Chatbot + API + dashboard" *(no user benefit)* |
| Name agentic features: "Plans personalised activities, adapts based on user responses." | No diagram or flow, making it hard to visualise. |
| Keep the stack relevant: "LLM for reasoning, mobile app for UI, Python APIs for data ingestion." | Forgetting to link how features actually improve the outcome. |

---

## 10. Demo video — detailed guidance

### 10.1 Suggested breakdown

| Time | Section | Content |
|---|---|---|
| 0:00–0:30 | **Opening hook** | Start with a relatable story or bold fact |
| 0:30–1:00 | **Problem explanation** | Show the problem in action |
| 1:00–1:30 | **Solution overview** | State how your solution addresses the issue |
| 1:30–3:30 | **Live / recorded demo** | Walk through features, show it working |
| 3:30–4:15 | **Impact & benefits** | Show before/after or metrics |
| 4:15–5:00 | **Closing & call to action** | End with a vision, invite adoption |

The demo itself gets **two of the five minutes**. The other three are framing.

### 10.2 Rules

- **Show, don't just tell** — demonstrate the AI *making a decision or taking an action*.
- **Highlight agentic features: where does it plan, act, adapt?**
- Clear voiceover or captions for accessibility.
- Avoid jargon, or explain terms briefly.
- Pace the delivery. Five minutes is short.
- *"If showing an AI chatbot, don't just show the interface — narrate the reasoning process behind its responses."*

### 10.3 Final presentation tips

- Focus on a strong problem statement **within reach**.
- Make the value obvious to judges **in the first minute**.
- Keep a logical flow: **problem → solution → impact**.
- Practice with the team to stay within the time limit.
- End with a powerful call to action.

---

## 11. Maximising our score — our plan

This section is **ours**, derived from the official requirements and guidance above. It is the part to argue about.

### 11.1 Testing & evaluation — the biggest cheap win

The deck **requires** testing/evaluation on the slides, spends a full slide on how to think about it, and then offers six ready-made metrics. Most teams will skip this. It is the clearest available differentiator on **Effectiveness** ("use evidence — data, tests, scenarios — to prove it works").

What the deck says about accuracy testing:

- Understand the difference in nuance compared to traditional ML accuracy measurement — precision/recall, F1 etc.
- *"For a chatbot use case, how would you prepare test data and measure accuracy?"*
- **"Are Agentic AI results always Yes/No?"** — the expected answer is no, so a binary pass/fail harness is not enough on its own.
- **Evaluation metrics:** identify relevant data points to capture, **in translation to the Problem Statement & Solution Objective**, and **justify your testing methodology**.

That last line is the instruction: the metrics have to be derived from *our* problem statement, not lifted generically. Pick from the deck's six, then add one that only makes sense for our problem.

**The six metrics the deck offers for digital agents:**

| # | Metric | Definition | The question it answers |
|---|---|---|---|
| 1 | **Schema Validation Pass Rate** | Share of outputs that parse and validate on the first attempt | "Is the output usable by another system?" |
| 2 | **Tool-Call Success Rate** | Share of tool calls that return a usable result; log the failures | "Does the agent reach for the right hands?" |
| 3 | **Task Completion Rate** | Requests resolved end to end without a human stepping in to finish them | "Did it carry the job to the end?" |
| 4 | **Token Cost Per Run** | Input + output + cache read + cache creation tokens across a whole run | "What does one answer actually cost?" |
| 5 | **Loop Discipline** | Iterations per task against the cap, and how often a run reaches the cap | "Is it converging or circling?" |
| 6 | **Answer Fidelity** | Score against a reviewed ground-truth set, using a rubric or an LLM judge | "Is it right, as well as plausible?" |

Metric 5 only exists if we have a cap. Metric 4 only exists if we log token usage — the deck notes token usage returns on every response, so this is nearly free.

*(The physical-AI set — task success rate, intervention rate, safety record, cycle time, robustness — does not apply to us, but "intervention rate: how often did a person rescue it" is a good honest framing to borrow for a human-in-the-loop design.)*

**Action:** every metric we report needs a denominator and a date. "Task completion 87% over 60 simulated runs, 26 Aug" beats "high accuracy."

### 11.2 Claim the agent classes explicitly

Topic #2 of the deck is a taxonomy of **eight digital agent classes**, and it says outright that *"many agents will belong to multiple classes."* Naming our classes on the architecture slide is free evidence that we know the material — it costs one line and directly serves "showcase your knowledge of Agentic AI."

| Class | Tagline | Definition |
|---|---|---|
| **Information** | Answer & Advise | Retrieve, summarise, or explain information |
| **Extraction** | Parse & Transform | Convert unstructured content into structured, actionable data |
| **Transaction** | Do & Automate | Perform tasks on behalf of the user by integrating with systems |
| **Decision-Support** | Guide & Recommend | Help with choices by analysing data and recommending actions |
| **Creative / Generative** | Create & Draft | Produce new content based on user intent |
| **Orchestration** | Coordinate & Integrate | Combine multiple systems and flows, acting as a "control tower" |
| **Personalized** | Adapt & Learn | Customise responses based on semantic and episodic context |
| **Embedded** | Live Where People Work | Exist inside other apps or processes rather than as standalone chatbots |

The physical classes (Perception, Monitoring & Inspection, Navigation, Locomotion & Control, Embodied Task) are out of scope for a software submission. Note the deck marks **Human-Robot Interaction** and **Fleet Coordination** as *"not recommended for this hackathon."*

The two case studies closest to a software build are worth copying structurally:
- **Case Study 1 (Educational Support Hub):** classification agent + department agents in an A2A network, knowledge base, escalation pipeline. Pattern named: **Multi-Agent (A2A Network)**.
- **Case Study 2 (Intelligent Exam Generation):** generator → reviewer feedback loop, then translator, then collated output for human review. Pattern named: **Reflection Pattern (Feedback Loop)**, and it is explicitly labelled **Human-in-the-loop**.

Both physical case studies also carry an explicit **"Human-in-the-loop:"** line. The deck clearly rewards naming the human checkpoint as a design feature rather than leaving it implicit.

### 11.3 Engineering guardrails the judges have been primed on

From "Building Agents That Hold Up" — *"these four decisions are made before we write code, and they are what separates a shipped agent from a demonstrated one."* A judge who sat through this deck will look for them.

| # | Principle | The failure it prevents | What to show in the repo |
|---|---|---|---|
| 1 | **Context rot is real** | Accuracy and consistency degrade well before the window limit, while cost and latency rise every turn | Short, single-purpose agents that do one job and exit |
| 2 | **Bound every loop** | *"A refine loop that exits when the critic is satisfied will sometimes never be satisfied, and we discover it from the bill."* | A hard iteration cap **held in state**, that ignores the model's judgement |
| 3 | **Descriptions are the interface** | A vague tool description produces an unused tool or a badly called one | Treat tool descriptions as the highest-leverage prompt text we write |
| 4 | **Keep payloads small** | Tools that return page dumps fill the window with material the model re-reads every turn | Return small typed results; hold large objects in state |

Also from the guardrails column of the stack slide:
- Verify model access in the region we deploy to.
- **Read model ids from a constant, never build them.**
- `allowed_tools` is an allow-list **and a security boundary**.
- **Bound every loop with a counter held in state.**

### 11.4 The reference stack

The deck says: *"We will build on this stack so what you learn from the technical sessions transfers into the submission."* Deviating is allowed, but staying on it is the low-risk path and makes the code legible to the judges.

| Layer | Options given |
|---|---|
| **Interface** | Your own front end — *no framework is required* |
| **Deploy & Serve** | AgentCore Runtime (`@app.entrypoint` handler) · or local first (POST to `localhost:8080`) |
| **Orchestrate** | `create_react_agent` (prebuilt ReAct loop) · **LangGraph** (nodes, edges, routers, loops) · **deepagents** (planning, files, sub-agents) · **Claude Agent SDK** (MCP tools, files, bash) |
| **Schema** | **Pydantic** — *"schema descriptions are the prompt"* |
| **Access** | boto3 `InvokeModel` · Converse API · `ChatBedrockConverse` (the LangChain wrapper) |
| **Model** | **Claude Haiku 4.5** (global profile, the default) · Claude Sonnet 4.5 (single-region alternative) |

Cross-cutting notes worth reusing verbatim in our architecture slide:
- Typed state with reducers where nodes write concurrently
- `InjectedState` reaches large objects without a prompt
- `InMemorySaver` plus `thread_id` carries a conversation
- Token usage returns on every response
- The `@app.entrypoint` handler is the seam a UI calls

Our architecture has parallel-ish writes to a shared knowledge base and three loops, which is exactly the "typed state with reducers" and "bounded loop" shape LangGraph is being recommended for.

### 11.5 Priority order if we run out of time

Ranked by marks-per-hour, given the rubric.

**The framing that should drive this list:** four of the five criteria are argued on the slide deck (§7.2), and only Technical Quality is graded primarily from the repo. So the deck is not the write-up you do on the last night — it is where 80% of the score is argued, and the code exists to earn the remaining 20% *and* to keep the deck honest.

1. **A README a stranger can follow, and code that runs.** Technical Quality is 20% and it is the only criterion graded from the repo. A prototype that doesn't start scores 0 there regardless of the deck.
2. **One measured number, with a denominator and a date.** Moves Benefits from 1 → 2 and Effectiveness from 1 → 2 simultaneously.
3. **The problem statement in POV format with a cited figure.** Graded under Presentation *and* gates Effectiveness.
4. **An evaluation slide.** Explicitly required, widely skipped.
5. **A named, defensible "nobody else does this."** The 1 → 2 gap on Originality.
6. **A scale/adoption sentence.** The 1 → 2 gap on Benefits.
7. **Rehearsal.** Presentation's 0/1/2 band is literally about whether judges need to prompt you.

### 11.6 Traps specific to us

- **"Fully addresses and resolves the problem" caps what we should claim.** If the problem statement is "teens can't find hobbies in Singapore," we cannot fully resolve it and we are capped at 1 on Effectiveness. Scope the statement to something a working prototype demonstrably closes.
- **The video must show the prototype we actually submit.** Requirement 8.4.1 is that the solution "can run as demonstrated in video." A mocked-up demo that the repo cannot reproduce fails both Technical Quality and Effectiveness.
- **The deck and the repo must describe the same system.** Requirement 8.4.2. Every agent named on the architecture slide should be findable as a module, and every loop drawn should have a visible cap.
- **One submission only for project files.** No re-uploads. Freeze and verify before submitting.

---

## 12. Gaps and ambiguities in the deck — confirm with organisers

| # | Issue | Impact | Ask |
|---|---|---|---|
| 1 | The "Pressure-Testing Our Own Statement" slide says *"put our statement through these **five** questions"* but lists only **four**. | Low — the four listed are usable as-is. | None needed; noted so nobody hunts for a missing fifth. |
| 2 | The deck gives **no submission deadline, portal, or file-format spec**. | High — we cannot plan the freeze without it. | Confirm the deadline, upload mechanism, and accepted formats (zip? repo link? mp4 codec?). |
| 3 | **No team size or eligibility rules** appear in this deck. | Medium | Confirm from the registration materials. |
| 4 | It is unclear whether the **Presentation** criterion is graded on a live pitch, the recorded video, or the deck alone. Two signals conflict: the alignment slide points Presentation at the **deck**, but the rubric wording ("some prompting or clarification needed") and the instruction to "**rehearse delivery**" both imply a **live Q&A**. | High — changes how much we rehearse and whether we prepare an objection-handling sheet. | Confirm whether there is a live pitch and Q&A, and how long. |
| 5 | The 5 GB project-files limit is generous; unclear whether large files (model weights, datasets) are expected or discouraged. | Low | Assume a lean repo. |
| 6 | Slide 10 of the sample flow is "Call to Action" — unclear whether judges expect a business/adoption ask or a vision statement. | Low | Do both in one line. |
| 7 | Topic numbering in the deck repeats ("Topic #4" is used for both *Case Studies* and *Understanding the Deliverables*). | None | Cosmetic. |

---

## 13. Source map

| Content here | Deck slide(s) |
|---|---|
| Problem statement recap | "Problem Statement (Recap)" |
| Design thinking + POV format | "Design Thinking: Framing the Problem Statement" |
| Six failure modes | "Six Ways a Problem Statement Fails" |
| Weak → sharp rewrites | "Weak to Sharp: Rewriting the Statement" |
| Pressure test | "Pressure-Testing Our Own Statement" |
| Problem vs solution split | "Where Agentic AI Belongs in the Story" |
| Agent classes | "Digital AI Agent Classes", "Physical AI Agent Classes" |
| Reference stack | "The Agentic AI Stack We Teach" |
| Four engineering decisions | "Building Agents That Hold Up" |
| Dev best practices, testing | "Development Best Practices" ×2 |
| Case studies | "Case Study 1–4" |
| Evaluation metrics | "Measuring Performance of Digital AI Agents", "…of Physical AI" |
| Deliverables list | "Understanding the Deliverables" |
| Criteria → artifact mapping | "Judging Criteria Alignment" |
| Rubric | "Judging Criteria (1/3)", "(2/3)", "(3/3)" |
| Project files requirements | "Project Files – Key Points" |
| Deck structure and tips | "Slide Deck: Structure Overview", "Key Content Tips", "Example" ×2 |
| Video structure and tips | "Demo Video: Structure" ×2 |
| Final tips | "Final Tips for Successful Presentation" |
