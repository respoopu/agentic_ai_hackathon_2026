#!/usr/bin/env python3
"""Select a geographically concentrated, hobby-diverse CKB review shortlist.

This script selects candidates for human review; it does not promote or verify
them. Geography is derived from explicit row text or a small reviewed mapping.
Local-channel provenance is only an ``area_hint`` and is never represented as a
confirmed URA planning area.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "data" / "ckb_review_queue.csv"
DEFAULT_OUT = ROOT / "data" / "ckb_shortlist.csv"
AS_OF = date(2026, 9, 2)

AREA_QUOTAS = {"Jurong West": 25, "Punggol": 10, "Bishan": 10}
SUPPLEMENTAL_IDS = {"WEB-luggage-market"}
SOURCE_QUOTAS = {
    "Jurong West": {
        "public_telegram_candidate": 10,
        "merged_nlb_draft": 2,
        "merged_activesg_draft": 3,
        "public_web_candidate": 10,
    },
    "Punggol": {
        "public_telegram_candidate": 0,
        "merged_nlb_draft": 6,
        "merged_activesg_draft": 4,
    },
    "Bishan": {
        "public_telegram_candidate": 3,
        "merged_nlb_draft": 2,
        "merged_activesg_draft": 1,
        "public_web_candidate": 4,
    },
}

EXPLICIT_AREA_PATTERNS = {
    "Jurong West": (
        r"\bjurong west\b",
        r"\bgek poh\b",
        r"\bboon lay\b",
        r"\bjurong spring\b",
        r"\bpioneer mrt\b",
    ),
    "Punggol": (
        r"\bone punggol\b",
        r"\bpunggol (?:coast|place|drive|field|way|waterway|library)\b",
    ),
    "Bishan": (r"\bbishan\b", r"\b579799\b", r"\b579778\b"),
    "Kallang": (r"\baperia mall\b", r"\b339511\b", r"\bkallang avenue\b"),
}

# Source pages do not expose URA planning areas. These exact facility mappings
# are review aids based on their names/addresses; humans still confirm them.
FACILITY_AREA_HINTS = {
    "Xingnan Primary School Field": "Jurong West",
    "Yuhua Secondary School Field": "Jurong West",
    "Lakeside Primary School Field": "Jurong West",
    "Punggol Cove Primary School Field": "Punggol",
    "Punggol View Primary School Field": "Punggol",
    "Waterway Primary School Field": "Punggol",
    "Northshore Primary School Field": "Punggol",
    "Horizon Primary School Field": "Punggol",
    "Ai Tong School Field": "Bishan",
}

LOCAL_CHANNEL_HINTS = {
    "OneBoonLay": "Jurong West",
    "Gek Poh Central Residents' Network": "Jurong West",
    "Bishan Connects": "Bishan",
    "Alpha Fitness Workouts": "Punggol",
}

HOBBY_PATTERNS = {
    "sporty": re.compile(
        r"\b(?:sport|fitness|walk|cycling|cycle|ride|dance|football|basketball|"
        r"bowl|swim|field|workout|pickleball|badminton|run|zumba|pilates)\b",
        re.IGNORECASE,
    ),
    "artistic": re.compile(
        r"\b(?:art|craft|music|performance|dance|poetry|sewing|paint|concert|"
        r"crochet|design|photography|film|sing|theatre|lantern)\b",
        re.IGNORECASE,
    ),
    "chill": re.compile(
        r"\b(?:cafe|coffee|book|puzzle|movie|screening|thrift|swap|market|"
        r"mind café|games?|festival|garden|reading)\b",
        re.IGNORECASE,
    ),
    "explorative": re.compile(
        r"\b(?:nature|garden|coding|technology|workshop|volunteer|tour|farm|"
        r"robot|3d|laser|heritage|sustainab|community|leadership)\b",
        re.IGNORECASE,
    ),
}

NON_HOBBY_PATTERN = re.compile(
    r"\b(?:job opportunities|job fair|career fair|health screening|pharmacy health|"
    r"medicine review|cost-of-living|cash payout|collect .*flag|licen[cs]e application|"
    r"renewal of vows|parenting workshop|exam care pack|data protection act|pdpa talk|"
    r"cancer awareness|seniors? 50 years)\b",
    re.IGNORECASE,
)

OUTSIDE_TARGET_VENUE_PATTERN = re.compile(
    r"\b(?:marina barrage|gardens? by the bay|sembawang hot spring park)\b",
    re.IGNORECASE,
)

KNOWN_UNAVAILABLE_IDS = {
    # The official page states "This facility is not available" (checked 2 Sep
    # 2026). Exclusion is safe; it does not claim human verification.
    "FTP-punggol-view-primary-school-field",
}

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

SHORTLIST_COLUMNS = [
    "selection_rank",
    "proposed_area",
    "area_evidence",
    "hobby_buckets",
    "automated_flags",
    "candidate_id",
    "source_kind",
    "source_name",
    "source_url",
    "registration_urls",
    "title_hint",
    "provider_hint",
    "venue_hint",
    "postal_hint",
    "date_hints",
    "time_hints",
    "cost_hints",
    "age_hints",
    "excerpt_or_notes",
    "missing_for_ckb",
    "review_decision",
    "confirmed_title",
    "confirmed_provider",
    "confirmed_provider_type",
    "confirmed_venue",
    "confirmed_postal_code",
    "confirmed_planning_area",
    "confirmed_nearest_mrt",
    "confirmed_cost_one_off_sgd",
    "confirmed_cost_recurring_sgd",
    "confirmed_equipment_cost_sgd",
    "confirmed_age_min",
    "confirmed_age_max",
    "confirmed_beginner_friendly",
    "confirmed_join_alone_ok",
    "confirmed_guest_allowed",
    "confirmed_commitment",
    "confirmed_schedule_kind",
    "confirmed_weekday",
    "confirmed_start_time",
    "confirmed_duration_min",
    "confirmed_first_session",
    "confirmed_num_sessions",
    "confirmed_fixed_dates",
    "confirmed_open_hours_note",
    "confirmed_weekday_evening_available",
    "confirmed_weekend_available",
    "confirmed_vibes",
    "confirmed_in_incumbent_directory",
    "reviewed_at",
    "reviewed_by",
    "review_notes",
]


def infer_area(row: dict[str, str]) -> tuple[str | None, str]:
    text = " ".join(
        row.get(field, "")
        for field in (
            "title_hint",
            "venue_hint",
            "postal_hint",
            "excerpt_or_notes",
        )
    ).lower()
    for area, patterns in EXPLICIT_AREA_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return area, "explicit row text; human must confirm URA boundary"
    facility = FACILITY_AREA_HINTS.get(row.get("venue_hint", ""))
    if facility:
        return facility, "reviewed facility mapping; human must confirm"
    channel = LOCAL_CHANNEL_HINTS.get(row.get("source_name", ""))
    if channel:
        return channel, "local source-channel hint only; venue may differ"
    return None, "no target-area evidence"


def hobby_buckets(row: dict[str, str]) -> list[str]:
    text = " ".join(
        row.get(field, "")
        for field in ("title_hint", "topic_hints", "excerpt_or_notes")
    )
    buckets = [name for name, pattern in HOBBY_PATTERNS.items() if pattern.search(text)]
    return buckets or ["unclassified"]


def _parse_hint_dates(value: str) -> list[date]:
    parsed: list[date] = []
    for iso in re.findall(r"\b20\d{2}-\d{2}-\d{2}", value):
        try:
            parsed.append(date.fromisoformat(iso))
        except ValueError:
            pass
    pattern = re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(20\d{2}|\d{2}))?\b"
    )
    for day_value, month_value, year_value in pattern.findall(value):
        month = MONTHS.get(month_value.lower())
        if month is None:
            continue
        year = int(year_value) if year_value else AS_OF.year
        if year < 100:
            year += 2000
        try:
            parsed.append(date(year, month, int(day_value)))
        except ValueError:
            pass
    return parsed


def automated_flags(row: dict[str, str], area_evidence: str) -> list[str]:
    text = f"{row.get('title_hint', '')} {row.get('excerpt_or_notes', '')}".lower()
    flags: list[str] = []
    if any(
        term in text for term in ("sold out", "registration has closed", "cancelled")
    ):
        flags.append("closed_or_cancelled_text")
    if NON_HOBBY_PATTERN.search(text):
        flags.append("not_a_hobby_activity")
    if OUTSIDE_TARGET_VENUE_PATTERN.search(text):
        flags.append("venue_outside_proposed_area")
    if row.get("candidate_id") in KNOWN_UNAVAILABLE_IDS:
        flags.append("official_source_says_unavailable")
    if not _age_overlaps_target(row.get("age_hints", "")):
        flags.append("stated_age_outside_13_17")
    dates = _parse_hint_dates(row.get("date_hints", ""))
    if dates and max(dates) < AS_OF:
        flags.append("all_detected_dates_expired")
    elif not dates:
        flags.append("date_requires_confirmation")
    if not row.get("age_hints", ""):
        flags.append("age_requires_confirmation")
    if not row.get("cost_hints", ""):
        flags.append("cost_requires_confirmation")
    if "hint only" in area_evidence:
        flags.append("area_is_source_hint_only")
    return flags


def _age_overlaps_target(value: str) -> bool:
    lowered = value.lower()
    if not value or "all ages" in lowered or "everyone" in lowered:
        return True
    numbers = [int(number) for number in re.findall(r"\d{1,3}", value)]
    if not numbers:
        return True
    age_min = min(numbers)
    age_max = 120 if re.search(r"\b(?:and above|or older|\+)\b", lowered) else max(numbers)
    return age_min <= 17 and age_max >= 13


def candidate_score(row: dict[str, str], flags: list[str], area_evidence: str) -> int:
    score = int(row.get("priority_score") or 0)
    score += 5 if "explicit row text" in area_evidence else 2
    score += 3 if row.get("age_hints") else 0
    score += 2 if row.get("cost_hints") else 0
    score += 1 if row.get("registration_urls") else 0
    score -= 20 if "closed_or_cancelled_text" in flags else 0
    score -= 20 if "all_detected_dates_expired" in flags else 0
    return score


def load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    prepared: list[dict[str, str]] = []
    for row in rows:
        area, area_evidence = infer_area(row)
        if area is None:
            continue
        buckets = hobby_buckets(row)
        flags = automated_flags(row, area_evidence)
        disqualifying = {
            "closed_or_cancelled_text",
            "all_detected_dates_expired",
            "not_a_hobby_activity",
            "official_source_says_unavailable",
            "stated_age_outside_13_17",
            "venue_outside_proposed_area",
        }
        if disqualifying.intersection(flags):
            continue
        prepared.append(
            {
                **row,
                "proposed_area": area,
                "area_evidence": area_evidence,
                "hobby_buckets": " | ".join(buckets),
                "automated_flags": " | ".join(flags),
                "_score": str(candidate_score(row, flags, area_evidence)),
            }
        )
    return prepared


def _take_diverse(
    pool: list[dict[str, str]], count: int, bucket_counts: Counter[str]
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    remaining = list(pool)
    activity_counts: Counter[str] = Counter()
    while remaining and len(selected) < count:

        def activity_key(row: dict[str, str]) -> str:
            title = row["title_hint"].lower()
            title = re.sub(r"\b(?:at|@|\||-)\s+.*$", "", title)
            title = re.sub(r"\b\d{4}\b", "", title)
            return re.sub(r"[^a-z0-9]+", " ", title).strip()

        def utility(row: dict[str, str]) -> tuple[int, int, str]:
            buckets = row["hobby_buckets"].split(" | ")
            diversity = sum(max(0, 5 - bucket_counts[bucket]) for bucket in buckets)
            repetition_penalty = activity_counts[activity_key(row)] * 12
            return (
                diversity - repetition_penalty,
                int(row["_score"]),
                row["candidate_id"],
            )

        best = max(remaining, key=utility)
        remaining.remove(best)
        selected.append(best)
        bucket_counts.update(best["hobby_buckets"].split(" | "))
        activity_counts.update([activity_key(best)])
    return selected


def select_shortlist(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for area, area_total in AREA_QUOTAS.items():
        area_pool = [row for row in rows if row["proposed_area"] == area]
        bucket_counts: Counter[str] = Counter()
        area_selected: list[dict[str, str]] = []
        for source_kind, quota in SOURCE_QUOTAS[area].items():
            source_pool = [
                row
                for row in area_pool
                if row["source_kind"] == source_kind and row not in area_selected
            ]
            area_selected.extend(_take_diverse(source_pool, quota, bucket_counts))
        if len(area_selected) < area_total:
            remainder = [row for row in area_pool if row not in area_selected]
            area_selected.extend(
                _take_diverse(remainder, area_total - len(area_selected), bucket_counts)
            )
        if len(area_selected) != area_total:
            raise ValueError(
                f"{area}: selected {len(area_selected)} rows, need {area_total}; "
                "expand the public candidate pool"
            )
        selected.extend(area_selected)

    supplements = [row for row in rows if row["candidate_id"] in SUPPLEMENTAL_IDS]
    found = {row["candidate_id"] for row in supplements}
    missing = SUPPLEMENTAL_IDS - found
    if missing:
        raise ValueError(f"missing supplemental shortlist rows: {sorted(missing)}")
    selected.extend(sorted(supplements, key=lambda row: row["candidate_id"]))

    output: list[dict[str, str]] = []
    for rank, row in enumerate(selected, start=1):
        output.append(
            {
                **{column: row.get(column, "") for column in SHORTLIST_COLUMNS},
                "selection_rank": str(rank),
            }
        )
    return output


def write_shortlist(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=SHORTLIST_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = select_shortlist(load_candidates(args.queue))
    write_shortlist(rows, args.out)
    areas = Counter(row["proposed_area"] for row in rows)
    sources = Counter(row["source_kind"] for row in rows)
    buckets = Counter(
        bucket for row in rows for bucket in row["hobby_buckets"].split(" | ")
    )
    print(f"Shortlist: {len(rows)} rows; areas={dict(areas)}")
    print(f"Sources: {dict(sources)}")
    print(f"Hobby buckets: {dict(buckets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
