"""Health / liveness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/ready")
def readiness() -> dict:
    """Readiness: verifies DB access and repository availability."""
    from app.db import get_session_factory
    from sqlalchemy import text as _text

    try:
        factory = get_session_factory()
        session = factory()
        try:
            session.execute(_text("SELECT 1"))
        finally:
            session.close()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "error",
        "database": db_ok,
    }


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
    }
