"""ScreeningRun persistence (V2 Phase E, 总纲 §19/§20/§45).

选股不是单纯条件过滤器：每个候选必须携带 Why Selected —— 命中规则、
因子分与由真实研究状态组成的解释（§20）。规则是强类型对象，
解释永远由可溯源事实拼装，绝不发明。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class ScreeningStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScreeningRunORM(Base):
    __tablename__ = "screening_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    card_id: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)
    universe_size: Mapped[int] = mapped_column(Integer, default=0)
    rules_json: Mapped[list] = mapped_column(JSON, default=list)
    candidates_json: Mapped[list] = mapped_column(JSON, default=list)
    excluded_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default=ScreeningStatus.RUNNING, index=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _row_to_run(row: ScreeningRunORM) -> dict:
    return {
        "run_id": row.run_id,
        "card_id": row.card_id,
        "universe_size": row.universe_size,
        "rules": [dict(r) for r in (row.rules_json or [])],
        "candidates": [dict(c) for c in (row.candidates_json or [])],
        "excluded_summary": dict(row.excluded_summary_json or {}),
        "status": row.status,
        "error": row.error,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        "updated_at": _ensure_utc(row.updated_at).isoformat() if row.updated_at else None,
    }


class ScreeningRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(self, *, card_id: str | None, rules: list[dict]) -> dict:
        now = _utc()
        row = ScreeningRunORM(
            run_id=f"sr_{uuid4().hex[:12]}",
            card_id=card_id,
            rules_json=rules,
            status=ScreeningStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _row_to_run(row)

    def get_run(self, run_id: str) -> dict | None:
        row = self._session.scalars(
            select(ScreeningRunORM).where(ScreeningRunORM.run_id == run_id)
        ).first()
        return None if row is None else _row_to_run(row)

    def list_runs(self, card_id: str | None = None, *, limit: int = 20) -> list[dict]:
        stmt = (
            select(ScreeningRunORM)
            .order_by(ScreeningRunORM.created_at.desc(), ScreeningRunORM.id.desc())
            .limit(limit)
        )
        if card_id is not None:
            stmt = stmt.where(ScreeningRunORM.card_id == card_id)
        return [_row_to_run(r) for r in self._session.scalars(stmt).all()]

    def update_run(self, run_id: str, mutate: Any) -> dict | None:
        row = self._session.scalars(
            select(ScreeningRunORM).where(ScreeningRunORM.run_id == run_id)
        ).first()
        if row is None:
            return None
        run = _row_to_run(row)
        run = mutate(run)
        row.universe_size = run["universe_size"]
        row.rules_json = run["rules"]
        row.candidates_json = run["candidates"]
        row.excluded_summary_json = run["excluded_summary"]
        row.status = run["status"]
        row.error = run["error"]
        row.updated_at = _utc()
        self._session.flush()
        return _row_to_run(row)
