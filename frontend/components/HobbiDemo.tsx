"use client";

import { FormEvent, useEffect, useState } from "react";

import { ActivityDetails } from "@/components/ActivityDetails";
import type {
  AdaptationView,
  ActivityPlanView,
  BookingStepResponse,
  BookingView,
  DemoApproveRequest,
  DemoAttendanceRequest,
  DemoSetupRequest,
  HealthView,
  PlanOptionView,
  PlanStepResponse,
  ShortlistStepResponse,
} from "@/lib/contracts";
import { DemoApiError, demoRequest } from "@/lib/http";

type Screen =
  | "login"
  | "profile"
  | "home"
  | "plan"
  | "details"
  | "approval"
  | "booked"
  | "debrief"
  | "adapted";
type Vibe = "sporty" | "artistic" | "chill" | "explorative";
type Profile = DemoSetupRequest & { display_name: string };

const DEMO_EMAIL = "maya@hobbi.test";
const DEMO_PASSWORD = "hobbi123";

const vibeOptions: Array<{ value: Vibe; label: string; note: string }> = [
  { value: "sporty", label: "Get moving", note: "Sports and active picks" },
  { value: "artistic", label: "Make stuff", note: "Art, craft and making" },
  { value: "chill", label: "Keep it chill", note: "Easy, low-pressure plans" },
  { value: "explorative", label: "Try anything", note: "Something unexpected" },
];

const journeySteps = ["Pick", "Check", "Book", "Done"];
const journeyPositions: Record<Screen, number> = {
  login: 0,
  profile: 0,
  home: 0,
  plan: 0,
  details: 0,
  approval: 1,
  booked: 2,
  debrief: 3,
  adapted: 3,
};

function errorMessage(error: unknown): string {
  return error instanceof DemoApiError
    ? error.message
    : "Something went wrong. Give it another try.";
}

function formatShortlistCost(value: number | string): string {
  const amount = Number(value);
  return amount === 0 ? "Free" : `S$${amount.toFixed(2)}`;
}

function formatShortlistTime(activity: ActivityPlanView): string {
  if (activity.session_flexible) return activity.schedule_note ?? "Flexible timing";
  return new Intl.DateTimeFormat("en-SG", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Singapore",
  }).format(new Date(activity.session_at));
}

function HobbiBuddy({ small = false }: { small?: boolean }) {
  return (
    <div className={small ? "buddy buddy-small" : "buddy"} aria-hidden="true">
      <svg viewBox="0 0 220 190">
        <path className="buddy-shadow" d="M52 168c8-17 33-26 63-26 31 0 56 9 64 26-12 11-37 17-64 17-26 0-51-6-63-17Z" />
        <path className="buddy-arm buddy-arm-left" d="M51 93C27 88 18 70 22 56c16 3 32 14 43 31Z" />
        <path className="buddy-arm buddy-arm-right" d="M168 91c20-14 38-12 48-1-10 13-28 21-49 16Z" />
        <path className="buddy-body" d="M111 21c43 0 75 31 75 76 0 45-25 72-74 72-50 0-78-27-78-71 0-43 32-77 77-77Z" />
        <path className="buddy-belly" d="M67 112c20 15 67 18 91-1-6 31-23 46-48 46-24 0-38-14-43-45Z" />
        <ellipse className="buddy-eye" cx="83" cy="83" rx="8" ry="10" />
        <ellipse className="buddy-eye" cx="138" cy="83" rx="8" ry="10" />
        <path className="buddy-smile" d="M91 106c12 11 25 11 37 0" />
        <path className="buddy-spark" d="m174 20 7 15 16 6-16 7-7 15-6-15-16-7 16-6Z" />
      </svg>
    </div>
  );
}

function NavIcon({ name }: { name: "home" | "profile" | "logout" }) {
  if (name === "home") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z" /></svg>;
  }
  if (name === "profile") {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21c1-5 4-7 8-7s7 2 8 7" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M14 8l4 4-4 4m4-4H8" /></svg>;
}

