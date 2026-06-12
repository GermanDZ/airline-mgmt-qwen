"""Audit logging infrastructure with SHA-256 hash chain integrity.

Provides immutable audit log entry creation and verification of
hash chain integrity per ADR-0005. Each entry's hash_prev is the
SHA-256 of the previous row's concatenated fields.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# --- Data model for audit entries ---


@dataclass(slots=True)
class AuditEntry:
    """Represents a single audit log entry.

    Attributes:
        actor_user_id: UUID of the user who performed the action.
        action: The action type (CREATE, UPDATE, DELETE, ACCESS, VALIDATE).
        entity_type: The type of entity affected.
        entity_id: UUID of the affected entity.
        snapshot: JSONB-serializable dict of entity state at time of change.
        hash_prev: SHA-256 hex digest of the previous entry's fields.
        created_at: Timestamp of when the entry was created.
    """

    actor_user_id: str
    action: str
    entity_type: str
    entity_id: str
    snapshot: dict[str, Any]
    hash_prev: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_ACCESS = "ACCESS"
    ACTION_VALIDATE = "VALIDATE"
    VALID_ACTIONS = frozenset(
        {ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE, ACTION_ACCESS, ACTION_VALIDATE}
    )

    def __post_init__(self) -> None:
        if self.action not in self.VALID_ACTIONS:
            raise ValueError(
                f"Invalid action '{self.action}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_ACTIONS))}"
            )


# --- Hash chain computation ---

_VALID_ACTIONS = frozenset(
    {"CREATE", "UPDATE", "DELETE", "ACCESS", "VALIDATE"}
)


def compute_hash_from_entry(entry: AuditEntry) -> str:
    """Compute the SHA-256 hash of an entry's fields.

    This hash is stored as `hash_prev` in the NEXT entry to form the chain.
    The hash input is a deterministic concatenation of canonical field values.

    Args:
        entry: The audit entry to hash.

    Returns:
        SHA-256 hex digest string (64 characters).
    """
    canonical = (
        str(entry.actor_user_id)
        + entry.action
        + str(entry.entity_type)
        + str(entry.entity_id)
        + _serialize_snapshot(entry.snapshot)
        + entry.created_at.isoformat()
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_prev_hash_from_entry(entry: AuditEntry) -> str:
    """Alias for compute_hash_from_entry — the output becomes the next entry's hash_prev."""
    return compute_hash_from_entry(entry)


def _serialize_snapshot(snapshot: dict[str, Any]) -> str:
    """Serialize a snapshot dict to a deterministic string for hashing.

    Keys are sorted for determinism; nested dicts are recursively sorted.

    Args:
        snapshot: The JSONB-serializable entity state.

    Returns:
        Deterministic string representation of the snapshot.
    """
    import json

    return json.dumps(snapshot, sort_keys=True, default=_json_default)


def _json_default(obj: Any) -> str:
    """JSON serializer fallback for non-standard types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


# --- Chain verification ---


def verify_chain(entries: list[AuditEntry]) -> tuple[bool, list[str]]:
    """Verify the integrity of a hash chain across audit entries.

    Checks that each entry's `hash_prev` matches the computed hash of the
    previous entry in the chain. The first entry must have an empty
    `hash_prev` (genesis entry).

    Args:
        entries: Ordered list of AuditEntry objects, sorted by creation time.

    Returns:
        Tuple of (is_valid, list_of_broken_chain_indices) where indices
        point to entries whose hash_prev does not match the expected value.
    """
    if not entries:
        return True, []

    broken_indices: list[str] = []

    for i, entry in enumerate(entries):
        if i == 0:
            # Genesis entry — no previous hash required (empty string is acceptable)
            if entry.hash_prev != "":
                broken_indices.append(
                    f"Entry {i}: genesis entry should have empty hash_prev "
                    f"(got {entry.hash_prev[:16]}...)"
                )
            continue

        expected_hash = compute_hash_from_entry(entries[i - 1])
        if entry.hash_prev != expected_hash:
            broken_indices.append(
                f"Entry {i}: expected prev_hash {expected_hash}, "
                f"got {entry.hash_prev}"
            )

    return len(broken_indices) == 0, broken_indices


def verify_chain_with_ids(entries: list[AuditEntry]) -> tuple[bool, list[str]]:
    """Like verify_chain but returns entry IDs in error messages instead of indices.

    Args:
        entries: Ordered list of AuditEntry objects.

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    if not entries:
        return True, []

    errors: list[str] = []

    for i, entry in enumerate(entries):
        if i == 0:
            if entry.hash_prev != "":
                errors.append(
                    f"Entry id={entry.actor_user_id}: genesis entry "
                    f"should have empty hash_prev (got {entry.hash_prev[:16]}...)"
                )
            continue

        expected_hash = compute_hash_from_entry(entries[i - 1])
        if entry.hash_prev != expected_hash:
            errors.append(
                f"Entry id={entry.actor_user_id}: broken chain at position "
                f"{i} — expected prev_hash {expected_hash[:16]}..., "
                f"got {entry.hash_prev[:16]}..."
            )

    return len(errors) == 0, errors


# --- Entry factory helpers ---


def create_audit_entry(
    actor_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    snapshot: dict[str, Any],
    prev_hash: str = "",
) -> AuditEntry:
    """Create a new audit log entry with the given parameters.

    Args:
        actor_user_id: UUID of the acting user.
        action: Action type (CREATE, UPDATE, DELETE, ACCESS, VALIDATE).
        entity_type: Type of the affected entity.
        entity_id: UUID of the affected entity.
        snapshot: Entity state as of this action.
        prev_hash: The hash_prev value from the previous entry.

    Returns:
        A new AuditEntry instance with computed timestamp.

    Raises:
        ValueError: If action is not a valid audit action type.
    """
    return AuditEntry(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        snapshot=snapshot,
        hash_prev=prev_hash,
    )


def build_chain(
    actor_user_id: str,
    entries_data: list[tuple[str, str, dict[str, Any]]],
) -> list[AuditEntry]:
    """Build a chain of audit entries where each entry's hash_prev points to
    the previous entry.

    Args:
        actor_user_id: UUID of the user performing all actions.
        entries_data: List of (action, entity_type, snapshot) tuples.
            Each subsequent entry will auto-link its hash_prev to the
            previous entry's computed hash.

    Returns:
        Ordered list of AuditEntry instances forming a valid chain.
    """
    entries: list[AuditEntry] = []
    for i, (action, entity_type, snapshot) in enumerate(entries_data):
        prev_hash = "" if i == 0 else compute_hash_from_entry(entries[-1])
        entry = create_audit_entry(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id="00000000-0000-0000-0000-000000000000",
            snapshot=snapshot,
            prev_hash=prev_hash,
        )
        entries.append(entry)
    return entries
