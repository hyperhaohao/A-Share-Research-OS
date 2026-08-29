"""WorkflowRun persistence (V2 Phase D, 总纲 §73/§37).

最小强类型 DAG 的运行记录：节点序列（Data → Rule → Validation → Output）
与指标都落库；事件同时经 RunEvent 持久化（回放/失败分析，§37 通用 run_id）。
工作流不发明数据 —— Data 节点只读真实证据层（PIT 可见）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _short_hex() -> str:
    return uuid4().hex[:12]


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class WorkflowStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus:
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


class WorkflowRunORM(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    card_id: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="card_quant_validation")
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    nodes_json: Mapped[list] = mapped_column(JSON, default=list)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default=WorkflowStatus.RUNNING, index=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _row_to_run(row: WorkflowRunORM) -> dict:
    return {
        "run_id": row.run_id,
        "instrument_id": row.instrument_id,
        "card_id": row.card_id,
        "kind": row.kind,
        "params": dict(row.params_json or {}),
        "nodes": [dict(n) for n in (row.nodes_json or [])],
        "metrics": dict(row.metrics_json or {}),
        "status": row.status,
        "error": row.error,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        "updated_at": _ensure_utc(row.updated_at).isoformat() if row.updated_at else None,
    }


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        instrument_id: str,
        kind: str,
        params: dict,
        nodes: list[dict],
        card_id: str | None = None,
    ) -> dict:
        now = _utc()
        row = WorkflowRunORM(
            run_id=f"wr_{_short_hex()}",
            instrument_id=instrument_id,
            card_id=card_id,
            kind=kind,
            params_json=params,
            nodes_json=nodes,
            status=WorkflowStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _row_to_run(row)

    def get_run(self, run_id: str) -> dict | None:
        row = self._session.scalars(
            select(WorkflowRunORM).where(WorkflowRunORM.run_id == run_id)
        ).first()
        return None if row is None else _row_to_run(row)

    def list_runs(self, card_id: str | None = None, *, limit: int = 20) -> list[dict]:
        stmt = (
            select(WorkflowRunORM)
            .order_by(WorkflowRunORM.created_at.desc(), WorkflowRunORM.id.desc())
            .limit(limit)
        )
        if card_id is not None:
            stmt = stmt.where(WorkflowRunORM.card_id == card_id)
        return [_row_to_run(r) for r in self._session.scalars(stmt).all()]

    def update_run(self, run_id: str, mutate: Any) -> dict | None:
        row = self._session.scalars(
            select(WorkflowRunORM).where(WorkflowRunORM.run_id == run_id)
        ).first()
        if row is None:
            return None
        run = _row_to_run(row)
        run = mutate(run)
        row.params_json = run["params"]
        row.nodes_json = run["nodes"]
        row.metrics_json = run["metrics"]
        row.status = run["status"]
        row.error = run["error"]
        row.updated_at = _utc()
        self._session.flush()
        return _row_to_run(row)
