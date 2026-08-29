"""V2 Phase F — 策略实验室（总纲 §21/§22/§46/§47）.

验收：
  - 筛选运行 → 组装可版本化策略（§46，候选即 universe）；
  - 跨标的回测：真实日线、逐标的指标、组合聚合；失败案例显形（§22）；
  - 数据不可得 → 回测诚实失败，验证被 422 拦截（§47 门槛）；
  - 验证后版本标 EXPERIMENTAL（§47 未通过/未全套验证不得进入正式盯盘）；
  - strategy_version / strategy_backtest artifact 溯源链完整。
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

BAR_COUNT = 60
HORIZON = 20
KLINE_JSON = {
    "data": {
        "klines": [
            f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},{10.0 + i * 0.1:.2f},"
            f"{10.0 + i * 0.1:.2f},{10.5 + i * 0.1:.2f},{9.5 + i * 0.1:.2f},"
            "1000,10000,1.0,1.0,0.1,1.0"
            for i in range(BAR_COUNT)
        ]
    }
}


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
                return httpx.Response(200, json=KLINE_JSON)
            return httpx.Response(500, text="kline source down")
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)


def _await(client, path: str, key: str, *, timeout_s: float = 60.0) -> dict:
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


@pytest.fixture()
def strategy_chain(client, monkeypatch):
    """pipeline → card → screening → strategy version (sync assembly)."""
    _mock_sources(monkeypatch)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_stratchain01")
    assert body.status_code == 202
    report_id = body.json()["report_id"]
    card = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": report_id}
    ).json()["card"]
    screening = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    assert screening.status_code == 202
    run = _await(client, f"/api/v1/screening-runs/{screening.json()['run']['run_id']}", "run")
    assert run["status"] == "completed", run
    created = client.post(
        "/api/v1/strategies/from-screening",
        json={"screening_run_id": run["run_id"]},
    )
    assert created.status_code == 201, created.text
    return {"card": card, "screening": run, "strategy": created.json()["strategy"]}


def test_strategy_assembled_from_screening(client, monkeypatch, strategy_chain):
    strategy = strategy_chain["strategy"]
    assert strategy["name"]
    assert strategy["version_no"] == 1
    assert strategy["status"] == "DRAFT"
    assert strategy["source_card_id"] == strategy_chain["card"]["card_id"]
    # universe comes from the screening candidates (§46)
    universe_ids = [m["instrument_id"] for m in strategy["universe"]]
    assert "SZSE:000831" in universe_ids
    assert len(strategy["universe"]) == strategy_chain["screening"]["excluded_summary"][
        "candidate_count"
    ]

    # artifact chain: strategy_version generated_from screening + card
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "strategy_version"}
    ).json()
    assert artifacts["count"] == 1
    lineage = client.get(f"/api/v1/artifacts/{artifacts['results'][0]['artifact_id']}/lineage").json()
    upstream = {u["artifact_type"] for u in lineage["upstream"]}
    assert {"screening_run", "experience_card"} <= upstream


def test_backtest_completes_with_failure_case_disclosure(client, monkeypatch, strategy_chain):
    strategy = strategy_chain["strategy"]
    # force a falling series: the same bars but reversed closes → negative avg
    falling = {
        "data": {
            "klines": [
                f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},"
                f"{20.0 - i * 0.1:.2f},{20.0 - i * 0.1:.2f},"
                f"{20.5 - i * 0.1:.2f},{19.5 - i * 0.1:.2f},"
                "1000,10000,1.0,1.0,0.1,1.0"
                for i in range(BAR_COUNT)
            ]
        }
    }

    def fake_get(url, timeout=10.0, **kwargs):
        if "kline" in url:
            return httpx.Response(200, json=falling)
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)

    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    assert launched.status_code == 202
    backtest = _await(
        client,
        f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}",
        "backtest",
    )
    assert backtest["status"] == "completed", backtest
    ok = [r for r in backtest["results"] if r.get("status") == "ok"]
    assert ok and ok[0]["samples"] == BAR_COUNT - HORIZON
    # §22: the falling series IS disclosed as a failure case, not hidden
    assert backtest["aggregate"]["portfolio_avg_return_pct"] < 0
    assert len(backtest["failure_cases"]) == len(ok)
    assert backtest["failure_cases"][0]["reason"] in ("平均收益为负", "命中率不足 50%")
    # §47 battery present in the aggregate
    assert backtest["aggregate"]["sensitivity"], "sensitivity combos missing"
    assert len(backtest["aggregate"]["sensitivity"]) >= 3
    assert backtest["aggregate"]["regime_split"], "regime split missing"

    bt_artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "strategy_backtest"}
    ).json()
    assert bt_artifacts["count"] == 1
    lineage = client.get(
        f"/api/v1/artifacts/{bt_artifacts['results'][0]['artifact_id']}/lineage"
    ).json()
    assert "strategy_version" in {u["artifact_type"] for u in lineage["upstream"]}


def test_validate_blocked_without_backtest(client, monkeypatch, strategy_chain):
    strategy = strategy_chain["strategy"]
    blocked = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert blocked.status_code == 422
    assert blocked.json()["error_code"] == "strategy.validation_blocked"
    detail = client.get(f"/api/v1/strategies/{strategy['version_id']}").json()["strategy"]
    assert detail["status"] == "DRAFT"


def test_validate_marks_experimental(client, monkeypatch, strategy_chain):
    strategy = strategy_chain["strategy"]
    _mock_sources(monkeypatch)  # rising bars
    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    assert launched.status_code == 202
    _await(
        client,
        f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}",
        "backtest",
    )
    validated = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert validated.status_code == 200, validated.text
    body = validated.json()["strategy"]
    # §47: v1 has not run the full battery → EXPERIMENTAL, never "正式"
    assert body["status"] == "EXPERIMENTAL"
    assert "EXPERIMENTAL" in body["verdict"]
    assert "盯盘" in body["verdict"]


def test_backtest_fails_honestly_without_bars(client, monkeypatch):
    # source down for the WHOLE flow — no kline evidence can ever reach the
    # ledger (a successful earlier fetch would legitimately serve dedup)
    _mock_sources(monkeypatch, kline_ok=False)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_stratnoBars")
    assert body.status_code == 202
    card = client.post(
        "/api/v1/experience-cards/from-report",
        json={"report_id": body.json()["report_id"]},
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
    assert launched.status_code == 202
    backtest = _await(
        client,
        f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}",
        "backtest",
    )
    assert backtest["status"] == "failed"
    assert "unavailable" in backtest["error"]
    # validate still refused after a failed backtest (§47 gate)
    blocked = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert blocked.status_code == 422


def test_strategy_from_missing_screening_is_404(client):
    resp = client.post(
        "/api/v1/strategies/from-screening",
        json={"screening_run_id": "sr_missing00000"},
    )
    assert resp.status_code == 404


def test_full_battery_validates_positive_strategy(client, monkeypatch, strategy_chain):
    """§47: with the full battery (cross-instrument + regime split +
    sensitivity) and a positive portfolio, the version earns VALIDATED."""
    strategy = strategy_chain["strategy"]
    # rising bars spanning TWO years → ≥2 regimes in the split
    two_year_rising = {"data": {"klines": [
        f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},"
        f"{10.0 + i * 0.1:.2f},{10.0 + i * 0.1:.2f},"
        f"{10.5 + i * 0.1:.2f},{9.5 + i * 0.1:.2f},"
        "1000,10000,1.0,1.0,0.1,1.0"
        for i in range(40)
    ] + [
        f"2026-{(i - 40) + 1:02d}-{(i % 28) + 1:02d},"
        f"{10.0 + i * 0.1:.2f},{10.0 + i * 0.1:.2f},"
        f"{10.5 + i * 0.1:.2f},{9.5 + i * 0.1:.2f},"
        "1000,10000,1.0,1.0,0.1,1.0"
        for i in range(40, 80)
    ]}}
    def two_year_get(url, timeout=10.0, **kwargs):
        if "kline" in url:
            return httpx.Response(200, json=two_year_rising)
        return httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", two_year_get)
    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    assert launched.status_code == 202
    _await(
        client,
        f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}",
        "backtest",
    )
    validated = client.post(f"/api/v1/strategies/{strategy['version_id']}/validate")
    assert validated.status_code == 200, validated.text
    body = validated.json()["strategy"]
    assert body["status"] == "VALIDATED"
    assert "VALIDATED" in body["verdict"]
    assert "分域" in body["verdict"]


def test_regime_split_uses_exit_year(client, monkeypatch, strategy_chain):
    strategy = strategy_chain["strategy"]
    # bars spanning two years: 40 bars in 2025, 20 in 2026
    two_year = {
        "data": {
            "klines": [
                (
                    f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},"
                    if i < 40
                    else f"2026-{(i - 40) + 1:02d}-"
                )
                + "15.00,15.00,15.50,14.50,1000,10000,1.0,1.0,0.1,1.0"
                for i in range(BAR_COUNT)
            ]
        }
    }

    def fake_get(url, timeout=10.0, **kwargs):
        if "kline" in url:
            # flat closes → forward returns exactly 0 → hit at threshold 0
            return httpx.Response(200, json={
                "data": {"klines": [
                    ("2025-%02d-%02d," % ((i // 28) + 1, (i % 28) + 1) if i < 40
                     else "2026-%02d-%02d," % (i - 39, (i % 28) + 1))
                    + "15.00,15.00,15.50,14.50,1000,10000,1.0,1.0,0.1,1.0"
                    for i in range(BAR_COUNT)
                ]}})
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)
    launched = client.post(f"/api/v1/strategies/{strategy['version_id']}/backtest")
    assert launched.status_code == 202
    backtest = _await(
        client,
        f"/api/v1/strategies/backtests/{launched.json()['backtest']['backtest_id']}",
        "backtest",
    )
    regimes = backtest["aggregate"]["regime_split"]
    assert set(regimes.keys()) == {"2025", "2026"}
    assert all(r["samples"] > 0 for r in regimes.values())
