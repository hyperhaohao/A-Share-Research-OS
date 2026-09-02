"""G6 API 级 — Strategy Lab 可执行回测（观澜语义迁移任务书 §G6）.

覆盖（真实 API + 证据层真实日线）：
  - Entry 变化 → 交易可解释变化（DoD）；
  - Exit/Risk 变化 → 持仓与收益变化（DoD）；
  - 无 Entry 规则 → INSUFFICIENT_SIGNALS 零交易（DoD）；
  - Artifact 注册。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
from app.application.strategy import StrategyVersionORM


@pytest.fixture()
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state._test_factory = factory
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


NOW = datetime.now(timezone.utc)
VERSION_ID = "strat_g6test000001"


def _seed_kline(client, prices: list[float], *, base_day: int = 1) -> None:
    """一条 kline 证据（真实证据层日线，load_daily_bars 消费）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        base = NOW - timedelta(days=base_day + len(prices))
        bars = []
        for i, p in enumerate(prices):
            bars.append({
                "date": str((base + timedelta(days=i)).date()),
                "close": p,
            })
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title="日线",
            summary=f"daily bars x{len(bars)}",
            source=f"provider_kline{base_day}{len(prices)}",
            source_type="exchange",
            authority_level=AuthorityLevel.A2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=at,
            available_time=at,
            ingested_time=at + timedelta(minutes=1),
            revision_time=at + timedelta(minutes=1),
            metadata={"bar_count": len(bars), "bars": bars},
        )
        EvidenceRepository(session).save(rec)
        session.commit()
    finally:
        session.close()


def _seed_version(client, *, entry_policy: dict, exit_policy: dict,
                  risk_policy: dict) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = StrategyVersionORM(
            version_id=VERSION_ID,
            name="G6 回测策略",
            version_no=1,
            philosophy="G6 可执行回测验证",
            source_card_id="exp_g6000000001",
            source_screening_run_id="sr_g60000000001",
            universe_json=[{"instrument_id": "SZSE:000831"}],
            entry_policy_json=entry_policy,
            exit_policy_json=exit_policy,
            risk_policy_json=risk_policy,
            status="EXPERIMENTAL",
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(row)
        session.commit()
        return VERSION_ID
    finally:
        session.close()


def _run_v2(client, version_id: str):
    return client.post(f"/api/v1/strategies/{version_id}/backtest-v2")


# 价格路径：先横盘 → 上冲 → 回落 → 横盘
RISING = [10.0] * 12 + [11.0, 12.5, 14.0, 15.5, 17.0] + [12.0] * 12


def test_entry_change_changes_trades(client):
    _seed_kline(client, RISING)
    _seed_version(client,
                  entry_policy={"kind": "forward_return", "horizon_days": 20,
                                "threshold_pct": 3.0},
                  exit_policy={"kind": "horizon_end"},
                  risk_policy={})
    r1 = _run_v2(client, VERSION_ID)
    assert r1.status_code == 202, r1.text
    agg1 = r1.json()["aggregate"]
    assert agg1["n_trades_total"] >= 1

    # Entry 门槛提高 → 交易变化（可解释：同一价格路径下门槛不同）
    _seed_version_entry_only(client, threshold_pct=300.0)
    r2 = _run_v2(client, VERSION_ID)
    agg2 = r2.json()["aggregate"]
    assert agg2["n_trades_total"] != agg1["n_trades_total"] or \
        agg2["entry_rules"] != agg1["entry_rules"]


def _seed_version_entry_only(client, *, threshold_pct: float) -> None:
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(StrategyVersionORM).where(StrategyVersionORM.version_id == VERSION_ID)
        ).first()
        row.entry_policy_json = {"kind": "forward_return", "horizon_days": 20,
                                 "threshold_pct": threshold_pct}
        session.commit()
    finally:
        session.close()


def test_exit_and_risk_change_path(client):
    # 上升后深度回落 → stop_loss/风险规则真实改变出场路径
    dipped = [10.0] * 12 + [11.0, 12.5, 14.0, 13.0, 10.5] + [10.5] * 12
    _seed_kline(client, dipped)
    _seed_version(client,
                  entry_policy={"kind": "forward_return", "horizon_days": 20,
                                "threshold_pct": 3.0},
                  exit_policy={"kind": "horizon_end"},
                  risk_policy={})
    agg1 = _run_v2(client, VERSION_ID).json()["aggregate"]

    # 加 stop_loss + 收紧回撤 → 持仓/收益路径变化
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(StrategyVersionORM).where(StrategyVersionORM.version_id == VERSION_ID)
        ).first()
        row.exit_policy_json = {"exit_rules": [{"kind": "stop_loss", "pct": 3.0}]}
        row.risk_policy_json = {"risk_rules": [{"kind": "max_drawdown", "pct": 6.0}]}
        session.commit()
    finally:
        session.close()
    agg2 = _run_v2(client, VERSION_ID).json()["aggregate"]
    assert agg2["mean_trade_return_pct"] != agg1["mean_trade_return_pct"] or         agg2["n_trades_total"] != agg1["n_trades_total"]


def test_no_entry_rules_insufficient_signals(client):
    _seed_kline(client, RISING)
    _seed_version(client,
                  entry_policy={"kind": "forward_return", "horizon_days": 20,
                                "threshold_pct": 0.0, "entry_rules": []},
                  exit_policy={"kind": "horizon_end"},
                  risk_policy={})
    r = _run_v2(client, VERSION_ID)
    assert r.status_code == 202
    agg = r.json()["aggregate"]
    assert agg["status"] == "INSUFFICIENT_SIGNALS"
    assert agg["n_trades_total"] == 0


def test_backtest_artifact_registered(client):
    _seed_kline(client, RISING)
    _seed_version(client,
                  entry_policy={"kind": "forward_return", "horizon_days": 20,
                                "threshold_pct": 3.0},
                  exit_policy={"kind": "horizon_end"},
                  risk_policy={})
    r = _run_v2(client, VERSION_ID)
    assert r.json()["artifact_id"]
