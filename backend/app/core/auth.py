"""Authentication utilities: JWT token management and password hashing.

Provides token creation/validation with configurable expiry,
and secure password hashing via bcrypt with salt rounds configuration.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The token subject (typically user_id or username).
        expires_delta: Optional timedelta to set token expiry.
            Defaults to 30 minutes if not provided.
        extra_claims: Additional claims to include in the token payload.

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=30)

    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, _get_secret_key(), algorithm=_get_algorithm())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode.

    Returns:
        Dictionary of claims from the token payload.

    Raises:
        ValueError: If the token is expired, invalid, or malformed.
    """
    try:
        payload = jwt.decode(
            token, _get_secret_key(), algorithms=[_get_algorithm()]
        )
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to verify.
        hashed_password: The bcrypt hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    return pwd_context.hash(password)


# --- Internal configuration (overridable for testing) ---

_SECRET_KEY: str | None = None
_ALGORITHM: str | None = None


def _get_secret_key() -> str:
    """Get the JWT secret key, with test-overridable default."""
    global _SECRET_KEY
    if _SECRET_KEY is None:
        _SECRET_KEY = "test-secret-key-for-development-only"
    return _SECRET_KEY


def _get_algorithm() -> str:
    """Get the JWT signing algorithm."""
    return "HS256"


def set_secret_key(key: str) -> None:
    """Override the secret key (for testing).

    Args:
        key: The secret key to use for token operations.
    """
    global _SECRET_KEY
    _SECRET_KEY = key
