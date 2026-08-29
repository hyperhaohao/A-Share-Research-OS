"""Tasks + scheduler API (M18; PW0/PW2: delete, run-now, schedule specs)."""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session, session_scope
from app.domain.evidence import utc_now
from app.scheduler.scheduler import HANDLERS, Scheduler
from app.scheduler.tasks import TaskRepository, TaskType, validate_schedule

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
    if payload.schedule is not None:
        try:
            validate_schedule(payload.schedule)
        except ValueError as exc:
            raise AppError(
                "task.schedule_invalid", status_code=422, detail=str(exc)
            ) from None
    from app.services.instrument_service import InstrumentService

    instrument_id = InstrumentService(session).resolve_id(payload.instrument)
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


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, session: Session = Depends(get_session)) -> None:
    """Delete the scheduling config; generated research history is kept."""
    repo = TaskRepository(session)
    task = repo.get(task_id)
    if task is None:
        raise AppError("task.not_found", status_code=404)
    if task.status.value == "running":
        raise AppError(
            "task.running", status_code=409,
            detail="task is executing; deletion is refused until it finishes",
        )
    repo.delete(task_id)


@router.post("/{task_id}/run", status_code=202)
def run_task_now(task_id: str, session: Session = Depends(get_session)) -> dict:
    """Run exactly this task now (background worker); status via GET /tasks."""
    repo = TaskRepository(session)
    task = repo.get(task_id)
    if task is None:
        raise AppError("task.not_found", status_code=404)
    if not task.enabled:
        raise AppError("task.disabled", status_code=422,
                       detail="enable the task before running it")
    if task.status.value == "running":
        raise AppError(
            "task.running", status_code=409,
            detail="task is already executing",
        )
    claimed = repo.claim(task_id, utc_now())
    if claimed is None:
        raise AppError("task.busy", status_code=409,
                       detail="another task for this instrument is running")
    # Commit the claim before the worker thread opens its own session
    # (uncommitted SQLite writes are invisible cross-connection).
    session.commit()
    thread = threading.Thread(
        target=_execute_task_in_background,
        args=(session.get_bind(), task_id),
        daemon=True,
    )
    thread.start()
    return {"task": _task_payload(claimed), "status": "running"}


def _execute_task_in_background(engine, task_id: str) -> None:
    """Worker thread: own session on the same engine; handler + completion
    mirror Scheduler.tick so API runs behave exactly like scheduled runs."""
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        repo = TaskRepository(worker_session)
        task = repo.get(task_id)
        if task is None:
            return
        handler = HANDLERS.get(task.task_type)
        try:
            if handler is None:
                raise ValueError(f"no handler for task type {task.task_type}")
            handler(worker_session, task)
            repo.complete(task_id, utc_now(), success=True)
        except Exception:  # noqa: BLE001 — failures mark the task, not the process
            # a handler may have poisoned the session (failed flush); roll
            # back so the failure mark itself can never fail — otherwise the
            # task would stay "running" until lease recovery
            worker_session.rollback()
            repo.complete(task_id, utc_now(), success=False)


@router.post("/scheduler/tick")
def scheduler_tick(session: Session = Depends(get_session)) -> dict:
    """One scheduler pass: recovery → claim due tasks → run → complete.

    Diagnostics/admin surface — the product UI drives single tasks via
    POST /tasks/{task_id}/run instead."""
    result = Scheduler(session).tick()
    return {
        "now": result.now,
        "claimed": result.claimed,
        "succeeded": result.succeeded,
        "failed": result.failed,
        "skipped_busy": result.skipped_busy,
        "recovered": result.recovered,
    }
