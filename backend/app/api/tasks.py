"""Tasks + scheduler API (M18)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.scheduler.scheduler import Scheduler
from app.scheduler.tasks import TaskRepository, TaskType
from app.api.market_data import resolve_instrument_id

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    instrument: str = Field(min_length=4, max_length=64)
    task_type: TaskType
    schedule: str | None = Field(default=None, max_length=64)
    research_level: str = Field(default="standard", max_length=32)


def _task_payload(task) -> dict:
    return {
        "task_id": task.task_id,
        "instrument_id": task.instrument_id,
        "task_type": task.task_type.value,
        "schedule": task.schedule,
        "research_level": task.research_level,
        "enabled": task.enabled,
        "status": task.status.value,
        "attempts": task.attempts,
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
    }


@router.post("", status_code=201)
def create_task(payload: TaskIn, session: Session = Depends(get_session)) -> dict:
    instrument_id = resolve_instrument_id(payload.instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    task = TaskRepository(session).create(
        instrument_id=instrument_id,
        task_type=payload.task_type,
        schedule=payload.schedule,
        research_level=payload.research_level,
    )
    return {"task": _task_payload(task)}


@router.get("")
def list_tasks(
    enabled: bool | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    tasks = TaskRepository(session).list_all(enabled=enabled)
    return {"count": len(tasks), "results": [_task_payload(t) for t in tasks]}


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    enabled: bool = Query(...),
    session: Session = Depends(get_session),
) -> dict:
    task = TaskRepository(session).set_enabled(task_id, enabled)
    if task is None:
        raise AppError("task.not_found", status_code=404)
    return {"task": _task_payload(task)}


@router.post("/scheduler/tick")
def scheduler_tick(session: Session = Depends(get_session)) -> dict:
    """One scheduler pass: recovery → claim due tasks → run → complete."""
    result = Scheduler(session).tick()
    return {
        "now": result.now,
        "claimed": result.claimed,
        "succeeded": result.succeeded,
        "failed": result.failed,
        "skipped_busy": result.skipped_busy,
        "recovered": result.recovered,
    }
