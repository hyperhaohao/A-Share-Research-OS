"""V2 Phase J — 完整复盘回灌（总纲 §79/§50/§53）.

验收：
  - Decision → 已验证 Prediction → RegressionReview → ExperienceCard v2 →
    StrategyVersion v2 → ResearchExperience 全链编排；
  - 缺环（无已验证预测）→ 422 显式拒绝，不假装闭环（§79）；
  - 教训 append-only（卡片 v(n+1) method=review；ResearchExperience 新记录）；
  - review artifact generated_from 预测 artifact，策略 v2 generated_from 复盘。
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


RAW_OK = (
    'v_sz000831="1~中国稀土~000831~24.83~1651.00~1655.00~32924~85755~24354~'
    "24.83~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "24.83~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "24.83/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    "24.83/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
    '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
)


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


def _mock_sources(monkeypatch) -> None:
    def fake_get(url, timeout=10.0, **kwargs):
        if "kline" in url:
            return httpx.Response(200, json={"data": {"klines": [
                f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},{10.0 + i * 0.1:.2f},"
                f"{10.0 + i * 0.1:.2f},{10.5 + i * 0.1:.2f},{9.5 + i * 0.1:.2f},"
                "1000,10000,1.0,1.0,0.1,1.0"
                for i in range(60)
            ]}})
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)


def _await(client, path: str, key: str, *, timeout_s: float = 30.0) -> dict:
    import time

    deadline = timeout_s
    payload = None
    while deadline > 0:
        payload = client.get(path).json()[key]
        if payload["status"] != "running":
            return payload
        time.sleep(0.1)
        deadline -= 0.1
    raise AssertionError(f"did not finish: {payload}")


def _chain_with_monitor(client, monkeypatch) -> dict:
    _mock_sources(monkeypatch)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_replay00001")
    assert body.status_code == 202
    report_id = body.json()["report_id"]
    card = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": report_id}
    ).json()["card"]
    screening = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    run = _await(client, f"/api/v1/screening-runs/{screening.json()['run']['run_id']}", "run")
    strategy = client.post(
        "/api/v1/strategies/from-screening",
        json={"screening_run_id": run["run_id"]},
    ).json()["strategy"]
    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    _await(client, f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}", "backtest")
    validated = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert validated.status_code == 200
    monitor = client.post(
        "/api/v1/strategy-monitors", json={"version_id": strategy["version_id"]}
    ).json()["monitor"]
    run_resp = client.post(f"/api/v1/strategy-monitors/{monitor['monitor_id']}/run")
    assert run_resp.status_code == 202
    for _ in range(200):
        detail = client.get(f"/api/v1/strategy-monitors/{monitor['monitor_id']}").json()
        if detail["monitor"]["last_run_at"]:
            break
        import time

        time.sleep(0.05)
    detail = client.get(f"/api/v1/strategy-monitors/{monitor['monitor_id']}").json()
    decision_id = detail["decisions"][0]["decision_id"]
    return {
        "report_id": report_id,
        "card": card,
        "strategy": strategy,
        "monitor": monitor,
        "decision_id": decision_id,
    }


def test_replay_refuses_without_validated_prediction(client, monkeypatch):
    chain = _chain_with_monitor(client, monkeypatch)
    # the chain has no matured prediction yet → the loop refuses honestly
    refused = client.post(
        "/api/v1/reviews/feedback", json={"decision_id": chain["decision_id"]}
    )
    assert refused.status_code == 422
    assert refused.json()["error_code"] == "replay.chain_incomplete"
    assert "validated prediction" in refused.json()["detail"]


def test_replay_full_loop_backfills_card_and_strategy(client, monkeypatch):
    chain = _chain_with_monitor(client, monkeypatch)
    # a MATURED validated prediction on the chain (as_of backdated so the
    # 20D horizon has passed; prices come from the real mocked quote series)
    from datetime import datetime, timedelta, timezone

    from app.domain.prediction import Direction, Horizon, PredictionRecord
    from app.storage.prediction_repo import PredictionRepository
    from app.services.validation_service import ValidationService

    from app.db import session_scope

    now = datetime.now(timezone.utc)

    def _seed_quote(price: float, available_at: datetime) -> None:
        from app.domain.evidence import (
            AuthorityLevel,
            EvidenceRecord,
            EvidenceType,
            FactStatus,
        )
        from app.storage.repository import EvidenceRepository

        record = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title=f"历史行情 000831（{available_at.date()}）",
            summary="复盘验证窗口内的行情证据",
            source="tencent_quote",
            source_type="market_data_provider",
            authority_level=AuthorityLevel.B2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=available_at,
            available_time=available_at,
            ingested_time=available_at,
            revision_time=available_at,
            metadata={"price": price},
        )
        with session_scope(client.app.state._test_factory) as session:
            EvidenceRepository(session).save(record)

    _seed_quote(24.00, now - timedelta(days=41))
    _seed_quote(25.00, now - timedelta(days=20))

    with session_scope(client.app.state._test_factory) as session:
        prediction = PredictionRecord(
            instrument_id="SZSE:000831",
            research_run_id=None,
            as_of=now - timedelta(days=40),
            horizon=Horizon.D20,
            expected_direction=Direction.UP,
            expected_return_range=(0.0, 10.0),
            confidence=0.6,
        )
        saved_id = PredictionRepository(session).save(prediction)
    validated = client.post(f"/api/v1/predictions/{saved_id}/validate")
    assert validated.status_code in (200, 201), validated.text
    validation_id = validated.json()["prediction"]["validation"]["validation_id"]

    feedback = client.post(
        "/api/v1/reviews/feedback", json={"decision_id": chain["decision_id"]}
    )
    assert feedback.status_code == 201, feedback.text
    result = feedback.json()["feedback"]
    assert result["validation_id"] == validation_id
    assert result["review_id"]

    # the lesson backfills the experience card as v(n+1), method=review
    card_detail = client.get(f"/api/v1/experience-cards/{chain['card']['card_id']}").json()["card"]
    assert result["card_version_no"] == card_detail["current_version"]
    assert card_detail["current_version"] >= 2
    review_version = next(
        v for v in card_detail["versions"] if v["version_no"] == card_detail["current_version"]
    )
    assert review_version["method"] == "review"
    assert "复盘教训" in card_detail["mechanism"]

    # the strategy version v(n+1) was re-assembled from the same screening run
    v2 = result["strategy_v2"]
    assert v2 is not None
    assert v2["version_no"] == chain["strategy"]["version_no"] + 1
    assert v2["source_card_id"] == chain["card"]["card_id"]

    # the ResearchExperience lesson exists (append-only, §53)
    experiences = client.get("/api/v1/regression/experiences").json()
    assert any(
        e["experience_id"] == result["experience_id"] for e in experiences["results"]
    )

    # artifacts: review generated_from the prediction; strategy v2 from the review
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "review"}
    ).json()
    assert artifacts["count"] == 1
    lineage = client.get(
        f"/api/v1/artifacts/{artifacts['results'][0]['artifact_id']}/lineage"
    ).json()
    upstream = {u["artifact_type"] for u in lineage["upstream"]}
    assert "prediction" in upstream
    downstream = {d["artifact_type"] for d in lineage["downstream"]}
    assert "strategy_version" in downstream


def test_replay_missing_decision_is_404(client):
    resp = client.post("/api/v1/reviews/feedback", json={"decision_id": "dec_missing000"})
    assert resp.status_code == 404
