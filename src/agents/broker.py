"""Sandbox-only booking and exactly-once ledger commitment."""

from __future__ import annotations

from pydantic import Field

from src.schema.events import BookingRecord
from src.schema.listing import ListingRecord
from src.schema.plan import GuardianVerdict, Plan, StrictModel
from src.store.personal_data import PersonalDataStore
from src.validation.orchestrator import Validator


class BrokerResult(StrictModel):
    records: list[BookingRecord] = Field(default_factory=list)
    replayed: bool = False
    failure_reason: str | None = None
    unavailable_listing_id: str | None = None
    teen_preparation: list[dict[str, object]] = Field(default_factory=list)
    parent_reassurance: list[dict[str, str]] = Field(default_factory=list)


class Broker:
    allowed_tools = frozenset({"sandbox_availability", "commit_plan_bookings"})

    def book(
        self,
        *,
        teen_id: str,
        plan: Plan,
        verdict: GuardianVerdict,
        listings: dict[str, ListingRecord],
        store: PersonalDataStore,
        unavailable_listing_ids: set[str] | None = None,
    ) -> BrokerResult:
        unavailable = unavailable_listing_ids or set()
        for item in plan.items:
            if item.listing_id in unavailable:
                return BrokerResult(
                    failure_reason=(
                        f"{item.listing_id} is unavailable for that session; "
                        "choose another listing and repeat Guardian approval"
                    ),
                    unavailable_listing_id=item.listing_id,
                )
        Validator.require_pass(Validator().g3(plan, verdict, listings))
        store.save_plan(teen_id, plan)
        store.save_guardian_verdict(teen_id, verdict)
        records, replayed = store.commit_plan_bookings(
            teen_id=teen_id, plan=plan, verdict=verdict
        )
        teen: list[dict[str, object]] = []
        parent: list[dict[str, str]] = []
        for record in records:
            listing = listings[record.listing_id]
            teen.append(
                {
                    "listing_id": listing.listing_id,
                    "bring": "water and any equipment named by the organiser",
                    "meet": listing.venue_name,
                    "people_come_alone": listing.join_alone_ok,
                    "guest_allowed": listing.guest_allowed,
                }
            )
            parent.append(
                {
                    "listing_id": listing.listing_id,
                    "organiser": listing.provider,
                    "venue": listing.venue_name,
                    "timing": next(
                        item.session_at.isoformat()
                        for item in plan.items
                        if item.listing_id == listing.listing_id
                    ),
                    "contact": str(listing.source_url),
                }
            )
        return BrokerResult(
            records=records,
            replayed=replayed,
            teen_preparation=teen,
            parent_reassurance=parent,
        )
