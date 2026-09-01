"""PII-isolated, whitelisted Discovery with deterministic cached replay."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field

from src.agents.tools import ToolGuard
from src.ckb.store import KnowledgeBase
from src.constants import DISCOVERY_ALLOWED_DOMAINS
from src.schema.listing import ListingRecord
from src.schema.plan import Plan, StrictModel
from src.validation.orchestrator import Validator


class DiscoveryResult(StrictModel):
    mode: str
    records: list[ListingRecord] = Field(default_factory=list)
    inserted: int = Field(ge=0)


class Discovery:
    allowed_tools = frozenset({"read_ckb", "fetch_whitelisted_url", "write_listing_record"})

    def __init__(self, validator: Validator | None = None) -> None:
        self.validator = validator or Validator()

    @staticmethod
    def _allowed(url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in DISCOVERY_ALLOWED_DOMAINS)

    def cached_replay(self, plan: Plan, path: str | Path, ckb: KnowledgeBase) -> DiscoveryResult:
        guard = ToolGuard("discovery")
        guard.require("reads", "CKB")
        guard.require("reads", "external_sources")
        guard.require("writes", "CKB.ListingRecord")
        self.validator.require_pass(self.validator.g1_plan(plan))
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        records = [ListingRecord.model_validate(value) for value in payload]
        disallowed = [
            str(record.source_url) for record in records if not self._allowed(str(record.source_url))
        ]
        if disallowed:
            raise PermissionError(
                "cached Discovery source is not whitelisted: " + ", ".join(disallowed)
            )
        self.validator.require_pass(self.validator.g1_records(records))
        inserted = sum(1 for record in records if ckb.upsert_discovered(record))
        return DiscoveryResult(mode="cached_replay", records=records, inserted=inserted)

    def live(
        self,
        plan: Plan,
        urls: Iterable[str],
        ckb: KnowledgeBase,
        fetch_extract: Callable[[str], ListingRecord | None],
    ) -> DiscoveryResult:
        guard = ToolGuard("discovery")
        guard.require("reads", "CKB")
        guard.require("reads", "external_sources")
        guard.require("writes", "CKB.ListingRecord")
        self.validator.require_pass(self.validator.g1_plan(plan))
        records: list[ListingRecord] = []
        for url in urls:
            if not self._allowed(url):
                raise PermissionError(f"Discovery domain is not whitelisted: {urlparse(url).hostname}")
            record = fetch_extract(url)
            if record is not None:
                records.append(record)
        self.validator.require_pass(self.validator.g1_records(records))
        inserted = sum(1 for record in records if ckb.upsert_discovered(record))
        return DiscoveryResult(mode="live", records=records, inserted=inserted)
