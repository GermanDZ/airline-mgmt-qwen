"""Tests for authentication utilities (JWT, password hashing)."""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_and_verify_roundtrip(self) -> None:
        """Hashed password should verify against the original."""
        password = "super_secret_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_hash_is_unique_per_call(self) -> None:
        """Two hashes of the same password should differ (bcrypt salt)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self) -> None:
        """Access token should encode the subject."""
        token = create_access_token(subject="user_42")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user_42"
        assert payload["type"] == "access"

    def test_create_refresh_token(self) -> None:
        """Refresh token should encode the subject with type=refresh."""
        token = create_refresh_token(subject="user_42")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user_42"
        assert payload["type"] == "refresh"

    def test_access_token_expires(self) -> None:
        """Access token should have an exp claim."""
        token = create_access_token(subject="user_42")
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_invalid_token_returns_none(self) -> None:
        """An invalid/malformed token should return None from decode_token."""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_tampered_token_returns_none(self) -> None:
        """A tampered token should be rejected."""
        token = create_access_token(subject="user_42")
        # Tamper with the signature
        parts = token.split(".")
        parts[2] = "tampered"
        tampered = ".".join(parts)
        result = decode_token(tampered)
        assert result is None

    def test_refresh_token_has_correct_expiry(self) -> None:
        """Refresh tokens should have a longer expiry than access tokens."""
        from app.core.config import get_settings

        settings = get_settings()
        short_token = create_access_token(subject="user", expires_delta=timedelta(minutes=5))
        long_token = create_refresh_token(subject="user")

        short_exp = decode_token(short_token)["exp"]
        long_exp = decode_token(long_token)["exp"]
        assert long_exp > short_exp
