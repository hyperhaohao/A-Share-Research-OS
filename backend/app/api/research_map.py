"""Industry map + global context API (V2 Phase H, 总纲 §11/§52/§77)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.market_data import resolve_instrument_id
from app.core.errors import AppError
from app.db import get_session
from app.services.research_map_service import ResearchMapService

router = APIRouter(prefix="/research-map", tags=["research-map"])


@router.get("/industry-map/{instrument_id}")
def get_industry_map(
    instrument_id: str,
    rebuild: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict:
    resolved = resolve_instrument_id(instrument_id, session, allow_remote=False)
    if resolved is None:
        raise AppError("instrument.not_found", status_code=404)
    service = ResearchMapService(session)
    snapshot = None if rebuild else service.latest_map(resolved)
    if snapshot is None:
        try:
            snapshot = service.build_industry_map(resolved)
        except KeyError:
            raise AppError(
                "industry_map.not_collected", status_code=404,
                detail="run the research pipeline first (industry profile missing)",
            ) from None
    return {"industry_map": snapshot}


@router.get("/global-context/{instrument_id}")
def get_global_context(
    instrument_id: str,
    topic: str = Query(default="macro_policy", max_length=32),
    rebuild: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict:
    resolved = resolve_instrument_id(instrument_id, session, allow_remote=False)
    if resolved is None:
        raise AppError("instrument.not_found", status_code=404)
    service = ResearchMapService(session)
    snapshot = None if rebuild else service.latest_context(resolved)
    if snapshot is None:
        try:
            snapshot = service.build_global_context(resolved, topic)
        except KeyError:
            raise AppError(
                "global_context.not_collected", status_code=404,
                detail="run the research pipeline first (macro evidence missing)",
            ) from None
    return {"global_context": snapshot}
