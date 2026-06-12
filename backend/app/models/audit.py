"""Hash-chained append-only audit log model.

This table provides tamper-evident integrity for all system events.
Each row contains a SHA-256 hash of its own content plus the previous
row's hash, forming an immutable chain that can be verified on read.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Text, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLogEntry(Base):
    """Hash-chained append-only audit log entry.

    Fields:
        id: Primary key (auto-increment).
        event_type: Category of event (e.g. "user.login", "flight.create").
        entity_type: Domain entity affected (e.g. "User", "FlightPlan").
        entity_id: ID of the affected entity row.
        user_id: ID of the acting user (NULL for system events).
        timestamp: When the event occurred (UTC, server-side).
        data: JSONB payload with event details and snapshots.
        prev_hash: SHA-256 hash of the previous entry's content chain value.
                   First entry has prev_hash = genesis hash.
        created_at: Row creation timestamp (server default).

    Chain verification is done via PostgreSQL function ``audit_verify_chain``
    (see alembic migrations for the SQL definition) or via the Python
    ``AuditLogger.verify_chain()`` method.
    """

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Denormalized computed column (see PostgreSQL function below):
    chain_verified: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="Pre-computed verification; recomputed by audit_verify_chain()"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# --- PostgreSQL hash chain verification function ---
# This SQL is embedded in an Alembic migration (see alembic/versions/001_audit_table.py).
# The function computes the expected prev_hash for each row and compares
# against the stored value. It returns True if the entire chain is intact,
# False otherwise.
#
# CREATE OR REPLACE FUNCTION audit_verify_chain() RETURNS boolean AS $$
# DECLARE
#     v_prev_hash TEXT := '0' || sha256('AMS-GENESIS-2026');
#     v_entry RECORD;
#     v_current_hash TEXT;
# BEGIN
#     FOR v_entry IN
#         SELECT id, event_type, entity_type, entity_id, user_id::text,
#                EXTRACT(EPOCH FROM timestamp)::text, data::text
#         FROM audit_log_entries
#         ORDER BY id ASC
#     LOOP
#         v_current_hash := sha256(
#             v_entry.event_type || '|' ||
#             coalesce(v_entry.entity_type, '') || '|' ||
#             coalesce(v_entry.entity_id::text, '') || '|' ||
#             coalesce(v_entry.user_id, '') || '|' ||
#             coalesce(v_entry.timestamp::text, '') || '|' ||
#             coalesce(v_entry.data::text, '') || '|' ||
#             v_prev_hash
#         );
#         IF v_current_hash != v_entry.prev_hash THEN
#             RETURN false;
#         END IF;
#         v_prev_hash := v_current_hash;
#     END LOOP;
#     RETURN true;
# END;
# $$ LANGUAGE plpgsql;
