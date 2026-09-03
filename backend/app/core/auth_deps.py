"""
FastAPI dependencies for authentication and authorization.
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.auth_models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """
    Validates Bearer access token, returns the authenticated User.
    Raises 401 if missing / expired / invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    user = db.get(User, int(user_id_str))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ---------------------------------------------------------------------------
# Role requirement factories
# ---------------------------------------------------------------------------

def require_role(*roles: UserRole):
    """
    Returns a FastAPI dependency that asserts the current user has one of the
    given roles. Usage:

        @router.post("/...")
        def my_endpoint(user: User = Depends(require_role(UserRole.admin, UserRole.analyst))):
            ...
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {[r.value for r in roles]}",
            )
        return user
    return _check


# Convenience aliases
require_admin = require_role(UserRole.admin)
require_analyst_or_above = require_role(UserRole.admin, UserRole.analyst)
