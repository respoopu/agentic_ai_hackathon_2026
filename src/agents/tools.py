"""Fail-closed per-component tool permissions."""

from __future__ import annotations

from dataclasses import dataclass

COMPONENT_PERMISSIONS = {
    "intake": {
        "reads": frozenset({"declared_input"}),
        "writes": frozenset({"Personal Data.setup"}),
        "gates": frozenset({"I0"}),
    },
    "planner": {
        "reads": frozenset({"CKB", "Personal Data"}),
        "writes": frozenset(),
        "gates": frozenset({"G1", "G2"}),
    },
    "discovery": {
        "reads": frozenset({"CKB", "external_sources"}),
        "writes": frozenset({"CKB.ListingRecord"}),
        "gates": frozenset({"G1"}),
    },
    "guardian": {
        "reads": frozenset({"approved_plan", "CKB", "Personal Data"}),
        "writes": frozenset(),
        "gates": frozenset({"G3"}),
    },
    "broker": {
        "reads": frozenset({"guardian_passed_plan"}),
        "writes": frozenset({"Personal Data.ledger", "booking_records"}),
        "gates": frozenset({"G4"}),
    },
    "observer": {
        "reads": frozenset({"AttendanceEvent", "BookingRecord", "DebriefSubmission"}),
        "writes": frozenset(
            {"Personal Data.attendance", "Personal Data.ledger", "Personal Data.preferences"}
        ),
        "gates": frozenset(),
    },
    "compliance": {
        "reads": frozenset({"CKB", "Personal Data"}),
        "writes": frozenset({"CKB.freshness", "Personal Data.plan_live_flags"}),
        "gates": frozenset(),
    },
    "validator": {
        "reads": frozenset({"inter_agent_payload_shape"}),
        "writes": frozenset({"gate_log"}),
        "gates": frozenset({"I0", "G1", "G2", "G3", "G4"}),
    },
}


class ToolPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolGuard:
    component: str

    def require(self, operation: str, resource: str) -> None:
        if self.component not in COMPONENT_PERMISSIONS:
            raise ToolPermissionError(f"unknown component {self.component}")
        allowed = COMPONENT_PERMISSIONS[self.component][operation]
        if resource not in allowed:
            raise ToolPermissionError(
                f"{self.component} cannot {operation[:-1]} {resource}"
            )
