"""Screening Run API (V2 Phase E, 总纲 §45/§20).

经验卡 → 全市场筛选：POST 立即后台执行（202）；候选带 Why Selected。
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.screening import ScreeningRepository
from app.core.errors import AppError
from app.db import get_session, session_scope
from app.services.screening_service import ScreeningService

router = APIRouter(prefix="/screening-runs", tags=["screening"])


class ScreeningFromCardIn(BaseModel):
    card_id: str = Field(min_length=6, max_length=32)


def _execute_in_background(engine, run_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        run = ScreeningRepository(worker_session).get_run(run_id)
        if run is None:
            return
        ScreeningService(worker_session).execute(run)


@router.post("/from-card", status_code=202)
def create_from_card(payload: ScreeningFromCardIn, session: Session = Depends(get_session)) -> dict:
    try:
        run = ScreeningService(session).create_from_card(payload.card_id)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    session.commit()
    thread = threading.Thread(
        target=_execute_in_background,
        args=(session.get_bind(), run["run_id"]),
        daemon=True,
    )
    thread.start()
    return {"run": run}


@router.get("")
def list_runs(
    card_id: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    results = ScreeningRepository(session).list_runs(card_id, limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = ScreeningRepository(session).get_run(run_id)
    if run is None:
        raise AppError("screening.not_found", status_code=404)
    return {"run": run}
