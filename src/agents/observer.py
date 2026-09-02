"""Attendance-first longitudinal adaptation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from src.agents.tools import ToolGuard
from src.schema.events import AttendanceEvent, DebriefRecord, DebriefSubmission
from src.schema.listing import ListingRecord
from src.schema.plan import StrictModel
from src.schema.preferences import Axis, DislikeSignal, PreferenceModel
from src.store.personal_data import PersonalDataStore

TEMPORARY_PAUSE_PHRASES = (
    "exam week",
    "exams run",
    "family travel",
    "need a pause",
    "this week is too busy",
    "sick this week",
    "another booking would not help this week",
)
PROVENANCE_RANK = {"seed": 0, "debrief": 1, "attendance": 2}


def is_temporary_pause_text(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in TEMPORARY_PAUSE_PHRASES)


def _attendance_axis(current: Axis, target: float, occurred_at: datetime) -> Axis:
    same_direction = current.provenance == "attendance" and current.value * target > 0
    if same_direction:
        direction = 1 if target > 0 else -1
        value = max(-1.0, min(1.0, current.value + direction * 0.1))
        confidence = min(1.0, current.confidence + 0.05)
    else:
        value = target
        confidence = 0.75
    return Axis(
        value=value,
        confidence=confidence,
        provenance="attendance",
        updated_at=occurred_at,
    )


def _stronger_axis(current: Axis, candidate: Axis) -> Axis:
    if PROVENANCE_RANK[candidate.provenance] < PROVENANCE_RANK[current.provenance]:
        return current
    return candidate


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
                axis_updates["intensity"] = _attendance_axis(
                    preferences.intensity, 0.6, event.occurred_at
                )
            if "chill" in listing.vibes:
                axis_updates["intensity"] = _attendance_axis(
                    preferences.intensity, -0.6, event.occurred_at
                )
            if "artistic" in listing.vibes:
                axis_updates["contact_noncontact"] = _attendance_axis(
                    preferences.contact_noncontact, 0.6, event.occurred_at
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
                        proposed = Axis(
                            value=-0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
                        current = updates.get("intensity", preferences.intensity)
                        assert isinstance(current, Axis)
                        updates["intensity"] = _stronger_axis(current, proposed)
                    elif activity_vibe == "chill":
                        proposed = Axis(
                            value=0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
                        current = updates.get("intensity", preferences.intensity)
                        assert isinstance(current, Axis)
                        updates["intensity"] = _stronger_axis(current, proposed)
                    elif activity_vibe == "artistic":
                        proposed = Axis(
                            value=-0.4,
                            confidence=0.5,
                            provenance="debrief",
                            updated_at=debrief.submitted_at,
                        )
                        current = updates.get(
                            "contact_noncontact", preferences.contact_noncontact
                        )
                        assert isinstance(current, Axis)
                        updates["contact_noncontact"] = _stronger_axis(
                            current, proposed
                        )
        updates.update({"debriefs": debrief_records, "dislikes": dislikes})
        adapted = PreferenceModel.model_validate({**preferences.model_dump(), **updates})
        temporary_pause = bool(
            not event.attended
            and debrief is not None
            and is_temporary_pause_text(debrief.text)
        )
        previous_was_temporary = bool(
            len(attendance) >= 2
            and any(
                record.booking_id == attendance[-2].booking_id
                and is_temporary_pause_text(record.text)
                for record in debrief_records
            )
        )
        if temporary_pause:
            action: Literal["none", "replan", "try_to_commit", "hold_this_week"] = (
                "hold_this_week"
            )
            reasons = ["temporary_constraint_no_booking_helpful"]
        elif (
            len(attendance) >= 2
            and not attendance[-1].attended
            and not attendance[-2].attended
            and not previous_was_temporary
        ):
            action: Literal["none", "replan", "try_to_commit", "hold_this_week"] = (
                "replan"
            )
            reasons = ["two_consecutive_no_shows"]
        elif len(attendance) >= 3 and all(value.attended for value in attendance[-3:]):
            action = "try_to_commit"
            reasons = ["sustained_repeat_attendance"]
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
