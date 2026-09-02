"""Strategy monitor persistence (V2 Phase G, 总纲 §23/§24/§25/§48/§49).

三分离（§24，不可合并）：
    Observation  系统观察到什么（真实数据：行情变化/公司事件/新闻证据）
    Signal       策略规则对观察产生的信号（强类型规则，带强度）
    DecisionRecord 最终研究决策（决策 + 置信度 + 理由 + 引用）

§25：只产生 Research Decision / Paper Decision，绝不定义真实下单。
后台由 Scheduler Worker 运行（§23），不是页面打开才工作。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, String, select
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


class MonitorStatus:
    ACTIVE = "active"
    PAUSED = "paused"


class DecisionKind:
    # §25: research decision only — paper level, never a real order
    RESEARCH_REVIEW = "research_review"
    RESEARCH_CONTINUE = "research_continue"


class StrategyMonitorORM(Base):
    __tablename__ = "strategy_monitors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    monitor_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    version_id: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(128))
    universe_json: Mapped[list] = mapped_column(JSON, default=list)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # G7（任务书 §G7）：状态机 + Cursor + 失败持久化
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    quote_cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ObservationORM(Base):
    """What the system observed (real data only, §24)."""

    __tablename__ = "strategy_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    monitor_id: Mapped[str] = mapped_column(String(24), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # quote_change | corporate_event | news
    text: Mapped[str] = mapped_column(String(1000))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignalORM(Base):
    """What the strategy rules produced from observations (§24)."""

    __tablename__ = "strategy_signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    monitor_id: Mapped[str] = mapped_column(String(24), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    rule_kind: Mapped[str] = mapped_column(String(32))
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    text: Mapped[str] = mapped_column(String(1000))
    observation_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # G7：信号方向 + 幂等键（同批输入重复运行不产生重复信号）
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class DecisionRecordORM(Base):
    """The final research decision (§49 fields, §25 paper/research only)."""

    __tablename__ = "strategy_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    monitor_id: Mapped[str] = mapped_column(String(24), index=True)
    version_id: Mapped[str] = mapped_column(String(24), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(String(2000))
    observation_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    signal_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _monitor_to_dict(row: StrategyMonitorORM) -> dict:
    return {
        "monitor_id": row.monitor_id,
        "version_id": row.version_id,
        "name": row.name,
        "universe": list(row.universe_json or []),
        "rules": dict(row.rules_json or {}),
        "enabled": row.enabled,
        "status": row.status,
        "quote_cursor": _ensure_utc(row.quote_cursor).isoformat() if row.quote_cursor else None,
        "evidence_cursor": _ensure_utc(row.evidence_cursor).isoformat() if row.evidence_cursor else None,
        "last_error": row.last_error,
        "last_run_at": _ensure_utc(row.last_run_at).isoformat() if row.last_run_at else None,
        "next_run_at": _ensure_utc(row.next_run_at).isoformat() if row.next_run_at else None,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


def _observation_to_dict(row: ObservationORM) -> dict:
    return {
        "observation_id": row.observation_id,
        "monitor_id": row.monitor_id,
        "instrument_id": row.instrument_id,
        "kind": row.kind,
        "text": row.text,
        "payload": dict(row.payload_json or {}),
        "evidence_ids": list(row.evidence_ids_json or []),
        "observed_at": _ensure_utc(row.observed_at).isoformat() if row.observed_at else None,
    }


def _signal_to_dict(row: SignalORM) -> dict:
    return {
        "signal_id": row.signal_id,
        "monitor_id": row.monitor_id,
        "instrument_id": row.instrument_id,
        "rule_kind": row.rule_kind,
        "strength": row.strength,
        "text": row.text,
        "direction": row.direction,
        "idempotency_key": row.idempotency_key,
        "observation_ids": list(row.observation_ids_json or []),
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


def _decision_to_dict(row: DecisionRecordORM) -> dict:
    return {
        "decision_id": row.decision_id,
        "monitor_id": row.monitor_id,
        "version_id": row.version_id,
        "decision": row.decision,
        "confidence": row.confidence,
        "rationale": row.rationale,
        "observation_ids": list(row.observation_ids_json or []),
        "signal_ids": list(row.signal_ids_json or []),
        "evidence_ids": list(row.evidence_ids_json or []),
        "as_of": _ensure_utc(row.as_of).isoformat() if row.as_of else None,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


class StrategyMonitorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- monitors ----------------------------------------------------------------

    def add_monitor(self, row: StrategyMonitorORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _monitor_to_dict(row)

    def get_monitor_row(self, monitor_id: str) -> StrategyMonitorORM | None:
        return self._session.scalars(
            select(StrategyMonitorORM).where(StrategyMonitorORM.monitor_id == monitor_id)
        ).first()

    def get_monitor(self, monitor_id: str) -> dict | None:
        row = self.get_monitor_row(monitor_id)
        return None if row is None else _monitor_to_dict(row)

    def list_monitors(self, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(StrategyMonitorORM)
            .order_by(StrategyMonitorORM.created_at.desc(), StrategyMonitorORM.id.desc())
            .limit(limit)
        ).all()
        return [_monitor_to_dict(r) for r in rows]

    def due_monitors(self, now: datetime) -> list[StrategyMonitorORM]:
        return list(
            self._session.scalars(
                select(StrategyMonitorORM).where(
                    StrategyMonitorORM.enabled.is_(True),
                    StrategyMonitorORM.next_run_at.is_not(None),
                    StrategyMonitorORM.next_run_at <= now,
                )
            ).all()
        )

    def save_monitor(self, row: StrategyMonitorORM) -> dict:
        self._session.flush()
        return _monitor_to_dict(row)

    # -- observations / signals / decisions ----------------------------------------

    def add_observation(self, row: ObservationORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _observation_to_dict(row)

    def latest_observation_at(self, monitor_id: str, instrument_id: str, kind: str) -> datetime | None:
        return self._session.scalar(
            select(ObservationORM.observed_at)
            .where(
                ObservationORM.monitor_id == monitor_id,
                ObservationORM.instrument_id == instrument_id,
                ObservationORM.kind == kind,
            )
            .order_by(ObservationORM.observed_at.desc())
            .limit(1)
        )

    def add_signal(self, row: SignalORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _signal_to_dict(row)

    def add_decision(self, row: DecisionRecordORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _decision_to_dict(row)

    def list_observations(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(ObservationORM)
            .where(ObservationORM.monitor_id == monitor_id)
            .order_by(ObservationORM.observed_at.desc(), ObservationORM.id.desc())
            .limit(limit)
        ).all()
        return [_observation_to_dict(r) for r in rows]

    def list_signals(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(SignalORM)
            .where(SignalORM.monitor_id == monitor_id)
            .order_by(SignalORM.created_at.desc(), SignalORM.id.desc())
            .limit(limit)
        ).all()
        return [_signal_to_dict(r) for r in rows]

    def list_decisions(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(DecisionRecordORM)
            .where(DecisionRecordORM.monitor_id == monitor_id)
            .order_by(DecisionRecordORM.created_at.desc(), DecisionRecordORM.id.desc())
            .limit(limit)
        ).all()
        return [_decision_to_dict(r) for r in rows]
