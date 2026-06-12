"""Initial schema — RBAC tables + audit log with hash chain function.

Revision ID: 001
Revises:
Create Date: 2026-06-11

Creates all foundation tables for Sprint 0:
  - users, roles, permissions (RBAC skeleton)
  - user_roles, role_permissions (association tables)
  - audit_log_entries (hash-chained append-only log)
  - audit_verify_chain() PostgreSQL function
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all foundation tables and the audit chain verification function."""

    # --- RBAC Tables ---

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Association tables
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.Column("permission_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
    )

    # --- Audit Log Table (hash-chained, append-only) ---
    op.create_table(
        "audit_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("data", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column(
            "chain_verified", sa.Boolean(), nullable=True,
            comment="Pre-computed verification; recomputed by audit_verify_chain()"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    # Create indexes for audit log queries
    op.create_index("ix_audit_log_entries_event_type", "audit_log_entries", ["event_type"])
    op.create_index("ix_audit_log_entries_user_id", "audit_log_entries", ["user_id"])
    op.create_index("ix_audit_log_entries_timestamp", "audit_log_entries", ["timestamp"])

    # --- Audit Chain Verification Function ---
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_verify_chain() RETURNS boolean AS $$
        DECLARE
            v_prev_hash TEXT := '71a3d48c5b9e4f3a8d2e1b6c0f9a4d8e7c3b2a1f0e9d8c7b6a5f4e3d2c1b0a';
            v_entry RECORD;
            v_current_hash TEXT;
        BEGIN
            FOR v_entry IN
                SELECT id, event_type, entity_type, entity_id, user_id::text,
                       EXTRACT(EPOCH FROM timestamp)::text, data::text, prev_hash
                FROM audit_log_entries
                ORDER BY id ASC
            LOOP
                v_current_hash := sha256(
                    v_entry.event_type || '|' ||
                    coalesce(v_entry.entity_type, '') || '|' ||
                    coalesce(v_entry.entity_id::text, '') || '|' ||
                    coalesce(v_entry.user_id, '') || '|' ||
                    coalesce(v_entry.timestamp::text, '') || '|' ||
                    coalesce(v_entry.data::text, '') || '|' ||
                    v_prev_hash
                );
                IF v_current_hash != v_entry.prev_hash THEN
                    RETURN false;
                END IF;
                v_prev_hash := v_current_hash;
            END LOOP;
            RETURN true;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Remove all foundation tables and the audit function."""
    op.execute("DROP FUNCTION IF EXISTS audit_verify_chain()")
    op.drop_table("audit_log_entries")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("permissions")
    op.drop_table("roles")
