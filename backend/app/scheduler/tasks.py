"""ResearchTask + Scheduler (任务书 §48/§49).

Separation of concerns (§49): the scheduler decides *when*; business logic
lives in independently testable functions registered per task type.

Guarantees:
  idempotency      claiming a task advances next_run_at atomically, so two
                   ticks never double-run the same period;
  retry            failures increment attempts and back off; exceeding
                   max_attempts marks the task failed;
  recovery         tasks stuck in ``running`` beyond the lease timeout are
                   rescheduled by the recovery scan (restart-safe);
  concurrency      one running task per instrument at a time.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, Integer, String, select, update
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import Session

from app.domain.evidence import utc_now
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base


class TaskType(str, Enum):
    MONITOR = "monitor"
    PERIODIC_FULL_RESEARCH = "periodic_full_research"
    EVENT_TRIGGER = "event_trigger"
    PREDICTION_VALIDATION = "prediction_validation"


class TaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    DISABLED = "disabled"


DEFAULT_INTERVALS = {"monitor": 300, "periodic_full_research": 86400, "event_trigger": 60, "prediction_validation": 3600}
MAX_ATTEMPTS = 5
LEASE_SECONDS = 900  # a running task older than this is considered interrupted


class ResearchTask(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    task_type: TaskType
    schedule: str = Field(default="interval:300", max_length=64)  # "interval:<seconds>"
    research_level: str = Field(default="standard", max_length=32)
    filters: dict = Field(default_factory=dict)
    enabled: bool = True

    status: TaskStatus = TaskStatus.IDLE
    attempts: int = 0
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    running_since: datetime | None = None

    created_at: datetime = Field(default_factory=utc_now)


class ResearchTaskORM(Base):
    __tablename__ = "research_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    schedule: Mapped[str] = mapped_column(String(64))
    research_level: Mapped[str] = mapped_column(String(32), default="standard")
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True)

    status: Mapped[str] = mapped_column(String(16), default="idle", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    running_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        instrument_id: str,
        task_type: TaskType,
        schedule: str | None = None,
        research_level: str = "standard",
        filters: dict | None = None,
    ) -> ResearchTask:
        interval = schedule or f"interval:{DEFAULT_INTERVALS[task_type.value]}"
        now = utc_now()
        seconds = int(interval.split(":", 1)[1])
        task = ResearchTask(
            instrument_id=instrument_id,
            task_type=task_type,
            schedule=interval,
            research_level=research_level,
            filters=filters or {},
            next_run_at=now,  # first run happens on the next scheduler tick
            created_at=now,
        )
        self._session.add(self._to_orm(task))
        self._session.flush()
        return task

    def list_all(self, *, enabled: bool | None = None) -> list[ResearchTask]:
        stmt = select(ResearchTaskORM)
        if enabled is not None:
            stmt = stmt.where(ResearchTaskORM.enabled == enabled)
        rows = self._session.scalars(stmt.order_by(ResearchTaskORM.created_at.desc())).all()
        return [self._row_to_domain(r) for r in rows]

    def get(self, task_id: str) -> ResearchTask | None:
        row = self._session.scalars(
            select(ResearchTaskORM).where(ResearchTaskORM.task_id == task_id)
        ).first()
        return None if row is None else self._row_to_domain(row)

    def set_enabled(self, task_id: str, enabled: bool) -> ResearchTask | None:
        task = self.get(task_id)
        if task is None:
            return None
        row = self._session.scalars(
            select(ResearchTaskORM).where(ResearchTaskORM.task_id == task_id)
        ).first()
        row.enabled = enabled
        row.status = TaskStatus.DISABLED.value if not enabled else TaskStatus.IDLE.value
        self._session.flush()
        task.enabled = enabled
        return task

    def due_tasks(self, now: datetime) -> list[ResearchTask]:
        rows = self._session.scalars(
            select(ResearchTaskORM).where(
                ResearchTaskORM.enabled.is_(True),
                ResearchTaskORM.status != TaskStatus.RUNNING.value,
                ResearchTaskORM.next_run_at.is_not(None),
                ResearchTaskORM.next_run_at <= now,
            )
        ).all()
        return [self._row_to_domain(r) for r in rows]

    def running_for_instrument(self, instrument_id: str) -> list[ResearchTask]:
        rows = self._session.scalars(
            select(ResearchTaskORM).where(
                ResearchTaskORM.instrument_id == instrument_id,
                ResearchTaskORM.status == TaskStatus.RUNNING.value,
            )
        ).all()
        return [self._row_to_domain(r) for r in rows]

    def claim(self, task_id: str, now: datetime) -> ResearchTask | None:
        """Atomically mark the task running and advance next_run_at.

        Returns None when the task was already claimed or disabled — this is
        the idempotency + concurrency gate.
        """
        task = self.get(task_id)
        if task is None or not task.enabled or task.status is TaskStatus.RUNNING:
            return None
        interval = int(task.schedule.split(":", 1)[1])
        # concurrency control: one running task per instrument
        if self.running_for_instrument(task.instrument_id):
            # reschedule shortly; another task for this instrument is running
            self._update_raw(
                task_id,
                next_run_at=now + timedelta(seconds=30),
            )
            return None
        self._update_raw(
            task_id,
            status=TaskStatus.RUNNING.value,
            running_since=now,
            last_run_at=now,
            attempts=task.attempts + 1,
            next_run_at=now + timedelta(seconds=interval),
        )
        return self.get(task_id)

    def complete(self, task_id: str, now: datetime, *, success: bool) -> None:
        task = self.get(task_id)
        if task is None:
            return
        if success:
            self._update_raw(task_id, status=TaskStatus.IDLE.value, running_since=None, attempts=0)
            return
        attempts = task.attempts
        if attempts >= MAX_ATTEMPTS:
            interval = int(task.schedule.split(":", 1)[1])
            self._update_raw(
                task_id,
                status=TaskStatus.FAILED.value,
                running_since=None,
                next_run_at=now + timedelta(seconds=interval),
            )
        else:
            # exponential backoff, capped at one hour, independent of the
            # schedule interval so interval:0 tasks still back off
            backoff = min(2 ** attempts * 30, 3600)
            self._update_raw(
                task_id,
                status=TaskStatus.IDLE.value,
                running_since=None,
                next_run_at=now + timedelta(seconds=backoff),
            )

    def recover_interrupted(self, now: datetime, *, lease_seconds: int = LEASE_SECONDS) -> list[str]:
        """Restart recovery: reschedule tasks stuck running past the lease."""
        cutoff = now - timedelta(seconds=lease_seconds)
        rows = self._session.scalars(
            select(ResearchTaskORM).where(
                ResearchTaskORM.status == TaskStatus.RUNNING.value,
                ResearchTaskORM.running_since.is_not(None),
                ResearchTaskORM.running_since < cutoff,
            )
        ).all()
        recovered: list[str] = []
        for row in rows:
            interval = int(row.schedule.split(":", 1)[1])
            backoff = min(2 ** row.attempts * 30, interval)
            row.status = TaskStatus.IDLE.value
            row.next_run_at = now + timedelta(seconds=backoff)
            row.running_since = None
            recovered.append(row.task_id)
        if recovered:
            self._session.flush()
        return recovered

    # -- raw update helper -----------------------------------------------------
    def _update_raw(self, task_id: str, **values) -> None:
        self._session.execute(
            update(ResearchTaskORM).where(ResearchTaskORM.task_id == task_id).values(**values)
        )
        self._session.flush()

    def _to_orm(self, task: ResearchTask) -> ResearchTaskORM:
        return ResearchTaskORM(
            task_id=task.task_id,
            instrument_id=task.instrument_id,
            task_type=task.task_type.value,
            schedule=task.schedule,
            research_level=task.research_level,
            filters_json=task.filters,
            enabled=task.enabled,
            status=task.status.value,
            attempts=task.attempts,
            last_run_at=task.last_run_at,
            next_run_at=task.next_run_at,
            running_since=task.running_since,
            created_at=task.created_at,
        )

    def _row_to_domain(self, r: ResearchTaskORM) -> ResearchTask:
        return ResearchTask(
            task_id=r.task_id,
            instrument_id=r.instrument_id,
            task_type=r.task_type,  # type: ignore[arg-type]
            schedule=r.schedule,
            research_level=r.research_level,
            filters=r.filters_json or {},
            enabled=r.enabled,
            status=r.status,  # type: ignore[arg-type]
            attempts=r.attempts,
            last_run_at=_ensure_utc(r.last_run_at),
            next_run_at=_ensure_utc(r.next_run_at),
            running_since=_ensure_utc(r.running_since),
            created_at=_ensure_utc(r.created_at),
        )
