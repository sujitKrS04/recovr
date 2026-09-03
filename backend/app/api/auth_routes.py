"""
Auth router: signup, login, refresh, logout, /me.

Cross-origin cookie config:
- CORS already allows http://localhost:5173 with allow_credentials=True (see main.py).
- refresh_token cookie is set with SameSite=Lax, secure=False for local HTTP dev.
  ⚠️  Set secure=True once deployed behind HTTPS.
- Frontend must send credentials:'include' on ALL fetch calls so the cookie
  is attached to /api/auth/refresh automatically.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.auth_models import Organization, RefreshToken, User, UserRole
from app.models.models import Transaction

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    org_name: str
    org_slug: str          # e.g. "acme" → used in DB slug field
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    org_id: int
    org_name: str
    org_slug: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_refresh_cookie(response: Response, raw_token: str, expires_at: datetime) -> None:
    """
    Write the httpOnly refresh token cookie.

    SameSite=Lax (or None) — works for cross-origin fetch calls (localhost:5173 -> localhost:8000).
    path="/" ensures the cookie is visible under http://localhost:8000 in browser DevTools
    and sent on all auth endpoints.
    """
    max_age = int((expires_at - _utc_now()).total_seconds())
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=False,   # ⚠️ Set secure=True when deployed over HTTPS
        max_age=max_age,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="lax",
        httponly=True,
    )


def _issue_tokens(user: User, db: Session, response: Response) -> TokenResponse:
    """Create and persist a new refresh token; mint a new access token."""
    raw, jti, expires_at = create_refresh_token(user.id)

    rt = RefreshToken(
        user_id=user.id,
        jti=jti,
        hashed_token=hash_refresh_token(raw),
        expires_at=expires_at,
    )
    db.add(rt)
    db.commit()

    access_token = create_access_token(
        subject=str(user.id),
        org_id=user.org_id,
        role=user.role.value,
    )

    _set_refresh_cookie(response, raw, expires_at)
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# POST /api/auth/signup  — create org + admin user
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)):
    # Validate slug uniqueness
    if db.query(Organization).filter(Organization.slug == body.org_slug).first():
        raise HTTPException(status_code=409, detail="Organization slug already taken.")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")

    org = Organization(slug=body.org_slug, name=body.org_name)
    db.add(org)
    db.flush()  # get org.id

    user = User(
        org_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.admin,   # first user in org gets admin
    )
    db.add(user)
    db.flush()

    # Seed 120 starter transactions for the new organization
    try:
        from scripts.generate_batch import build_records
        import random
        random.seed(org.id + 500)
        raw_records = build_records()
        for idx, rec in enumerate(raw_records):
            rec_clean = {k: v for k, v in rec.items() if not k.startswith("_")}
            rec_clean["external_payment_id"] = f"pay_{body.org_slug}_{idx+1:04d}"
            rec_clean["org_id"] = org.id
            db.add(Transaction(**rec_clean))
        db.flush()
    except Exception as e:
        import logging
        logging.warning(f"Could not seed starter transactions for org {org.id}: {e}")

    return _issue_tokens(user, db, response)


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")
    return _issue_tokens(user, db, response)


# ---------------------------------------------------------------------------
# POST /api/auth/refresh  — exchange httpOnly cookie for new access token
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    # Cookie is automatically read — frontend must send credentials:'include'
    refresh_token: str | None = Cookie(default=None),
):
    """
    Silent token refresh using the httpOnly refresh_token cookie.

    ⚠️  Frontend MUST include credentials:'include' on this fetch call —
    without it the browser will not send the cookie, causing a silent 401.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token missing or invalid.",
    )

    if not refresh_token:
        raise credentials_exc

    hashed = hash_refresh_token(refresh_token)
    rt = db.query(RefreshToken).filter(
        RefreshToken.hashed_token == hashed,
        RefreshToken.revoked == False,
    ).first()

    if not rt:
        raise credentials_exc
    if rt.expires_at < _utc_now():
        raise credentials_exc

    user = db.get(User, rt.user_id)
    if not user or not user.is_active:
        raise credentials_exc

    # Rotate: revoke old token
    rt.revoked = True
    db.flush()

    return _issue_tokens(user, db, response)


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
    current_user: User = Depends(get_current_user),
):
    if refresh_token:
        hashed = hash_refresh_token(refresh_token)
        rt = db.query(RefreshToken).filter(
            RefreshToken.hashed_token == hashed,
            RefreshToken.user_id == current_user.id,
        ).first()
        if rt:
            rt.revoked = True
            db.commit()

    _clear_refresh_cookie(response)


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, current_user.org_id)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        org_id=current_user.org_id,
        org_name=org.name if org else "",
        org_slug=org.slug if org else "",
    )
