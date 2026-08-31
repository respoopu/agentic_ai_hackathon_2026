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
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "data" / "seed_ckb.csv"
QUARANTINE = ROOT / "data" / "quarantine_listings.json"
OUT = ROOT / "data" / "seed_ckb.json"

AGE_FLOOR, AGE_CEILING = 13, 17
STALE_AFTER_DAYS = 30

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
FALSE = {"no", "n", "false", "0", ""}


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
    s = (v or "").strip().replace("$", "").replace("S$", "").replace(",", "")
    if not s:
        return "0"
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise RowError(f"{field}: not a number: {v!r}")
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
    except ValueError:
        raise RowError(f"{field}: not a whole number: {v!r}")


def _date(
    v: str, field: str, required: bool = True, allow_future: bool = False
) -> str | None:
    s = (v or "").strip()
    if not s:
        if required:
            raise RowError(f"{field}: required")
        return None
    try:
        d = date.fromisoformat(s)
    except ValueError:
        raise RowError(f"{field}: use YYYY-MM-DD, got {v!r}")
    # A session date is meant to be ahead of us; a verification date never is.
    if d > date.today() and not allow_future:
        raise RowError(f"{field}: {s} is in the future")
    return s


def _time(v: str, field: str) -> str | None:
    s = (v or "").strip()
    if not s:
        return None
    try:
        return time.fromisoformat(s).isoformat(timespec="minutes")
    except ValueError:
        raise RowError(f"{field}: use HH:MM (24h), got {v!r}")


def _one_of(v: str, allowed: set[str], field: str) -> str:
    s = (v or "").strip().lower()
    if s not in allowed:
        raise RowError(f"{field}: expected one of {sorted(allowed)}, got {v!r}")
    return s


# --------------------------------------------------------------------------
# row -> record
# --------------------------------------------------------------------------


def parse_row(raw: dict[str, str], line_no: int) -> dict:
    def g(k: str) -> str:
        return (raw.get(k) or "").strip()

    rec: dict = {
        "listing_id": g("listing_id"),
        "title": g("title"),
        "provider": g("provider"),
        "provider_type": _one_of(g("provider_type"), PROVIDER_TYPES, "provider_type"),
        "source_url": g("source_url"),
        "verified_at": _date(g("verified_at"), "verified_at", required=False),
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
        "freshness_state": "fresh",
        "last_seen_at": datetime.now().isoformat(timespec="seconds"),
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
    if rec["verification"] == "verified":
        if not rec["verified_at"] or not rec["verified_by"]:
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

    rec["schedule"] = parse_schedule(g, raw)
    rec["cost_total_first_session"] = str(
        Decimal(rec["cost_one_off_sgd"]) + Decimal(rec["equipment_cost_sgd"])
    )
    return rec


def parse_schedule(g, raw: dict[str, str]) -> dict:
    kind = _one_of(
        g("schedule_kind"), {"weekly", "fixed_dates", "drop_in"}, "schedule_kind"
    )
    s: dict = {"kind": kind}

    if kind == "weekly":
        s["weekday"] = _one_of(g("weekday"), WEEKDAYS, "weekday")
        s["start_time"] = _time(g("start_time"), "start_time")
        s["duration_min"] = _int(g("duration_min"), "duration_min", required=False)
        s["first_session"] = _date(
            g("first_session"), "first_session", required=False, allow_future=True
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
            try:
                datetime.fromisoformat(d)
            except ValueError:
                raise RowError(f"fixed_dates: use YYYY-MM-DDTHH:MM, got {d!r}")
            if datetime.fromisoformat(d) < datetime.now():
                raise RowError(f"fixed_dates: {d} has already happened")
        s["fixed_dates"] = dates
    else:  # drop_in
        if not g("open_hours_note"):
            raise RowError("open_hours_note: required when schedule_kind=drop_in")
        s["open_hours_note"] = g("open_hours_note")
        for field in ("weekday_evening_available", "weekend_available"):
            if not g(field):
                raise RowError(f"{field}: required when schedule_kind=drop_in")
            s[field] = _bool(g(field), field)
    return s


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
    return s["kind"] == "weekly" and s.get("weekday") in {"sat", "sun"}


# --------------------------------------------------------------------------
# coverage report
# --------------------------------------------------------------------------


def coverage(records: list[dict]) -> list[tuple[str, bool, str]]:
    """Each check names the doc requirement it exists to satisfy."""
    real = [r for r in records if not r.get("is_fictional")]
    fake = [r for r in records if r.get("is_fictional")]
    free = [r for r in real if is_free(r)]

    by_area: dict[str, list[dict]] = defaultdict(list)
    for r in real:
        by_area[r["planning_area"]].append(r)
    deep = max(by_area, key=lambda a: len(by_area[a])) if by_area else None
    deep_rows = by_area.get(deep, [])
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
        "A3 · at least 3 planning areas",
        len(by_area) >= 3,
        f"{len(by_area)} areas: {', '.join(sorted(by_area)) or 'none'}",
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
    }
    short = {a: n for a, n in thin.items() if n < 3}
    check(
        "A3 · >=3 free, beginner, join-alone per area",
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
        f"{deep or '-'}: {len(ev)} free weekday-evening (want <=2), "
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
        f"{deep or '-'} has {sorted(deep_vibes) or 'none'}; "
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

    cutoff = date.today() - timedelta(days=STALE_AFTER_DAYS)
    stale = [
        r
        for r in real
        if r["verified_at"] and date.fromisoformat(r["verified_at"]) < cutoff
    ]
    check(
        f"freshness · verified within {STALE_AFTER_DAYS} days",
        not stale,
        "all fresh" if not stale else f"{len(stale)} rows need re-checking",
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
    args = ap.parse_args()

    if not args.sheet.exists():
        print(f"no sheet at {args.sheet.relative_to(ROOT)}")
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
                records.append(parse_row(raw, i))
            except RowError as e:
                errors.append(f"  row {i} ({(raw.get('title') or '?')[:40]}): {e}")

    if QUARANTINE.exists():
        blob = json.loads(QUARANTINE.read_text())
        fake = blob["listings"] if isinstance(blob, dict) else blob
        for r in fake:
            # Set here as well as in the file: a row in the quarantine file is
            # fictional by virtue of being in it, whatever the row claims.
            r["is_fictional"] = True
            if r.get("verification") != "unverified":
                errors.append(
                    f"  quarantine {r.get('listing_id')}: "
                    "must be verification='unverified'"
                )
            hostname = urlsplit(str(r.get("source_url", ""))).hostname or ""
            if not hostname.endswith(".invalid"):
                errors.append(
                    f"  quarantine {r.get('listing_id')}: source_url must use the "
                    "reserved "
                    ".invalid TLD so it can never resolve to a real business"
                )
        records.extend(fake)

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
    coverage_results = coverage(records)
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
        print(f"\n  not writing {OUT.name} — fix the rejected rows first\n")
        return 1

    # Run the executable schema contract before writing so a failed conformance
    # pass can never leave a malformed build artifact behind.
    try:  # optional tighter pass, once the agent env is installed
        sys.path.insert(0, str(ROOT))
        from src.schema.listing import ListingRecord  # noqa: PLC0415

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
        print(f"  not writing {OUT.name}\n")
        return 1

    if args.coverage_only:
        print()
        return 0 if passed == total else 1

    if passed != total and not args.allow_incomplete:
        print(
            f"\n  not writing {OUT.name} — coverage is incomplete "
            "(use --allow-incomplete only for local development)\n"
        )
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)} ({len(records)} listings)")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
