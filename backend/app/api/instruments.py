"""Instrument search / lookup API — unified through InstrumentService (PW0)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.instrument_service import InstrumentService

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _profile_payload(profile) -> dict:
    data = profile.model_dump(mode="json")
    # Explicit missing-data contract: absent analytical fields are surfaced
    # as null so clients can render "missing" instead of guessing (任务书 §8).
    for optional in ("industry", "sector", "market_cap"):
        data[optional] = data.get(optional)
    return data


@router.get("")
def search_instruments(
    query: str = Query(default="", max_length=64, description="code, name, or alias"),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    resolutions = InstrumentService(session).search(query, limit=limit)
    return {
        "query": query,
        "count": len(resolutions),
        "results": [
            {"matched_by": r.matched_by, "instrument": _profile_payload(r.instrument)}
            for r in resolutions
        ],
    }


@router.get("/{instrument_id}")
def get_instrument(instrument_id: str, session: Session = Depends(get_session)) -> dict:
    profile = InstrumentService(session).get_profile(instrument_id)
    if profile is None:
        raise AppError("instrument.not_found", status_code=404)
    return {"instrument": _profile_payload(profile)}
