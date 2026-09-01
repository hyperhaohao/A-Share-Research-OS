"""Scheduler: tick loop + business function registry (任务书 §49).

The scheduler only decides *when* — every task type maps to a business
function that is independently runnable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.domain.evidence import utc_now
from app.scheduler.tasks import TaskRepository, TaskType
from app.services.monitor import MonitorService
from app.services.pipeline import ResearchPipeline  # noqa: F401 (used by handlers below)


@dataclass
class TickResult:
    now: str
    claimed: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped_busy: list[str] = field(default_factory=list)
    recovered: list[str] = field(default_factory=list)


def run_monitor_task(session: Session, task) -> None:
    """Monitor one instrument, act on materiality (DELTA → new version,
    FULL → full pipeline) — the action dispatch lives in MonitorService
    so both the scheduler and the /monitor/run API behave identically."""
    MonitorService(session).run_monitor(task.instrument_id)


def run_full_research_task(session: Session, task) -> None:
    """Business function: FULL research pipeline for one instrument.

    This is the single Full Research implementation — the scheduler's
    PERIODIC_FULL_RESEARCH tasks and the monitor's FULL_RESEARCH decision
    both land here (整改二轮 F0.1)."""
    ResearchPipeline(session).run(task.instrument_id)


def run_prediction_validation(session: Session, task) -> None:
    """Business function: validate all due, unvalidated predictions."""
    from app.services.validation_service import ValidationService

    service = ValidationService(session)
    for prediction in service.due_unvalidated():
        try:
            service.validate(prediction.prediction_id)
        except ValueError:
            # premature (no prices yet) — stays due for the next tick
            continue


# Registry: task type → business function.
HANDLERS: dict[TaskType, Callable[[Session, object], None]] = {
    TaskType.MONITOR: run_monitor_task,
    TaskType.PERIODIC_FULL_RESEARCH: run_full_research_task,
    TaskType.PREDICTION_VALIDATION: run_prediction_validation,
}


class Scheduler:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TaskRepository(session)

    def tick(self, *, now: datetime | None = None) -> TickResult:
        now = now or utc_now()
        result = TickResult(now=now.isoformat())

        result.recovered = self._repo.recover_interrupted(now)

        for task in self._repo.due_tasks(now):
            claimed = self._repo.claim(task.task_id, now)
            if claimed is None:
                result.skipped_busy.append(task.task_id)
                continue
            result.claimed.append(task.task_id)

            handler = HANDLERS.get(task.task_type)
            try:
                if handler is None:
                    raise ValueError(f"no handler for task type {task.task_type}")
                handler(self._session, claimed)
                self._repo.complete(task.task_id, utc_now(), success=True)
                result.succeeded.append(task.task_id)
            except Exception:  # noqa: BLE001 — failures must not kill the tick
                self._repo.complete(task.task_id, utc_now(), success=False)
                result.failed.append(task.task_id)

        # strategy monitors run in the SAME background loop (§23: 后台由
        # Scheduler Worker 运行，不是页面打开才工作)
        from app.services.strategy_monitor_service import (
            StrategyMonitorRefusal,
            StrategyMonitorService,
        )

        monitor_service = StrategyMonitorService(self._session)
        for monitor_row in monitor_service._repo.due_monitors(now):  # noqa: SLF001
            try:
                monitor_service.run_monitor(monitor_row.monitor_id)
                result.succeeded.append(monitor_row.monitor_id)
            except StrategyMonitorRefusal as exc:
                result.failed.append(f"{monitor_row.monitor_id}: {exc}")
            except Exception:  # noqa: BLE001 — one monitor must not kill the tick
                result.failed.append(monitor_row.monitor_id)

        # F9：帷幄后台任务跑道 —— Scheduler Worker 泵（持久化 + lease 恢复，
        # 不依赖 daemon thread，§8.8）。一个 tick 泵多个任务（有界）。
        from app.services.background_runway import run_one

        for _ in range(5):
            try:
                done = run_one(self._session, worker_id=f"tick-{id(now)}")
            except Exception:  # noqa: BLE001 — one task must not kill the tick
                self._session.rollback()
                result.failed.append("background_runway")
                break
            if done is None:
                break
            result.succeeded.append(done["task_id"])

        return result
