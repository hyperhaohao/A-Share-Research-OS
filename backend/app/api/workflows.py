"""Workflow Run API (V2 Phase D, 总纲 §44/§73).

经验卡 → 验证工作流：POST 立即后台执行（202），进度经 GET 轮询；
节点/指标/事件全部落库。未注册的 handoff 动作仍被显式拒绝。
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.workflow import WorkflowRepository
from app.core.errors import AppError
from app.db import get_session, session_scope
from app.quant.expression import ExpressionError
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow-runs", tags=["workflow"])


class WorkflowFromCardIn(BaseModel):
    card_id: str = Field(min_length=6, max_length=32)
    horizon_days: int = Field(default=20, ge=1, le=250)
    threshold_pct: float = Field(default=0.0, ge=-100.0, le=100.0)
    expression: str | None = Field(default=None, max_length=200)


def _execute_in_background(engine, run_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        run = WorkflowRepository(worker_session).get_run(run_id)
        if run is None:
            return
        try:
            WorkflowService(worker_session).execute(run)
        except Exception:  # noqa: BLE001 — never kill the process on a workflow
            worker_session.rollback()
            WorkflowRepository(worker_session).update_run(
                run_id, lambda p: {**p, "status": "failed", "error": "workflow execution crashed"}
            )


@router.post("/from-card", status_code=202)
def create_from_card(payload: WorkflowFromCardIn, session: Session = Depends(get_session)) -> dict:
    try:
        run = WorkflowService(session).create_from_card(
            payload.card_id,
            horizon_days=payload.horizon_days,
            threshold_pct=payload.threshold_pct,
            expression=payload.expression,
        )
    except ExpressionError as exc:
        raise AppError("workflow.expression_invalid", status_code=422, detail=str(exc)) from None
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
    results = WorkflowRepository(session).list_runs(card_id, limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = WorkflowRepository(session).get_run(run_id)
    if run is None:
        raise AppError("workflow.not_found", status_code=404)
    return {"run": run}


@router.get("/{run_id}/events")
def run_events(run_id: str, session: Session = Depends(get_session)) -> dict:
    from app.application.run_events import list_run_events

    results = list_run_events(session, run_id)
    if not results:
        raise AppError("workflow.events_not_found", status_code=404)
    return {"run_id": run_id, "count": len(results), "results": results}
