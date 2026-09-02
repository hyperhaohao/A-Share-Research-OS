"""G8 — Causal Replay（观澜语义迁移任务书 §G8）.

覆盖：
  - Prediction 因果引用 Decision（§G8.1）：from-decision 创建落 decision_id；
  - 无关 Prediction 不能进入 Replay（严格因果过滤，DoD）；
  - Attribution（§G8.3）：方向错误且回撤显著 → rule_error（确定性）；
  - 规则反馈改变**可执行定义**（§G8.5）：rule_error → 新策略版本
    exit_rules 追加 stop_loss（规则体变化，非仅描述）；
  - 旧版本不可变（§G8.6）。
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
from app.application.strategy_monitor import DecisionRecordORM, SignalORM


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
VERSION_ID = "strat_g8test000001"
MONITOR_ID = "mon_g8test0000001"
DECISION_ID = "dec_g8test0000001"


def _seed_decision_chain(client, *, decision_id: str = DECISION_ID,
                         monitor_id: str = MONITOR_ID) -> None:
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = StrategyVersionORM(
            version_id=VERSION_ID,
            name="G8 因果回放策略",
            version_no=1,
            philosophy="G8 验证",
            source_card_id="exp_g8000000001",
            source_screening_run_id="sr_g80000000001",
            universe_json=[{"instrument_id": "SZSE:000831"}],
            entry_policy_json={"kind": "forward_return", "horizon_days": 20,
                               "threshold_pct": 3.0},
            exit_policy_json={"kind": "horizon_end"},
            risk_policy_json={},
            status="EXPERIMENTAL",
            created_at=NOW,
            updated_at=NOW,
        )
        mon = __import__("app.application.strategy_monitor",
                         fromlist=["StrategyMonitorORM"]).StrategyMonitorORM(
            monitor_id=monitor_id,
            version_id=VERSION_ID,
            name="G8 监控",
            universe_json=[{"instrument_id": "SZSE:000831"}],
            rules_json={"interval_seconds": 3600},
            enabled=True,
            created_at=NOW,
            updated_at=NOW,
        )
        dec = DecisionRecordORM(
            decision_id=decision_id,
            monitor_id=monitor_id,
            version_id=VERSION_ID,
            decision="research_review",
            confidence=0.6,
            rationale="G8 因果链验证",
            observation_ids_json=[],
            signal_ids_json=[],
            evidence_ids_json=[],
            as_of=NOW,
            created_at=NOW,
        )
        session.add_all([row, mon, dec])
        session.commit()
    finally:
        session.close()


def _seed_spot_quotes(client) -> None:
    """入场/到期两个时点的现货报价（validation _price_at 消费）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        for key, days_ago, price in (("entry", 40.0, 10.0), ("due", 20.0, 12.0)):
            at = NOW - timedelta(days=days_ago)
            rec = EvidenceRecord(
                instrument_id="SZSE:000831",
                evidence_type=EvidenceType.MARKET_QUOTE,
                title="现货报价",
                summary=f"price={price}",
                source=f"provider_quote_{key}",
                source_type="exchange",
                authority_level=AuthorityLevel.A2,
                fact_status=FactStatus.CONFIRMED_FACT,
                event_time=at,
                available_time=at,
                ingested_time=at + timedelta(minutes=1),
                revision_time=at + timedelta(minutes=1),
                metadata={"price": price},
            )
            EvidenceRepository(session).save(rec)
        session.commit()
    finally:
        session.close()


def _seed_kline_history(client, *, days: int = 60) -> None:
    """种子覆盖预测窗口的日线（验证需要 as_of→due 区间报价）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        base = NOW - timedelta(days=days)
        bars = []
        price = 10.0
        for i in range(days):
            price = round(price * (1.01 if i % 5 < 3 else 0.99), 3)
            bars.append({"date": str((base + timedelta(days=i)).date()),
                         "close": price})
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title="日线（历史窗口）",
            summary=f"daily bars x{len(bars)}",
            source="provider_kline_g8",
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


def _link_prediction(client, decision_id: str, *, link: bool = True,
                     mature_days_ago: float = 40.0) -> str:
    """创建（可选因果链接的）已验证成熟预测。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.storage.prediction_repo import PredictionORM, PredictionRepository
        from app.domain.prediction import PredictionRecord, Direction, Horizon
        from app.domain.evidence import utc_now

        at = NOW - timedelta(days=mature_days_ago)
        rec = PredictionRecord(
            instrument_id="SZSE:000831",
            research_run_id=None,
            as_of=at,
            horizon=Horizon.D20,
            expected_direction=Direction.UP,
            expected_return_range=(0.0, 10.0),
            confidence=0.6,
            decision_id=decision_id if link else None,
        )
        saved_id = PredictionRepository(session).save(rec)
        session.commit()
        return saved_id
    finally:
        session.close()


def _validate_prediction(client, prediction_id: str) -> None:
    r = client.post(f"/api/v1/predictions/{prediction_id}/validate")
    assert r.status_code in (200, 201), r.text


def _replay(client, decision_id: str):
    return client.post("/api/v1/reviews/feedback", json={"decision_id": decision_id})


# ── §G8.1：因果引用 ─────────────────────────────────────────────────────────


def test_unlinked_prediction_cannot_replay(client):
    _seed_decision_chain(client)
    # 无因果链接的成熟预测（同标的、已验证）→ 仍不得进入 Replay
    _seed_spot_quotes(client)
    pred_id = _link_prediction(client, DECISION_ID, link=False)
    _validate_prediction(client, pred_id)
    r = _replay(client, DECISION_ID)
    assert r.status_code in (409, 422), r.text
    assert "no validated prediction" in r.json()["detail"]


def test_linked_prediction_replays_with_causal_chain(client):
    _seed_decision_chain(client)
    _seed_spot_quotes(client)
    pred_id = _link_prediction(client, DECISION_ID, link=True)
    _validate_prediction(client, pred_id)
    r = _replay(client, DECISION_ID)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    # 因果链 ID 全可见（Decision → Prediction → Review → 卡/策略）
    fb = body["feedback"]
    assert fb["prediction_id"] == pred_id
    assert fb["validation_id"]


# ── §G8.3/§G8.5：归因与可执行规则反馈 ───────────────────────────────────────


def test_rule_error_feedback_changes_executable_rules(client):
    _seed_decision_chain(client)
    _seed_spot_quotes(client)
    pred_id = _link_prediction(client, DECISION_ID, link=True)
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.storage.prediction_repo import PredictionORM

        row = session.scalars(
            select(PredictionORM).where(PredictionORM.prediction_id == pred_id)
        ).first()
        row.expected_direction = "down"
        session.commit()
    finally:
        session.close()
    _validate_prediction(client, pred_id)

    r = _replay(client, DECISION_ID)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    feedback = body["feedback"]
    dims = [a["dimension"] for a in feedback["attributions"]]
    assert "rule_error" in dims, dims

    # 规则反馈 → 新策略版本出场规则变化（可执行规则修改，§G8.5）
    assert feedback.get("rule_feedback"), body
    changed = feedback["rule_feedback"]["changed_exit_rules"]
    assert any(r2["kind"] == "stop_loss" for r2 in changed)
    assert feedback["rule_feedback"]["old_version_id"] == VERSION_ID

    # 旧版本不可变：旧版本的出场规则保持 horizon_end
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(StrategyVersionORM).where(StrategyVersionORM.version_id == VERSION_ID)
        ).first()
        assert (row.exit_policy_json or {}).get("exit_rules") is None
    finally:
        session.close()
