"""V2 Phase G — 策略盯盘（总纲 §23/§24/§25/§48/§49）.

验收：
  - EXPERIMENTAL 门槛：DRAFT 版本建立盯盘 → 422 显式拒绝（§47 衔接）；
  - 一次运行产生 Observation（真实数据）→ Signal（规则）→ DecisionRecord
    三分离记录，互相引用，§49 全字段落库；
  - 决策只到 Research Decision（§25），rationale 显式注明；
  - Scheduler.tick 后台运行 due monitors（§23）。
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


def _mock_sources(monkeypatch, *, kline_ok: bool = True) -> None:
    def fake_get(url, timeout=10.0, **kwargs):
        if "kline" in url:
            if kline_ok:
                return httpx.Response(200, json={"data": {"klines": [
                    f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},{10.0 + i * 0.1:.2f},"
                    f"{10.0 + i * 0.1:.2f},{10.5 + i * 0.1:.2f},{9.5 + i * 0.1:.2f},"
                    "1000,10000,1.0,1.0,0.1,1.0"
                    for i in range(60)
                ]}})
            return httpx.Response(500, text="kline down")
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)


def _seed_second_quote(client) -> None:
    """A second, earlier quote evidence so the monitor's quote_change
    observation has a real price pair (production accumulates these over
    time; the mocked pipeline only creates one)."""
    from datetime import datetime, timedelta, timezone

    from app.db import session_scope
    from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
    from app.storage.repository import EvidenceRepository

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=1)
    record = EvidenceRecord(
        instrument_id="SZSE:000831",
        evidence_type=EvidenceType.MARKET_QUOTE,
        title="实时行情 000831（早前快照）",
        summary="盯盘测试用第二条行情证据",
        source="tencent_quote",
        source_type="market_data_provider",
        authority_level=AuthorityLevel.B2,
        fact_status=FactStatus.CONFIRMED_FACT,
        event_time=earlier,
        available_time=earlier,
        ingested_time=earlier,
        revision_time=earlier,
        metadata={"price": 26.10},
    )
    with session_scope(client.app.state._test_factory) as session:
        EvidenceRepository(session).save(record)


def _experimental_strategy(client, monkeypatch) -> dict:
    _mock_sources(monkeypatch)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_monchain001")
    assert body.status_code == 202
    card = client.post(
        "/api/v1/experience-cards/from-report",
        json={"report_id": body.json()["report_id"]},
    ).json()["card"]
    screening = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    run = screening.json()["run"]
    for _ in range(100):
        run = client.get(f"/api/v1/screening-runs/{run['run_id']}").json()["run"]
        if run["status"] != "running":
            break
    strategy = client.post(
        "/api/v1/strategies/from-screening",
        json={"screening_run_id": run["run_id"]},
    ).json()["strategy"]
    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    assert launched.status_code == 202
    for _ in range(200):
        bt = client.get(
            f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}"
        ).json()["backtest"]
        if bt["status"] != "running":
            break
    validated = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert validated.status_code == 200, validated.text
    _seed_second_quote(client)
    return validated.json()["strategy"]


def test_monitor_gate_and_three_way_separation(client, monkeypatch):
    strategy = _experimental_strategy(client, monkeypatch)
    assert strategy["status"] == "EXPERIMENTAL"

    created = client.post(
        "/api/v1/strategy-monitors",
        json={"version_id": strategy["version_id"]},
    )
    assert created.status_code == 201, created.text
    monitor = created.json()["monitor"]
    assert monitor["enabled"] is True
    assert monitor["next_run_at"] is not None

    run = client.post(f"/api/v1/strategy-monitors/{monitor['monitor_id']}/run")
    assert run.status_code == 202
    for _ in range(200):
        detail = client.get(f"/api/v1/strategy-monitors/{monitor['monitor_id']}").json()
        if detail["monitor"]["last_run_at"]:
            break
        import time

        time.sleep(0.05)

    detail = client.get(f"/api/v1/strategy-monitors/{monitor['monitor_id']}").json()
    # §24: the three records are separate, each with ids referencing the upstream
    assert isinstance(detail["observations"], list)
    assert isinstance(detail["signals"], list)
    assert len(detail["decisions"]) == 1
    decision = detail["decisions"][0]
    assert decision["decision"] in ("research_review", "research_continue")
    assert decision["version_id"] == strategy["version_id"]
    assert "Research Decision" in decision["rationale"]
    assert decision["observation_ids"] == [o["observation_id"] for o in detail["observations"]]
    assert decision["signal_ids"] == [s["signal_id"] for s in detail["signals"]]
    # quote_change observation derives from REAL pinned quote evidence
    quote_obs = [o for o in detail["observations"] if o["kind"] == "quote_change"]
    assert quote_obs and quote_obs[0]["evidence_ids"]
    assert "行情变化" in quote_obs[0]["text"]


def test_monitor_creation_blocked_for_draft_version(client, monkeypatch):
    _mock_sources(monkeypatch, kline_ok=False)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_monchain002")
    card = client.post(
        "/api/v1/experience-cards/from-report",
        json={"report_id": body.json()["report_id"]},
    ).json()["card"]
    screening = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    run = screening.json()["run"]
    for _ in range(100):
        run = client.get(f"/api/v1/screening-runs/{run['run_id']}").json()["run"]
        if run["status"] != "running":
            break
    strategy = client.post(
        "/api/v1/strategies/from-screening",
        json={"screening_run_id": run["run_id"]},
    ).json()["strategy"]
    assert strategy["status"] == "DRAFT"

    blocked = client.post(
        "/api/v1/strategy-monitors", json={"version_id": strategy["version_id"]}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error_code"] == "monitor.gate_blocked"
    assert "EXPERIMENTAL" in blocked.json()["detail"]


def test_scheduler_tick_runs_due_monitors(client, monkeypatch):
    strategy = _experimental_strategy(client, monkeypatch)
    monitor = client.post(
        "/api/v1/strategy-monitors", json={"version_id": strategy["version_id"]}
    ).json()["monitor"]
    # next_run_at is now → the scheduler tick must pick it up (§23)
    tick = client.post("/api/v1/tasks/scheduler/tick")
    assert tick.status_code == 200
    body = tick.json()
    assert monitor["monitor_id"] in body["succeeded"]
    detail = client.get(f"/api/v1/strategy-monitors/{monitor['monitor_id']}").json()
    assert detail["monitor"]["last_run_at"] is not None
    assert len(detail["decisions"]) == 1
