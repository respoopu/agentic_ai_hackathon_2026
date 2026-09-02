"use client";

import { FormEvent, useEffect, useState } from "react";

import { ActivityDetails } from "@/components/ActivityDetails";
import type {
  AdaptationView,
  ApprovalRequirements,
  BookingStepResponse,
  BookingView,
  DemoApproveRequest,
  DemoAttendanceRequest,
  DemoSetupRequest,
  HealthView,
  PlanStepResponse,
} from "@/lib/contracts";
import { DemoApiError, demoRequest } from "@/lib/http";

type Stage = "setup" | "plan" | "approval" | "booked" | "debrief" | "adapted";
type Vibe = "sporty" | "artistic" | "chill" | "explorative";

const stages = [
  { key: "plan", label: "Plan", detail: "Find a reversible first try" },
  { key: "approval", label: "Check", detail: "Trusted adult reviews it" },
  { key: "booked", label: "Book", detail: "Sandbox action only" },
  { key: "adapted", label: "Learn", detail: "Use real attendance evidence" },
] as const;

const stagePosition: Record<Stage, number> = {
  setup: 0,
  plan: 0,
  approval: 1,
  booked: 2,
  debrief: 3,
  adapted: 3,
};

const vibeOptions: Array<{ value: Vibe; label: string; note: string }> = [
  { value: "sporty", label: "Move", note: "active and energetic" },
  { value: "artistic", label: "Make", note: "creative and hands-on" },
  { value: "chill", label: "Unwind", note: "calm and low-pressure" },
  { value: "explorative", label: "Explore", note: "something unexpected" },
];

function errorMessage(error: unknown): string {
  return error instanceof DemoApiError
    ? error.message
    : "Something interrupted this step. Please try again.";
}

function friendlyAxis(axis: string): string {
  return {
    indoor_outdoor: "setting",
    team_solo: "group style",
    contact_noncontact: "creative fit",
    intensity: "energy level",
    competitive_social: "social pace",
  }[axis] ?? axis;
}

