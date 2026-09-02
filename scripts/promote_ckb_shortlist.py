#!/usr/bin/env python3
"""Validate human CKB attestations and promote approved rows to the seed CSV.

The shortlist is a review surface, not a source of truth. This command fails
closed when any row is pending, when a rejection has no reason, or when an
approved row cannot pass the canonical builder's own row validation.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

try:
    from scripts.build_ckb import COLUMNS, ROOT, SG_TZ, RowError, parse_row
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from build_ckb import COLUMNS, ROOT, SG_TZ, RowError, parse_row

DEFAULT_SHORTLIST = ROOT / "data" / "ckb_shortlist.csv"
DEFAULT_OUT = ROOT / "data" / "seed_ckb.csv"
DECISIONS = {"approve", "reject"}
NON_HUMAN_REVIEWERS = {"agent", "automation", "bot", "claude", "codex", "script"}

CONFIRMED_TO_SEED = {
    "confirmed_title": "title",
    "confirmed_provider": "provider",
    "confirmed_provider_type": "provider_type",
    "confirmed_venue": "venue_name",
    "confirmed_postal_code": "postal_code",
    "confirmed_planning_area": "planning_area",
    "confirmed_nearest_mrt": "nearest_mrt",
    "confirmed_cost_one_off_sgd": "cost_one_off_sgd",
    "confirmed_cost_recurring_sgd": "cost_recurring_sgd",
    "confirmed_equipment_cost_sgd": "equipment_cost_sgd",
    "confirmed_age_min": "age_min",
    "confirmed_age_max": "age_max",
    "confirmed_beginner_friendly": "beginner_friendly",
    "confirmed_join_alone_ok": "join_alone_ok",
    "confirmed_guest_allowed": "guest_allowed",
    "confirmed_commitment": "commitment",
    "confirmed_schedule_kind": "schedule_kind",
    "confirmed_weekday": "weekday",
    "confirmed_start_time": "start_time",
    "confirmed_duration_min": "duration_min",
    "confirmed_first_session": "first_session",
    "confirmed_num_sessions": "num_sessions",
    "confirmed_fixed_dates": "fixed_dates",
    "confirmed_open_hours_note": "open_hours_note",
    "confirmed_weekday_evening_available": "weekday_evening_available",
    "confirmed_weekend_available": "weekend_available",
    "confirmed_vibes": "vibes",
    "confirmed_in_incumbent_directory": "in_incumbent_directory",
}


class SignoffError(ValueError):
    """Raised when the human review sheet is incomplete or inconsistent."""


def _reviewer_is_human(value: str) -> bool:
    tokens = {token.lower() for token in value.replace("-", " ").split()}
    return bool(value.strip()) and not NON_HUMAN_REVIEWERS.intersection(tokens)


def _promoted_row(row: dict[str, str], *, as_of: datetime) -> dict[str, str]:
    candidate_id = row.get("candidate_id", "<missing>")
    reviewer = row.get("reviewed_by", "").strip()
    if not _reviewer_is_human(reviewer):
        raise SignoffError(
            f"{candidate_id}: reviewed_by must identify the human who checked the source"
        )
    reviewed_at = row.get("reviewed_at", "").strip()
    seed = {column: "" for column in COLUMNS}
    seed.update(
        {
            "listing_id": candidate_id,
            "source_url": row.get("source_url", "").strip(),
            "verified_at": reviewed_at,
            "verified_by": reviewer,
            "verification": "verified",
            "notes": row.get("review_notes", "").strip(),
        }
    )
    for confirmed, canonical in CONFIRMED_TO_SEED.items():
        seed[canonical] = row.get(confirmed, "").strip()

    try:
        parse_row(seed, as_of=as_of)
    except RowError as exc:
        raise SignoffError(f"{candidate_id}: {exc}") from exc
    return seed


def validate_and_promote(
    rows: Iterable[dict[str, str]], *, as_of: datetime
) -> tuple[list[dict[str, str]], dict[str, int]]:
    approved: list[dict[str, str]] = []
    rejected = 0
    pending: list[str] = []
    seen_ids: set[str] = set()
    for row in rows:
        candidate_id = row.get("candidate_id", "").strip()
        if not candidate_id or candidate_id in seen_ids:
            raise SignoffError(f"duplicate or missing candidate_id: {candidate_id!r}")
        seen_ids.add(candidate_id)
        decision = row.get("review_decision", "").strip().lower()
        if decision not in DECISIONS:
            pending.append(candidate_id)
            continue
        if decision == "reject":
            if not row.get("review_notes", "").strip():
                raise SignoffError(f"{candidate_id}: rejected rows need review_notes")
            if not _reviewer_is_human(row.get("reviewed_by", "")):
                raise SignoffError(f"{candidate_id}: rejection needs a human reviewed_by")
            if not row.get("reviewed_at", "").strip():
                raise SignoffError(f"{candidate_id}: rejection needs reviewed_at")
            rejected += 1
            continue
        approved.append(_promoted_row(row, as_of=as_of))

    if pending:
        sample = ", ".join(pending[:5])
        suffix = "..." if len(pending) > 5 else ""
        raise SignoffError(
            f"{len(pending)} rows are pending human review: {sample}{suffix}"
        )
    if not approved:
        raise SignoffError("no rows were approved; refusing to publish an empty seed")
    return approved, {
        "approved": len(approved),
        "rejected": rejected,
        "reviewed": len(seen_ids),
    }


def write_seed(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", type=Path, default=DEFAULT_SHORTLIST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--as-of", type=datetime.fromisoformat)
    args = parser.parse_args()
    as_of = args.as_of or datetime.now(SG_TZ)
    try:
        with args.shortlist.open(encoding="utf-8", newline="") as handle:
            rows, summary = validate_and_promote(csv.DictReader(handle), as_of=as_of)
    except SignoffError as exc:
        parser.error(str(exc))
    write_seed(rows, args.out)
    print(
        f"Promoted {summary['approved']} human-approved rows; "
        f"retained {summary['rejected']} documented rejections in the review sheet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
