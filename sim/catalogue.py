"""Clearly labelled synthetic catalogue used only by the evaluation harness."""

from __future__ import annotations

from datetime import UTC, datetime

from src.ckb.seed_loader import hydrate_listing
from src.schema.listing import Listing, ListingRecord

AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def records() -> list[ListingRecord]:
    rows = []
    specifications = [
        ("SYN-sport-free", "sporty", "0", 10),
        ("SYN-chill-free", "chill", "0", 10),
        ("SYN-art-free", "artistic", "0", 12),
        ("SYN-explore-free", "explorative", "0", 14),
        ("SYN-sport-paid", "sporty", "8", 18),
        ("SYN-chill-paid", "chill", "12", 20),
        ("SYN-art-paid", "artistic", "15", 25),
        ("SYN-explore-paid", "explorative", "20", 30),
    ]
    for listing_id, vibe, cost, _ in specifications:
        rows.append(
            ListingRecord.model_validate(
                {
                    "listing_id": listing_id,
                    "title": f"Synthetic {vibe} taster",
                    "provider": "Synthetic Evaluation Provider",
                    "provider_type": "private_unverified",
                    "source_url": f"https://{listing_id.lower()}.invalid/evaluation",
                    "verified_at": None,
                    "verified_by": None,
                    "verification": "unverified",
                    "is_fictional": True,
                    "cost_one_off_sgd": cost,
                    "cost_recurring_sgd": "0",
                    "equipment_cost_sgd": "0",
                    "venue_name": "Synthetic Evaluation Venue",
                    "postal_code": "640518",
                    "planning_area": "Jurong West",
                    "nearest_mrt": None,
                    "age_min": 13,
                    "age_max": 17,
                    "beginner_friendly": True,
                    "join_alone_ok": True,
                    "guest_allowed": True,
                    "commitment": "taster",
                    "schedule": {
                        "kind": "drop_in",
                        "open_hours_note": "Synthetic weekend slot",
                        "weekday_evening_available": True,
                        "weekend_available": True,
                    },
                    "vibes": [vibe],
                    "in_incumbent_directory": False,
                    "last_seen_at": AS_OF,
                    "freshness_state": "fresh",
                    "notes": "Synthetic evaluation fixture; never presented as a real listing.",
                }
            )
        )
    return rows


def listings() -> list[Listing]:
    distances = {
        listing_id: travel
        for listing_id, _, _, travel in [
            ("SYN-sport-free", "sporty", "0", 10),
            ("SYN-chill-free", "chill", "0", 10),
            ("SYN-art-free", "artistic", "0", 12),
            ("SYN-explore-free", "explorative", "0", 14),
            ("SYN-sport-paid", "sporty", "8", 18),
            ("SYN-chill-paid", "chill", "12", 20),
            ("SYN-art-paid", "artistic", "15", 25),
            ("SYN-explore-paid", "explorative", "20", 30),
        ]
    }
    return [
        hydrate_listing(
            record,
            travel_min_home=distances[record.listing_id],
            travel_min_school=distances[record.listing_id] + 3,
            as_of=AS_OF,
        )
        for record in records()
    ]
