"""Provider-vetting and plan-level trusted-adult checkpoint."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime

from src.agents.tools import ToolGuard
from src.schema.listing import ListingRecord
from src.schema.plan import GuardianVerdict, Plan


class Guardian:
    allowed_tools = frozenset({"read_ckb_verification", "read_rules_consent"})

    def review(
        self,
        *,
        plan: Plan,
        listings: Mapping[str, ListingRecord],
        provider_approval_ids: dict[str, str] | None = None,
        attendance_approval_id: str | None = None,
        spend_approval_id: str | None = None,
        parental_rules: list[str] | None = None,
    ) -> GuardianVerdict:
        guard = ToolGuard("guardian")
        for resource in ("approved_plan", "CKB", "Personal Data"):
            guard.require("reads", resource)
        provider_approvals = provider_approval_ids or {}
        reasons: list[str] = []
        for item in plan.items:
            listing = listings.get(item.listing_id)
            if listing is None:
                reasons.append(f"listing_not_found:{item.listing_id}")
            elif listing.verification == "retired":
                reasons.append(f"listing_dead:{item.listing_id}")
            elif listing.verification != "verified" and not provider_approvals.get(item.listing_id):
                reasons.append(f"provider_vetting_required:{item.listing_id}")
        if attendance_approval_id is None:
            reasons.append("attendance_approval_required")
        if plan.total_cost_sgd > 0 and spend_approval_id is None:
            reasons.append("spend_approval_required")
        if "no_paid_activities" in set(parental_rules or []) and plan.total_cost_sgd > 0:
            reasons.append("parental_rule:no_paid_activities")
        reviewed_at = datetime.now(UTC)
        identity = json.dumps(
            {
                "plan_id": plan.plan_id,
                "reasons": reasons,
                "provider_approval_ids": provider_approvals,
                "attendance_approval_id": attendance_approval_id,
                "spend_approval_id": spend_approval_id,
                "reviewed_at": reviewed_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return GuardianVerdict(
            verdict_id=f"verdict_{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
            plan_id=plan.plan_id,
            approved=not reasons,
            provider_approval_ids=provider_approvals,
            attendance_approval_id=attendance_approval_id,
            spend_approval_id=spend_approval_id,
            reason_codes=reasons,
            reviewed_at=reviewed_at,
        )
