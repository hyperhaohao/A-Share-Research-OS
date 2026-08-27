"""SSE stream + pipeline run API (M23) and watchlist API (§56)."""

from __future__ import annotations

import queue
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.api.market_data import resolve_instrument_id
from app.core.errors import AppError
from app.core.events import get_event_bus
from app.db import get_session
from app.services.pipeline import ResearchPipeline
from app.storage.orm import WatchlistORM

router = APIRouter(tags=["events"])


@router.post("/pipeline/run", status_code=202)
def run_pipeline(
    instrument: str = Query(min_length=4, max_length=64),
    language: str = Query(default="zh-CN", pattern="^(zh-CN|en-US)$"),
    run_id: str | None = Query(default=None, max_length=64,
                               description="client-generated id to subscribe before running"),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    try:
        outcome = ResearchPipeline(session).run(instrument_id, language=language, run_id=run_id)
    except Exception as exc:  # noqa: BLE001 — run_failed already emitted
        raise AppError("pipeline.failed", status_code=500, detail=str(exc)[:300]) from None
    return {
        "run_id": outcome.run_id,
        "snapshot_id": outcome.snapshot_id,
        "report_id": outcome.report_id,
        "gate_status": outcome.gate_status,
        "events": outcome.events,
    }


@router.get("/events/stream")
def event_stream(
    run_id: str = Query(min_length=3, max_length=64),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    _ = session
    bus = get_event_bus()
    q = bus.subscribe(run_id)

    def generator():
        try:
            # open stream with a retry hint
            yield "retry: 3000\n\n"
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield event.sse_line()
                if event.event in ("run_completed", "run_failed"):
                    break
        finally:
            bus.unsubscribe(run_id, q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# -- watchlist (§56 nav + §57 dashboard needs) -----------------------------------
class WatchlistIn(BaseModel):
    instrument: str = Field(min_length=4, max_length=64)
    note: str = Field(default="", max_length=500)


watchlist_router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@watchlist_router.post("", status_code=201)
def add_to_watchlist(payload: WatchlistIn, session: Session = Depends(get_session)) -> dict:
    instrument_id = resolve_instrument_id(payload.instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    existing = session.query(WatchlistORM).filter_by(instrument_id=instrument_id).first()
    if existing is None:
        row = WatchlistORM(
            instrument_id=instrument_id,
            note=payload.note,
            added_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.flush()
    return {"instrument_id": instrument_id, "note": payload.note}


@watchlist_router.get("")
def get_watchlist(session: Session = Depends(get_session)) -> dict:
    rows = session.query(WatchlistORM).order_by(WatchlistORM.added_at.desc()).all()
    return {
        "count": len(rows),
        "results": [
            {"instrument_id": r.instrument_id, "note": r.note, "added_at": r.added_at.isoformat()}
            for r in rows
        ],
    }


@watchlist_router.delete("/{instrument_id}", status_code=204)
def remove_from_watchlist(instrument_id: str, session: Session = Depends(get_session)) -> None:
    session.query(WatchlistORM).filter_by(instrument_id=instrument_id.upper()).delete()
    session.flush()
    return None
