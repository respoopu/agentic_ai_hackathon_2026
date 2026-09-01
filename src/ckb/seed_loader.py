"""Load the built seed artifact and hydrate records for one planning request.

``scripts/build_ckb.py`` owns the build-time boundary: it validates the source
CSV plus quarantine fixtures and emits ``data/seed_ckb.json``. This module owns
the application boundary: it refuses malformed artifacts and converts a stored
``ListingRecord`` into the teen-relative ``Listing`` used by Planner.

Travel times and cohort presence are supplied by deterministic services. They
are deliberately not persisted on the shared listing record because both are
relative to the teen making the request.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from pydantic import TypeAdapter

from src.schema.listing import SG_TZ, Listing, ListingRecord, PeerCohort, Schedule

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_PATH = ROOT / "data" / "seed_ckb.json"


def load_seed_records(path: Path = DEFAULT_SEED_PATH) -> list[ListingRecord]:
    """Read and validate the immutable build artifact.

    The entire artifact is validated before any record is returned, preventing
    a partial CKB load when one row is malformed. Quarantine fixtures remain in
    the CKB intentionally: Planner may rank them, but Guardian must block them
    from teen-facing output unless a trusted adult approves the provider. The
    loader validates records; it is not an authorisation boundary.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = TypeAdapter(list[ListingRecord]).validate_python(payload)
    ids = [record.listing_id for record in records]
    duplicates = sorted({listing_id for listing_id in ids if ids.count(listing_id) > 1})
    if duplicates:
        raise ValueError(
            f"duplicate listing IDs in seed artifact: {', '.join(duplicates)}"
        )
    return records


def expand_next_sessions(
    schedule: Schedule,
    *,
    as_of: datetime | None = None,
) -> list[datetime]:
    """Expand structured schedules into future sessions Planner can compare.

    Drop-in opening hours remain free text by design and therefore do not
    become invented timestamps.
    """

    boundary = as_of or datetime.now(SG_TZ)
    if boundary.tzinfo is None:
        boundary = boundary.replace(tzinfo=SG_TZ)
    else:
        boundary = boundary.astimezone(SG_TZ)
    if schedule.kind == "fixed_dates":
        return sorted(
            session for session in schedule.fixed_dates if session >= boundary
        )
    if schedule.kind == "drop_in":
        return []

    assert schedule.weekday is not None
    assert schedule.start_time is not None
    assert schedule.first_session is not None
    assert schedule.num_sessions is not None

    first = datetime.combine(schedule.first_session, schedule.start_time, tzinfo=SG_TZ)
    sessions = (
        first + timedelta(weeks=offset) for offset in range(schedule.num_sessions)
    )
    return [session for session in sessions if session >= boundary]


def hydrate_listing(
    record: ListingRecord,
    *,
    travel_min_home: int,
    travel_min_school: int,
    peer_cohort: PeerCohort | None = None,
    as_of: datetime | None = None,
) -> Listing:
    """Create the request-scoped record consumed by Planner."""

    return Listing.model_validate(
        {
            **record.model_dump(),
            "travel_min_home": travel_min_home,
            "travel_min_school": travel_min_school,
            "peer_cohort": peer_cohort,
            "next_sessions": expand_next_sessions(record.schedule, as_of=as_of),
        }
    )


def hydrate_seed_records(
    records: Iterable[ListingRecord],
    *,
    travel_times: dict[str, tuple[int, int]],
    cohorts: dict[str, PeerCohort] | None = None,
    as_of: datetime | None = None,
) -> list[Listing]:
    """Hydrate a seed set without granting Planner any write capability."""

    cohort_by_listing = cohorts or {}
    hydrated: list[Listing] = []
    for record in records:
        try:
            home_minutes, school_minutes = travel_times[record.listing_id]
        except KeyError as exc:
            raise ValueError(f"missing travel times for {record.listing_id}") from exc
        hydrated.append(
            hydrate_listing(
                record,
                travel_min_home=home_minutes,
                travel_min_school=school_minutes,
                peer_cohort=cohort_by_listing.get(record.listing_id),
                as_of=as_of,
            )
        )
    return hydrated
