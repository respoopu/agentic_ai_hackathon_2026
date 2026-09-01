"""Transactional runtime view over the immutable seed CKB artifact."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from src.ckb.seed_loader import load_seed_records
from src.schema.listing import ListingRecord


class KnowledgeBase:
    """SQLite runtime CKB seeded through the merged loader, never a new builder."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._memory = self._new_connection()
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS listings (
                       listing_id TEXT PRIMARY KEY,
                       verification TEXT NOT NULL,
                       freshness_state TEXT NOT NULL,
                       source_host TEXT NOT NULL,
                       record_json TEXT NOT NULL,
                       updated_at TEXT NOT NULL
                   )"""
            )

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        if self.path != ":memory:":
            connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory is not None:
            yield self._memory
            return
        connection = self._new_connection()
        try:
            yield connection
        finally:
            connection.close()

    def close(self) -> None:
        if self._memory is not None:
            self._memory.close()
            self._memory = None

    def seed(self, records: Iterable[ListingRecord]) -> int:
        inserted = 0
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for record in records:
                    cursor = connection.execute(
                        """INSERT OR IGNORE INTO listings
                           (listing_id, verification, freshness_state, source_host,
                            record_json, updated_at) VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            record.listing_id,
                            record.verification,
                            record.freshness_state,
                            record.source_url.host or "",
                            record.model_dump_json(),
                            record.last_seen_at.isoformat(),
                        ),
                    )
                    inserted += cursor.rowcount
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return inserted

    def seed_from_artifact(self, path: Path | None = None) -> int:
        records = load_seed_records(path) if path is not None else load_seed_records()
        return self.seed(records)

    def upsert_discovered(self, record: ListingRecord) -> bool:
        """Store a typed discovery record; returns False for an exact duplicate."""

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT record_json FROM listings WHERE listing_id=?", (record.listing_id,)
            ).fetchone()
            if existing is not None:
                stored = ListingRecord.model_validate_json(existing["record_json"])
                if stored == record:
                    return False
                raise ValueError(f"listing id collision for {record.listing_id}")
            connection.execute(
                "INSERT INTO listings VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.listing_id,
                    record.verification,
                    record.freshness_state,
                    record.source_url.host or "",
                    record.model_dump_json(),
                    record.last_seen_at.isoformat(),
                ),
            )
        return True

    def get(self, listing_id: str) -> ListingRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM listings WHERE listing_id=?", (listing_id,)
            ).fetchone()
        return None if row is None else ListingRecord.model_validate_json(row["record_json"])

    def all(self) -> list[ListingRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_json FROM listings ORDER BY listing_id"
            ).fetchall()
        return [ListingRecord.model_validate_json(row["record_json"]) for row in rows]

    def update_record(self, record: ListingRecord) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE listings SET verification=?, freshness_state=?, source_host=?,
                   record_json=?, updated_at=? WHERE listing_id=?""",
                (
                    record.verification,
                    record.freshness_state,
                    record.source_url.host or "",
                    record.model_dump_json(),
                    datetime.now(record.last_seen_at.tzinfo).isoformat(),
                    record.listing_id,
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError(record.listing_id)
