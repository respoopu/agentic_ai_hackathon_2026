"""Listing records and their per-request hydration.

There are two types here and the distinction matters.

`ListingRecord` is what a human transcribes from a real page and what lives in
`data/seed_ckb.json`. Every field on it is a property *of the activity*.

`Listing` is what the Planner reasons over. It is a `ListingRecord` plus three
things that only exist relative to a particular teen: how far it is from their
home, how far from their school, and who else their age is going.

v2.1 of architecture.md put `travel_min_home`, `travel_min_school` and
`peer_cohort` directly on `Listing` and treated `Listing` as the stored record.
That works with one persona and breaks with twelve across three regions, since
a stored row cannot carry a travel time that differs per reader. The split
below is the fix; §5 of architecture.md is updated to match.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

# The cohort boundary is a consent boundary, not a preference (D7).
AGE_FLOOR = 13
AGE_CEILING = 17
SG_TZ = ZoneInfo("Asia/Singapore")

ProviderType = Literal[
    "cc",  # Community Club course
    "activesg",  # ActiveSG programme, academy or club
    "third_space",  # youth hub, community art space, drop-in space
    "school",  # school facility open beyond its own students
    "commercial",  # a business, vetted
    "informal",  # basketball court, skate park, fitness corner
    "private_unverified",  # quarantine only. Never reaches a teen unapproved.
]

# Used to audit coverage of the seed set. NEVER shown back to a teen, and never
# used to filter: it biases nothing at runtime. See D10's five rules and A9.
Vibe = Literal["sporty", "artistic", "chill", "explorative"]

_WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


class Schedule(BaseModel):
    """When the thing happens.

    Transcribe the *recurrence*, not eight individual Tuesdays. `next_sessions`
    on the hydrated `Listing` is expanded from this at load time.
    """

    kind: Literal["weekly", "fixed_dates", "drop_in"]

    # kind == "weekly"
    weekday: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"] | None = None
    start_time: time | None = None
    duration_min: int | None = Field(default=None, ge=1)
    first_session: date | None = None
    num_sessions: int | None = Field(default=None, ge=1)

    # kind == "fixed_dates"
    fixed_dates: list[datetime] = Field(default_factory=list)

    # kind == "drop_in" — a court or a park. Free-text because opening hours are
    # written a hundred different ways. The two booleans below make the exact
    # evaluation slices explicit rather than attempting to parse that prose.
    open_hours_note: str | None = None
    weekday_evening_available: bool | None = None
    weekend_available: bool | None = None

    @field_validator("fixed_dates", mode="before")
    @classmethod
    def _normalise_fixed_dates(cls, values: object) -> object:
        if not isinstance(values, list):
            return values
        normalised: list[datetime] = []
        for value in values:
            parsed = (
                value if isinstance(value, datetime) else datetime.fromisoformat(value)
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=SG_TZ)
            else:
                parsed = parsed.astimezone(SG_TZ)
            normalised.append(parsed)
        return normalised

    @model_validator(mode="after")
    def _required_fields_per_kind(self) -> Schedule:
        if self.kind == "weekly":
            missing = [
                f
                for f in (
                    "weekday",
                    "start_time",
                    "duration_min",
                    "first_session",
                    "num_sessions",
                )
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(f"weekly schedule missing {', '.join(missing)}")
            assert self.weekday is not None
            assert self.first_session is not None
            if self.first_session.weekday() != _WEEKDAY_INDEX[self.weekday]:
                raise ValueError(
                    f"first_session {self.first_session} is not a declared "
                    f"{self.weekday}"
                )
        elif self.kind == "fixed_dates" and not self.fixed_dates:
            raise ValueError("fixed_dates schedule has no dates")
        elif self.kind == "drop_in":
            if not self.open_hours_note:
                raise ValueError("drop_in schedule needs an open_hours_note")
            if self.weekday_evening_available is None or self.weekend_available is None:
                raise ValueError(
                    "drop_in schedule needs explicit weekday-evening and "
                    "weekend availability"
                )
        return self

    def is_weekday_evening(self) -> bool:
        """Used by the coverage report to check adversarial scenario 2."""
        if self.kind == "drop_in":
            return bool(self.weekday_evening_available)
        if self.kind != "weekly" or self.weekday is None or self.start_time is None:
            return False
        return self.weekday in (
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
        ) and self.start_time >= time(17, 0)

    def is_weekend(self) -> bool:
        if self.kind == "drop_in":
            return bool(self.weekend_available)
        return self.kind == "weekly" and self.weekday in ("sat", "sun")


class ListingRecord(BaseModel):
    """One real activity, transcribed by hand from a page someone actually opened.

    Nothing in here depends on who is asking.
    """

    # Stored rows are an inter-component contract. Unknown fields are rejected
    # so schema drift cannot silently enter the CKB.
    model_config = ConfigDict(extra="forbid")

    listing_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_type: ProviderType

    # --- provenance. The whole set is worthless without these three. ---
    source_url: HttpUrl
    verified_at: date | None  # a human opened the page on this date
    verified_by: str | None  # and it was this person. Accountability, not credit.

    verification: Literal["verified", "unverified", "retired"]
    is_fictional: bool = False  # quarantine rows only. Enforced below.

    # --- money. 0 is common and is the point. ---
    cost_one_off_sgd: Decimal = Decimal("0")
    cost_recurring_sgd: Decimal = Decimal("0")
    equipment_cost_sgd: Decimal = Decimal("0")
    cost_total_first_session: Decimal | None = None  # derived and checked below

    # --- where. Not how far: that is per-teen, see `Listing`. ---
    venue_name: str = Field(min_length=1)
    postal_code: str  # 6 digits
    postal_sector: str = ""  # first 2 digits; filled below if not supplied
    planning_area: str = Field(min_length=1)  # URA planning area, e.g. "Toa Payoh"
    nearest_mrt: str | None = None

    # --- who it is for ---
    age_min: int = Field(ge=0, le=120)
    age_max: int = Field(ge=0, le=120)
    beginner_friendly: bool
    join_alone_ok: bool
    guest_allowed: bool

    commitment: Literal["taster", "one_off", "short_course", "term"]
    schedule: Schedule

    vibes: list[Vibe] = Field(min_length=1)  # coverage auditing only
    in_incumbent_directory: bool  # is it already on ActiveSG/Skoop/etc? Feeds B9.

    last_seen_at: datetime
    freshness_state: Literal["fresh", "stale", "dead"] = "fresh"
    notes: str | None = None

    @property
    def is_free(self) -> bool:
        return (
            self.cost_one_off_sgd == 0
            and self.cost_recurring_sgd == 0
            and self.equipment_cost_sgd == 0
        )

    @field_validator("postal_code")
    @classmethod
    def _six_digits(cls, v: str) -> str:
        if not (len(v) == 6 and v.isdigit()):
            raise ValueError(f"postal_code must be 6 digits, got {v!r}")
        return v

    @field_validator("cost_one_off_sgd", "cost_recurring_sgd", "equipment_cost_sgd")
    @classmethod
    def _non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("cost cannot be negative")
        return v

    @field_validator("verified_at")
    @classmethod
    def _not_in_the_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError(f"verified_at {v} is in the future")
        return v

    @field_validator("last_seen_at", mode="before")
    @classmethod
    def _normalise_last_seen(cls, value: object) -> datetime:
        parsed = (
            value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        )
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=SG_TZ)
        return parsed.astimezone(SG_TZ)

    @model_validator(mode="after")
    def _coherent(self) -> ListingRecord:
        if not self.postal_sector:
            self.postal_sector = self.postal_code[:2]
        elif self.postal_sector != self.postal_code[:2]:
            raise ValueError(
                f"postal_sector {self.postal_sector!r} does not match "
                f"postal_code {self.postal_code!r}"
            )

        if self.age_min > self.age_max:
            raise ValueError(f"age_min {self.age_min} > age_max {self.age_max}")

        expected_first_cost = self.cost_one_off_sgd + self.equipment_cost_sgd
        if self.cost_total_first_session is None:
            self.cost_total_first_session = expected_first_cost
        elif self.cost_total_first_session != expected_first_cost:
            raise ValueError(
                "cost_total_first_session must equal cost_one_off_sgd + "
                "equipment_cost_sgd"
            )

        # A row nobody 13-17 can attend cannot help any teen, and its presence
        # would make the age-boundary test (A11) pass vacuously.
        if self.age_max < AGE_FLOOR or self.age_min > AGE_CEILING:
            raise ValueError(
                f"age range {self.age_min}-{self.age_max} cannot overlap "
                f"{AGE_FLOOR}-{AGE_CEILING}"
            )

        # Provenance discipline. "Verified" means a named human, on a named day.
        if self.verification == "verified":
            if self.is_fictional:
                raise ValueError("a fictional listing can never be verified")
            if self.verified_at is None or not self.verified_by:
                raise ValueError("verified rows need both verified_at and verified_by")

        # The safety interlock. Invented rows exist to be caught by the vetting
        # queue on camera; one leaking out as real is the worst outcome here.
        if self.is_fictional:
            if self.verification != "unverified":
                raise ValueError("fictional rows must be verification='unverified'")
            if self.provider_type != "private_unverified":
                raise ValueError(
                    "fictional rows must be provider_type='private_unverified'"
                )
            if not (self.source_url.host or "").endswith(".invalid"):
                raise ValueError(
                    "fictional rows must use a reserved .invalid source URL"
                )

        if (self.verification == "retired") != (self.freshness_state == "dead"):
            raise ValueError(
                "verification='retired' and freshness_state='dead' must change together"
            )

        return self


class PeerCohort(BaseModel):
    """Aggregate presence. There is no identity in this object, by construction.

    Resolved at planning-area or 2-digit postal-sector level and never at school
    level; suppressed below the k-floor of 5. See architecture.md §9.3 and A12.
    """

    same_age_band: Literal["none", "few", "some", "many"]
    same_area: bool
    suppressed: bool

    @model_validator(mode="after")
    def _protect_small_buckets(self) -> PeerCohort:
        if self.same_age_band in {"none", "few"} and not self.suppressed:
            raise ValueError("none/few cohort buckets must be suppressed")
        return self


class Listing(ListingRecord):
    """A `ListingRecord` seen from one teen's position. This is what Planner ranks."""

    travel_min_home: int
    travel_min_school: int
    peer_cohort: PeerCohort | None = None
    next_sessions: list[datetime] = Field(default_factory=list)

    @field_validator("travel_min_home", "travel_min_school")
    @classmethod
    def _non_negative_travel(cls, value: int) -> int:
        if value < 0:
            raise ValueError("travel time cannot be negative")
        return value
