import type { ActivityPlanView } from "@/lib/contracts";

function formatMoney(value: number | string): string {
  const amount = Number(value);
  return amount === 0 ? "Free" : `S$${amount.toFixed(2)}`;
}

function formatSession(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    weekday: "long",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
}

export function ActivityDetails({
  activity,
  compact = false,
}: {
  activity: ActivityPlanView;
  compact?: boolean;
}) {
  return (
    <article className={compact ? "activity-sheet compact" : "activity-sheet"}>
      <div className="activity-heading">
        <div>
          <p className="eyebrow">{activity.commitment.replace("_", " ")} · first try</p>
          <h2>{activity.title}</h2>
        </div>
        <p className="activity-price">{formatMoney(activity.cost_sgd)}</p>
      </div>

      <dl className="activity-facts">
        <div>
          <dt>When</dt>
          <dd>
            {activity.session_flexible
              ? activity.schedule_note ?? "Flexible drop-in hours"
              : formatSession(activity.session_at)}
          </dd>
        </div>
        <div>
          <dt>Where</dt>
          <dd>
            {activity.venue_name}, {activity.planning_area}
            {activity.nearest_mrt ? ` · near ${activity.nearest_mrt} MRT` : ""}
          </dd>
        </div>
        <div>
          <dt>Organiser</dt>
          <dd>{activity.organiser}</dd>
        </div>
        <div>
          <dt>Session</dt>
          <dd>
            {activity.duration_hours} {activity.duration_hours === 1 ? "hour" : "hours"} · ages{" "}
            {activity.age_min}–{activity.age_max}
          </dd>
        </div>
      </dl>

      <div className="trust-line" aria-label="Activity trust and welcome signals">
        <span>{activity.beginner_friendly ? "Beginner-friendly" : "Some experience needed"}</span>
        <span>{activity.join_alone_ok ? "Good for going solo" : "Bring someone you know"}</span>
        <span className={activity.verification === "verified" ? "verified" : "review"}>
          {activity.verification === "verified" ? "Human-verified" : "Adult review needed"}
        </span>
      </div>

      <a className="source-link" href={activity.source_url} target="_blank" rel="noreferrer">
        View organiser source <span aria-hidden="true">↗</span>
      </a>
    </article>
  );
}
