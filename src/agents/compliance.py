"""Manually triggered, off-request-path listing freshness monitor."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import datetime

from pydantic import Field

from src.ckb.store import KnowledgeBase
from src.constants import MAX_FETCHES_PER_DOMAIN, MAX_LISTINGS_PER_SCAN
from src.schema.plan import StrictModel
from src.store.personal_data import PersonalDataStore


class ComplianceResult(StrictModel):
    trigger: str = "manual_poc"
    request_path_blocked: bool = False
    listings_scanned: int = Field(ge=0, le=MAX_LISTINGS_PER_SCAN)
    max_fetches_for_any_domain: int = Field(ge=0, le=MAX_FETCHES_PER_DOMAIN)
    retired_listing_ids: list[str] = Field(default_factory=list)
    flagged_plans: list[dict[str, str]] = Field(default_factory=list)


class Compliance:
    allowed_tools = frozenset({"read_ckb", "check_source", "update_freshness", "flag_live_plan"})

    def scan(
        self,
        *,
        ckb: KnowledgeBase,
        personal_data: PersonalDataStore,
        source_is_alive: Callable[[str], bool],
        now: datetime,
    ) -> ComplianceResult:
        fetches: Counter[str] = Counter()
        retired: list[str] = []
        flagged: list[dict[str, str]] = []
        scanned = 0
        for record in ckb.all():
            if scanned >= MAX_LISTINGS_PER_SCAN:
                break
            host = record.source_url.host or ""
            if fetches[host] >= MAX_FETCHES_PER_DOMAIN:
                continue
            # Fictional quarantine fixtures stay unverified; their schema
            # intentionally forbids claiming a real retired verification state.
            if record.is_fictional or record.verification == "retired":
                continue
            fetches[host] += 1
            scanned += 1
            if source_is_alive(str(record.source_url)):
                refreshed = record.model_copy(update={"last_seen_at": now})
                ckb.update_record(refreshed)
                continue
            dead = record.model_copy(
                update={"verification": "retired", "freshness_state": "dead", "last_seen_at": now}
            )
            # Re-validate copied models because Pydantic model_copy is intentionally
            # non-validating and this is a storage boundary.
            dead = type(record).model_validate(dead.model_dump())
            ckb.update_record(dead)
            retired.append(record.listing_id)
            flagged.extend(personal_data.flag_dead_listing(record.listing_id))
        return ComplianceResult(
            listings_scanned=scanned,
            max_fetches_for_any_domain=max(fetches.values(), default=0),
            retired_listing_ids=retired,
            flagged_plans=flagged,
        )
