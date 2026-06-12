"""Authentication utilities: JWT tokens, password hashing, RBAC dependencies."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with the given subject.

    Args:
        subject: Identifier for the token holder (typically user ID or username).
        expires_delta: Optional custom expiry. Defaults to settings access duration.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token with rotation support."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# --- RBAC model stubs (SQLAlchemy models defined in app/models/) ---

from typing import Optional  # noqa: E402

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base  # noqa: F401


class UserModel(Base):
    """User entity with password hash and RBAC membership.

    Full CRUD implementation comes in Sprint 1 (S1-T01).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    # Relationships (filled in Sprint 1)
    # roles: relationship("UserRole", back_populates="user")


class RoleModel(Base):
    """Role entity for RBAC.

    Full CRUD implementation comes in Sprint 1 (S1-T01).
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class PermissionModel(Base):
    """Permission entity for fine-grained RBAC.

    Full CRUD implementation comes in Sprint 1 (S1-T01).
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class UserRoleModel(Base):
    """Association table: User <-> Role (many-to-many)."""

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(primary_key=True)


class RolePermissionModel(Base):
    """Association table: Role <-> Permission (many-to-many)."""

    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(primary_key=True)
    permission_id: Mapped[int] = mapped_column(primary_key=True)


# --- Dependency injection for authenticated user ---

from fastapi import Depends, HTTPException, status  # noqa: E402, F402
from fastapi.security import OAuth2PasswordBearer  # noqa: E402

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Dependency that extracts and validates the JWT token, returning user info.

    Returns a dict with at least {"sub": user_id}.
    Full User model resolution comes in Sprint 1 (S1-T01).
    """
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type (expected access token)",
        )
    return {"sub": payload["sub"], **payload}
