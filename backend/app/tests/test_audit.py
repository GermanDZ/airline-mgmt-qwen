"""Tests for audit logging module: hash chain integrity and entry creation.

Covers:
- AuditEntry validation (action types, field requirements)
- Hash computation from entries
- Chain verification with valid chains
- Chain detection when entries are tampered with
- Genesis entry handling (no previous hash)
- Edge cases (empty list, single entry, multi-entry chains)
"""

import pytest

from app.core.audit import (
    AuditEntry,
    build_chain,
    compute_hash_from_entry,
    compute_prev_hash_from_entry,
    create_audit_entry,
    verify_chain,
    verify_chain_with_ids,
)


# --- Fixtures ---


@pytest.fixture
def valid_user_id() -> str:
    """Return a valid UUID string for test user IDs."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def valid_entity_id() -> str:
    """Return a valid UUID string for test entity IDs."""
    return "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


@pytest.fixture
def sample_snapshot() -> dict:
    """Return a sample JSONB-serializable snapshot."""
    return {
        "flight_number": "AA123",
        "departure": "JFK",
        "arrival": "LHR",
        "status": "filed",
    }


@pytest.fixture
def genesis_entry(valid_user_id: str, valid_entity_id: str, sample_snapshot: dict) -> AuditEntry:
    """Create the first entry in a hash chain (no prev_hash)."""
    return create_audit_entry(
        actor_user_id=valid_user_id,
        action=AuditEntry.ACTION_CREATE,
        entity_type="flight_plan",
        entity_id=valid_entity_id,
        snapshot=sample_snapshot,
        prev_hash="",  # Genesis entry
    )


@pytest.fixture
def second_entry(genesis_entry: AuditEntry, valid_user_id: str, sample_snapshot: dict) -> AuditEntry:
    """Create the second entry in a chain (points to genesis)."""
    return create_audit_entry(
        actor_user_id=valid_user_id,
        action=AuditEntry.ACTION_UPDATE,
        entity_type="flight_plan",
        entity_id="6ba7b810-9dad-11d1-80b4-00c04fd430c9",
        snapshot={"status": "approved"},
        prev_hash=compute_hash_from_entry(genesis_entry),
    )


# --- AuditEntry model tests ---


class TestAuditEntryModel:
    """Tests for the AuditEntry data model."""

    def test_create_valid_entry(self, valid_user_id, valid_entity_id, sample_snapshot):
        """Valid entry creation should succeed."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        assert entry.actor_user_id == valid_user_id
        assert entry.action == AuditEntry.ACTION_CREATE
        assert entry.entity_type == "flight_plan"

    def test_default_action_is_not_set(self, valid_user_id, valid_entity_id, sample_snapshot):
        """Action is a required field — should raise on missing."""
        with pytest.raises(TypeError):
            create_audit_entry(  # type: ignore[call-arg]
                actor_user_id=valid_user_id,
                entity_type="flight_plan",
                entity_id=valid_entity_id,
                snapshot=sample_snapshot,
            )

    def test_invalid_action_raises(self, valid_user_id, valid_entity_id, sample_snapshot):
        """Invalid action types should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid action"):
            create_audit_entry(
                actor_user_id=valid_user_id,
                action="INVALID_ACTION",
                entity_type="flight_plan",
                entity_id=valid_entity_id,
                snapshot=sample_snapshot,
            )

    @pytest.mark.parametrize(
        "action",
        ["CREATE", "UPDATE", "DELETE", "ACCESS", "VALIDATE"],
    )
    def test_all_valid_actions(self, valid_user_id, valid_entity_id, sample_snapshot, action):
        """All defined action types should be accepted."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=action,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        assert entry.action == action

    def test_hash_prev_defaults_to_empty(self, valid_user_id, valid_entity_id, sample_snapshot):
        """hash_prev should default to empty string."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        assert entry.hash_prev == ""


class TestHashComputation:
    """Tests for SHA-256 hash computation from audit entries."""

    def test_hash_is_64_char_hex(self, valid_user_id, valid_entity_id, sample_snapshot):
        """SHA-256 hash should be a 64-character hex string."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        h = compute_hash_from_entry(entry)
        assert len(h) == 64
        # Verify it's valid hex
        int(h, 16)

    def test_same_input_same_hash(self, valid_user_id, valid_entity_id, sample_snapshot):
        """Same entry should always produce the same hash (deterministic)."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        h1 = compute_hash_from_entry(entry)
        h2 = compute_hash_from_entry(entry)
        assert h1 == h2

    def test_different_entries_different_hash(self, valid_user_id, sample_snapshot):
        """Different entries should produce different hashes."""
        entry1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot=sample_snapshot,
        )
        entry2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-2",
            snapshot=sample_snapshot,
        )
        h1 = compute_hash_from_entry(entry1)
        h2 = compute_hash_from_entry(entry2)
        assert h1 != h2

    def test_hash_changes_with_action(self, valid_user_id, valid_entity_id, sample_snapshot):
        """Changing the action should change the hash."""
        entry_create = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        entry_update = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_UPDATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        assert compute_hash_from_entry(entry_create) != compute_hash_from_entry(entry_update)

    def test_compute_prev_hash_alias(self, valid_user_id, valid_entity_id, sample_snapshot):
        """compute_prev_hash_from_entry should be equivalent to compute_hash_from_entry."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        assert (
            compute_prev_hash_from_entry(entry) == compute_hash_from_entry(entry)
        )

    def test_hash_changes_with_snapshot(self, valid_user_id, valid_entity_id):
        """Different snapshots should produce different hashes."""
        entry1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot={"status": "filed"},
        )
        entry2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot={"status": "approved"},
        )
        assert compute_hash_from_entry(entry1) != compute_hash_from_entry(entry2)


