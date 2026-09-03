"""
Security helpers: password hashing + JWT access/refresh token generation/verification.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(
    subject: str,          # user.id as str
    org_id: int,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = _now_utc() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": org_id,
        "role": role,
        "exp": expire,
        "iat": _now_utc(),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """
    Returns (raw_token, jti, expires_at).
    - raw_token  — opaque random string placed in httpOnly cookie
    - jti        — unique ID stored in DB for revocation
    - expires_at — UTC datetime used for DB record
    """
    jti = secrets.token_urlsafe(32)
    raw = secrets.token_urlsafe(64)
    expires_at = _now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw, jti, expires_at


def hash_refresh_token(raw: str) -> str:
    """SHA-256 hash stored in DB — raw never touches the DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises JWTError if invalid/expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
