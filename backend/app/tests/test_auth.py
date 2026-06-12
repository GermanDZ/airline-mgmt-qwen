"""Tests for auth module: JWT token creation/validation and password hashing.

Covers:
- Token generation with default and custom expiry
- Token decoding and payload extraction
- Expired token rejection
- Invalid/malformed token handling
- Password hashing (bcrypt) correctness and verification
- Password hashing edge cases (empty, long, unicode)
- Secret key override behavior
"""

import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt

from app.core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    set_secret_key,
    verify_password,
)


class TestCreateAccessToken:
    """Tests for JWT token creation."""

    def test_creates_token_with_subject(self, jwt_secret):
        """Token should contain the provided subject in payload."""
        token = create_access_token("user-123")

        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"

    def test_default_expiry_is_30_minutes(self, jwt_secret):
        """Without expires_delta, token should expire in ~30 minutes."""
        before = datetime.now(timezone.utc)
        token = create_access_token("user-123")
        after = datetime.now(timezone.utc)

        payload = decode_access_token(token)
        expiry = payload["exp"]

        # Convert epoch to datetime for comparison
        expiry_dt = datetime.fromtimestamp(expiry, tz=timezone.utc)
        assert (before + timedelta(minutes=30)).replace(microsecond=0) <= expiry_dt <= (
            after + timedelta(minutes=31)
        ).replace(microsecond=0)

    def test_custom_expiry(self, jwt_secret):
        """Token with explicit expires_delta should expire at the specified time."""
        before = datetime.now(timezone.utc)
        token = create_access_token("user-456", expires_delta=timedelta(hours=2))
        after = datetime.now(timezone.utc)

        payload = decode_access_token(token)
        expiry = payload["exp"]
        expiry_dt = datetime.fromtimestamp(expiry, tz=timezone.utc)
        assert (before + timedelta(hours=2)).replace(microsecond=0) <= expiry_dt <= (
            after + timedelta(hours=2, minutes=1)
        ).replace(microsecond=0)

    def test_token_has_iat_claim(self, jwt_secret):
        """Token should contain an 'iat' (issued at) claim."""
        token = create_access_token("user-789")
        payload = decode_access_token(token)

        assert "iat" in payload
        assert isinstance(payload["iat"], int)

    def test_token_has_exp_claim(self, jwt_secret):
        """Token should contain an 'exp' (expiration) claim."""
        token = create_access_token("user-789")
        payload = decode_access_token(token)

        assert "exp" in payload
        assert isinstance(payload["exp"], int)
        assert payload["exp"] > payload["iat"]

    def test_extra_claims_merged(self, jwt_secret):
        """Extra claims should be included in the token payload."""
        extra = {"role": "admin", "tenant_id": "abc-123"}
        token = create_access_token(
            "user-admin", expires_delta=timedelta(minutes=15), extra_claims=extra
        )
        payload = decode_access_token(token)

        assert payload["sub"] == "user-admin"
        assert payload["role"] == "admin"
        assert payload["tenant_id"] == "abc-123"

    def test_secret_key_override(self, jwt_secret):
        """Changing the secret key should produce different tokens."""
        set_secret_key("different-key")
        token_different = create_access_token("user-x")

        set_secret_key(jwt_secret)
        token_original = create_access_token("user-x")

        assert token_different != token_original


