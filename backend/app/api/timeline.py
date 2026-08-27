"""Timeline API (M16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.market_data import resolve_instrument_id
from app.core.errors import AppError
from app.db import get_session
from app.services.timeline import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("")
def get_timeline(
    instrument: str = Query(min_length=4, max_length=64),
    kinds: str | None = Query(default=None, description="comma-separated event kinds"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    kind_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    events = TimelineService(session).build(
        instrument_id, kinds=kind_list, limit=limit, offset=offset
    )
    return {
        "instrument_id": instrument_id,
        "count": len(events),
        "results": [e.as_dict() for e in events],
    }
