"""Attendance-first longitudinal adaptation."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.schema.events import AttendanceEvent, DebriefRecord, DebriefSubmission
from src.schema.listing import ListingRecord
from src.schema.plan import StrictModel
from src.schema.preferences import Axis, DislikeSignal, PreferenceModel
from src.store.personal_data import PersonalDataStore


class ObserverResult(StrictModel):
    action: Literal["replan", "commit", "hold_this_week"]
    persisted: bool
    reason_codes: list[str] = Field(default_factory=list)
    preferences: PreferenceModel


class Observer:
    allowed_tools = frozenset({"record_attendance", "record_debrief", "update_preferences"})

    def observe(
        self,
        *,
        teen_id: str,
        event: AttendanceEvent,
        preferences: PreferenceModel,
        store: PersonalDataStore,
        listing: ListingRecord | None = None,
        debrief: DebriefSubmission | None = None,
    ) -> ObserverResult:
        if debrief is not None and debrief.booking_id != event.booking_id:
            raise ValueError("debrief does not match attendance booking")
        attendance = [*preferences.attendance, event]
        debrief_records = list(preferences.debriefs)
        dislikes = list(preferences.dislikes)
        updates: dict[str, object] = {"attendance": attendance}
        if event.attended and listing is not None:
            axis_updates: dict[str, Axis] = {}
            if "sporty" in listing.vibes:
                axis_updates["intensity"] = Axis(
                    value=0.6, confidence=0.75, provenance="attendance", updated_at=event.occurred_at
                )
            if "chill" in listing.vibes:
                axis_updates["intensity"] = Axis(
                    value=-0.6, confidence=0.75, provenance="attendance", updated_at=event.occurred_at
                )
            if "artistic" in listing.vibes:
                axis_updates["contact_noncontact"] = Axis(
                    value=0.6, confidence=0.75, provenance="attendance", updated_at=event.occurred_at
                )
            updates.update(axis_updates)
        persisted_debrief: DebriefRecord | None = None
        if debrief is not None:
            persisted_debrief = DebriefRecord(
                booking_id=debrief.booking_id,
                text=debrief.text,
                submitted_at=debrief.submitted_at,
            )
            debrief_records.append(persisted_debrief)
            lower = debrief.text.lower()
            if any(word in lower for word in ("boring", "hate", "not my thing")):
                attribution = "activity"
            elif any(word in lower for word in ("far", "crowd", "people", "coach", "venue")):
                attribution = "instance"
            else:
                attribution = "unattributed"
            if any(word in lower for word in ("boring", "hate", "far", "awkward", "uncomfortable")):
                dislikes.append(
                    DislikeSignal(
                        axis="activity_fit",
                        listing_id=listing.listing_id if listing is not None else "unknown",
                        attribution=attribution,
                        strength=0.6,
                        recorded_at=debrief.submitted_at,
                    )
                )
        updates.update({"debriefs": debrief_records, "dislikes": dislikes})
        adapted = PreferenceModel.model_validate({**preferences.model_dump(), **updates})
        if len(attendance) >= 2 and not attendance[-1].attended and not attendance[-2].attended:
            action: Literal["replan", "commit", "hold_this_week"] = "replan"
            reasons = ["two_consecutive_no_shows"]
        elif len(attendance) >= 3 and all(value.attended for value in attendance[-3:]):
            action = "commit"
            reasons = ["sustained_repeat_attendance"]
        else:
            action = "hold_this_week"
            reasons = ["insufficient_evidence_for_change"]
        persisted = store.record_outcome(
            teen_id=teen_id,
            event=event,
            preferences=adapted,
            debrief=persisted_debrief,
        )
        return ObserverResult(
            action=action,
            persisted=persisted,
            reason_codes=reasons,
            preferences=adapted,
        )
