"""Strategy monitor API (V2 Phase G, 总纲 §23/§48/§49)."""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.strategy_monitor import StrategyMonitorRepository
from app.core.errors import AppError
from app.db import get_session, session_scope
from app.services.strategy_monitor_service import (
    StrategyMonitorRefusal,
    StrategyMonitorService,
)

router = APIRouter(prefix="/strategy-monitors", tags=["strategy-monitor"])


class MonitorFromVersionIn(BaseModel):
    version_id: str = Field(min_length=6, max_length=32)
    interval_seconds: int = Field(default=3600, ge=60, le=86400 * 7)


def _run_in_background(engine, monitor_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        try:
            StrategyMonitorService(worker_session).run_monitor(monitor_id)
        except Exception:  # noqa: BLE001 — background failure must not kill the app
            worker_session.rollback()


@router.post("", status_code=201)
def create_monitor(payload: MonitorFromVersionIn, session: Session = Depends(get_session)) -> dict:
    try:
        monitor = StrategyMonitorService(session).create_monitor(
            payload.version_id, interval_seconds=payload.interval_seconds
        )
    except KeyError:
        raise AppError("strategy.not_found", status_code=404) from None
    except StrategyMonitorRefusal as exc:
        raise AppError("monitor.gate_blocked", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"monitor": monitor}


@router.get("")
def list_monitors(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = StrategyMonitorService(session).list_monitors(limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{monitor_id}")
def get_monitor(monitor_id: str, session: Session = Depends(get_session)) -> dict:
    service = StrategyMonitorService(session)
    monitor = service.get_monitor(monitor_id)
    if monitor is None:
        raise AppError("monitor.not_found", status_code=404)
    return {
        "monitor": monitor,
        "observations": service.list_observations(monitor_id),
        "signals": service.list_signals(monitor_id),
        "decisions": service.list_decisions(monitor_id),
    }


@router.post("/{monitor_id}/run", status_code=202)
def run_monitor(monitor_id: str, session: Session = Depends(get_session)) -> dict:
    repo = StrategyMonitorRepository(session)
    if repo.get_monitor(monitor_id) is None:
        raise AppError("monitor.not_found", status_code=404)
    session.commit()
    thread = threading.Thread(
        target=_run_in_background,
        args=(session.get_bind(), monitor_id),
        daemon=True,
    )
    thread.start()
    return {"monitor_id": monitor_id, "status": "running"}