class TestChainVerification:
    """Tests for hash chain integrity verification."""

    def test_empty_list_is_valid(self):
        """An empty list should be considered a valid (trivial) chain."""
        is_valid, errors = verify_chain([])
        assert is_valid is True
        assert errors == []

    def test_single_entry_genesis_valid(self, genesis_entry):
        """A single genesis entry with empty hash_prev is valid."""
        is_valid, errors = verify_chain([genesis_entry])
        assert is_valid is True
        assert errors == []

    def test_two_entry_chain_valid(self, genesis_entry, second_entry):
        """A properly linked two-entry chain should be valid."""
        is_valid, errors = verify_chain([genesis_entry, second_entry])
        assert is_valid is True
        assert errors == []

    def test_three_entry_chain_valid(self, valid_user_id, sample_snapshot):
        """A multi-entry chain with correct prev_hash linking should be valid."""
        e1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={"step": 1},
        )
        e2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_UPDATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={"step": 2},
            prev_hash=compute_hash_from_entry(e1),
        )
        e3 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_DELETE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={"step": 3},
            prev_hash=compute_hash_from_entry(e2),
        )
        is_valid, errors = verify_chain([e1, e2, e3])
        assert is_valid is True
        assert errors == []

    def test_tampered_second_entry_detected(self, genesis_entry):
        """Tampering with an entry's fields should break the chain."""
        # Create second entry correctly linked to genesis
        tampered_second = create_audit_entry(
            actor_user_id=genesis_entry.actor_user_id,
            action=AuditEntry.ACTION_UPDATE,  # Changed from original action
            entity_type="flight_plan",
            entity_id=genesis_entry.entity_id,
            snapshot={"status": "tampered"},
            prev_hash=compute_hash_from_entry(genesis_entry),  # Correct link
        )

        is_valid, errors = verify_chain([genesis_entry, tampered_second])
        assert is_valid is False
        assert len(errors) == 1

    def test_broken_prev_hash_on_third_entry(self, valid_user_id):
        """Wrong hash_prev on a non-first entry should be detected."""
        e1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
        )
        e2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_UPDATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
            prev_hash=compute_hash_from_entry(e1),
        )
        e3_bad = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_DELETE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
            prev_hash="0" * 64,  # Intentionally wrong hash
        )

        is_valid, errors = verify_chain([e1, e2, e3_bad])
        assert is_valid is False
        assert len(errors) == 1
        assert "Entry 2:" in errors[0]

    def test_tampered_genesis_has_wrong_prev_hash(self):
        """Genesis entry with non-empty hash_prev should be flagged."""
        fake_genesis = create_audit_entry(
            actor_user_id="user-1",
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
            prev_hash="some_hash_value",  # Genesis should have empty hash_prev
        )

        is_valid, errors = verify_chain([fake_genesis])
        assert is_valid is False
        assert len(errors) == 1
        assert "genesis" in errors[0].lower()

    def test_multiple_broken_links(self, valid_user_id):
        """Multiple tampered entries should all be reported."""
        e1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
        )
        bad_e2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_UPDATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
            prev_hash="wrong" * 13,
        )
        bad_e3 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_DELETE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
            prev_hash="wrong" * 13,
        )

        is_valid, errors = verify_chain([e1, bad_e2, bad_e3])
        assert is_valid is False
        assert len(errors) == 2


