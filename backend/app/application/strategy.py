"""Strategy Lab persistence (V2 Phase F, 总纲 §21/§22/§47).

策略实验室：把经验卡 + 筛选 + 工作流组装成可版本化策略，跨标的验证。
回测必须真实显示失败（§22：收益 -5.8% 就显示 -5.8%）；未通过验证的
版本只能标 EXPERIMENTAL（§47），不得伪装为正式策略。
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


class StrategyStatus:
    DRAFT = "DRAFT"
    EXPERIMENTAL = "EXPERIMENTAL"
    VALIDATED = "VALIDATED"


class BacktestStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StrategyVersionORM(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    philosophy: Mapped[str] = mapped_column(String(2000))
    source_card_id: Mapped[str] = mapped_column(String(24), index=True)
    source_screening_run_id: Mapped[str] = mapped_column(String(24))
    universe_json: Mapped[list] = mapped_column(JSON, default=list)
    entry_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    exit_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default=StrategyStatus.DRAFT, index=True)
    verdict: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StrategyBacktestRunORM(Base):
    __tablename__ = "strategy_backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    version_id: Mapped[str] = mapped_column(String(24), index=True)
    results_json: Mapped[list] = mapped_column(JSON, default=list)
    aggregate_json: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_cases_json: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default=BacktestStatus.RUNNING, index=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _version_to_dict(row: StrategyVersionORM, *, backtest_count: int | None = None) -> dict:
    data = {
        "version_id": row.version_id,
        "name": row.name,
        "version_no": row.version_no,
        "philosophy": row.philosophy,
        "source_card_id": row.source_card_id,
        "source_screening_run_id": row.source_screening_run_id,
        "universe": list(row.universe_json or []),
        "entry_policy": dict(row.entry_policy_json or {}),
        "exit_policy": dict(row.exit_policy_json or {}),
        "risk_policy": dict(row.risk_policy_json or {}),
        "status": row.status,
        "verdict": row.verdict,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        "updated_at": _ensure_utc(row.updated_at).isoformat() if row.updated_at else None,
    }
    if backtest_count is not None:
        data["backtest_count"] = backtest_count
    return data


def _backtest_to_dict(row: StrategyBacktestRunORM) -> dict:
    return {
        "backtest_id": row.backtest_id,
        "version_id": row.version_id,
        "results": [dict(r) for r in (row.results_json or [])],
        "aggregate": dict(row.aggregate_json or {}),
        "failure_cases": [dict(f) for f in (row.failure_cases_json or [])],
        "status": row.status,
        "error": row.error,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


class StrategyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- versions ------------------------------------------------------------------

    def add_version(self, row: StrategyVersionORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _version_to_dict(row)

    def get_version_row(self, version_id: str) -> StrategyVersionORM | None:
        return self._session.scalars(
            select(StrategyVersionORM).where(StrategyVersionORM.version_id == version_id)
        ).first()

    def get_version(self, version_id: str) -> dict | None:
        row = self.get_version_row(version_id)
        return None if row is None else _version_to_dict(row)

    def list_versions(self, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(StrategyVersionORM)
            .order_by(StrategyVersionORM.created_at.desc(), StrategyVersionORM.id.desc())
            .limit(limit)
        ).all()
        return [_version_to_dict(r) for r in rows]

    def next_version_no(self, name: str) -> int:
        current = self._session.scalar(
            select(func_max_version()).where(StrategyVersionORM.name == name)
        )
        return (current or 0) + 1

    def save_version(self, row: StrategyVersionORM) -> dict:
        self._session.flush()
        return _version_to_dict(row)

    # -- backtests -------------------------------------------------------------------

    def add_backtest(self, row: StrategyBacktestRunORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _backtest_to_dict(row)

    def get_backtest_row(self, backtest_id: str) -> StrategyBacktestRunORM | None:
        return self._session.scalars(
            select(StrategyBacktestRunORM).where(
                StrategyBacktestRunORM.backtest_id == backtest_id
            )
        ).first()

    def get_backtest(self, backtest_id: str) -> dict | None:
        row = self.get_backtest_row(backtest_id)
        return None if row is None else _backtest_to_dict(row)

    def list_backtests(self, version_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(StrategyBacktestRunORM)
            .where(StrategyBacktestRunORM.version_id == version_id)
            .order_by(StrategyBacktestRunORM.created_at.desc(), StrategyBacktestRunORM.id.desc())
        ).all()
        return [_backtest_to_dict(r) for r in rows]

    def save_backtest(self, row: StrategyBacktestRunORM) -> dict:
        self._session.flush()
        return _backtest_to_dict(row)

    def update_backtest(self, backtest_id: str, mutate: Any) -> dict | None:
        row = self.get_backtest_row(backtest_id)
        if row is None:
            return None
        run = _backtest_to_dict(row)
        run = mutate(run)
        row.results_json = run["results"]
        row.aggregate_json = run["aggregate"]
        row.failure_cases_json = run["failure_cases"]
        row.status = run["status"]
        row.error = run["error"]
        row.updated_at = _utc()
        self._session.flush()
        return _backtest_to_dict(row)


def func_max_version():
    from sqlalchemy import func

    return func.max(StrategyVersionORM.version_no)
