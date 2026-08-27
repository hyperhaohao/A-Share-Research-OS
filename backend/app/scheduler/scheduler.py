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


@dataclass
class TickResult:
    now: str
    claimed: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped_busy: list[str] = field(default_factory=list)
    recovered: list[str] = field(default_factory=list)


def run_monitor_task(session: Session, task) -> None:
    """Business function: monitor one instrument (independently runnable)."""
    MonitorService(session).run_monitor(task.instrument_id)


def run_periodic_full_research(session: Session, task) -> None:
    """Business function: full research — collect + snapshot + report."""
    from app.services.evidence_collector import collect_capability_evidence
    from app.services.report_compiler import ReportCompiler
    from app.storage.report_repo import ReportRepository
    from app.storage.repository import EvidenceRepository
    from app.storage.snapshot_repo import SnapshotRepository

    instrument_id = task.instrument_id
    evidence_repo = EvidenceRepository(session)
    collect_capability_evidence(
        instrument_id, "market_data", repo=evidence_repo, fresh=True
    )
    snapshot = SnapshotRepository(session).build(
        instrument_id, utc_now(), evidence_repo=evidence_repo
    )
    report = ReportCompiler(session).compile(snapshot.snapshot_id)
    rendered = ReportCompiler(session).render_and_gate(report, language="zh-CN")
    ReportRepository(session).save(
        instrument_id=instrument_id,
        snapshot_id=snapshot.snapshot_id,
        language="zh-CN",
        gate_status=rendered["gate"]["status"],
        published=False,
        markdown=rendered["markdown"],
        html=rendered["html"],
        content={},
    )


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
    TaskType.PERIODIC_FULL_RESEARCH: run_periodic_full_research,
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

        return result