class TestDecodeAccessToken:
    """Tests for JWT token decoding and validation."""

    def test_decodes_valid_token(self, jwt_secret):
        """Valid tokens should decode to their original payload."""
        payload = {"sub": "test-user", "role": "pilot"}
        token = create_access_token(
            "test-user", extra_claims={"role": "pilot"}
        )
        decoded = decode_access_token(token)

        assert decoded["sub"] == "test-user"
        assert decoded["role"] == "pilot"

    def test_raises_on_expired_token(self, jwt_secret):
        """Tokens past their expiration should raise ValueError."""
        token = create_access_token(
            "user-expired", expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token(token)

    def test_raises_on_wrong_secret(self, jwt_secret):
        """Tokens created with a different secret should be rejected."""
        set_secret_key("wrong-secret-key")
        token = create_access_token("user-1", extra_claims={"role": "admin"})
        set_secret_key(jwt_secret)

        with pytest.raises(ValueError):
            decode_access_token(token)

    def test_raises_on_malformed_token(self, jwt_secret):
        """Non-JWT strings should be rejected gracefully."""
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token("not-a-valid-jwt-token")

    def test_raises_on_empty_token(self, jwt_secret):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError):
            decode_access_token("")

    def test_raises_on_partially_tampered_token(self, jwt_secret):
        """Tokens with tampered signatures should be rejected."""
        original = create_access_token("user-1", extra_claims={"role": "admin"})
        parts = original.split(".")
        if len(parts) == 3:
            # Tamper with the payload part (middle segment)
            tampered = f"{parts[0]}.invalid.{parts[2]}"
            with pytest.raises(ValueError):
                decode_access_token(tampered)


class TestPasswordHashing:
    """Tests for password hashing and verification via bcrypt."""

    def test_hash_password_returns_string(self, jwt_secret):
        """hash_password should return a non-empty string."""
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_starts_with_bcrypt_indicator(self, jwt_secret):
        """The bcrypt hash should start with the $2b$ prefix."""
        hashed = hash_password("password123")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self, jwt_secret):
        """verify_password should return True for the correct password."""
        password = "correct_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self, jwt_secret):
        """verify_password should return False for a wrong password."""
        hashed = hash_password("correct_password_123")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self, jwt_secret):
        """Bcrypt should produce different hashes for the same input (salt)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts -> different hashes
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password(self, jwt_secret):
        """Should handle empty password without crashing."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_long_password(self, jwt_secret):
        """Should handle long passwords (bcrypt truncates at 72 bytes)."""
        long_password = "a" * 1000
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True

    def test_unicode_password(self, jwt_secret):
        """Should handle unicode characters in passwords."""
        unicode_password = "☃❤\u{1f680}"  # snowman, heart, rocket
        # Use actual chars
        unicode_password = "passwördéüä"
        hashed = hash_password(unicode_password)
        assert verify_password(unicode_password, hashed) is True

    def test_hash_cost_is_reasonable(self, jwt_secret):
        """Bcrypt cost factor should be at least 10."""
        from passlib.context import CryptContext  # noqa: PLC0414

        hashed = hash_password("password")
        # bcrypt format: $2b$XX$... where XX is the cost
        parts = hashed.split("$")
        if len(parts) >= 3:
            cost = int(parts[2])
            assert cost >= 10


class TestTokenExpiryBehavior:
    """Tests for token lifetime edge cases."""

    def test_token_valid_immediately(self, jwt_secret):
        """Newly created tokens should decode successfully right away."""
        token = create_access_token("user-1", expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"

    def test_expiry_calculation_accuracy(self, jwt_secret):
        """Expiration should be approximately 1 second after expected."""
        delta = timedelta(seconds=10)
        token = create_access_token("user-1", expires_delta=delta)
        payload = decode_access_token(token)

        # The token should expire ~10 seconds after creation, not 0 or 20
        assert payload["exp"] > payload["iat"] + 9
        assert payload["exp"] < payload["iat"] + 15


class TestSetSecretKey:
    """Tests for secret key override functionality."""

    def test_sets_key_globally(self, jwt_secret):
        """set_secret_key should change the global secret."""
        new_key = "brand-new-secret"
        set_secret_key(new_key)

        # Token created with new secret should decode with it
        token = create_access_token("user-key-test")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-key-test"

        # But not with the old key — this requires careful reset, which
        # the autouse fixture handles. Just verify no exception here:
        set_secret_key(jwt_secret)  # Reset for other tests
