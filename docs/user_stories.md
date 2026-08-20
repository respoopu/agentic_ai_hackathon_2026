# User Stories — Hobbi

*Grouped by user category. Each row: story, what Hobbi needs to know, and the feature it implies. See [project_brief.md](./project_brief.md) for the full product context and hard constraints referenced below.*

---

## Teen — Discovery & Personalization

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a teen, I want to discover hobbies that suit me because I don't know what I would enjoy.** | Interests, personality, indoor/outdoor preference, solo/social preference | AI hobby recommender |
| **As a teen, I want recommendations to improve when I tell Hobbi what I liked or disliked.** | Likes/dislikes, clicks, attendance | Feedback-based recommendations |

> ⚠️ "Personality" input must never become left-brain/right-brain or MBTI-style typing — this is a **hard, non-negotiable constraint** (project_brief.md §6). Use non-stigmatising preference signals (indoor/outdoor, team/solo, contact/non-contact, high/low intensity, competitive/social) instead of a fixed personality label. Feedback should also favour *revealed* (behavioural) preference over self-report where possible (§3, §11).

---

## Teen — Practical Filters

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a teen, I want hobbies within my budget so I don't get recommended things I can't afford.** | One-time cost, recurring cost, equipment cost, budget | Budget filter + estimated cost |
| **As a teen, I want activities that fit my schedule.** | Free days, available times, school commitments | Availability matching |
| **As a teen, I want groups near me so travelling isn't a pain.** | General location, maximum travel time/distance | Location + travel-time filtering |
| **As a teen, I want to meet people around my age so I don't end up in a group of 40-year-olds.** | Participant age range | Age-range filtering |

> ⚠️ Budget filtering must support **S$0** as a fully viable input, not an edge case (§4 — "the agent must produce a viable plan at S$0").

---

## Teen — Confidence & First-Timers

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a beginner, I want groups that welcome beginners so I don't feel embarrassed joining.** | Experience level, group requirements | Beginner-friendly indicator |
| **As someone joining alone, I want to know how welcoming a group is to newcomers.** | Whether people usually join alone, newcomer process | "Good for first-timers" badge |
| **As a shy teen, I want to know what will happen before I arrive so I feel less anxious.** | Meeting format, group size, meeting point, activities | "What to expect" preview |
| **As a teen, I want to know exactly what I need before joining.** | Equipment, clothing, skill prerequisites | Preparation checklist |
| **As a teen, I want to bring a friend if I'm uncomfortable attending alone.** | Whether groups allow guests | Invite/share with friend |

---

## Teen — Decision Support

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a teen, I want to try a hobby without committing lots of money.** | Trial sessions, rentals, free groups | "Try it first" / low-commitment filter |
| **As a teen, I want to see actual upcoming sessions rather than just reading about a hobby.** | Group calendars/events | Upcoming events feed |
| **As a teen, I want to save interesting hobbies and come back later.** | User favourites | Saved hobbies/groups |
| **As a teen, I want to compare different activities before deciding.** | Cost, distance, time, social level, equipment | Hobbi comparison |

> The "try it first" filter is the product surface for the loop's explore phase: cheapest experiments first, before term-long commitments (§3).

---

## Teen — Trust Signals

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a teen, I want to know whether a group is active before travelling there.** | Recent posts/events/activity | Activity/last-verified indicator |
| **As a teen, I want to know whether the information is trustworthy.** | Source, verification date | Source attribution + verified listing |

---

## Parent

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As a parent, I want to understand where my child is going and who is running the activity.** | Organizer identity, venue, timings, contact | Organizer/venue information |
| **As a parent, I want potentially unsafe activities or groups to be flagged.** | Moderation signals, venue type, organizer verification | Safety/moderation system |

> Safety/moderation is the mandatory vetting-queue requirement for unverified providers — a **hard, non-negotiable constraint** (§6). An unverified private provider must never be surfaced directly to the youth; it goes to a trusted adult for approval first.

---

## Hobbi (the Platform)

| User story | What Hobbi needs to know | Feature this implies |
|---|---|---|
| **As Hobbi, we want to detect outdated groups so users aren't sent to dead Telegram/Instagram communities.** | Last activity, link validity, event recency | Automated freshness checking |
