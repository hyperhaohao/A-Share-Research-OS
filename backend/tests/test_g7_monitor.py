"""G7 — Strategy-aware Monitor（观澜语义迁移任务书 §G7）.

覆盖：
  - 执行所引用策略版本规则（§G7.2）：strategy_entry_exit 信号来自 G6 引擎
    对真实日线的执行；
  - Cursor 幂等（§G7 DoD1）：同批输入重复运行不产生重复信号；
  - 状态机（§G7.3）：ACTIVE↔PAUSED→RETIRED；PAUSED 不运行；非法转换 422；
  - 允许 VALIDATED 版本监控（§G7.4）；
  - 信号方向保留（§G7.10）；
  - 决策置信度可解释（F4 basis 在 rationale 中）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

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
VERSION_ID = "strat_g7test000001"


def _seed_kline(client, prices: list[float]) -> None:
    factory = client.app.state._test_factory
    session = factory()
    try:
        base = NOW - timedelta(days=len(prices))
        bars = [{"date": str((base + timedelta(days=i)).date()), "close": p}
                for i, p in enumerate(prices)]
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title="日线",
            summary=f"daily bars x{len(bars)}",
            source="provider_kline_g7",
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


def _seed_version(client, *, status: str = "EXPERIMENTAL") -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = StrategyVersionORM(
            version_id=VERSION_ID,
            name="G7 监控策略",
            version_no=1,
            philosophy="G7 策略感知监控验证",
            source_card_id="exp_g7000000001",
            source_screening_run_id="sr_g70000000001",
            universe_json=[{"instrument_id": "SZSE:000831"}],
            entry_policy_json={"kind": "forward_return", "horizon_days": 20,
                               "threshold_pct": 3.0},
            exit_policy_json={"kind": "horizon_end"},
            risk_policy_json={},
            status=status,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(row)
        session.commit()
        return VERSION_ID
    finally:
        session.close()


def _create_monitor(client, version_id: str) -> str:
    out = client.post("/api/v1/strategy-monitors", json={
        "version_id": version_id, "interval_seconds": 3600,
    })
    assert out.status_code in (200, 201), out.text
    return out.json()["monitor"]["monitor_id"]


def _run(client, monitor_id: str) -> dict:
    """同步执行盯盘（确定性测试；生产由 Scheduler Worker 泵驱动）。"""
    from app.services.strategy_monitor_service import StrategyMonitorService

    factory = client.app.state._test_factory
    session = factory()
    try:
        out = StrategyMonitorService(session).run_monitor(monitor_id)
        session.commit()
        return out
    finally:
        session.close()


# ── 执行策略规则 + Cursor 幂等 ───────────────────────────────────────────────


def test_monitor_executes_strategy_rules_and_cursor_idempotent(client):
    _seed_version(client)
    _seed_kline(client, [10.0] * 10 + [11.0, 12.5, 14.0, 15.5, 17.0] + [12.0] * 30)
    monitor_id = _create_monitor(client, VERSION_ID)

    body1 = _run(client, monitor_id)
    assert body1["strategy_signals"] >= 1  # 执行了策略规则（非通用新闻）

    # 信号方向保留（§G7.10）
    detail = client.get(f"/api/v1/strategy-monitors/{monitor_id}").json()
    results = detail.get("signals") or []
    assert any(s.get("direction") == "long" for s in results)

    # Cursor 幂等：Cursor 未推进（无新行情）→ 重复运行不产生重复信号
    n_before = len(results)
    body2 = _run(client, monitor_id)
    assert body2["strategy_signals"] == 0  # Cursor 幂等：无新行情 → 零新策略信号
    detail2 = client.get(f"/api/v1/strategy-monitors/{monitor_id}").json()
    results2 = detail2.get("signals") or []
    assert len(results2) == n_before  # 无重复信号


def test_validated_version_can_be_monitored(client):
    _seed_version(client, status="VALIDATED")
    _seed_kline(client, [10.0, 10.5, 11.0] * 4)
    monitor_id = _create_monitor(client, VERSION_ID)
    assert monitor_id


# ── 状态机 ───────────────────────────────────────────────────────────────────


def test_state_machine_and_paused_not_running(client):
    _seed_version(client)
    _seed_kline(client, [10.0, 10.5, 11.0] * 4)
    monitor_id = _create_monitor(client, VERSION_ID)

    # ACTIVE → PAUSED
    paused = client.post(f"/api/v1/strategy-monitors/{monitor_id}/status",
                         json={"status": "PAUSED"})
    assert paused.status_code == 200
    assert paused.json()["monitor"]["status"] == "PAUSED"

    # PAUSED 不运行（§G7 DoD3）
    with pytest.raises(Exception) as exc_info:
        _run(client, monitor_id)
    assert "PAUSED" in str(exc_info.value)

    # PAUSED → ACTIVE（恢复）
    resumed = client.post(f"/api/v1/strategy-monitors/{monitor_id}/status",
                          json={"status": "ACTIVE"})
    assert resumed.json()["monitor"]["status"] == "ACTIVE"

    # RETIRED 终态：非法回转 422
    client.post(f"/api/v1/strategy-monitors/{monitor_id}/status",
                json={"status": "RETIRED"})
    r = client.post(f"/api/v1/strategy-monitors/{monitor_id}/status",
                    json={"status": "ACTIVE"})
    assert r.status_code == 422
    assert r.json()["error_code"] == "monitor.bad_transition"


def test_confidence_rationale_explained(client):
    _seed_version(client)
    _seed_kline(client, [10.0] * 10 + [11.0, 12.5, 14.0, 15.5, 17.0] + [12.0] * 30)
    monitor_id = _create_monitor(client, VERSION_ID)
    body = _run(client, monitor_id)
    decision = body["decision"]
    # F4：置信度可解释（basis 落 rationale）
    assert "置信度 basis" in decision["rationale"]
