"""Auth API — multi-user authentication (部署准备：多用户认证).

Opt-in via ``ASRO_AUTH_ENABLED=true``. Default (false) keeps local dev /
E2E auth-free. When enabled, /api/v1/* requires a Bearer token except
/auth/* and /health.

First user bootstrap: register is open when the users table is empty
(creates admin). Subsequent registrations require an admin Bearer token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from sqlalchemy.orm import Session

from app.auth import (
    LoginIn,
    RegisterIn,
    UserRepository,
    create_token,
    decode_token,
    verify_password,
)
from app.config import get_settings
from app.core.errors import AppError
from app.db import get_session


def _auth_enabled() -> bool:
    return get_settings().auth_enabled

router = APIRouter(prefix="/auth", tags=["auth"])
def _get_user_from_token(request: Request) -> dict | None:
    """Decode the Bearer token from the request headers (None if absent/invalid)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return decode_token(auth_header.removeprefix("Bearer ").strip())


@router.post("/register", status_code=201)
def register(payload: RegisterIn, request: Request, session: Session = Depends(get_session)) -> dict:
    repo = UserRepository(session)
    is_first = repo.count() == 0

    if not is_first:
        # after bootstrap: only admins can create additional users (when auth is on)
        if _auth_enabled():
            token_user = _get_user_from_token(request)
            if token_user is None:
                raise AppError("auth.token_required", status_code=401,
                               detail="Bearer token required to register users")
            if token_user.get("role") != "admin":
                raise AppError("auth.admin_required", status_code=403,
                               detail="only admin can create users")
        # auth disabled: registration is open (local dev mode)

    if repo.get_by_username(payload.username) is not None:
        raise AppError("auth.username_taken", status_code=409)

    role = "admin" if is_first else payload.role
    row = repo.create_user(username=payload.username, password=payload.password, role=role)
    session.commit()
    return {"user": {"user_id": row.user_id, "username": row.username, "role": row.role}}


@router.post("/login")
def login(payload: LoginIn, session: Session = Depends(get_session)) -> dict:
    repo = UserRepository(session)
    row = repo.get_by_username(payload.username)
    if row is None or not row.enabled or not verify_password(payload.password, row.password_hash):
        raise AppError("auth.invalid_credentials", status_code=401)
    token = create_token(row.username, row.role)
    return {"access_token": token, "token_type": "bearer", "role": row.role}


@router.get("/me")
def me(request: Request, session: Session = Depends(get_session)) -> dict:
    auth_on = get_settings().auth_enabled
    if not auth_on:
        return {"username": "anonymous", "role": "admin", "auth_enabled": False}
    token_user = _get_user_from_token(request)
    if token_user is None:
        raise AppError("auth.token_required", status_code=401)
    return {
        "username": token_user["sub"],
        "role": token_user.get("role", "viewer"),
        "auth_enabled": True,
    }
