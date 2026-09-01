#!/usr/bin/env python3
"""Draft seed-CKB rows from ActiveSG's free-to-play facility directory.

    python3 scripts/fetch_activesg_free_play.py                    # all zones
    python3 scripts/fetch_activesg_free_play.py --zone West,Northeast
    python3 scripts/fetch_activesg_free_play.py --out data/draft_ftp.csv

Every area sweep found the same thing: free *programmes* for teens barely
exist, and the real free supply is space — school fields opened to the public
under the Dual Use Scheme, stadium tracks, courts. These rows come from an
ActiveSG directory and therefore do not count as absent from incumbent
directories for B9, even when other activity directories omit them.

activesgcircle.gov.sg serves this server-rendered (unlike activesg.gov.sg,
which 403s everything). The zone-filtered listing page carries names and
addresses; opening hours are on each detail page, so those are fetched
serially with a delay. The site did not rate-limit during development, but
there is no reason to hammer it.

Same discipline as the NLB fetcher: rows are drafts. verification=unverified,
verified_at blank, and age left empty because these pages do not state one.
build_ckb.py will refuse them until a human signs for them.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_ckb import COLUMNS  # noqa: E402

BASE = "https://www.activesgcircle.gov.sg"
LISTING = BASE + "/facilities/free-to-play"
ZONES = ["Central", "East", "North", "Northeast", "West"]
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
)
SKIP_SLUGS = {"free-to-play", "individual-rates", "swimming-pools", "search"}
DAYS = {
    "mon": "mon",
    "tue": "tue",
    "wed": "wed",
    "thu": "thu",
    "fri": "fri",
    "sat": "sat",
    "sun": "sun",
}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_listing(page: str, zone: str) -> list[dict]:
    """Each facility is a `cst-con-grp` block: link, <h2> name, address."""
    out = []
    for block in page.split('<div class="cst-con-grp">')[1:]:
        m = re.search(
            r'href="(' + re.escape(BASE) + r'/facilities/([a-z0-9\-]+))"', block
        )
        if not m or m.group(2) in SKIP_SLUGS:
            continue
        name = re.search(r"<h2>(.*?)</h2>", block, re.S)
        addr = re.search(r'<div class="cst-address">(.*?)</div>', block, re.S)
        address = strip_tags(addr.group(1)) if addr else ""
        postal = re.search(r"Singapore\s+(\d{6})", address)
        out.append(
            {
                "url": m.group(1),
                "slug": m.group(2),
                "name": strip_tags(name.group(1)) if name else m.group(2),
                "address": address,
                "postal": postal.group(1) if postal else "",
                "zone": zone,
            }
        )
    # the listing repeats cards in some layouts; keep first occurrence of each slug
    seen, unique = set(), []
    for f in out:
        if f["slug"] not in seen:
            seen.add(f["slug"])
            unique.append(f)
    return unique


def parse_hours(detail: str) -> str:
    """Free-text hours note. These pages write hours a dozen ways; don't parse,
    transcribe. The schema takes drop_in hours as a note for exactly this reason."""
    txt = strip_tags(
        re.sub(r"<script.*?</script>|<style.*?</style>", " ", detail, flags=re.S)
    )
    windows = re.findall(
        r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*(?:\s*(?:-|–|to|&|and)\s*"
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*)?\s*:?\s*"
        r"\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)\s*(?:-|–|to)\s*\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm))",
        txt,
        re.I,
    )
    seen, kept = set(), []
    for w in windows:
        k = re.sub(r"\s+", " ", w).strip()
        if k.lower() not in seen:
            seen.add(k.lower())
            kept.append(k)
    return "; ".join(kept)


def to_row(f: dict, hours: str) -> dict:
    is_school = "school" in f["name"].lower()
    flags = []
    if not hours:
        flags.append("HOURS NOT FOUND — read the page")
    if not f["postal"]:
        flags.append("POSTAL NOT ON PAGE")
    flags.append("age not stated on page — decide and fill")
    flags.append("DRAFT from activesgcircle free-to-play — verify before using")

    return {
        "listing_id": f"FTP-{f['slug']}",
        "title": f["name"],
        "provider": "Sport Singapore (ActiveSG)",
        # A school field opened to the public is the `school` provider type;
        # a stadium track or court is `informal`.
        "provider_type": "school" if is_school else "informal",
        "source_url": f["url"],
        "verified_at": "",
        "verified_by": "",
        "verification": "unverified",
        "cost_one_off_sgd": "0",  # the whole category is "free to play"
        "cost_recurring_sgd": "0",
        "equipment_cost_sgd": "0",
        "venue_name": f["name"],
        "postal_code": f["postal"],
        "planning_area": "",  # human: from the address
        "nearest_mrt": "",
        "age_min": "",  # not stated on these pages. Do not guess.
        "age_max": "",
        # The directory does not state participation rules. Leave them for the
        # human verifier rather than manufacturing A3-friendly answers.
        "beginner_friendly": "",
        "join_alone_ok": "",
        "guest_allowed": "",
        "commitment": "taster",
        "schedule_kind": "drop_in",
        "weekday": "",
        "start_time": "",
        "duration_min": "",
        "first_session": "",
        "num_sessions": "",
        "fixed_dates": "",
        "open_hours_note": hours,
        "vibes": "sporty",
        "in_incumbent_directory": "yes",  # sourced from ActiveSG's own directory
        "notes": f"zone: {f['zone']} · {f['address']} · " + " · ".join(flags),
        # Do not infer evaluation fields from category membership. A human
        # reads the captured hours and records both booleans explicitly.
        "weekday_evening_available": "",
        "weekend_available": "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zone", help=f"comma-separated, from {ZONES}")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "draft_free_play.csv")
    ap.add_argument(
        "--delay", type=float, default=1.0, help="seconds between detail fetches"
    )
    ap.add_argument("--force", action="store_true", help="overwrite --out")
    args = ap.parse_args()
    args.out = args.out.resolve()

    if args.out.exists() and not args.force:
        print(f"refusing to overwrite {args.out}; pass --force after reviewing it")
        return 1

    zones = [z.strip() for z in args.zone.split(",")] if args.zone else ZONES

    facilities: list[dict] = []
    for z in zones:
        try:
            page = get(f"{LISTING}?activesg_zone={z}")
        except Exception as e:  # noqa: BLE001
            print(f"  {z}: could not fetch listing ({type(e).__name__})")
            continue
        found = parse_listing(page, z)
        facilities.extend(found)
        print(f"  {z}: {len(found)} facilities")

    print(f"\n  fetching {len(facilities)} detail pages for opening hours...")
    rows = []
    for f in facilities:
        try:
            hours = parse_hours(get(f["url"]))
        except Exception as e:  # noqa: BLE001
            print(f"    {f['slug']}: {type(e).__name__}")
            hours = ""
        rows.append(to_row(f, hours))
        time.sleep(args.delay)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    with_hours = sum(1 for r in rows if r["open_hours_note"])
    with_postal = sum(1 for r in rows if r["postal_code"])
    schools = sum(1 for r in rows if r["provider_type"] == "school")
    display_path = (
        args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    )
    print(f"\n  wrote {display_path} — {len(rows)} draft rows")
    print(f"    {with_hours}/{len(rows)} have opening hours")
    print(f"    {with_postal}/{len(rows)} have a postal code")
    print(
        f"    {schools} school fields (provider_type=school), "
        f"{len(rows) - schools} other free facilities"
    )
    print(
        "\n  DRAFTS. age_min/age_max are deliberately blank — these pages do not\n"
        "  state an age and guessing one is what this whole task is trying to\n"
        "  avoid. Fill age, planning_area, and sign for each row.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
