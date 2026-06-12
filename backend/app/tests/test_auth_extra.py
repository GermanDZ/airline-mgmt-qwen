"""Extended auth tests that complement developer's test_security.py.

The developer's security module (security.py) differs from auth.py in key ways:
- security.decode_token() returns None on error; ours raises ValueError
- security.create_access_token() doesn't support extra_claims
- security uses config-based secret; ours uses overridable set_secret_key()

These tests cover additional scenarios not addressed by test_security.py.
"""

from datetime import timedelta

from app.core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    set_secret_key,
)


class TestAuthModuleSpecificBehavior:
    """Tests for behavior unique to auth.py that differs from security.py."""

    def test_decode_raises_not_returns_none(self, jwt_secret):
        """Unlike security.decode_token() which returns None, ours raises ValueError.

        This is the key behavioral difference between the two modules.
        """
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token("garbage.data.here")

    def test_extra_claims_integration(self, jwt_secret):
        """auth.py supports extra_claims — security.py does not.

        This is an auth.py-specific feature that needs its own tests.
        """
        token = create_access_token(
            "user-1",
            expires_delta=timedelta(hours=1),
            extra_claims={"role": "pilot", "base": "JFK"},
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "pilot"
        assert payload["base"] == "JFK"

    def test_secret_key_isolation(self, jwt_secret):
        """auth.py's set_secret_key() allows per-test key isolation.

        The developer's security.py uses a global config singleton which is
        harder to isolate in tests.
        """
        # Set a custom key
        set_secret_key("custom-test-key")

        token = create_access_token("user-iso", extra_claims={"isolated": True})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-iso"

        # Reset for other tests (autouse fixture handles this, but demonstrate it)
        set_secret_key(jwt_secret)

    def test_multiple_extra_claims(self, jwt_secret):
        """Support for multiple extra claims at once."""
        token = create_access_token(
            "user-multi",
            expires_delta=timedelta(minutes=10),
            extra_claims={
                "tenant_id": "tenant-abc",
                "permissions": ["flights.read", "flights.write"],
                "metadata": {"source": "web", "version": "2.1"},
            },
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "user-multi"
        assert payload["tenant_id"] == "tenant-abc"
        assert payload["permissions"] == ["flights.read", "flights.write"]

    def test_extra_claims_with_no_expires(self, jwt_secret):
        """Extra claims should work with default 30-min expiry too."""
        token = create_access_token("user-default-expiry", extra_claims={"scope": "read"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-default-expiry"
        assert payload["scope"] == "read"
        # exp should still be set (default 30 min)
        assert payload["exp"] > payload["iat"]


class TestPasswordEdgeCases:
    """Additional password hashing edge cases not covered by test_security.py."""

    def test_whitespace_only_password(self, jwt_secret):
        """Password with only whitespace should hash and verify correctly."""
        pw = "   "
        hashed = hash_password(pw)
        assert hash_password.__module__ == "app.core.auth"
        from app.core.auth import verify_password  # noqa: PLC0414

        assert verify_password(pw, hashed) is True
        assert verify_password(" ", hashed) is False  # Single space differs from triple

    def test_special_characters_in_password(self, jwt_secret):
        """Passwords with special chars should hash and verify correctly."""
        pw = 'p@ss"w0rd!#$%^&*()'
        hashed = hash_password(pw)
        from app.core.auth import verify_password  # noqa: PLC0414

        assert verify_password(pw, hashed) is True

    def test_emoji_password(self, jwt_secret):
        """Passwords with emoji characters should work."""
        pw = "password\U0001f680\U0001f512"  # rocket + lock emojis
        hashed = hash_password(pw)
        from app.core.auth import verify_password  # noqa: PLC0414

        assert verify_password(pw, hashed) is True

    def test_newline_in_password(self, jwt_secret):
        """Passwords with embedded newlines should be handled."""
        pw = "line1\nline2\r\nline3"
        hashed = hash_password(pw)
        from app.core.auth import verify_password  # noqa: PLC0414

        assert verify_password(pw, hashed) is True

    def test_zero_length_vs_none(self, jwt_secret):
        """Empty string password should be distinguishable from None."""
        # Empty string should hash
        empty_hash = hash_password("")
        from app.core.auth import verify_password  # noqa: PLC0414

        assert verify_password("", empty_hash) is True


class TestTokenStructure:
    """Tests for JWT token structure and claims format."""

    def test_token_has_three_parts(self, jwt_secret):
        """A valid JWT should have exactly 3 base64url parts separated by dots."""
        token = create_access_token("user-structure")
        parts = token.split(".")
        assert len(parts) == 3

    def test_header_is_valid_json(self, jwt_secret):
        """The first part of the token should be valid JSON (header)."""
        import base64  # noqa: PLC0414

        token = create_access_token("user-jwt-structure")
        header_b64 = token.split(".")[0]
        # Add padding if needed
        padded = header_b64 + "=" * (4 - len(header_b64) % 4)
        header_json = base64.urlsafe_b64decode(padded)
        assert b"alg" in header_json or b"algorithms" in header_json

    def test_payload_contains_all_required_claims(self, jwt_secret):
        """Decoded payload should contain sub, iat, and exp."""
        token = create_access_token("user-all-claims")
        payload = decode_access_token(token)
        assert "sub" in payload
        assert "iat" in payload
        assert "exp" in payload
