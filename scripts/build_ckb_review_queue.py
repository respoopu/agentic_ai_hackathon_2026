#!/usr/bin/env python3
"""Combine merged CKB drafts and public-social leads into one review queue.

The output is deliberately not accepted by ``scripts/build_ckb.py``. It is a
research worksheet that makes missing evidence visible before a human promotes
selected rows into ``data/seed_ckb.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFTS = (
    ROOT / "data" / "draft_free_play.csv",
    ROOT / "data" / "draft_nlb.csv",
    ROOT / "data" / "draft_nlb_west.csv",
)
DEFAULT_SOCIAL = ROOT / "data" / "draft_social_candidates.json"
DEFAULT_WEB = ROOT / "data" / "draft_web_candidates.json"
DEFAULT_OUT = ROOT / "data" / "ckb_review_queue.csv"
TARGET_AREAS = {"Jurong West", "Punggol", "Bishan"}

QUEUE_COLUMNS = [
    "candidate_id",
    "source_kind",
    "source_name",
    "source_url",
    "registration_urls",
    "title_hint",
    "provider_hint",
    "venue_hint",
    "postal_hint",
    "area_hints",
    "date_hints",
    "time_hints",
    "cost_hints",
    "age_hints",
    "topic_hints",
    "excerpt_or_notes",
    "missing_for_ckb",
    "priority_score",
    "review_decision",
    "reviewed_at",
    "reviewed_by",
    "review_notes",
]

REVIEW_FIELDS = (
    "verified_at",
    "verified_by",
    "cost_one_off_sgd",
    "planning_area",
    "age_min",
    "age_max",
    "beginner_friendly",
    "join_alone_ok",
    "guest_allowed",
)


def _join(values: Iterable[str]) -> str:
    return " | ".join(value.strip() for value in values if value and value.strip())


def _source_kind(path: Path) -> str:
    if "free_play" in path.name:
        return "merged_activesg_draft"
    return "merged_nlb_draft"


def _normalized_url(value: str) -> str:
    parts = urlsplit(value.strip())
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", "")
    )


def _candidate_key(row: dict[str, str]) -> str:
    source_url = _normalized_url(row["source_url"])
    if row["source_kind"] == "public_web_candidate":
        return f"{source_url}#{row['candidate_id']}"
    if row["source_kind"] == "public_telegram_candidate":
        external_registration_urls = [
            normalized
            for value in row["registration_urls"].split(" | ")
            if (normalized := _normalized_url(value))
            and urlsplit(normalized).netloc not in {"t.me", "telegram.me"}
        ]
        if external_registration_urls:
            return f"registration:{external_registration_urls[0]}"
    return source_url


def draft_rows(paths: Iterable[Path]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if not row.get("listing_id") or row["listing_id"].startswith("#"):
                    continue
                missing = [
                    field for field in REVIEW_FIELDS if not row.get(field, "").strip()
                ]
                schedule = row.get("fixed_dates") or _join(
                    [row.get("weekday", ""), row.get("start_time", "")]
                )
                topics = row.get("vibes", "")
                area = row.get("planning_area", "")
                score = 4
                score += 2 if row.get("age_min") and row.get("age_max") else 0
                score += 2 if row.get("postal_code") else 0
                score += 2 if schedule else 0
                score += 1 if area in TARGET_AREAS else 0
                score -= len(missing)
                output.append(
                    {
                        "candidate_id": row["listing_id"],
                        "source_kind": _source_kind(path),
                        "source_name": row.get("provider", ""),
                        "source_url": row.get("source_url", ""),
                        "registration_urls": "",
                        "title_hint": row.get("title", ""),
                        "provider_hint": row.get("provider", ""),
                        "venue_hint": row.get("venue_name", ""),
                        "postal_hint": row.get("postal_code", ""),
                        "area_hints": area,
                        "date_hints": schedule,
                        "time_hints": row.get("open_hours_note", ""),
                        "cost_hints": _join(
                            [
                                row.get("cost_one_off_sgd", ""),
                                row.get("cost_recurring_sgd", ""),
                                row.get("equipment_cost_sgd", ""),
                            ]
                        ),
                        "age_hints": _join(
                            [row.get("age_min", ""), row.get("age_max", "")]
                        ),
                        "topic_hints": topics,
                        "excerpt_or_notes": row.get("notes", ""),
                        "missing_for_ckb": _join(missing),
                        "priority_score": str(score),
                        "review_decision": "",
                        "reviewed_at": "",
                        "reviewed_by": "",
                        "review_notes": "",
                    }
                )
    return output


def candidate_rows(path: Path, *, source_kind: str) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    output: list[dict[str, str]] = []
    for candidate in payload.get("candidates", []):
        detected = candidate.get("detected", {})
        areas = candidate.get("area_hints", [])
        topics = candidate.get("topic_hints", [])
        missing = list(REVIEW_FIELDS)
        if detected.get("costs"):
            missing.remove("cost_one_off_sgd")
        if detected.get("ages"):
            missing.remove("age_min")
            missing.remove("age_max")
        score = 1
        score += 2 if detected.get("dates") else 0
        score += 1 if detected.get("times") else 0
        score += 2 if detected.get("costs") else 0
        score += 3 if detected.get("ages") else 0
        score += 2 if detected.get("postal_codes") else 0
        score += 2 if TARGET_AREAS.intersection(areas) else 0
        output.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_kind": source_kind,
                "source_name": candidate.get("source_name", ""),
                "source_url": candidate.get("source_url", ""),
                "registration_urls": _join(candidate.get("registration_urls", [])),
                "title_hint": candidate.get("title_hint", ""),
                "provider_hint": candidate.get("source_name", ""),
                "venue_hint": "",
                "postal_hint": _join(detected.get("postal_codes", [])),
                "area_hints": _join(areas),
                "date_hints": _join(detected.get("dates", [])),
                "time_hints": _join(detected.get("times", [])),
                "cost_hints": _join(detected.get("costs", [])),
                "age_hints": _join(detected.get("ages", [])),
                "topic_hints": _join(topics),
                "excerpt_or_notes": candidate.get("excerpt", ""),
                "missing_for_ckb": _join(missing),
                "priority_score": str(score),
                "review_decision": "",
                "reviewed_at": "",
                "reviewed_by": "",
                "review_notes": "",
            }
        )
    return output


def build_queue(
    draft_paths: Iterable[Path],
    social_path: Path,
    web_path: Path | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    combined = draft_rows(draft_paths) + candidate_rows(
        social_path, source_kind="public_telegram_candidate"
    )
    if web_path is not None:
        combined += candidate_rows(web_path, source_kind="public_web_candidate")
    deduplicated: dict[str, dict[str, str]] = {}
    duplicate_count = 0
    for row in combined:
        # Public venue/evidence pages can support distinct activities. Social
        # reposts of one specific registration link are one candidate.
        key = _candidate_key(row)
        existing = deduplicated.get(key)
        if existing is None:
            deduplicated[key] = row
            continue
        duplicate_count += 1
        # Keep the more complete version. This drops draft_nlb_west duplicates
        # without making file order a hidden policy.
        if int(row["priority_score"]) > int(existing["priority_score"]):
            deduplicated[key] = row
    rows = sorted(
        deduplicated.values(),
        key=lambda row: (
            -int(row["priority_score"]),
            row["source_kind"],
            row["candidate_id"],
        ),
    )
    summary = {
        "merged_drafts": sum(row["source_kind"].startswith("merged_") for row in rows),
        "public_candidates": sum(
            row["source_kind"].startswith("public_") for row in rows
        ),
        "duplicates_removed": duplicate_count,
        "total": len(rows),
    }
    return rows, summary


def write_queue(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--social", type=Path, default=DEFAULT_SOCIAL)
    parser.add_argument("--web", type=Path, default=DEFAULT_WEB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("drafts", nargs="*", type=Path, default=list(DEFAULT_DRAFTS))
    args = parser.parse_args()
    rows, summary = build_queue(args.drafts, args.social, args.web)
    write_queue(rows, args.out)
    print(
        f"Review queue: {summary['total']} unique candidates "
        f"({summary['merged_drafts']} merged drafts + "
        f"{summary['public_candidates']} public leads; "
        f"{summary['duplicates_removed']} duplicates removed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
