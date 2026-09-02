#!/usr/bin/env python3
"""Turn the transcription sheet into a validated seed CKB, and say what is missing.

    python3 scripts/build_ckb.py                    # validate + build
    python3 scripts/build_ckb.py --check-urls       # also confirm every link resolves
    python3 scripts/build_ckb.py --coverage-only    # just the gap report, no write

Reads  data/seed_ckb.csv       (hand-transcribed, one row per real activity)
       data/quarantine_listings.json  (invented, for the vetting demo)
Writes data/seed_ckb.json

Stdlib only, on purpose. Anyone on the team can run this on a fresh laptop
without setting up the agent environment. If pydantic happens to be installed
it runs a final conformance pass against src/schema/listing.py.

Two jobs, and the second is the more useful one:

  1. Refuse rows that are not properly sourced.
  2. Print which coverage cells are still empty, named against the test that
     needs them. "45 listings" is not the target; the cells are.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "data" / "seed_ckb.csv"
QUARANTINE = ROOT / "data" / "quarantine_listings.json"
OUT = ROOT / "data" / "seed_ckb.json"

AGE_FLOOR, AGE_CEILING = 13, 17
STALE_AFTER_DAYS = 30
DEEP_AREA = "Jurong West"
TARGET_AREAS = {"Jurong West", "Punggol", "Bishan"}
SG_TZ = ZoneInfo("Asia/Singapore")

PROVIDER_TYPES = {
    "cc",
    "activesg",
    "third_space",
    "school",
    "commercial",
    "informal",
    "private_unverified",
}
VIBES = {"sporty", "artistic", "chill", "explorative"}
WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
WEEKDAY_INDEX = {
    day: index
    for index, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun"))
}
COMMITMENTS = {"taster", "one_off", "short_course", "term"}

COLUMNS = [
    "listing_id",
    "title",
    "provider",
    "provider_type",
    "source_url",
    "verified_at",
    "verified_by",
    "verification",
    "cost_one_off_sgd",
    "cost_recurring_sgd",
    "equipment_cost_sgd",
    "venue_name",
    "postal_code",
    "planning_area",
    "nearest_mrt",
    "age_min",
    "age_max",
    "beginner_friendly",
    "join_alone_ok",
    "guest_allowed",
    "commitment",
    "schedule_kind",
    "weekday",
    "start_time",
    "duration_min",
    "first_session",
    "num_sessions",
    "fixed_dates",
    "open_hours_note",
    "vibes",
    "in_incumbent_directory",
    "notes",
    "weekday_evening_available",
    "weekend_available",
]

TRUE = {"yes", "y", "true", "1"}
FALSE = {"no", "n", "false", "0"}

LISTING_REQUIRED_KEYS = {
    "listing_id",
    "title",
    "provider",
    "provider_type",
    "source_url",
    "verified_at",
    "verified_by",
    "verification",
    "is_fictional",
    "cost_one_off_sgd",
    "cost_recurring_sgd",
    "equipment_cost_sgd",
    "venue_name",
    "postal_code",
    "planning_area",
    "age_min",
    "age_max",
    "beginner_friendly",
    "join_alone_ok",
    "guest_allowed",
    "commitment",
    "schedule",
    "vibes",
    "in_incumbent_directory",
    "last_seen_at",
    "freshness_state",
}
LISTING_OPTIONAL_KEYS = {
    "cost_total_first_session",
    "postal_sector",
    "nearest_mrt",
    "notes",
}


class RowError(Exception):
    pass


# --------------------------------------------------------------------------
# field parsers
# --------------------------------------------------------------------------


def _bool(v: str, field: str) -> bool:
    s = (v or "").strip().lower()
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    raise RowError(f"{field}: expected yes/no, got {v!r}")


def _money(v: str, field: str) -> str:
    s = (v or "").strip().replace("S$", "").replace("$", "").replace(",", "")
    if not s:
        raise RowError(f"{field}: required; enter 0 explicitly when free")
    try:
        d = Decimal(s)
    except InvalidOperation as exc:
        raise RowError(f"{field}: not a number: {v!r}") from exc
    if d < 0:
        raise RowError(f"{field}: negative cost {v!r}")
    return str(d)


def _int(v: str, field: str, required: bool = True) -> int | None:
    s = (v or "").strip()
    if not s:
        if required:
            raise RowError(f"{field}: required")
        return None
    try:
        return int(s)
    except ValueError as exc:
        raise RowError(f"{field}: not a whole number: {v!r}") from exc


def _date(
    v: str,
    field: str,
    *,
    as_of: datetime,
    required: bool = True,
    allow_future: bool = False,
) -> str | None:
    s = (v or "").strip()
    if not s:
        if required:
            raise RowError(f"{field}: required")
        return None
    try:
        d = date.fromisoformat(s)
    except ValueError as exc:
        raise RowError(f"{field}: use YYYY-MM-DD, got {v!r}") from exc
    # A session date is meant to be ahead of us; a verification date never is.
    if d > as_of.date() and not allow_future:
        raise RowError(f"{field}: {s} is in the future")
    return s


def _datetime(value: str | datetime, field: str) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise RowError(f"{field}: use an ISO-8601 date-time, got {value!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SG_TZ)
    return parsed.astimezone(SG_TZ)


def _time(v: str, field: str) -> str | None:
    s = (v or "").strip()
    if not s:
        return None
    try:
        return time.fromisoformat(s).isoformat(timespec="minutes")
    except ValueError as exc:
        raise RowError(f"{field}: use HH:MM (24h), got {v!r}") from exc


def _one_of(v: str, allowed: set[str], field: str) -> str:
    s = (v or "").strip().lower()
    if s not in allowed:
        raise RowError(f"{field}: expected one of {sorted(allowed)}, got {v!r}")
    return s


# --------------------------------------------------------------------------
# row -> record
# --------------------------------------------------------------------------


def parse_row(raw: dict[str, str], *, as_of: datetime) -> dict:
    def g(k: str) -> str:
        return (raw.get(k) or "").strip()

    rec: dict = {
        "listing_id": g("listing_id"),
        "title": g("title"),
        "provider": g("provider"),
        "provider_type": _one_of(g("provider_type"), PROVIDER_TYPES, "provider_type"),
        "source_url": g("source_url"),
        "verified_at": _date(
            g("verified_at"), "verified_at", as_of=as_of, required=False
        ),
        "verified_by": g("verified_by") or None,
        "verification": _one_of(
            g("verification"), {"verified", "unverified", "retired"}, "verification"
        ),
        "is_fictional": False,
        "cost_one_off_sgd": _money(g("cost_one_off_sgd"), "cost_one_off_sgd"),
        "cost_recurring_sgd": _money(g("cost_recurring_sgd"), "cost_recurring_sgd"),
        "equipment_cost_sgd": _money(g("equipment_cost_sgd"), "equipment_cost_sgd"),
        "venue_name": g("venue_name"),
        "postal_code": g("postal_code"),
        "planning_area": g("planning_area"),
        "nearest_mrt": g("nearest_mrt") or None,
        "age_min": _int(g("age_min"), "age_min"),
        "age_max": _int(g("age_max"), "age_max"),
        "beginner_friendly": _bool(g("beginner_friendly"), "beginner_friendly"),
        "join_alone_ok": _bool(g("join_alone_ok"), "join_alone_ok"),
        "guest_allowed": _bool(g("guest_allowed"), "guest_allowed"),
        "commitment": _one_of(g("commitment"), COMMITMENTS, "commitment"),
        "in_incumbent_directory": _bool(
            g("in_incumbent_directory"), "in_incumbent_directory"
        ),
        "notes": g("notes") or None,
        "freshness_state": (
            "dead" if g("verification").lower() == "retired" else "fresh"
        ),
        "last_seen_at": as_of.isoformat(timespec="seconds"),
    }

    for field in ("listing_id", "title", "provider", "venue_name", "planning_area"):
        if not rec[field]:
            raise RowError(f"{field}: required")

    if not rec["source_url"].startswith(("http://", "https://")):
        raise RowError(
            f"source_url: must be a full http(s) URL, got {rec['source_url']!r}"
        )

    pc = rec["postal_code"]
    if not (len(pc) == 6 and pc.isdigit()):
        raise RowError(f"postal_code: must be 6 digits, got {pc!r}")
    rec["postal_sector"] = pc[:2]

    if rec["age_min"] > rec["age_max"]:
        raise RowError(f"age_min {rec['age_min']} > age_max {rec['age_max']}")
    # A row no 13-17 year old can attend helps nobody, and its presence would
    # make the age-boundary test (A11) pass without meaning anything.
    if rec["age_max"] < AGE_FLOOR or rec["age_min"] > AGE_CEILING:
        raise RowError(
            f"age range {rec['age_min']}-{rec['age_max']} never overlaps "
            f"{AGE_FLOOR}-{AGE_CEILING} — this row cannot serve any teen"
        )

    # Provenance. "Verified" means a named person, on a named day.
    if rec["verification"] == "verified" and (
        not rec["verified_at"] or not rec["verified_by"]
    ):
        raise RowError(
            "verification=verified needs both verified_at and verified_by "
            "— an unattributed row is not a verified row"
        )

    vibes = [v.strip().lower() for v in g("vibes").split("|") if v.strip()]
    bad = set(vibes) - VIBES
    if bad:
        raise RowError(f"vibes: unknown {sorted(bad)}, allowed {sorted(VIBES)}")
    if not vibes:
        raise RowError("vibes: at least one required (used for coverage auditing only)")
    rec["vibes"] = vibes

    rec["schedule"] = parse_schedule(g, as_of=as_of)
    rec["cost_total_first_session"] = str(
        Decimal(rec["cost_one_off_sgd"]) + Decimal(rec["equipment_cost_sgd"])
    )
    return rec


def parse_schedule(g, *, as_of: datetime) -> dict:
    kind = _one_of(
        g("schedule_kind"), {"weekly", "fixed_dates", "drop_in"}, "schedule_kind"
    )
    s: dict = {"kind": kind}

    if kind == "weekly":
        s["weekday"] = _one_of(g("weekday"), WEEKDAYS, "weekday")
        s["start_time"] = _time(g("start_time"), "start_time")
        s["duration_min"] = _int(g("duration_min"), "duration_min", required=False)
        s["first_session"] = _date(
            g("first_session"),
            "first_session",
            as_of=as_of,
            required=False,
            allow_future=True,
        )
        s["num_sessions"] = _int(g("num_sessions"), "num_sessions", required=False)
        for f in ("start_time", "duration_min", "first_session", "num_sessions"):
            if s[f] is None:
                raise RowError(f"{f}: required when schedule_kind=weekly")
        if s["duration_min"] <= 0:
            raise RowError("duration_min: must be greater than zero")
        if s["num_sessions"] <= 0:
            raise RowError("num_sessions: must be greater than zero")
        first_day = date.fromisoformat(s["first_session"])
        if first_day.weekday() != WEEKDAY_INDEX[s["weekday"]]:
            raise RowError(
                f"first_session: {first_day} is not a declared {s['weekday']}"
            )
    elif kind == "fixed_dates":
        dates = [d.strip() for d in g("fixed_dates").split("|") if d.strip()]
        if not dates:
            raise RowError("fixed_dates: required when schedule_kind=fixed_dates")
        for d in dates:
            parsed = _datetime(d, "fixed_dates")
            if parsed < as_of:
                raise RowError(f"fixed_dates: {d} has already happened")
        s["fixed_dates"] = [
            _datetime(value, "fixed_dates").isoformat(timespec="minutes")
            for value in dates
        ]
    else:  # drop_in
        if not g("open_hours_note"):
            raise RowError("open_hours_note: required when schedule_kind=drop_in")
        s["open_hours_note"] = g("open_hours_note")
        for field in ("weekday_evening_available", "weekend_available"):
            if not g(field):
                raise RowError(f"{field}: required when schedule_kind=drop_in")
            s[field] = _bool(g(field), field)
    return s


def validate_quarantine_record(
    raw: object,
    *,
    index: int,
) -> dict:
    """Validate a fictional fixture without third-party dependencies."""

    label = f"quarantine row {index}"
    if not isinstance(raw, dict):
        raise RowError(f"{label}: expected an object")

    missing = LISTING_REQUIRED_KEYS - set(raw)
    extra = set(raw) - LISTING_REQUIRED_KEYS - LISTING_OPTIONAL_KEYS
    if missing:
        raise RowError(f"{label}: missing keys {sorted(missing)}")
    if extra:
        raise RowError(f"{label}: unknown keys {sorted(extra)}")

    rec = dict(raw)
    if rec.get("is_fictional") is not True:
        raise RowError(f"{label}: is_fictional must be true")
    listing_id = rec.get("listing_id")
    if not isinstance(listing_id, str) or not listing_id.strip():
        raise RowError(f"{label}: listing_id must be a non-empty string")
    label = f"quarantine {listing_id}"

    for field in ("title", "provider", "venue_name", "planning_area"):
        if not isinstance(rec.get(field), str) or not rec[field].strip():
            raise RowError(f"{label}: {field} must be a non-empty string")

    if rec.get("provider_type") != "private_unverified":
        raise RowError(f"{label}: provider_type must be 'private_unverified'")
    if rec.get("verification") != "unverified":
        raise RowError(f"{label}: verification must be 'unverified'")
    if rec.get("freshness_state") != "fresh":
        raise RowError(
            f"{label}: an unverified fixture must have freshness_state='fresh'"
        )
    if rec.get("verified_at") is not None or rec.get("verified_by") is not None:
        raise RowError(f"{label}: fictional rows cannot carry verification attribution")

    source_url = rec.get("source_url")
    hostname = urlsplit(str(source_url or "")).hostname or ""
    if not str(source_url).startswith(("http://", "https://")):
        raise RowError(f"{label}: source_url must be a full http(s) URL")
    if not hostname.endswith(".invalid"):
        raise RowError(f"{label}: source_url must use the reserved .invalid TLD")

    for field in (
        "cost_one_off_sgd",
        "cost_recurring_sgd",
        "equipment_cost_sgd",
    ):
        rec[field] = _money(str(rec.get(field, "")), field)
    expected_cost = Decimal(rec["cost_one_off_sgd"]) + Decimal(
        rec["equipment_cost_sgd"]
    )
    if "cost_total_first_session" in rec:
        actual_cost = Decimal(
            _money(
                str(rec["cost_total_first_session"]),
                "cost_total_first_session",
            )
        )
        if actual_cost != expected_cost:
            raise RowError(f"{label}: cost_total_first_session does not balance")
    rec["cost_total_first_session"] = str(expected_cost)

    postal_code = rec.get("postal_code")
    if not isinstance(postal_code, str) or not (
        len(postal_code) == 6 and postal_code.isdigit()
    ):
        raise RowError(f"{label}: postal_code must be 6 digits")
    expected_sector = postal_code[:2]
    if rec.get("postal_sector") not in (None, "", expected_sector):
        raise RowError(f"{label}: postal_sector does not match postal_code")
    rec["postal_sector"] = expected_sector

    for field in ("age_min", "age_max"):
        value = rec.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RowError(f"{label}: {field} must be a whole number")
        if not 0 <= value <= 120:
            raise RowError(f"{label}: {field} must be between 0 and 120")
    if rec["age_min"] > rec["age_max"]:
        raise RowError(f"{label}: age_min cannot exceed age_max")
    if rec["age_max"] < AGE_FLOOR or rec["age_min"] > AGE_CEILING:
        raise RowError(f"{label}: age range does not overlap {AGE_FLOOR}-{AGE_CEILING}")

    for field in (
        "beginner_friendly",
        "join_alone_ok",
        "guest_allowed",
        "in_incumbent_directory",
    ):
        if not isinstance(rec.get(field), bool):
            raise RowError(f"{label}: {field} must be a boolean")
    if (
        not isinstance(rec.get("commitment"), str)
        or rec["commitment"] not in COMMITMENTS
    ):
        raise RowError(f"{label}: invalid commitment {rec.get('commitment')!r}")

    vibes = rec.get("vibes")
    if (
        not isinstance(vibes, list)
        or not vibes
        or any(not isinstance(vibe, str) for vibe in vibes)
    ):
        raise RowError(f"{label}: vibes must be a non-empty list of strings")
    bad_vibes = set(vibes) - VIBES
    if bad_vibes:
        raise RowError(f"{label}: unknown vibes {sorted(bad_vibes)}")

    rec["schedule"] = validate_quarantine_schedule(rec.get("schedule"), label=label)
    rec["last_seen_at"] = _datetime(
        str(rec.get("last_seen_at", "")), "last_seen_at"
    ).isoformat(timespec="seconds")
    if rec.get("nearest_mrt") is not None and not isinstance(rec["nearest_mrt"], str):
        raise RowError(f"{label}: nearest_mrt must be a string or null")
    if rec.get("notes") is not None and not isinstance(rec["notes"], str):
        raise RowError(f"{label}: notes must be a string or null")
    return rec


def validate_quarantine_schedule(raw: object, *, label: str) -> dict:
    if not isinstance(raw, dict):
        raise RowError(f"{label}: schedule must be an object")
    kind = raw.get("kind")
    common = {"kind"}
    if kind == "weekly":
        allowed = common | {
            "weekday",
            "start_time",
            "duration_min",
            "first_session",
            "num_sessions",
        }
        if set(raw) - allowed:
            raise RowError(f"{label}: weekly schedule has unknown fields")
        weekday = raw.get("weekday")
        if not isinstance(weekday, str) or weekday not in WEEKDAYS:
            raise RowError(f"{label}: invalid weekly weekday")
        start_time = _time(str(raw.get("start_time") or ""), "start_time")
        if start_time is None:
            raise RowError(f"{label}: start_time must use HH:MM")
        duration = raw.get("duration_min")
        sessions = raw.get("num_sessions")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            raise RowError(f"{label}: duration_min must be a positive integer")
        if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions <= 0:
            raise RowError(f"{label}: num_sessions must be a positive integer")
        try:
            first = date.fromisoformat(str(raw.get("first_session") or ""))
        except ValueError as exc:
            raise RowError(f"{label}: invalid first_session") from exc
        if first.weekday() != WEEKDAY_INDEX[weekday]:
            raise RowError(f"{label}: first_session does not match weekday")
        return {
            "kind": "weekly",
            "weekday": weekday,
            "start_time": start_time,
            "duration_min": duration,
            "first_session": first.isoformat(),
            "num_sessions": sessions,
        }
    if kind == "fixed_dates":
        allowed = common | {"fixed_dates"}
        if set(raw) - allowed:
            raise RowError(f"{label}: fixed_dates schedule has unknown fields")
        values = raw.get("fixed_dates")
        if not isinstance(values, list) or not values:
            raise RowError(f"{label}: fixed_dates must be a non-empty list")
        return {
            "kind": "fixed_dates",
            "fixed_dates": [
                _datetime(str(value), "fixed_dates").isoformat(timespec="minutes")
                for value in values
            ],
        }
    if kind == "drop_in":
        allowed = common | {
            "open_hours_note",
            "weekday_evening_available",
            "weekend_available",
        }
        if set(raw) - allowed:
            raise RowError(f"{label}: drop_in schedule has unknown fields")
        note = raw.get("open_hours_note")
        if not isinstance(note, str) or not note.strip():
            raise RowError(f"{label}: open_hours_note must be non-empty")
        for field in ("weekday_evening_available", "weekend_available"):
            if not isinstance(raw.get(field), bool):
                raise RowError(f"{label}: {field} must be a boolean")
        return dict(raw)
    raise RowError(f"{label}: invalid schedule kind {kind!r}")


# --------------------------------------------------------------------------
# derived helpers
# --------------------------------------------------------------------------


def is_free(rec: dict) -> bool:
    return all(
        Decimal(rec[k]) == 0
        for k in ("cost_one_off_sgd", "cost_recurring_sgd", "equipment_cost_sgd")
    )


def is_weekday_evening(rec: dict) -> bool:
    s = rec["schedule"]
    if s["kind"] == "drop_in":
        return s["weekday_evening_available"]
    if s["kind"] == "fixed_dates":
        return any(
            value.weekday() < 5 and value.time() >= time(17)
            for value in map(datetime.fromisoformat, s["fixed_dates"])
        )
    if s["kind"] != "weekly" or not s.get("start_time"):
        return False
    return (
        s["weekday"] in {"mon", "tue", "wed", "thu", "fri"}
        and s["start_time"] >= "17:00"
    )


def is_weekend(rec: dict) -> bool:
    s = rec["schedule"]
    if s["kind"] == "drop_in":
        return s["weekend_available"]
    if s["kind"] == "fixed_dates":
        return any(
            value.weekday() >= 5
            for value in map(datetime.fromisoformat, s["fixed_dates"])
        )
    return s["kind"] == "weekly" and s.get("weekday") in {"sat", "sun"}


# --------------------------------------------------------------------------
# coverage report
# --------------------------------------------------------------------------


def coverage(
    records: list[dict],
    *,
    deep_area: str = DEEP_AREA,
    as_of: datetime | None = None,
) -> list[tuple[str, bool, str]]:
    """Each check names the doc requirement it exists to satisfy."""
    real = [r for r in records if not r.get("is_fictional")]
    fake = [r for r in records if r.get("is_fictional")]
    free = [r for r in real if is_free(r)]

    by_area: dict[str, list[dict]] = defaultdict(list)
    for r in real:
        by_area[r["planning_area"]].append(r)
    densest = max(by_area, key=lambda area: len(by_area[area])) if by_area else None
    deep_rows = by_area.get(deep_area, [])
    deep_free = [r for r in deep_rows if is_free(r)]

    results: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, detail: str) -> None:
        results.append((label, ok, detail))

    check(
        "volume · 40-60 real + quarantine",
        40 <= len(records) <= 60,
        f"{len(real)} real + {len(fake)} quarantine = {len(records)}",
    )
    check(
        "A3 · configured deep area + 3 planning areas",
        len(by_area) >= 3 and bool(deep_rows) and densest == deep_area,
        f"{len(by_area)} areas; configured={deep_area!r}; densest={densest!r}",
    )

    thin = {
        a: len(
            [
                r
                for r in rows
                if is_free(r) and r["beginner_friendly"] and r["join_alone_ok"]
            ]
        )
        for a, rows in by_area.items()
        if a in TARGET_AREAS
    }
    for area in TARGET_AREAS - thin.keys():
        thin[area] = 0
    short = {a: n for a, n in thin.items() if n < 3}
    check(
        "A3 · >=3 free, beginner, join-alone per target area",
        not short and bool(thin),
        ("no rows yet" if not thin else "all areas clear")
        if not short
        else "short: " + ", ".join(f"{a} has {n}" for a, n in sorted(short.items())),
    )

    ev = [r for r in deep_free if is_weekday_evening(r)]
    we = [r for r in deep_free if is_weekend(r)]
    check(
        "scenario 2 · the demo moment",
        len(ev) <= 2 and len(we) >= 6,
        f"{deep_area}: {len(ev)} free weekday-evening (want <=2), "
        f"{len(we)} free weekend (want >=6)",
    )

    at13 = [r for r in real if r["age_min"] == AGE_FLOOR]
    at17 = [r for r in real if r["age_max"] == AGE_CEILING]
    check(
        "A11 · age boundary rows exist",
        bool(at13) and bool(at17),
        f"{len(at13)} start at {AGE_FLOOR}, {len(at17)} end at {AGE_CEILING}",
    )

    check(
        "A1 · quarantine set",
        len(fake) >= 8 and all(r["verification"] == "unverified" for r in fake),
        f"{len(fake)} fictional unverified rows (want >=8)",
    )

    retire = [r for r in real if "#demo-retire" in (r.get("notes") or "")]
    check(
        "scenario 4 · a row to retire on camera",
        len(retire) >= 1,
        f"{len(retire)} tagged #demo-retire",
    )

    longtail = [r for r in real if not r["in_incumbent_directory"]]
    pct = (100 * len(longtail) / len(real)) if real else 0
    check(
        "B9 · long-tail share >= 40%",
        pct >= 40,
        f"{pct:.0f}% not in incumbent directories ({len(longtail)}/{len(real)})",
    )

    deep_vibes = {v for r in deep_rows for v in r["vibes"]}
    check(
        "D10 · all four vibes in the deep area",
        deep_vibes == VIBES,
        f"{deep_area} has {sorted(deep_vibes) or 'none'}; "
        f"missing {sorted(VIBES - deep_vibes) or 'none'}",
    )

    ptypes = Counter(r["provider_type"] for r in real)
    want = {"cc": 3, "activesg": 3, "third_space": 2, "informal": 3, "commercial": 1}
    gaps = {t: (ptypes.get(t, 0), n) for t, n in want.items() if ptypes.get(t, 0) < n}
    check(
        "provider-type spread",
        not gaps,
        "all types covered"
        if not gaps
        else "short: "
        + ", ".join(f"{t} {have}/{n}" for t, (have, n) in sorted(gaps.items())),
    )

    check(
        "free supply is the majority",
        len(free) >= len(real) / 2 if real else False,
        f"{len(free)}/{len(real)} rows are S$0",
    )

    reference = as_of or datetime.now(SG_TZ)
    cutoff = reference.date() - timedelta(days=STALE_AFTER_DAYS)
    stale = [
        r
        for r in real
        if r["verified_at"] and date.fromisoformat(r["verified_at"]) < cutoff
    ]
    check(
        f"freshness · verified within {STALE_AFTER_DAYS} days",
        bool(real) and not stale,
        "no real rows"
        if not real
        else ("all fresh" if not stale else f"{len(stale)} rows need re-checking"),
    )

    return results


# --------------------------------------------------------------------------
# url checking
# --------------------------------------------------------------------------


def check_urls(records: list[dict]) -> tuple[list[str], list[str]]:
    """Returns (dead, unchecked). A 403 is not a dead link — gov sites block bots."""
    dead, unchecked = [], []
    for r in records:
        if r.get("is_fictional"):
            continue
        url = r["source_url"]
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0 (compatible; hobbi-ckb-validator/1.0)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    dead.append(f"{r['listing_id']}: HTTP {resp.status} — {url}")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                dead.append(f"{r['listing_id']}: HTTP {e.code} — {url}")
            else:
                unchecked.append(f"{r['listing_id']}: HTTP {e.code} — {url}")
        except Exception as e:  # noqa: BLE001 — network is allowed to be flaky
            unchecked.append(f"{r['listing_id']}: {type(e).__name__} — {url}")
    return dead, unchecked


# --------------------------------------------------------------------------


def display_path(path: Path) -> Path:
    resolved = path.resolve()
    return resolved.relative_to(ROOT) if resolved.is_relative_to(ROOT) else resolved


def atomic_write_json(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(records, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        assert temp_path is not None
        os.replace(temp_path, path)
    except BaseException:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(SG_TZ)
    return _datetime(value, "as_of")


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-urls", action="store_true", help="HEAD every source_url")
    ap.add_argument(
        "--coverage-only", action="store_true", help="report gaps, write nothing"
    )
    ap.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="write a structurally valid artifact even when coverage checks have gaps",
    )
    ap.add_argument("--sheet", type=Path, default=SHEET)
    ap.add_argument("--quarantine", type=Path, default=QUARANTINE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--deep-area", default=DEEP_AREA)
    ap.add_argument(
        "--as-of",
        help="ISO-8601 build time; naive values are interpreted as Asia/Singapore",
    )
    args = ap.parse_args()
    args.sheet = args.sheet.resolve()
    args.quarantine = args.quarantine.resolve()
    args.out = args.out.resolve()

    try:
        as_of = parse_as_of(args.as_of)
    except RowError as exc:
        print(exc)
        return 1

    if not args.sheet.exists():
        print(f"no sheet at {display_path(args.sheet)}")
        print("Export the transcription sheet as CSV and save it there.")
        return 1

    records: list[dict] = []
    errors: list[str] = []

    with args.sheet.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            print(f"sheet is missing columns: {', '.join(sorted(missing))}")
            return 1
        for i, raw in enumerate(reader, start=2):
            if not (raw.get("listing_id") or "").strip():
                continue  # blank spacer row
            if (raw.get("listing_id") or "").strip().startswith("#"):
                continue  # commented-out example row
            try:
                records.append(parse_row(raw, as_of=as_of))
            except RowError as e:
                errors.append(f"  row {i} ({(raw.get('title') or '?')[:40]}): {e}")

    if args.quarantine.exists():
        try:
            blob = json.loads(args.quarantine.read_text(encoding="utf-8"))
            fake = blob["listings"] if isinstance(blob, dict) else blob
            if not isinstance(fake, list):
                raise RowError("quarantine payload must contain a list of listings")
        except (json.JSONDecodeError, KeyError, OSError, RowError) as exc:
            errors.append(f"  quarantine file: {exc}")
            fake = []
        for index, raw in enumerate(fake, start=1):
            try:
                records.append(validate_quarantine_record(raw, index=index))
            except (InvalidOperation, RowError) as exc:
                errors.append(f"  {exc}")

    ids = Counter(r["listing_id"] for r in records)
    for lid, n in ids.items():
        if n > 1:
            errors.append(f"  duplicate listing_id {lid!r} appears {n} times")

    n_quarantine = sum(1 for r in records if r.get("is_fictional"))
    n_ok = len(records) - n_quarantine
    print(
        f"\n  {args.sheet.name}: {n_ok} rows accepted, {len(errors)} rejected"
        f"  (+{n_quarantine} quarantine)"
    )

    if errors:
        print()
        print("\n".join(errors[:25]))
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")

    print("\n  coverage\n  " + "-" * 62)
    passed = 0
    coverage_results = coverage(records, deep_area=args.deep_area, as_of=as_of)
    for label, ok, detail in coverage_results:
        print(f"  {'PASS' if ok else 'GAP '}  {label:<42} {detail}")
        passed += ok
    total = len(coverage_results)
    print("  " + "-" * 62)
    print(f"  {passed}/{total} coverage checks pass")

    if args.check_urls:
        print("\n  checking links...")
        dead, unchecked = check_urls(records)
        if dead:
            print(
                f"\n  {len(dead)} DEAD links — these must be fixed or the rows dropped:"
            )
            print("\n".join(f"    {d}" for d in dead))
        if unchecked:
            print(
                f"\n  {len(unchecked)} could not be checked automatically (bot-blocked "
                "or flaky) — open these by hand:"
            )
            print("\n".join(f"    {u}" for u in unchecked))
        if not dead and not unchecked:
            print("  all links resolve")
        errors.extend(dead)

    if errors:
        print(f"\n  not writing {args.out.name} — fix the rejected rows first\n")
        return 1

    # Run the executable schema contract before writing so a failed conformance
    # pass can never leave a malformed build artifact behind.
    try:  # optional tighter pass, once the agent env is installed
        sys.path.insert(0, str(ROOT))
        from src.schema.listing import ListingRecord

        for r in records:
            ListingRecord.model_validate(r)
        print("\n  pydantic conformance: OK")
    except ImportError:
        print(
            "\n  pydantic not installed — skipped conformance pass "
            "(structural checks ran)"
        )
    except Exception as e:  # noqa: BLE001
        print(f"\n  pydantic conformance FAILED: {e}")
        print(f"  not writing {args.out.name}\n")
        return 1

    if args.coverage_only:
        print()
        return 0 if passed == total else 1

    if passed != total and not args.allow_incomplete:
        print(
            f"\n  not writing {args.out.name} — coverage is incomplete "
            "(use --allow-incomplete only for local development)\n"
        )
        return 1

    atomic_write_json(args.out, records)
    print(f"\n  wrote {display_path(args.out)} ({len(records)} listings)")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