function VibeIcon({ vibe }: { vibe: Vibe }) {
  const content = {
    sporty: <><circle cx="12" cy="12" r="8" /><path d="m7 6 4 3 5-2 1 5-4 4v4M4 12h6l3-3" /></>,
    artistic: <><path d="m5 19 3-1 10-10-2-2L6 16Z" /><path d="m14 6 2-2 4 4-2 2M4 20h16" /></>,
    chill: <><path d="M19 4C10 4 5 8 5 15c4 1 8 0 11-3 2-2 3-5 3-8Z" /><path d="M5 20c2-5 6-8 11-11" /></>,
    explorative: <><circle cx="12" cy="12" r="9" /><path d="m15 9-2 5-5 2 2-5Z" /></>,
  }[vibe];
  return <svg className="vibe-icon" viewBox="0 0 24 24" aria-hidden="true">{content}</svg>;
}

function MetricIcon({ type }: { type: "tries" | "budget" | "time" }) {
  const content = {
    tries: <><path d="M5 5h14v5a2 2 0 0 0 0 4v5H5v-5a2 2 0 0 0 0-4Z" /><path d="M12 8v8" /></>,
    budget: <><circle cx="12" cy="12" r="9" /><path d="M15 8.5c-.8-.5-1.7-.7-2.7-.7-1.7 0-3 .8-3 2s1.2 1.8 3 2.1 3 .9 3 2.1-1.3 2-3 2c-1.2 0-2.3-.3-3.2-1M12 5.5v13" /></>,
    time: <><circle cx="12" cy="13" r="8" /><path d="M12 9v4l3 2M9 3h6" /></>,
  }[type];
  return <svg className="metric-icon" viewBox="0 0 24 24" aria-hidden="true">{content}</svg>;
}

function AttendanceIcon({ went }: { went: boolean }) {
  return went
    ? <svg className="attendance-icon" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="18" /><path d="m16 24 6 6 11-13" /></svg>
    : <svg className="attendance-icon" viewBox="0 0 48 48" aria-hidden="true"><rect x="8" y="11" width="32" height="29" rx="7" /><path d="M16 7v8M32 7v8M8 20h32m-20 7 8 8m0-8-8 8" /></svg>;
}

function JourneyProgress({ screen }: { screen: Screen }) {
  const position = journeyPositions[screen];
  return (
    <div className="journey-progress" aria-label={`Step ${position + 1} of 4`}>
      {journeySteps.map((step, index) => (
        <div className={index <= position ? "journey-step active" : "journey-step"} key={step}>
          <span>{index < position ? "✓" : index + 1}</span>
          <small>{step}</small>
        </div>
      ))}
    </div>
  );
}

