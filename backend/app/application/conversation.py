"""ConversationSession / ConversationTurn / ResearchPlan persistence
(V2 Phase B, 总纲 §40/§41).

对话不是聊天记录堆积：每一轮指挥官回复引用它产出的 ResearchPlan 与
Artifact —— 产物永远 Artifact 化（§41），Context 只描述上下文（红线 4/5）。
计划是结构化对象（左栏直接渲染，§40），不是聊天文本。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _short_hex() -> str:
    return uuid4().hex[:12]


class PlanStepStatus:
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


class ResearchPlanStep(BaseModel):
    """One planned action (总纲 §40)."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(default_factory=lambda: f"step_{_short_hex()}")
    title: str
    # resolve_instrument / run_pipeline / open_report / create_task / create_prediction
    action: str
    status: str = PlanStepStatus.PENDING
    artifact_ids: list[str] = Field(default_factory=list)
    detail: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PlanStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationSessionORM(Base):
    __tablename__ = "command_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # F9：会话治理（任务书 §8.9）
    status: Mapped[str] = mapped_column(String(16), default="active")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConversationTurnORM(Base):
    __tablename__ = "command_turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turn_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(24), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | commander
    text: Mapped[str] = mapped_column(String(2000))
    plan_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    artifact_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchPlanORM(Base):
    __tablename__ = "research_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)
    instrument_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default=PlanStatus.RUNNING, index=True)
    steps_json: Mapped[list] = mapped_column(JSON, default=list)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _row_to_plan(row: ResearchPlanORM) -> dict:
    return {
        "plan_id": row.plan_id,
        "session_id": row.session_id,
        "instrument_id": row.instrument_id,
        "title": row.title,
        "status": row.status,
        "steps": [dict(s) for s in (row.steps_json or [])],
        "meta": dict(row.meta_json or {}),
        "run_id": row.run_id,
        "error": row.error,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        "updated_at": _ensure_utc(row.updated_at).isoformat() if row.updated_at else None,
    }


def _row_to_turn(row: ConversationTurnORM) -> dict:
    return {
        "turn_id": row.turn_id,
        "session_id": row.session_id,
        "role": row.role,
        "text": row.text,
        "plan_id": row.plan_id,
        "artifact_ids": list(row.artifact_ids_json or []),
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- sessions ---------------------------------------------------------------

    def create_session(self, title: str) -> dict:
        row = ConversationSessionORM(
            session_id=f"ses_{_short_hex()}",
            title=title[:128],
            created_at=_utc(),
        )
        self._session.add(row)
        self._session.flush()
        return {
            "session_id": row.session_id,
            "title": row.title,
            "created_at": row.created_at.isoformat(),
        }

    def list_sessions(
        self, *, limit: int = 50, include_archived: bool = False
    ) -> list[dict]:
        """F9 会话治理：默认不含 archived；按最后活动排序。"""
        stmt = (
            select(ConversationSessionORM)
            .order_by(ConversationSessionORM.created_at.desc(), ConversationSessionORM.id.desc())
            .limit(limit)
        )
        if not include_archived:
            archived = "archived"
            stmt = stmt.where(
                (ConversationSessionORM.status != archived)
                | (ConversationSessionORM.status.is_(None))
            )
        rows = self._session.scalars(stmt).all()
        return [
            {
                "session_id": r.session_id,
                "title": r.title,
                "status": r.status,
                "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None,
                "last_activity_at": (
                    _ensure_utc(r.last_activity_at).isoformat()
                    if r.last_activity_at
                    else None
                ),
            }
            for r in rows
        ]

    def get_session(self, session_id: str) -> dict | None:
        row = self._session.scalars(
            select(ConversationSessionORM).where(
                ConversationSessionORM.session_id == session_id
            )
        ).first()
        if row is None:
            return None
        return {
            "session_id": row.session_id,
            "title": row.title,
            "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        }

    # -- turns --------------------------------------------------------------------

    def add_turn(
        self,
        session_id: str,
        *,
        role: str,
        text: str,
        plan_id: str | None = None,
        artifact_ids: list[str] | None = None,
    ) -> dict:
        turn = ConversationTurnORM(
            turn_id=f"turn_{_short_hex()}",
            session_id=session_id,
            role=role,
            text=text[:2000],
            plan_id=plan_id,
            artifact_ids_json=artifact_ids or [],
            created_at=_utc(),
        )
        self._session.add(turn)
        self._session.flush()
        return _row_to_turn(turn)

    def list_turns(self, session_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(ConversationTurnORM)
            .where(ConversationTurnORM.session_id == session_id)
            .order_by(ConversationTurnORM.created_at, ConversationTurnORM.id)
        ).all()
        return [_row_to_turn(r) for r in rows]

    # -- plans ---------------------------------------------------------------------

    def create_plan(
        self,
        *,
        title: str,
        steps: list[ResearchPlanStep],
        session_id: str | None = None,
        instrument_id: str | None = None,
        meta: dict | None = None,
    ) -> dict:
        now = _utc()
        row = ResearchPlanORM(
            plan_id=f"plan_{_short_hex()}",
            session_id=session_id,
            instrument_id=instrument_id,
            title=title[:256],
            status=PlanStatus.RUNNING,
            steps_json=[s.model_dump(mode="json") for s in steps],
            meta_json=meta or {},
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _row_to_plan(row)

    def get_plan(self, plan_id: str) -> dict | None:
        row = self._session.scalars(
            select(ResearchPlanORM).where(ResearchPlanORM.plan_id == plan_id)
        ).first()
        return None if row is None else _row_to_plan(row)

    def list_plans(self, session_id: str | None = None, *, limit: int = 20) -> list[dict]:
        stmt = (
            select(ResearchPlanORM)
            .order_by(ResearchPlanORM.created_at.desc(), ResearchPlanORM.id.desc())
            .limit(limit)
        )
        if session_id is not None:
            stmt = stmt.where(ResearchPlanORM.session_id == session_id)
        return [_row_to_plan(r) for r in self._session.scalars(stmt).all()]

    def update_plan(self, plan_id: str, mutate: Any) -> dict | None:
        """Apply ``mutate(plan_dict) -> plan_dict`` and persist atomically."""
        row = self._session.scalars(
            select(ResearchPlanORM).where(ResearchPlanORM.plan_id == plan_id)
        ).first()
        if row is None:
            return None
        plan = _row_to_plan(row)
        plan = mutate(plan)
        row.title = plan["title"]
        row.instrument_id = plan["instrument_id"]
        row.status = plan["status"]
        row.steps_json = plan["steps"]
        row.run_id = plan["run_id"]
        row.error = plan["error"]
        row.updated_at = _utc()
        self._session.flush()
        return _row_to_plan(row)
