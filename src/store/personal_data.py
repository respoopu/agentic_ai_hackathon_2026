"""SQLite-backed Personal Data with narrow, transactional mutation methods."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.schema.events import AttendanceEvent, BookingRecord, DebriefRecord
from src.schema.plan import (
    BudgetLedger,
    ConsentRecord,
    GuardianVerdict,
    Plan,
    PlanItem,
    SessionRequest,
)
from src.schema.preferences import PreferenceModel


class PersonalDataError(RuntimeError):
    """Base error whose message is safe to turn into an actionable response."""


class StaleLedgerVersion(PersonalDataError):
    pass


class AuthorizationError(PersonalDataError):
    pass


class LedgerConstraintError(PersonalDataError):
    pass


class ReplayConflict(PersonalDataError):
    pass


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    teen_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL UNIQUE,
    declared_age INTEGER NOT NULL CHECK (declared_age BETWEEN 13 AND 17),
    request_json TEXT NOT NULL,
    parental_rules_json TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    preferences_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_records (
    consent_id TEXT PRIMARY KEY,
    teen_id TEXT NOT NULL REFERENCES profiles(teen_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    granted INTEGER NOT NULL CHECK (granted IN (0, 1)),
    granted_by TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledgers (
    teen_id TEXT PRIMARY KEY REFERENCES profiles(teen_id) ON DELETE CASCADE,
    money_total_sgd TEXT NOT NULL,
    money_spent_sgd TEXT NOT NULL,
    money_committed_sgd TEXT NOT NULL,
    hours_per_week REAL NOT NULL,
    hours_committed REAL NOT NULL,
    tries_total INTEGER NOT NULL,
    tries_used INTEGER NOT NULL,
    tries_abandoned INTEGER NOT NULL,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS guardian_verdicts (
    verdict_id TEXT PRIMARY KEY,
    teen_id TEXT NOT NULL REFERENCES profiles(teen_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK (approved IN (0, 1)),
    verdict_json TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    teen_id TEXT NOT NULL REFERENCES profiles(teen_id) ON DELETE CASCADE,
    plan_json TEXT NOT NULL,
    is_live INTEGER NOT NULL DEFAULT 1 CHECK (is_live IN (0, 1)),
    needs_replan INTEGER NOT NULL DEFAULT 0 CHECK (needs_replan IN (0, 1)),
    flag_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_items (
    plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    listing_id TEXT NOT NULL,
    session_at TEXT NOT NULL,
    PRIMARY KEY (plan_id, listing_id, session_at)
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    teen_id TEXT NOT NULL REFERENCES profiles(teen_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL REFERENCES plans(plan_id),
    listing_id TEXT NOT NULL,
    guardian_verdict_id TEXT NOT NULL REFERENCES guardian_verdicts(verdict_id),
    status TEXT NOT NULL,
    ledger_transaction_id TEXT UNIQUE,
    logical_commitment_key TEXT NOT NULL UNIQUE,
    committed_sgd TEXT NOT NULL,
    committed_hours REAL NOT NULL,
    reconciled INTEGER NOT NULL DEFAULT 0 CHECK (reconciled IN (0, 1)),
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_transactions (
    ledger_transaction_id TEXT PRIMARY KEY,
    teen_id TEXT NOT NULL REFERENCES profiles(teen_id) ON DELETE CASCADE,
    logical_commitment_key TEXT NOT NULL UNIQUE,
    booking_id TEXT NOT NULL UNIQUE REFERENCES bookings(booking_id),
    ledger_version_before INTEGER NOT NULL,
    ledger_version_after INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance_events (
    booking_id TEXT PRIMARY KEY REFERENCES bookings(booking_id),
    attended INTEGER NOT NULL CHECK (attended IN (0, 1)),
    occurred_at TEXT NOT NULL,
    event_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS debriefs (
    booking_id TEXT PRIMARY KEY REFERENCES bookings(booking_id),
    text TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    record_json TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _json(value: Any) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class PersonalDataStore:
    """The only broad Personal Data capability; agents receive narrow methods."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._memory_connection = self._new_connection()
        self.initialize()

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            yield self._memory_connection
            return
        connection = self._new_connection()
        try:
            yield connection
        finally:
            connection.close()

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def setup_profile(
        self,
        *,
        teen_id: str,
        thread_id: str,
        declared_age: int,
        request: SessionRequest,
        ledger: BudgetLedger,
        preferences: PreferenceModel,
        consents: Sequence[ConsentRecord],
        parental_rules: Sequence[str] = (),
        constraints: dict[str, Any] | None = None,
    ) -> None:
        if not 13 <= declared_age <= 17:
            raise PersonalDataError("ineligible age must not be persisted")
        if not any(c.kind == "personal_data" and c.granted for c in consents):
            raise PersonalDataError("personal-data consent is required before persistence")
        if any(c.teen_id != teen_id for c in consents):
            raise PersonalDataError("consent record belongs to another teen")
        timestamp = _now().isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                exists = connection.execute(
                    "SELECT 1 FROM profiles WHERE teen_id = ?", (teen_id,)
                ).fetchone()
                if exists:
                    connection.execute(
                        """UPDATE profiles SET thread_id=?, declared_age=?, request_json=?,
                           parental_rules_json=?, constraints_json=?, updated_at=?
                           WHERE teen_id=?""",
                        (
                            thread_id,
                            declared_age,
                            _json(request),
                            _json(list(parental_rules)),
                            _json(constraints or {}),
                            timestamp,
                            teen_id,
                        ),
                    )
                else:
                    connection.execute(
                        """INSERT INTO profiles
                           (teen_id, thread_id, declared_age, request_json,
                            parental_rules_json, constraints_json, preferences_json,
                            created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            teen_id,
                            thread_id,
                            declared_age,
                            _json(request),
                            _json(list(parental_rules)),
                            _json(constraints or {}),
                            _json(preferences),
                            timestamp,
                            timestamp,
                        ),
                    )
                    connection.execute(
                        """INSERT INTO ledgers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        self._ledger_values(teen_id, ledger),
                    )
                for consent in consents:
                    owner = connection.execute(
                        "SELECT teen_id FROM consent_records WHERE consent_id=?",
                        (consent.consent_id,),
                    ).fetchone()
                    if owner is not None and owner["teen_id"] != teen_id:
                        raise AuthorizationError("consent id belongs to another teen")
                    connection.execute(
                        """INSERT INTO consent_records
                           (consent_id, teen_id, kind, granted, granted_by, recorded_at)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(consent_id) DO UPDATE SET
                           granted=excluded.granted, granted_by=excluded.granted_by,
                           recorded_at=excluded.recorded_at""",
                        (
                            consent.consent_id,
                            consent.teen_id,
                            consent.kind,
                            int(consent.granted),
                            consent.granted_by,
                            consent.recorded_at.isoformat(),
                        ),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _ledger_values(teen_id: str, ledger: BudgetLedger) -> tuple[Any, ...]:
        return (
            teen_id,
            str(ledger.money_total_sgd),
            str(ledger.money_spent_sgd),
            str(ledger.money_committed_sgd),
            ledger.hours_per_week,
            ledger.hours_committed,
            ledger.tries_total,
            ledger.tries_used,
            ledger.tries_abandoned,
            ledger.version,
        )

    @staticmethod
    def _ledger_from_row(row: sqlite3.Row) -> BudgetLedger:
        return BudgetLedger(
            money_total_sgd=Decimal(row["money_total_sgd"]),
            money_spent_sgd=Decimal(row["money_spent_sgd"]),
            money_committed_sgd=Decimal(row["money_committed_sgd"]),
            hours_per_week=row["hours_per_week"],
            hours_committed=row["hours_committed"],
            tries_total=row["tries_total"],
            tries_used=row["tries_used"],
            tries_abandoned=row["tries_abandoned"],
            version=row["version"],
        )

    def get_ledger(self, teen_id: str) -> BudgetLedger:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ledgers WHERE teen_id = ?", (teen_id,)
            ).fetchone()
        if row is None:
            raise PersonalDataError(f"unknown teen {teen_id}")
        return self._ledger_from_row(row)

    def planner_snapshot(self, teen_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            profile = connection.execute(
                "SELECT * FROM profiles WHERE teen_id = ?", (teen_id,)
            ).fetchone()
            consent_rows = connection.execute(
                "SELECT kind, granted FROM consent_records WHERE teen_id = ?", (teen_id,)
            ).fetchall()
            booked_rows = connection.execute(
                """SELECT listing_id FROM bookings
                   WHERE teen_id=? AND status='booked' AND reconciled=0""",
                (teen_id,),
            ).fetchall()
        if profile is None:
            raise PersonalDataError(f"unknown teen {teen_id}")
        return {
            "request": SessionRequest.model_validate_json(profile["request_json"]),
            "ledger": self.get_ledger(teen_id),
            "preferences": PreferenceModel.model_validate_json(profile["preferences_json"]),
            "parental_rules": json.loads(profile["parental_rules_json"]),
            "constraints": json.loads(profile["constraints_json"]),
            "consent": {row["kind"]: bool(row["granted"]) for row in consent_rows},
            "booked_listing_ids": {row["listing_id"] for row in booked_rows},
        }

    def guardian_snapshot(self, teen_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            profile = connection.execute(
                """SELECT parental_rules_json, constraints_json FROM profiles
                   WHERE teen_id=?""",
                (teen_id,),
            ).fetchone()
            consents = connection.execute(
                "SELECT kind, granted FROM consent_records WHERE teen_id=?",
                (teen_id,),
            ).fetchall()
        if profile is None:
            raise PersonalDataError(f"unknown teen {teen_id}")
        constraints = json.loads(profile["constraints_json"])
        return {
            "parental_rules": json.loads(profile["parental_rules_json"]),
            "provider_approval_ids": constraints.get("provider_approval_ids", {}),
            "attendance_approval_id": constraints.get("attendance_approval_id"),
            "spend_approval_id": constraints.get("spend_approval_id"),
            "consent": {row["kind"]: bool(row["granted"]) for row in consents},
        }

    def profile_identity(self, teen_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT teen_id, thread_id, declared_age FROM profiles WHERE teen_id=?",
                (teen_id,),
            ).fetchone()
        if row is None:
            raise PersonalDataError(f"unknown teen {teen_id}")
        return dict(row)

    def get_booking(self, booking_id: str) -> BookingRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM bookings WHERE booking_id=?", (booking_id,)
            ).fetchone()
        if row is None:
            raise PersonalDataError(f"unknown booking {booking_id}")
        return BookingRecord.model_validate_json(row["record_json"])

    def save_plan(self, teen_id: str, plan: Plan, *, live: bool = True) -> None:
        timestamp = _now().isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                owner = connection.execute(
                    "SELECT teen_id, plan_json FROM plans WHERE plan_id=?", (plan.plan_id,)
                ).fetchone()
                if owner is not None and owner["teen_id"] != teen_id:
                    raise ReplayConflict("plan id belongs to another teen")
                if owner is not None and Plan.model_validate_json(owner["plan_json"]) != plan:
                    raise ReplayConflict("plan id collision with different plan content")
                connection.execute(
                    """INSERT INTO plans (plan_id, teen_id, plan_json, is_live, created_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(plan_id) DO UPDATE SET plan_json=excluded.plan_json,
                       is_live=excluded.is_live""",
                    (plan.plan_id, teen_id, _json(plan), int(live), timestamp),
                )
                connection.execute("DELETE FROM plan_items WHERE plan_id = ?", (plan.plan_id,))
                connection.executemany(
                    "INSERT INTO plan_items (plan_id, listing_id, session_at) VALUES (?, ?, ?)",
                    [
                        (plan.plan_id, item.listing_id, item.session_at.isoformat())
                        for item in plan.items
                    ],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def save_guardian_verdict(self, teen_id: str, verdict: GuardianVerdict) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                owner = connection.execute(
                    """SELECT teen_id, verdict_json FROM guardian_verdicts
                       WHERE verdict_id=?""",
                    (verdict.verdict_id,),
                ).fetchone()
                if owner is not None and owner["teen_id"] != teen_id:
                    raise ReplayConflict("verdict id belongs to another teen")
                if (
                    owner is not None
                    and GuardianVerdict.model_validate_json(owner["verdict_json"]) != verdict
                ):
                    raise ReplayConflict("verdict id collision with different authorization")
                connection.execute(
                    """INSERT OR IGNORE INTO guardian_verdicts
                       (verdict_id, teen_id, plan_id, approved, verdict_json, reviewed_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        verdict.verdict_id,
                        teen_id,
                        verdict.plan_id,
                        int(verdict.approved),
                        _json(verdict),
                        verdict.reviewed_at.isoformat(),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def logical_commitment_key(plan: Plan, item: PlanItem) -> str:
        return "|".join(
            (plan.plan_id, item.listing_id, item.session_at.isoformat(), str(item.cost_sgd))
        )

    @classmethod
    def stable_transaction_id(cls, plan: Plan, item: PlanItem) -> str:
        digest = hashlib.sha256(cls.logical_commitment_key(plan, item).encode()).hexdigest()
        return f"ledger_{digest[:24]}"

    def commit_booking(
        self,
        *,
        teen_id: str,
        plan: Plan,
        item: PlanItem,
        verdict: GuardianVerdict,
        transaction_id: str | None = None,
    ) -> tuple[BookingRecord, bool]:
        """Commit once. Returns ``(record, replayed)``."""

        if len(plan.items) != 1:
            raise PersonalDataError("use commit_plan_bookings for a multi-item plan")

        expected_transaction = self.stable_transaction_id(plan, item)
        tx_id = transaction_id or expected_transaction
        if tx_id != expected_transaction:
            raise ReplayConflict("transaction id does not match the logical commitment")
        if item not in plan.items:
            raise PersonalDataError("booking item is not part of the approved plan")
        if not verdict.approved or verdict.plan_id != plan.plan_id:
            raise AuthorizationError("approved Guardian verdict must match the plan")

        logical_key = self.logical_commitment_key(plan, item)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                replay = connection.execute(
                    "SELECT logical_commitment_key, record_json FROM bookings WHERE ledger_transaction_id = ?",
                    (tx_id,),
                ).fetchone()
                if replay is not None:
                    if replay["logical_commitment_key"] != logical_key:
                        raise ReplayConflict("transaction id was used for another commitment")
                    connection.commit()
                    return BookingRecord.model_validate_json(replay["record_json"]), True

                stored_verdict = connection.execute(
                    """SELECT approved, plan_id FROM guardian_verdicts
                       WHERE verdict_id = ? AND teen_id = ?""",
                    (verdict.verdict_id, teen_id),
                ).fetchone()
                if (
                    stored_verdict is None
                    or not stored_verdict["approved"]
                    or stored_verdict["plan_id"] != plan.plan_id
                ):
                    raise AuthorizationError("Guardian verdict is missing, rejected, or mismatched")

                ledger_row = connection.execute(
                    "SELECT * FROM ledgers WHERE teen_id = ?", (teen_id,)
                ).fetchone()
                if ledger_row is None:
                    raise PersonalDataError(f"unknown teen {teen_id}")
                ledger = self._ledger_from_row(ledger_row)
                if ledger.version != plan.ledger_version:
                    raise StaleLedgerVersion(
                        f"ledger changed from version {plan.ledger_version} to {ledger.version}; replan"
                    )
                if item.cost_sgd > ledger.money_remaining_sgd:
                    raise LedgerConstraintError("booking exceeds remaining money")
                if item.duration_hours > ledger.hours_remaining:
                    raise LedgerConstraintError("booking exceeds remaining weekly hours")
                if ledger.tries_remaining < 1:
                    raise LedgerConstraintError("no exploration tries remain")

                booking_digest = hashlib.sha256(tx_id.encode()).hexdigest()[:20]
                record = BookingRecord(
                    booking_id=f"booking_{booking_digest}",
                    plan_id=plan.plan_id,
                    listing_id=item.listing_id,
                    guardian_verdict_id=verdict.verdict_id,
                    status="booked",
                    ledger_transaction_id=tx_id,
                    committed_sgd=item.cost_sgd,
                    committed_hours=item.duration_hours,
                    created_at=_now(),
                )
                next_version = ledger.version + 1
                connection.execute(
                    """UPDATE ledgers SET money_committed_sgd=?, hours_committed=?,
                       tries_used=?, version=? WHERE teen_id=? AND version=?""",
                    (
                        str(ledger.money_committed_sgd + item.cost_sgd),
                        ledger.hours_committed + item.duration_hours,
                        ledger.tries_used + 1,
                        next_version,
                        teen_id,
                        ledger.version,
                    ),
                )
                connection.execute(
                    """INSERT INTO bookings
                       (booking_id, teen_id, plan_id, listing_id, guardian_verdict_id,
                        status, ledger_transaction_id, logical_commitment_key,
                        committed_sgd, committed_hours, record_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.booking_id,
                        teen_id,
                        plan.plan_id,
                        item.listing_id,
                        verdict.verdict_id,
                        record.status,
                        tx_id,
                        logical_key,
                        str(item.cost_sgd),
                        item.duration_hours,
                        _json(record),
                        record.created_at.isoformat(),
                    ),
                )
                connection.execute(
                    """INSERT INTO ledger_transactions VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tx_id,
                        teen_id,
                        logical_key,
                        record.booking_id,
                        ledger.version,
                        next_version,
                        record.created_at.isoformat(),
                    ),
                )
                connection.commit()
                return record, False
            except Exception:
                connection.rollback()
                raise

    def commit_plan_bookings(
        self,
        *,
        teen_id: str,
        plan: Plan,
        verdict: GuardianVerdict,
    ) -> tuple[list[BookingRecord], bool]:
        """Atomically commit every item in one approved Plan.

        The ledger version is checked once and incremented once. Each logical
        item still receives its own deterministic idempotency key, so a replay
        can return the exact stored records without repeating any side effect.
        """

        if not verdict.approved or verdict.plan_id != plan.plan_id:
            raise AuthorizationError("approved Guardian verdict must match the plan")
        logical = [self.logical_commitment_key(plan, item) for item in plan.items]
        transactions = [self.stable_transaction_id(plan, item) for item in plan.items]
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                placeholders = ",".join("?" for _ in transactions)
                existing = connection.execute(
                    f"SELECT ledger_transaction_id, logical_commitment_key, record_json "
                    f"FROM bookings WHERE ledger_transaction_id IN ({placeholders})",
                    transactions,
                ).fetchall()
                if existing:
                    if len(existing) != len(plan.items):
                        raise ReplayConflict("partial plan replay detected")
                    by_transaction = {row["ledger_transaction_id"]: row for row in existing}
                    records: list[BookingRecord] = []
                    for tx_id, logical_key in zip(transactions, logical, strict=True):
                        row = by_transaction.get(tx_id)
                        if row is None or row["logical_commitment_key"] != logical_key:
                            raise ReplayConflict("transaction id was used for another commitment")
                        records.append(BookingRecord.model_validate_json(row["record_json"]))
                    connection.commit()
                    return records, True

                stored_verdict = connection.execute(
                    """SELECT approved, plan_id FROM guardian_verdicts
                       WHERE verdict_id = ? AND teen_id = ?""",
                    (verdict.verdict_id, teen_id),
                ).fetchone()
                if (
                    stored_verdict is None
                    or not stored_verdict["approved"]
                    or stored_verdict["plan_id"] != plan.plan_id
                ):
                    raise AuthorizationError("Guardian verdict is missing, rejected, or mismatched")
                ledger_row = connection.execute(
                    "SELECT * FROM ledgers WHERE teen_id = ?", (teen_id,)
                ).fetchone()
                if ledger_row is None:
                    raise PersonalDataError(f"unknown teen {teen_id}")
                ledger = self._ledger_from_row(ledger_row)
                if ledger.version != plan.ledger_version:
                    raise StaleLedgerVersion(
                        f"ledger changed from version {plan.ledger_version} to {ledger.version}; replan"
                    )
                total_hours = sum(item.duration_hours for item in plan.items)
                if plan.total_cost_sgd > ledger.money_remaining_sgd:
                    raise LedgerConstraintError("plan exceeds remaining money")
                if total_hours > ledger.hours_remaining:
                    raise LedgerConstraintError("plan exceeds remaining weekly hours")
                if len(plan.items) > ledger.tries_remaining:
                    raise LedgerConstraintError("plan exceeds remaining exploration tries")

                created_at = _now()
                next_version = ledger.version + 1
                records = []
                for item, logical_key, tx_id in zip(
                    plan.items, logical, transactions, strict=True
                ):
                    booking_digest = hashlib.sha256(tx_id.encode()).hexdigest()[:20]
                    record = BookingRecord(
                        booking_id=f"booking_{booking_digest}",
                        plan_id=plan.plan_id,
                        listing_id=item.listing_id,
                        guardian_verdict_id=verdict.verdict_id,
                        status="booked",
                        ledger_transaction_id=tx_id,
                        committed_sgd=item.cost_sgd,
                        committed_hours=item.duration_hours,
                        created_at=created_at,
                    )
                    connection.execute(
                        """INSERT INTO bookings
                           (booking_id, teen_id, plan_id, listing_id, guardian_verdict_id,
                            status, ledger_transaction_id, logical_commitment_key,
                            committed_sgd, committed_hours, record_json, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            record.booking_id,
                            teen_id,
                            plan.plan_id,
                            item.listing_id,
                            verdict.verdict_id,
                            record.status,
                            tx_id,
                            logical_key,
                            str(item.cost_sgd),
                            item.duration_hours,
                            _json(record),
                            created_at.isoformat(),
                        ),
                    )
                    connection.execute(
                        "INSERT INTO ledger_transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            tx_id,
                            teen_id,
                            logical_key,
                            record.booking_id,
                            ledger.version,
                            next_version,
                            created_at.isoformat(),
                        ),
                    )
                    records.append(record)
                connection.execute(
                    """UPDATE ledgers SET money_committed_sgd=?, hours_committed=?,
                       tries_used=?, version=? WHERE teen_id=? AND version=?""",
                    (
                        str(ledger.money_committed_sgd + plan.total_cost_sgd),
                        ledger.hours_committed + total_hours,
                        ledger.tries_used + len(plan.items),
                        next_version,
                        teen_id,
                        ledger.version,
                    ),
                )
                connection.commit()
                return records, False
            except Exception:
                connection.rollback()
                raise

    def record_outcome(
        self,
        *,
        teen_id: str,
        event: AttendanceEvent,
        preferences: PreferenceModel,
        debrief: DebriefRecord | None = None,
    ) -> bool:
        """Reconcile one booking outcome atomically. False means exact replay."""

        if debrief is not None and debrief.booking_id != event.booking_id:
            raise PersonalDataError("debrief and attendance refer to different bookings")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT attended FROM attendance_events WHERE booking_id = ?",
                    (event.booking_id,),
                ).fetchone()
                if existing is not None:
                    if bool(existing["attended"]) != event.attended:
                        raise ReplayConflict("attendance outcome conflicts with stored event")
                    connection.commit()
                    return False
                booking = connection.execute(
                    """SELECT committed_sgd, committed_hours, reconciled
                       FROM bookings WHERE booking_id = ? AND teen_id = ?""",
                    (event.booking_id, teen_id),
                ).fetchone()
                if booking is None:
                    raise PersonalDataError("attendance references an unknown booking")
                if booking["reconciled"]:
                    raise ReplayConflict("booking was reconciled without its event")
                ledger_row = connection.execute(
                    "SELECT * FROM ledgers WHERE teen_id = ?", (teen_id,)
                ).fetchone()
                if ledger_row is None:
                    raise PersonalDataError(f"unknown teen {teen_id}")
                ledger = self._ledger_from_row(ledger_row)
                committed = Decimal(booking["committed_sgd"])
                hours = float(booking["committed_hours"])
                connection.execute(
                    """UPDATE ledgers SET money_spent_sgd=?, money_committed_sgd=?,
                       hours_committed=?, tries_abandoned=?, version=? WHERE teen_id=?""",
                    (
                        str(ledger.money_spent_sgd + committed),
                        str(ledger.money_committed_sgd - committed),
                        max(0.0, ledger.hours_committed - hours),
                        ledger.tries_abandoned + (0 if event.attended else 1),
                        ledger.version + 1,
                        teen_id,
                    ),
                )
                connection.execute(
                    "INSERT INTO attendance_events VALUES (?, ?, ?, ?)",
                    (
                        event.booking_id,
                        int(event.attended),
                        event.occurred_at.isoformat(),
                        _json(event),
                    ),
                )
                if debrief is not None:
                    connection.execute(
                        "INSERT INTO debriefs VALUES (?, ?, ?, ?)",
                        (
                            debrief.booking_id,
                            debrief.text,
                            debrief.submitted_at.isoformat(),
                            _json(debrief),
                        ),
                    )
                connection.execute(
                    "UPDATE profiles SET preferences_json=?, updated_at=? WHERE teen_id=?",
                    (_json(preferences), _now().isoformat(), teen_id),
                )
                connection.execute(
                    "UPDATE bookings SET reconciled=1 WHERE booking_id=?",
                    (event.booking_id,),
                )
                connection.commit()
                return True
            except Exception:
                connection.rollback()
                raise

    def flag_dead_listing(self, listing_id: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """SELECT p.plan_id, p.teen_id FROM plans p
                       JOIN plan_items i ON i.plan_id = p.plan_id
                       WHERE i.listing_id = ? AND p.is_live = 1""",
                    (listing_id,),
                ).fetchall()
                connection.execute(
                    """UPDATE plans SET needs_replan=1, flag_reason=?
                       WHERE plan_id IN (SELECT plan_id FROM plan_items WHERE listing_id=?)
                       AND is_live=1""",
                    (f"listing_dead:{listing_id}", listing_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return [dict(row) for row in rows]

    def live_listing_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT DISTINCT i.listing_id FROM plan_items i
                   JOIN plans p ON p.plan_id=i.plan_id WHERE p.is_live=1"""
            ).fetchall()
        return {row["listing_id"] for row in rows}