export function HobbiDemo() {
  const [screen, setScreen] = useState<Screen>("login");
  const [health, setHealth] = useState<HealthView | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [selectedVibes, setSelectedVibes] = useState<Vibe[]>([]);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [shortlistResponse, setShortlistResponse] = useState<ShortlistStepResponse | null>(null);
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
  }, [screen]);

  const plan = planResponse?.plan ?? null;
  const requirements = planResponse?.approval_requirements ?? null;
  const booking = bookingResponse?.bookings?.[0] ?? null;
  const nextPlan = nextPlanResponse?.plan ?? null;
  const inJourney = ["plan", "details", "approval", "booked", "debrief", "adapted"].includes(screen);

  function toggleVibe(vibe: Vibe) {
    setSelectedVibes((current) =>
      current.includes(vibe) ? current.filter((item) => item !== vibe) : [...current, vibe],
    );
  }

  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (data.get("email") !== DEMO_EMAIL || data.get("password") !== DEMO_PASSWORD) {
      setError("Use the demo email and password shown below.");
      return;
    }
    setError(null);
    setScreen(profile ? "home" : "profile");
  }

  function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setProfile({
      display_name: String(data.get("display_name")),
      declared_age: Number(data.get("age")),
      goal: String(data.get("goal")),
      money_total_sgd: Number(data.get("budget")),
      hours_per_week: Number(data.get("hours")),
      tries_total: Number(data.get("tries")),
      max_travel_min: Number(data.get("travel")),
      cold_start_vibes: selectedVibes,
      parental_rules: verifiedOnly ? ["verified_only"] : [],
    });
    setError(null);
    setScreen("home");
  }

  async function createPlan(vibeOverride?: Vibe) {
    if (!profile) return;
    setBusy(true);
    setError(null);
    const { display_name: _displayName, ...savedProfile } = profile;
    const payload = vibeOverride
      ? { ...savedProfile, cold_start_vibes: [vibeOverride] }
      : savedProfile;
    try {
      const result = await demoRequest<ShortlistStepResponse>("/api/plan", payload);
      if (!result.options.length) throw new Error("No activities returned");
      setShortlistResponse(result);
      setPlanResponse(null);
      setScreen("plan");
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
      setScreen("booked");
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
      const result = await demoRequest<{ ok: boolean; adaptation: AdaptationView }>("/api/attendance", payload);
      setAdaptation(result.adaptation);
      setScreen("adapted");
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
      const result = await demoRequest<PlanStepResponse>("/api/next-plan", { teen_id: planResponse.teen_id });
      if (!result.plan || !result.approval_requirements) throw new Error("No next activity returned");
      setNextPlanResponse(result);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  function clearJourney() {
    setShortlistResponse(null);
    setPlanResponse(null);
    setBookingResponse(null);
    setAdaptation(null);
    setNextPlanResponse(null);
    setAttended(true);
    setDebrief("");
    setError(null);
  }

  function goHome() {
    clearJourney();
    setScreen("home");
  }

  function logout() {
    clearJourney();
    setProfile(null);
    setSelectedVibes([]);
    setVerifiedOnly(false);
    setScreen("login");
  }

  if (screen === "login") {
    return (
      <main className="login-page">
        <section className="login-art">
          <div className="login-wordmark">hobbi<span>.</span></div>
          <HobbiBuddy />
          <h1>Your next thing is out there.</h1>
        </section>
        <section className="login-panel">
          <form className="login-form" onSubmit={login}>
            <div><p className="screen-kicker">Welcome back</p><h2>Log in to Hobbi</h2></div>
            <label>Email<input name="email" type="email" autoComplete="email" placeholder="you@example.com" required /></label>
            <label>Password<input name="password" type="password" autoComplete="current-password" placeholder="Your password" required /></label>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <button className="action-button primary" type="submit">Log in</button>
            <div className="demo-login"><strong>Demo account</strong><span>{DEMO_EMAIL}</span><span>{DEMO_PASSWORD}</span></div>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="product-shell">
      <aside className="product-nav">
        <button className="nav-wordmark" type="button" onClick={goHome} aria-label="Hobbi home">hobbi<span>.</span></button>
        <nav aria-label="Main navigation">
          <button className={screen === "home" || inJourney ? "nav-item active" : "nav-item"} type="button" onClick={goHome} aria-current={screen === "home" ? "page" : undefined}><NavIcon name="home" /><span>Home</span></button>
          <button className={screen === "profile" ? "nav-item active" : "nav-item"} type="button" onClick={() => setScreen("profile")} aria-current={screen === "profile" ? "page" : undefined}><NavIcon name="profile" /><span>Profile</span></button>
        </nav>
        <button className="nav-item logout" type="button" onClick={logout}><NavIcon name="logout" /><span>Log out</span></button>
      </aside>

      <section className="product-main">
        <header className="mobile-header">
          <button className="nav-wordmark" type="button" onClick={goHome}>hobbi<span>.</span></button>
        </header>
        {inJourney ? <JourneyProgress screen={screen} /> : null}
        {error && screen !== "profile" ? <p className="page-error" role="alert">{error}</p> : null}

        {screen === "profile" ? <ProfileScreen profile={profile} selectedVibes={selectedVibes} verifiedOnly={verifiedOnly} onToggleVibe={toggleVibe} onVerifiedChange={setVerifiedOnly} onSave={saveProfile} /> : null}
        {screen === "home" && profile ? <HomeScreen profile={profile} health={health} busy={busy} onStart={() => createPlan()} onExplore={createPlan} onEdit={() => setScreen("profile")} /> : null}

        {screen === "plan" && shortlistResponse ? <ShortlistScreen options={shortlistResponse.options} onSelect={(option) => { setPlanResponse({ ok: true, teen_id: shortlistResponse.teen_id, outcome: option.outcome, plan: option.plan, approval_requirements: option.approval_requirements }); setScreen("details"); }} onBack={goHome} /> : null}

        {screen === "details" && plan ? (
          <section className="task-screen" key="details">
            <div className="task-heading"><p className="screen-kicker">Your pick</p><h1>Good choice</h1><p>Here’s everything you need before asking an adult.</p></div>
            <ActivityDetails activity={plan.activities[0]} />
            <div className="task-actions"><button className="action-button secondary" type="button" onClick={() => setScreen(shortlistResponse ? "plan" : "home")}>Back to picks</button><button className="action-button primary" type="button" onClick={() => setScreen("approval")}>Ask my adult</button></div>
          </section>
        ) : null}

        {screen === "approval" && plan && requirements ? (
          <section className="task-screen" key="approval">
            <div className="task-heading"><p className="screen-kicker">Adult check</p><h1>Is this okay?</h1><p>Review the activity before approving the demo booking.</p></div>
            <div className="adult-check-list">
              <CheckRow label="Organiser" value={plan.activities[0].organiser} />
              <CheckRow label="Location" value={plan.activities[0].venue_name} />
              <CheckRow label="Cost" value={Number(plan.total_cost_sgd) === 0 ? "Free" : `S$${Number(plan.total_cost_sgd).toFixed(2)}`} />
              <CheckRow label="Approval" value={requirements.provider_listing_ids?.length ? "Provider needs review" : "Verified organiser"} />
            </div>
            <a className="plain-link" href={plan.activities[0].source_url} target="_blank" rel="noreferrer">Open organiser page ↗</a>
            <div className="task-actions"><button className="action-button secondary" type="button" onClick={() => setScreen("details")}>Back</button><button className="action-button primary" type="button" onClick={approvePlan} disabled={busy}>{busy ? "Booking…" : "Approve as demo adult"}</button></div>
          </section>
        ) : null}

        {screen === "booked" && booking ? <BookedScreen booking={booking} onContinue={() => setScreen("debrief")} /> : null}

        {screen === "debrief" && booking ? (
          <section className="task-screen checkin-screen" key="debrief">
            <div className="task-heading"><p className="screen-kicker">Quick check-in</p><h1>How did it go?</h1></div>
            <form onSubmit={recordAttendance}>
              <div className="attendance-choice" role="group" aria-label="Attendance">
                <button className={attended ? "choice-button selected" : "choice-button"} type="button" onClick={() => setAttended(true)} aria-pressed={attended}><AttendanceIcon went /><span>I went</span></button>
                <button className={!attended ? "choice-button selected" : "choice-button"} type="button" onClick={() => setAttended(false)} aria-pressed={!attended}><AttendanceIcon went={false} /><span>I missed it</span></button>
              </div>
              <label className="debrief-field">Anything else?<textarea value={debrief} onChange={(event) => setDebrief(event.target.value)} maxLength={2000} placeholder="Optional" /></label>
              <div className="quick-replies">{["Loved it", "It was okay", "Not my thing"].map((reply) => <button className={debrief === reply ? "selected" : ""} type="button" key={reply} onClick={() => setDebrief(reply)} aria-pressed={debrief === reply}>{reply}</button>)}</div>
              <div className="task-actions"><button className="action-button primary full" type="submit" disabled={busy}>{busy ? "Saving…" : "Save check-in"}</button></div>
            </form>
          </section>
        ) : null}

        {screen === "adapted" && adaptation && plan ? (
          <section className="task-screen result-screen" key="adapted">
            {nextPlan ? (
              <><div className="task-heading"><p className="screen-kicker">Next up</p><h1>Try this next</h1></div><ActivityDetails activity={nextPlan.activities[0]} /><div className="task-actions"><button className="action-button secondary" type="button" onClick={goHome}>Home</button><button className="action-button primary" type="button" onClick={() => { setPlanResponse(nextPlanResponse); setNextPlanResponse(null); setBookingResponse(null); setAdaptation(null); setScreen("approval"); }}>Review activity</button></div></>
            ) : (
              <><HobbiBuddy small /><div className="task-heading centered"><p className="screen-kicker">Check-in saved</p><h1>{adaptation.action === "hold_this_week" ? "Take the week off" : "Got it!"}</h1><p>{adaptation.action === "hold_this_week" ? "Come back when your schedule clears up." : "Your next pick will use this feedback."}</p></div><div className="task-actions centered"><button className="action-button secondary" type="button" onClick={goHome}>Home</button>{adaptation.action !== "hold_this_week" ? <button className="action-button primary" type="button" onClick={revealNextPlan} disabled={busy}>{busy ? "Finding…" : "Find another activity"}</button> : null}</div></>
            )}
          </section>
        ) : null}
      </section>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        <button className={screen === "home" || inJourney ? "active" : ""} type="button" onClick={goHome}><NavIcon name="home" /><span>Home</span></button>
        <button className={screen === "profile" ? "active" : ""} type="button" onClick={() => setScreen("profile")}><NavIcon name="profile" /><span>Profile</span></button>
        <button type="button" onClick={logout}><NavIcon name="logout" /><span>Log out</span></button>
      </nav>
    </main>
  );
}

function ProfileScreen({ profile, selectedVibes, verifiedOnly, onToggleVibe, onVerifiedChange, onSave }: { profile: Profile | null; selectedVibes: Vibe[]; verifiedOnly: boolean; onToggleVibe: (vibe: Vibe) => void; onVerifiedChange: (checked: boolean) => void; onSave: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <section className="profile-screen">
      <div className="page-heading"><p className="screen-kicker">Your profile</p><h1>{profile ? "Update your picks" : "Make Hobbi yours"}</h1><p>Set what works for you. You can change this anytime.</p></div>
      <form className="profile-form" onSubmit={onSave}>
        <fieldset><legend>About you</legend><div className="field-grid two"><label>Name<input name="display_name" defaultValue={profile?.display_name ?? "Maya"} required maxLength={40} /></label><label>Age<input name="age" type="number" min="13" max="17" defaultValue={profile?.declared_age ?? 15} required /></label></div></fieldset>
        <fieldset><legend>What do you want to do?</legend><label className="goal-field"><input name="goal" defaultValue={profile?.goal ?? "Try something new after school"} required maxLength={500} /></label></fieldset>
        <fieldset><legend>Pick your vibe <small>Choose any</small></legend><div className="vibe-grid">{vibeOptions.map((vibe) => <button className={selectedVibes.includes(vibe.value) ? "vibe-button selected" : "vibe-button"} type="button" key={vibe.value} onClick={() => onToggleVibe(vibe.value)} aria-pressed={selectedVibes.includes(vibe.value)}><VibeIcon vibe={vibe.value} />{vibe.label}</button>)}</div></fieldset>
        <fieldset><legend>Your limits</legend><div className="field-grid limits"><label>Budget<input name="budget" type="number" min="0" step="1" defaultValue={profile?.money_total_sgd ?? 20} required /><small>S$ total</small></label><label>Time<input name="hours" type="number" min="0.5" max="40" step="0.5" defaultValue={profile?.hours_per_week ?? 2} required /><small>hours/week</small></label><label>Tries<input name="tries" type="number" min="1" max="12" defaultValue={profile?.tries_total ?? 3} required /><small>activities</small></label><label>Travel<input name="travel" type="number" min="5" max="120" step="5" defaultValue={profile?.max_travel_min ?? 45} required /><small>minutes max</small></label></div></fieldset>
        <label className="switch-row"><span><strong>Verified organisers only</strong><small>Hide organisers that still need an adult check.</small></span><input type="checkbox" checked={verifiedOnly} onChange={(event) => onVerifiedChange(event.target.checked)} /></label>
        <button className="action-button primary save-profile" type="submit">Save profile</button>
      </form>
    </section>
  );
}

function HomeScreen({ profile, health, busy, onStart, onExplore, onEdit }: { profile: Profile; health: HealthView | null; busy: boolean; onStart: () => void; onExplore: (vibe: Vibe) => void; onEdit: () => void }) {
  return (
    <section className="home-screen">
      <header className="home-heading"><div><p className="screen-kicker">Hey {profile.display_name}!</p><h1>What should we try?</h1></div></header>

      <div className="home-primary-grid">
        <div className="quest-panel"><div><span className="quest-label">READY WHEN YOU ARE</span><h2>Find your next activity</h2><p>{profile.goal}</p><button className="action-button primary" type="button" onClick={onStart} disabled={busy}>{busy ? "Finding a match…" : "Find an activity"}</button></div><HobbiBuddy small /></div>
        <aside className="profile-card">
          <div className="profile-card-heading"><div><p className="screen-kicker">Your profile</p><h2>{profile.cold_start_vibes?.length ? "Your picks" : "Surprise me"}</h2></div><button className="text-button" type="button" onClick={onEdit}>Edit</button></div>
          <div className="profile-vibes">{profile.cold_start_vibes?.length ? profile.cold_start_vibes.map((vibe) => <span key={vibe}><VibeIcon vibe={vibe} />{vibeOptions.find((item) => item.value === vibe)?.label}</span>) : <p>Any vibe works</p>}</div>
          <div className="profile-constraints"><span><strong>{profile.max_travel_min} min</strong> max travel</span><span><strong>{profile.parental_rules?.includes("verified_only") ? "Verified" : "Flexible"}</strong> organisers</span></div>
          <p className={health?.ready_for_real_planning ? "catalogue-status ready" : "catalogue-status"}><span />{health?.ready_for_real_planning ? `${health.real_activities} activities ready` : "Checking activities"}</p>
        </aside>
      </div>

      <div className="stats-row" aria-label="Your activity limits"><div><MetricIcon type="tries" /><strong>{profile.tries_total}</strong><small>tries left</small></div><div><MetricIcon type="budget" /><strong>S${profile.money_total_sgd}</strong><small>budget</small></div><div><MetricIcon type="time" /><strong>{profile.hours_per_week}h</strong><small>per week</small></div></div>

      <section className="explore-section">
        <div className="section-heading"><div><p className="screen-kicker">Quick start</p><h2>Explore by vibe</h2></div><p>Pick one for this search.</p></div>
        <div className="explore-grid">{vibeOptions.map((vibe) => <button className={`explore-tile ${vibe.value}`} type="button" key={vibe.value} onClick={() => onExplore(vibe.value)} disabled={busy}><VibeIcon vibe={vibe.value} /><span><strong>{vibe.label}</strong><small>{vibe.note}</small></span><b aria-hidden="true">→</b></button>)}</div>
      </section>
    </section>
  );
}

function ShortlistScreen({ options, onSelect, onBack }: { options: PlanOptionView[]; onSelect: (option: PlanOptionView) => void; onBack: () => void }) {
  return (
    <section className="task-screen shortlist-screen" key="plan">
      <div className="task-heading"><p className="screen-kicker">Your matches</p><h1>Try this next</h1><p>We found {options.length} activities that fit. Pick one to see the full details.</p></div>
      <div className="shortlist" aria-label="Activity matches">
        {options.map((option, index) => {
          const activity = option.plan.activities[0];
          return (
            <button className={index === 0 ? "shortlist-item top-pick" : "shortlist-item"} type="button" key={option.plan.plan_id} onClick={() => onSelect(option)}>
              <span className="shortlist-rank">{index + 1}</span>
              <span className="shortlist-copy">
                <span className="shortlist-label">{index === 0 ? "Top pick" : activity.commitment.replace("_", " ")}</span>
                <strong>{activity.title}</strong>
                <small>{activity.venue_name} · {activity.nearest_mrt ? `${activity.nearest_mrt} MRT` : activity.planning_area}</small>
                <span className="shortlist-meta"><span>{formatShortlistTime(activity)}</span><span>{activity.duration_hours}h</span><span>{formatShortlistCost(activity.cost_sgd)}</span></span>
              </span>
              <span className="shortlist-action">View <span aria-hidden="true">→</span></span>
            </button>
          );
        })}
      </div>
      <div className="task-actions"><button className="action-button secondary" type="button" onClick={onBack}>Back home</button></div>
    </section>
  );
}

function CheckRow({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function BookedScreen({ booking, onContinue }: { booking: BookingView; onContinue: () => void }) {
  return (
    <section className="task-screen booked-screen" key="booked">
      <div className="success-mark" aria-hidden="true">✓</div>
      <div className="task-heading centered"><p className="screen-kicker">Demo booking</p><h1>Nice, you’re in!</h1><p>No provider was contacted and no payment was made.</p></div>
      <div className="booking-ticket"><div><span>Activity</span><strong>{booking.activity.title}</strong></div><div><span>Meet at</span><strong>{booking.preparation.meet}</strong></div><div><span>Bring</span><strong>{booking.preparation.bring}</strong></div></div>
      <div className="task-actions centered"><button className="action-button primary" type="button" onClick={onContinue}>Check in after activity</button></div>
    </section>
  );
}