export function HobbiDemo() {
  const [stage, setStage] = useState<Stage>("setup");
  const [health, setHealth] = useState<HealthView | null>(null);
  const [selectedVibes, setSelectedVibes] = useState<Vibe[]>([]);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [planResponse, setPlanResponse] = useState<PlanStepResponse | null>(null);
  const [bookingResponse, setBookingResponse] = useState<BookingStepResponse | null>(null);
  const [adaptation, setAdaptation] = useState<AdaptationView | null>(null);
  const [nextPlanResponse, setNextPlanResponse] = useState<PlanStepResponse | null>(null);
  const [attended, setAttended] = useState(true);
  const [debrief, setDebrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    demoRequest<HealthView>("/api/health")
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch(() => {
        if (active) setHealth(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [stage]);

  const plan = planResponse?.plan ?? null;
  const requirements = planResponse?.approval_requirements ?? null;
  const booking = bookingResponse?.bookings?.[0] ?? null;
  const nextPlan = nextPlanResponse?.plan ?? null;

  function toggleVibe(vibe: Vibe) {
    setSelectedVibes((current) =>
      current.includes(vibe) ? current.filter((item) => item !== vibe) : [...current, vibe],
    );
  }

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const data = new FormData(event.currentTarget);
    const payload: DemoSetupRequest = {
      declared_age: Number(data.get("age")),
      goal: String(data.get("goal")),
      money_total_sgd: Number(data.get("budget")),
      hours_per_week: Number(data.get("hours")),
      tries_total: Number(data.get("tries")),
      max_travel_min: Number(data.get("travel")),
      cold_start_vibes: selectedVibes,
      parental_rules: verifiedOnly ? ["verified_only"] : [],
    };
    try {
      const result = await demoRequest<PlanStepResponse>("/api/plan", payload);
      if (!result.plan || !result.approval_requirements) {
        throw new Error("No displayable plan returned");
      }
      setPlanResponse(result);
      setStage("plan");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function approvePlan() {
    if (!planResponse || !plan || !requirements) return;
    setBusy(true);
    setError(null);
    const payload: DemoApproveRequest = {
      teen_id: planResponse.teen_id,
      plan_id: plan.plan_id,
      provider_listing_ids: requirements.provider_listing_ids ?? [],
      spend_ceiling_sgd: requirements.spend_required ? plan.total_cost_sgd : null,
    };
    try {
      const result = await demoRequest<BookingStepResponse>("/api/approve", payload);
      if (!result.bookings?.length) throw new Error("No booking returned");
      setBookingResponse(result);
      setStage("booked");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function recordAttendance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!planResponse || !booking) return;
    setBusy(true);
    setError(null);
    const payload: DemoAttendanceRequest = {
      teen_id: planResponse.teen_id,
      booking_id: booking.booking_id,
      attended,
      debrief: debrief.trim() || null,
    };
    try {
      const result = await demoRequest<{ ok: boolean; adaptation: AdaptationView }>(
        "/api/attendance",
        payload,
      );
      setAdaptation(result.adaptation);
      setStage("adapted");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function revealNextPlan() {
    if (!planResponse) return;
    setBusy(true);
    setError(null);
    try {
      const result = await demoRequest<PlanStepResponse>("/api/next-plan", {
        teen_id: planResponse.teen_id,
      });
      if (!result.plan) throw new Error("No next plan returned");
      setNextPlanResponse(result);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  function resetDemo() {
    setStage("setup");
    setSelectedVibes([]);
    setVerifiedOnly(false);
    setPlanResponse(null);
    setBookingResponse(null);
    setAdaptation(null);
    setNextPlanResponse(null);
    setAttended(true);
    setDebrief("");
    setError(null);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="wordmark" type="button" onClick={resetDemo} aria-label="Start Hobbi again">
          hobbi<span className="wordmark-dot">.</span>
        </button>
        <div className="runtime-status" aria-live="polite">
          <span className={health?.ready_for_real_planning ? "status-dot ready" : "status-dot"} />
          {health?.ready_for_real_planning
            ? `${health.real_activities} real activities ready`
            : health
              ? "Catalogue needs attention"
              : "Checking catalogue"}
        </div>
        <span className="demo-label">Local prototype</span>
      </header>

      <div className="workspace">
        <aside className="stage-rail" aria-label="Hobbi journey">
          <p className="rail-title">Your first try</p>
          <ol>
            {stages.map((item, index) => {
              const activeIndex = stagePosition[stage];
              const state = index < activeIndex ? "done" : index === activeIndex ? "current" : "later";
              return (
                <li className={state} key={item.key}>
                  <span className="stage-number">{index < activeIndex ? "✓" : `0${index + 1}`}</span>
                  <span>
                    <strong>{item.label}</strong>
                    <small>{item.detail}</small>
                  </span>
                </li>
              );
            })}
          </ol>
          <div className="agent-note">
            <span className="agent-orbit" aria-hidden="true" />
            <p>
              <strong>Agents act within limits.</strong>
              Planning is automatic. Approval is human. Every booking here is simulated.
            </p>
          </div>
        </aside>

        <section className="main-stage" aria-live="polite">
          {error ? (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button type="button" onClick={() => setError(null)}>Dismiss</button>
            </div>
          ) : null}

          {stage === "setup" ? (
            <section className="step-panel setup-panel" key="setup">
              <div className="intro-lockup">
                <p className="eyebrow">Plan · one reversible experiment</p>
                <h1>Find a first try that actually fits.</h1>
                <p>
                  Tell Hobbi what is practical. The Planner will choose a real Singapore activity;
                  it will not give you a personality label.
                </p>
              </div>

              <form className="setup-form" onSubmit={createPlan}>
                <fieldset className="form-section">
                  <legend>Start with the week you have</legend>
                  <div className="field-grid">
                    <label className="wide-field">
                      <span>What would make this try worthwhile?</span>
                      <textarea
                        name="goal"
                        defaultValue="I want something low-pressure where it is okay to arrive alone."
                        maxLength={500}
                        required
                      />
                    </label>
                    <label>
                      <span>Age</span>
                      <select name="age" defaultValue="15">
                        {[13, 14, 15, 16, 17].map((age) => <option key={age}>{age}</option>)}
                      </select>
                    </label>
                    <label>
                      <span>Total budget</span>
                      <select name="budget" defaultValue="20">
                        <option value="0">S$0</option>
                        <option value="10">S$10</option>
                        <option value="20">S$20</option>
                        <option value="50">S$50</option>
                      </select>
                    </label>
                    <label>
                      <span>Time each week</span>
                      <select name="hours" defaultValue="3">
                        <option value="1">1 hour</option>
                        <option value="2">2 hours</option>
                        <option value="3">3 hours</option>
                        <option value="5">5 hours</option>
                      </select>
                    </label>
                    <label>
                      <span>Tries available</span>
                      <select name="tries" defaultValue="3">
                        <option value="1">1 try</option>
                        <option value="2">2 tries</option>
                        <option value="3">3 tries</option>
                        <option value="4">4 tries</option>
                      </select>
                    </label>
                    <label>
                      <span>Travel limit</span>
                      <select name="travel" defaultValue="45">
                        <option value="20">20 minutes</option>
                        <option value="30">30 minutes</option>
                        <option value="45">45 minutes</option>
                        <option value="60">60 minutes</option>
                      </select>
                    </label>
                  </div>
                </fieldset>

                <fieldset className="form-section">
                  <legend>Where should we start?</legend>
                  <p className="field-help">Optional. These choices nudge the first plan; they never filter your options.</p>
                  <div className="vibe-row">
                    {vibeOptions.map((vibe) => {
                      const selected = selectedVibes.includes(vibe.value);
                      return (
                        <button
                          className={selected ? "vibe selected" : "vibe"}
                          type="button"
                          aria-label={`${vibe.label}: ${vibe.note}`}
                          aria-pressed={selected}
                          onClick={() => toggleVibe(vibe.value)}
                          key={vibe.value}
                        >
                          <strong>{vibe.label}</strong>
                          <span>{vibe.note}</span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="surprise-note">
                    {selectedVibes.length === 0 ? "Surprise me is on." : `${selectedVibes.length} gentle nudge${selectedVibes.length > 1 ? "s" : ""} selected.`}
                  </p>
                </fieldset>

                <label className="check-line">
                  <input
                    type="checkbox"
                    checked={verifiedOnly}
                    onChange={(event) => setVerifiedOnly(event.target.checked)}
                  />
                  <span>
                    <strong>Only use human-verified organisers</strong>
                    <small>Leave off to let a trusted adult review sourced, unverified providers.</small>
                  </span>
                </label>

                <div className="form-action">
                  <p>Teen and trusted adult complete this local-demo setup together.</p>
                  <button className="primary-button" type="submit" disabled={busy || health?.ready_for_real_planning === false}>
                    {busy ? "Planning…" : "Plan my first try"}<span aria-hidden="true">→</span>
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          {stage === "plan" && plan ? (
            <section className="step-panel" key="plan">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Planner finished · no booking made</p>
                  <h1>A practical first experiment.</h1>
                </div>
                <span className="decision-mark" aria-hidden="true">01</span>
              </div>
              <ActivityDetails activity={plan.activities[0]} />
              <div className="reason-line">
                <strong>Why this came first</strong>
                <p>It fits the declared limits and keeps commitment low. Your setup choices influenced ranking only; nothing became a permanent label.</p>
              </div>
              <div className="step-actions">
                <button className="text-button" type="button" onClick={resetDemo}>Start over</button>
                <button className="primary-button" type="button" onClick={() => setStage("approval")}>
                  Pass to trusted adult <span aria-hidden="true">→</span>
                </button>
              </div>
            </section>
          ) : null}

          {stage === "approval" && plan && requirements ? (
            <section className="step-panel adult-panel" key="approval">
              <div className="role-change">
                <span className="role-icon" aria-hidden="true">A</span>
                <div>
                  <p className="eyebrow">Human checkpoint</p>
                  <h1>Trusted-adult review</h1>
                  <p>Hobbi pauses here. The adult approves this exact plan—not a blank cheque for later changes.</p>
                </div>
              </div>
              <ActivityDetails activity={plan.activities[0]} compact />
              <div className="approval-list">
                <div><span>✓</span><p><strong>Attendance</strong>Approve this person attending this session.</p></div>
                <div><span>✓</span><p><strong>Organiser and venue</strong>{plan.activities[0].organiser} at {plan.activities[0].venue_name}.</p></div>
                {requirements.provider_listing_ids?.length ? (
                  <div><span>!</span><p><strong>Provider vetting</strong>This sourced organiser is not yet human-verified. Review the linked source before approving.</p></div>
                ) : (
                  <div><span>✓</span><p><strong>Provider vetting</strong>The organiser record was checked by a named human.</p></div>
                )}
                <div><span>✓</span><p><strong>Spending limit</strong>{requirements.spend_required ? `Approve up to S$${Number(plan.total_cost_sgd).toFixed(2)}.` : "No spend approval needed; this plan is free."}</p></div>
              </div>
              <div className="step-actions">
                <button className="text-button" type="button" onClick={() => setStage("plan")}>Back to plan</button>
                <button className="primary-button" type="button" onClick={approvePlan} disabled={busy}>
                  {busy ? "Booking…" : "Approve & book in sandbox"}<span aria-hidden="true">→</span>
                </button>
              </div>
            </section>
          ) : null}

          {stage === "booked" && booking ? (
            <BookedStep booking={booking} onContinue={() => setStage("debrief")} />
          ) : null}

          {stage === "debrief" && booking ? (
            <section className="step-panel debrief-panel" key="debrief">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Observer · evidence after action</p>
                  <h1>What actually happened?</h1>
                  <p>Attendance counts more than the setup screen. One difficult session will not become a permanent judgement.</p>
                </div>
                <span className="decision-mark" aria-hidden="true">04</span>
              </div>
              <form onSubmit={recordAttendance}>
                <div className="attendance-toggle" role="group" aria-label="Attendance">
                  <button className={attended ? "selected" : ""} type="button" aria-pressed={attended} onClick={() => setAttended(true)}>I went</button>
                  <button className={!attended ? "selected" : ""} type="button" aria-pressed={!attended} onClick={() => setAttended(false)}>I did not go</button>
                </div>
                <label className="debrief-field">
                  <span>Anything Hobbi should learn?</span>
                  <textarea
                    value={debrief}
                    onChange={(event) => setDebrief(event.target.value)}
                    placeholder="The activity was fine, but the group felt awkward…"
                    maxLength={2000}
                  />
                </label>
                <div className="quick-notes" aria-label="Example reflections">
                  <button type="button" onClick={() => { setAttended(false); setDebrief("It was not my thing."); }}>Not my thing</button>
                  <button type="button" onClick={() => { setAttended(true); setDebrief("I liked it and would try something similar."); }}>I liked it</button>
                  <button type="button" onClick={() => { setAttended(false); setDebrief("Exam week — I need a pause."); }}>Busy this week</button>
                </div>
                <div className="step-actions">
                  <button className="text-button" type="button" onClick={() => setStage("booked")}>Back</button>
                  <button className="primary-button" type="submit" disabled={busy}>
                    {busy ? "Learning…" : "Save what happened"}<span aria-hidden="true">→</span>
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          {stage === "adapted" && adaptation && plan ? (
            <section className="step-panel adapted-panel" key="adapted">
              <div className="adaptation-heading">
                <div className="signal-orbit" aria-hidden="true"><span /></div>
                <div>
                  <p className="eyebrow">Observer saved the evidence</p>
                  <h1>{adaptation.action === "hold_this_week" ? "This week can wait." : "A little wiser, not boxed in."}</h1>
                  <p>{adaptation.action === "hold_this_week" ? "Hobbi recognised a temporary constraint and will not treat it as a dislike." : "Hobbi recorded this experience without turning it into a permanent personality label."}</p>
                </div>
              </div>

              <div className="learning-ledger">
                <div>
                  <span className="ledger-number">{adaptation.dislikes_recorded}</span>
                  <p><strong>new dislike signal</strong><small>Temporary and designed to decay</small></p>
                </div>
                <div>
                  <span className="ledger-number">{adaptation.preference_changes?.length ?? 0}</span>
                  <p><strong>preference update</strong><small>Grounded in attendance evidence</small></p>
                </div>
                <div>
                  <span className="ledger-number">0</span>
                  <p><strong>permanent labels</strong><small>Hobbi never diagnoses a type</small></p>
                </div>
              </div>

              {adaptation.preference_changes?.length ? (
                <div className="change-list">
                  {adaptation.preference_changes.map((change) => (
                    <p key={change.axis}><strong>{friendlyAxis(change.axis)}</strong> now uses {change.evidence} evidence with {Math.round(change.after_confidence * 100)}% confidence.</p>
                  ))}
                </div>
              ) : null}

              {nextPlan ? (
                <div className="next-reveal">
                  <div className="comparison-line">
                    <span>First try</span><strong>{plan.activities[0].title}</strong>
                    <span aria-hidden="true">→</span>
                    <span>Next experiment</span><strong>{nextPlan.activities[0].title}</strong>
                  </div>
                  <ActivityDetails activity={nextPlan.activities[0]} compact />
                  <div className="step-actions">
                    <button className="text-button" type="button" onClick={resetDemo}>Run a fresh demo</button>
                    <button className="primary-button" type="button" onClick={() => { setPlanResponse(nextPlanResponse); setNextPlanResponse(null); setStage("approval"); }}>
                      Review the next plan <span aria-hidden="true">→</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="step-actions">
                  <button className="text-button" type="button" onClick={resetDemo}>Run a fresh demo</button>
                  <button className="primary-button" type="button" onClick={revealNextPlan} disabled={busy || adaptation.action === "hold_this_week"}>
                    {adaptation.action === "hold_this_week" ? "No new plan this week" : busy ? "Replanning…" : "See the next experiment"}<span aria-hidden="true">→</span>
                  </button>
                </div>
              )}
            </section>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function BookedStep({ booking, onContinue }: { booking: BookingView; onContinue: () => void }) {
  return (
    <section className="step-panel booked-panel" key="booked">
      <div className="sandbox-banner">
        <span className="sandbox-stamp">Sandbox</span>
        <div><p className="eyebrow">Broker completed the action</p><h1>Practice booking confirmed.</h1></div>
      </div>
      <p className="sandbox-explainer">No real provider was contacted and no payment was made. The ledger commitment and booking record are real inside this local prototype.</p>
      <div className="booking-columns">
        <section>
          <p className="eyebrow">For the teen</p>
          <h2>Know the first ten minutes.</h2>
          <dl>
            <div><dt>Meet</dt><dd>{booking.preparation.meet}</dd></div>
            <div><dt>Bring</dt><dd>{booking.preparation.bring}</dd></div>
            <div><dt>Going alone</dt><dd>{booking.preparation.people_come_alone ? "Other newcomers may arrive alone too." : "Bring someone you know if possible."}</dd></div>
            <div><dt>Bring a friend</dt><dd>{booking.preparation.guest_allowed ? "The listing allows guests." : "Check with the organiser first."}</dd></div>
          </dl>
        </section>
        <section>
          <p className="eyebrow">For the trusted adult</p>
          <h2>One concise record.</h2>
          <dl>
            <div><dt>Organiser</dt><dd>{booking.adult_summary.organiser}</dd></div>
            <div><dt>Venue</dt><dd>{booking.adult_summary.venue}</dd></div>
            <div><dt>Record</dt><dd className="booking-id">{booking.booking_id}</dd></div>
          </dl>
        </section>
      </div>
      <div className="step-actions">
        <span className="quiet-confirmation">G4 checked · exactly one ledger commitment</span>
        <button className="primary-button" type="button" onClick={onContinue}>Log what happened <span aria-hidden="true">→</span></button>
      </div>
    </section>
  );
}
