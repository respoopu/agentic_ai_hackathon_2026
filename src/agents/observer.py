"""Attendance-first longitudinal adaptation."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.agents.tools import ToolGuard
from src.schema.events import AttendanceEvent, DebriefRecord, DebriefSubmission
from src.schema.listing import ListingRecord
from src.schema.plan import StrictModel
from src.schema.preferences import Axis, DislikeSignal, PreferenceModel
from src.store.personal_data import PersonalDataStore


class ObserverResult(StrictModel):
    action: Literal["none", "replan", "try_to_commit", "hold_this_week"]
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
        guard = ToolGuard("observer")
        for resource in ("AttendanceEvent", "BookingRecord", "DebriefSubmission"):
            guard.require("reads", resource)
        for resource in (
            "Personal Data.attendance",
            "Personal Data.ledger",
            "Personal Data.preferences",
        ):
            guard.require("writes", resource)
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
            if (
                listing is not None
                and any(
                    word in lower
                    for word in (
                        "boring",
                        "hate",
                        "not my thing",
                        "far",
                        "awkward",
                        "uncomfortable",
                    )
                )
            ):
                activity_vibe = next(
                    (vibe for vibe in ("sporty", "artistic", "chill") if vibe in listing.vibes),
                    "other",
                )
                signal_axis = (
                    f"vibe:{activity_vibe}" if attribution == "activity" else "activity_fit"
                )
                dislikes.append(
                    DislikeSignal(
                        axis=signal_axis,
                        listing_id=listing.listing_id,
                        provider=listing.provider if attribution == "instance" else None,
                        attribution=attribution,
                        strength=0.6,
                        recorded_at=debrief.submitted_at,
                    )
                )
                corroborating = [
                    signal
                    for signal in dislikes
                    if signal.attribution == "activity" and signal.axis == signal_axis
                ]
                if attribution == "activity" and len(corroborating) >= 2:
                    if activity_vibe == "sporty":
                        updates["intensity"] = Axis(
                            value=-0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
                    elif activity_vibe == "chill":
                        updates["intensity"] = Axis(
                            value=0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
                    elif activity_vibe == "artistic":
                        updates["contact_noncontact"] = Axis(
                            value=-0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
        updates.update({"debriefs": debrief_records, "dislikes": dislikes})
        adapted = PreferenceModel.model_validate({**preferences.model_dump(), **updates})
        lower_debrief = debrief.text.lower() if debrief is not None else ""
        temporary_pause = not event.attended and any(
            phrase in lower_debrief
            for phrase in (
                "exam week",
                "family travel",
                "this week is too busy",
                "sick this week",
                "another booking would not help this week",
            )
        )
        if len(attendance) >= 2 and not attendance[-1].attended and not attendance[-2].attended:
            action: Literal["none", "replan", "try_to_commit", "hold_this_week"] = (
                "replan"
            )
            reasons = ["two_consecutive_no_shows"]
        elif len(attendance) >= 3 and all(value.attended for value in attendance[-3:]):
            action = "try_to_commit"
            reasons = ["sustained_repeat_attendance"]
        elif temporary_pause:
            action = "hold_this_week"
            reasons = ["temporary_constraint_no_booking_helpful"]
        else:
            action = "none"
            reasons = [
                "one_no_show_recorded"
                if not event.attended
                else "insufficient_evidence_for_change"
            ]
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
