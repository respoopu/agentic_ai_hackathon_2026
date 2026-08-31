#!/usr/bin/env python3
"""Draft seed-CKB rows from NLB's public events API, filtered to ages 13-17.

    python3 scripts/fetch_nlb_teen_events.py                  # all libraries
    python3 scripts/fetch_nlb_teen_events.py --area "Toa Payoh,Bishan"
    python3 scripts/fetch_nlb_teen_events.py --out data/draft_nlb.csv

nlb.gov.sg is a JavaScript shell that returns nothing to a fetcher. Its events
actually live on nlb.libcal.com, which serves structured JSON and — crucially —
lets you filter on audience 2280, NLB's own "Teenagers (13-17 yo)" tag. That is
the exact cohort in D7, tagged by the provider rather than inferred by us.

What this script is and is not
------------------------------
It is a TYPING SAVER. Every row it writes comes from a field in the API
response, and every row carries the real event URL. Nothing is inferred from a
model's memory.

It is NOT verification. Rows are written as `verification=unverified` with
`verified_at` blank on purpose, so scripts/build_ckb.py will refuse them until
a human opens the link and fills in their name and the date. That is the whole
discipline of this task and the script must not be the thing that breaks it.

Columns it cannot know are left blank for the human: postal_code,
beginner_friendly, join_alone_ok, guest_allowed. Build a library -> postal code
map once and those are a few seconds each.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_ckb import COLUMNS  # noqa: E402

API = "https://nlb.libcal.com/ajax/calendar/list"
TEEN_AUDIENCE_ID = 2280  # NLB's own "Teenagers (13-17 yo)" tag
CALENDAR_ID = 11498
PER_PAGE = 100

# NLB's category strings -> our four coverage vibes. Only used for auditing
# coverage of the seed set; never shown to a teen, never used to filter (A9).
VIBE_HINTS = {
    "technology": "explorative",
    "science": "explorative",
    "nature": "explorative",
    "history": "explorative",
    "heritage": "explorative",
    "career": "explorative",
    "art": "artistic",
    "craft": "artistic",
    "music": "artistic",
    "writing": "artistic",
    "literary": "artistic",
    "reading": "chill",
    "wellness": "chill",
    "health": "chill",
    "sport": "sporty",
    "fitness": "sporty",
    "dance": "sporty",
}


def fetch_page(page: int) -> dict:
    params = {
        "c": CALENDAR_ID,
        "date": "0000-00-00",
        "perpage": PER_PAGE,
        "page": page,
        "audience": TEEN_AUDIENCE_ID,
        "cats": "",
        "camps": "",
        "inc": 0,
    }
    req = urllib.request.Request(
        f"{API}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; hobbi-ckb/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_all() -> list[dict]:
    first = fetch_page(1)
    total = int(first.get("total_results", 0))
    events = list(first.get("results", []))
    page = 2
    while len(events) < total and page < 20:
        more = fetch_page(page).get("results", [])
        if not more:
            break
        events.extend(more)
        page += 1
    return events


def is_teen_tagged(event: dict) -> bool:
    """The API filter is generous. Confirm the tag is actually on the record."""
    return any(a.get("id") == TEEN_AUDIENCE_ID for a in event.get("audiences") or [])


def vibes_for(event: dict) -> str:
    cats = (event.get("categories") or "").lower() + " " + (event.get("title") or "").lower()
    hits = {v for k, v in VIBE_HINTS.items() if k in cats}
    return "|".join(sorted(hits)) or "explorative"  # a library default a human can correct


def to_row(event: dict, seq: int) -> dict:
    start = event.get("startdt") or ""
    try:
        when = datetime.fromisoformat(start).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        when = ""

    # An empty registration_cost is how libcal renders a free event, but it is
    # also how it renders one that simply did not fill the field in. Zero here,
    # flagged in notes, confirmed by the human who opens the link.
    cost = (event.get("registration_cost") or "").strip()
    cost_note = "" if not cost else f"page shows cost {cost!r} — CHECK"

    return {
        "listing_id": f"NLB-{seq:03d}",
        "title": (event.get("title") or "").strip(),
        "provider": "National Library Board",
        "provider_type": "third_space",
        "source_url": event.get("url") or "",
        "verified_at": "",  # deliberately blank — a human fills this
        "verified_by": "",  # and this
        "verification": "unverified",
        "cost_one_off_sgd": "0" if not cost else "",
        "cost_recurring_sgd": "0",
        "equipment_cost_sgd": "0",
        "venue_name": (event.get("location") or event.get("campus") or "").strip(),
        "postal_code": "",  # human: build a library -> postal map once
        "planning_area": "",  # human: from the campus name
        "nearest_mrt": "",
        "age_min": "13",  # from NLB's own Teenagers (13-17 yo) tag
        "age_max": "17",
        "beginner_friendly": "",  # human: read the description
        "join_alone_ok": "",
        "guest_allowed": "",
        "commitment": "one_off",
        "schedule_kind": "fixed_dates",
        "weekday": "",
        "start_time": "",
        "duration_min": "",
        "first_session": "",
        "num_sessions": "",
        "fixed_dates": when,
        "open_hours_note": "",
        "vibes": vibes_for(event),
        "in_incumbent_directory": "no",
        "notes": " · ".join(
            x for x in [
                f"campus: {event.get('campus') or '?'}",
                f"categories: {event.get('categories') or '?'}",
                cost_note,
                "DRAFT from libcal API — open the link and verify before using",
            ] if x
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--area", help="comma-separated campus filter, e.g. 'Toa Payoh,Bishan'")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "draft_nlb.csv")
    ap.add_argument("--include-past", action="store_true")
    args = ap.parse_args()
    args.out = args.out.resolve()

    print("  fetching nlb.libcal.com, audience = Teenagers (13-17 yo)...")
    events = [e for e in fetch_all() if is_teen_tagged(e)]
    print(f"  {len(events)} teen-tagged events islandwide")

    if args.area:
        wanted = [a.strip().lower() for a in args.area.split(",")]
        events = [
            e for e in events
            if any(w in (e.get("campus") or "").lower() for w in wanted)
        ]
        print(f"  {len(events)} after area filter ({args.area})")

    if not args.include_past:
        now = datetime.now()
        kept = []
        for e in events:
            try:
                if datetime.fromisoformat(e.get("startdt") or "") >= now:
                    kept.append(e)
            except ValueError:
                pass
        dropped = len(events) - len(kept)
        events = kept
        print(f"  {len(events)} still upcoming ({dropped} already past, dropped)")

    events.sort(key=lambda e: e.get("startdt") or "")
    rows = [to_row(e, i) for i, e in enumerate(events, start=1)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    by_campus: dict[str, int] = {}
    for e in events:
        by_campus[e.get("campus") or "?"] = by_campus.get(e.get("campus") or "?", 0) + 1

    print(f"\n  wrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out} — {len(rows)} draft rows\n")
    for campus, n in sorted(by_campus.items(), key=lambda kv: -kv[1]):
        print(f"    {n:3}  {campus}")

    print(
        "\n  These are DRAFTS. Every row is verification=unverified with no\n"
        "  verified_at, so build_ckb.py will reject them until a human opens\n"
        "  the link. Fill postal_code, planning_area, beginner_friendly,\n"
        "  join_alone_ok and guest_allowed, confirm the cost, then set\n"
        "  verification=verified with your name and today's date.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
