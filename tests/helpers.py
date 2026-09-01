from __future__ import annotations

from datetime import UTC, datetime

from src.ckb.seed_loader import hydrate_listing
from src.schema.listing import Listing, ListingRecord

NOW = datetime(2026, 9, 1, 10, tzinfo=UTC)


def listing_record(
    listing_id: str = "L-001",
    *,
    cost: str = "0",
    verification: str = "verified",
    provider_type: str = "cc",
    vibes: list[str] | None = None,
) -> ListingRecord:
    fictional = provider_type == "private_unverified"
    source = (
        f"https://{listing_id.lower()}.invalid/activity"
        if fictional
        else f"https://www.onepa.gov.sg/courses/{listing_id.lower()}"
    )
    return ListingRecord.model_validate(
        {
            "listing_id": listing_id,
            "title": f"Activity {listing_id}",
            "provider": "Example Community Club" if not fictional else "Fictional Coach",
            "provider_type": provider_type,
            "source_url": source,
            "verified_at": None if verification != "verified" else "2026-08-31",
            "verified_by": None if verification != "verified" else "test-reviewer",
            "verification": verification,
            "is_fictional": fictional,
            "cost_one_off_sgd": cost,
            "cost_recurring_sgd": "0",
            "equipment_cost_sgd": "0",
            "venue_name": "Community Hall",
            "postal_code": "640518",
            "planning_area": "Jurong West",
            "nearest_mrt": "Boon Lay",
            "age_min": 13,
            "age_max": 17,
            "beginner_friendly": True,
            "join_alone_ok": True,
            "guest_allowed": True,
            "commitment": "taster",
            "schedule": {
                "kind": "drop_in",
                "open_hours_note": "weekends 9am to 7pm",
                "weekday_evening_available": False,
                "weekend_available": True,
            },
            "vibes": vibes or ["chill"],
            "in_incumbent_directory": False,
            "last_seen_at": NOW,
            "freshness_state": "fresh",
        }
    )


def hydrated(record: ListingRecord, travel: int = 10) -> Listing:
    return hydrate_listing(
        record,
        travel_min_home=travel,
        travel_min_school=travel,
        as_of=NOW,
    )