class TestChainVerificationWithIDs:
    """Tests for verify_chain_with_ids variant."""

    def test_returns_user_id_in_errors(self, valid_user_id):
        """Error messages should reference user IDs instead of indices."""
        e1 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id="id-1",
            snapshot={},
        )
        bad_e2 = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_UPDATE,
            entity_type="flight_plan",
            entity_id="id-2",
            snapshot={},
            prev_hash="0" * 64,
        )

        is_valid, errors = verify_chain_with_ids([e1, bad_e2])
        assert is_valid is False
        assert valid_user_id in errors[0]


class TestBuildChain:
    """Tests for the build_chain convenience function."""

    def test_builds_single_entry_chain(self, valid_user_id):
        """build_chain with one entry should create a valid chain."""
        entries = build_chain(valid_user_id, [
            (AuditEntry.ACTION_CREATE, "flight_plan", {"step": 1}),
        ])
        assert len(entries) == 1
        assert entries[0].hash_prev == ""

        is_valid, errors = verify_chain(entries)
        assert is_valid is True

    def test_builds_multi_entry_chain(self, valid_user_id):
        """build_chain should auto-link all entries correctly."""
        entries = build_chain(valid_user_id, [
            (AuditEntry.ACTION_CREATE, "flight_plan", {"step": 1}),
            (AuditEntry.ACTION_UPDATE, "flight_plan", {"step": 2}),
            (AuditEntry.ACTION_UPDATE, "crew_roster", {"step": 3}),
        ])
        assert len(entries) == 3

        # Verify the chain
        is_valid, errors = verify_chain(entries)
        assert is_valid is True
        assert errors == []

    def test_build_chain_entries_have_correct_fields(self, valid_user_id):
        """Each built entry should have correct action and entity_type."""
        entries = build_chain(valid_user_id, [
            ("CREATE", "flight_plan", {"origin": "JFK"}),
            ("UPDATE", "flight_plan", {"status": "approved"}),
        ])
        assert entries[0].action == "CREATE"
        assert entries[0].entity_type == "flight_plan"
        assert entries[1].action == "UPDATE"
        assert entries[1].entity_type == "flight_plan"


class TestCreateAuditEntryDefaults:
    """Tests for create_audit_entry factory function."""

    def test_creates_entry_with_all_fields(self, valid_user_id, valid_entity_id, sample_snapshot):
        """create_audit_entry should set all provided fields."""
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_ACCESS,
            entity_type="dashboard",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
            prev_hash="abc123",
        )
        assert entry.actor_user_id == valid_user_id
        assert entry.action == AuditEntry.ACTION_ACCESS
        assert entry.entity_type == "dashboard"
        assert entry.entity_id == valid_entity_id
        assert entry.snapshot == sample_snapshot
        assert entry.hash_prev == "abc123"

    def test_created_at_is_set(self, valid_user_id, valid_entity_id, sample_snapshot):
        """created_at should be set to current time."""
        import datetime  # noqa: PLC0414

        before = datetime.datetime.now(datetime.timezone.utc)
        entry = create_audit_entry(
            actor_user_id=valid_user_id,
            action=AuditEntry.ACTION_CREATE,
            entity_type="flight_plan",
            entity_id=valid_entity_id,
            snapshot=sample_snapshot,
        )
        after = datetime.datetime.now(datetime.timezone.utc)

        assert before <= entry.created_at <= after
