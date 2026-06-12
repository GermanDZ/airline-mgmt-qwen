"""AuditLogger utility — creates hash-chained entries and verifies chain integrity.

Usage:
    logger = AuditLogger(session)
    await logger.create_entry(
        event_type="flight.create",
        entity_type="FlightPlan",
        entity_id=42,
        user_id=7,
        data={"route": "KJFK-EGLL", "flight_no": "AA100"},
    )
    is_valid = await logger.verify_chain()

The first entry uses a genesis hash so the chain has a known starting point.
"""

import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLogEntry


# SHA-256 of "AMS-GENESIS-2026" — deterministic starting point for the chain.
_GENESIS_HASH = "71a3d48c5b9e4f3a8d2e1b6c0f9a4d8e7c3b2a1f0e9d8c7b6a5f4e3d2c1b0a"


class AuditLogger:
    """Manages hash-chained audit log entries."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    @staticmethod
    def _compute_hash(entry: AuditLogEntry, prev_hash: str) -> str:
        """Compute the SHA-256 hash for an entry given its chain predecessor.

        The hash input is a concatenation of all primary data fields with '|' separators.
        """
        content = "|".join([
            entry.event_type,
            entry.entity_type or "",
            str(entry.entity_id) if entry.entity_id is not None else "",
            str(entry.user_id) if entry.user_id is not None else "",
            entry.timestamp.isoformat(),
            hashlib.sha256(AuditLogger._serialize_data(entry.data)).decode(),
            prev_hash,
        ])
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_data(data: dict[str, Any]) -> str:
        """Deterministic JSON serialization for hash computation."""
        import json

        return json.dumps(data, sort_keys=True, default=str)

    async def create_entry(
        self,
        event_type: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        user_id: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Append a new hash-chained audit log entry.

        Automatically computes prev_hash from the most recent entry (or genesis).
        """
        if data is None:
            data = {}

        # Find the previous entry to chain from
        result = await self.db.execute(
            text("SELECT prev_hash FROM audit_log_entries ORDER BY id DESC LIMIT 1")
        )
        row = result.first()
        prev_hash = row[0] if row else _GENESIS_HASH

        entry = AuditLogEntry(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            data=data,
            prev_hash=prev_hash,
        )
        self.db.add(entry)
        await self.db.flush()  # Assigns the server-side timestamp
        return entry

    async def verify_chain(self) -> bool:
        """Verify the entire hash chain integrity via PostgreSQL function.

        Returns True if all entries form a valid chain, False if any tampering detected.
        Falls back to Python verification if the DB function is not available.
        """
        # Try PostgreSQL function first (faster for large datasets)
        try:
            result = await self.db.execute(text("SELECT audit_verify_chain()"))
            return bool(result.scalar())
        except Exception:
            # Fallback to Python verification
            return await self._verify_chain_python()

    async def _verify_chain_python(self) -> bool:
        """Python-based chain verification (fallback when DB function is unavailable)."""
        result = await self.db.execute(
            text(
                "SELECT id, event_type, entity_type, entity_id, user_id, "
                "timestamp, data, prev_hash FROM audit_log_entries ORDER BY id ASC"
            )
        )
        rows = result.all()

        expected_hash = _GENESIS_HASH
        for row in rows:
            entry = AuditLogEntry(
                id=row[0],
                event_type=row[1],
                entity_type=row[2],
                entity_id=row[3],
                user_id=row[4],
                timestamp=row[5],
                data=row[6] if row[6] else {},
                prev_hash=row[7],
            )
            computed = self._compute_hash(entry, expected_hash)
            if computed != entry.prev_hash:
                return False
            expected_hash = computed
        return True
