"""V2 Phase D — 验证工作流（最小强类型 DAG，总纲 §44/§73）.

验收：
  - ExperienceCard → POST /workflow-runs/from-card → 后台执行 DAG
    Data(真实日线) → Rule(前向收益) → Validation(指标) → Output(落库+注册)；
  - 指标确定性（构造线性上涨序列 → 命中率 100%；阈值高于全部样本 → 0%）；
  - quant validation 记录写入经验卡（§72 衔接），artifact 注册并
    generated_from experience_card，事件回放完整（§37）；
  - 日线不可得 → 节点失败显形，不伪造指标。
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
# linear rise: close = 10.00 + i*0.10 → every forward return positive
KLINE_JSON = {
    "data": {
        "klines": [
            # unique ascending dates (2025-01-01 …) so the sorted series is
            # strictly the linear rise; close = open = 10.00 + i*0.10
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


def _make_card(client, monkeypatch, *, kline_ok: bool = True) -> dict:
    _mock_sources(monkeypatch, kline_ok=kline_ok)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_wfcard0001")
    assert body.status_code == 202
    report_id = body.json()["report_id"]
    created = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": report_id}
    )
    assert created.status_code == 201, created.text
    return created.json()["card"]


def _await_run(client, run_id: str, *, timeout_s: float = 60.0) -> dict:
    import time

    deadline = timeout_s
    run = None
    while deadline > 0:
        run = client.get(f"/api/v1/workflow-runs/{run_id}").json()["run"]
        if run["status"] != "running":
            return run
        time.sleep(0.1)
        deadline -= 0.1
    raise AssertionError(f"workflow did not finish: {run}")


def _await_workflow_on_card(client, card_id: str, monkeypatch, **params) -> dict:
    created = client.post(
        "/api/v1/workflow-runs/from-card",
        json={"card_id": card_id, **params},
    )
    assert created.status_code == 202, created.text
    return _await_run(client, created.json()["run"]["run_id"])


def test_workflow_completes_with_deterministic_metrics(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    run = _await_workflow_on_card(client, card["card_id"], monkeypatch, horizon_days=HORIZON)

    assert run["status"] == "completed", run
    assert run["instrument_id"] == "SZSE:000831"
    by_kind = {n["kind"]: n for n in run["nodes"]}
    assert all(n["status"] == "ok" for n in run["nodes"]), run["nodes"]
    assert "根日线" in by_kind["data"]["detail"]

    metrics = run["metrics"]
    assert metrics["samples"] == BAR_COUNT - HORIZON
    # linear rise → every forward return clears a 0% threshold
    assert metrics["hit_rate_pct"] == 100.0
    assert metrics["avg_return_pct"] is not None
    assert metrics["worst_return_pct"] > 0

    # §72 衔接: the quant validation landed on the card
    detail = client.get(f"/api/v1/experience-cards/{card['card_id']}").json()["card"]
    quant = [v for v in detail["validations"] if v["method"] == "quant"]
    assert len(quant) == 1
    assert "量化验证" in quant[0]["summary"]
    assert detail["status"] == "VALIDATING"

    # artifact: workflow_run linked generated_from the experience card
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "workflow_run"}
    ).json()
    assert artifacts["count"] == 1
    wf_art = artifacts["results"][0]
    lineage = client.get(f"/api/v1/artifacts/{wf_art['artifact_id']}/lineage").json()
    upstream = {u["artifact_type"] for u in lineage["upstream"]}
    assert "experience_card" in upstream

    # §37: the workflow's events are replayable
    replay = client.get(f"/api/v1/workflow-runs/{run['run_id']}/events")
    assert replay.status_code == 200
    types = [e["event_type"] for e in replay.json()["results"]]
    assert types[0] == "workflow_started"
    assert types[-1] == "workflow_completed"
    assert types.count("node_updated") >= 8  # 4 nodes × (running + ok)


def test_workflow_threshold_above_all_returns_gives_zero_hits(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    # return(i) = 2/(100+i) is decreasing → the max is the FIRST window:
    # (close[20]/close[0] - 1) = 20% → any threshold above it yields 0 hits
    max_gain_pct = ((10.0 + 20 * 0.1) / 10.0 - 1) * 100
    assert abs(max_gain_pct - 20.0) < 1e-9
    run = _await_workflow_on_card(
        client, card["card_id"], monkeypatch,
        horizon_days=HORIZON, threshold_pct=max_gain_pct + 1.0,
    )
    assert run["status"] == "completed"
    assert run["metrics"]["hit_rate_pct"] == 0.0


def test_workflow_fails_honestly_when_bars_unavailable(client, monkeypatch):
    # the source is down for the WHOLE test — no kline evidence can exist in
    # the ledger (a successful earlier fetch would legitimately serve dedup)
    card = _make_card(client, monkeypatch, kline_ok=False)
    created = client.post(
        "/api/v1/workflow-runs/from-card",
        json={"card_id": card["card_id"], "horizon_days": 20},
    )
    assert created.status_code == 202
    run = _await_run(client, created.json()["run"]["run_id"])

    assert run["status"] == "failed"
    by_kind = {n["kind"]: n for n in run["nodes"]}
    assert by_kind["data"]["status"] == "failed"
    assert "unavailable" in by_kind["data"]["error"]
    # no validation record written — the DAG stopped before Output
    detail = client.get(f"/api/v1/experience-cards/{card['card_id']}").json()["card"]
    assert [v for v in detail["validations"] if v["method"] == "quant"] == []


def test_workflow_from_missing_card_is_404(client):
    resp = client.post(
        "/api/v1/workflow-runs/from-card",
        json={"card_id": "exp_missing0000", "horizon_days": 20},
    )
    assert resp.status_code == 404


def test_workflow_events_404_for_unknown_run(client):
    resp = client.get("/api/v1/workflow-runs/wr_missing00000/events")
    assert resp.status_code == 404


def test_quant_expression_node_evaluates_card_rule(client, monkeypatch):
    """深度扩展 c: the expression node evaluates the card's quant rule as a
    typed DAG step; a passing rule on the rising series and a failing one
    both record an honest verdict."""
    card = _make_card(client, monkeypatch)
    run = _await_workflow_on_card(
        client, card["card_id"], monkeypatch,
        horizon_days=HORIZON, expression="avg_return > 0 AND hit_rate >= 99",
    )
    assert run["status"] == "completed", run
    by_kind = {n["kind"]: n for n in run["nodes"]}
    assert "expression" in by_kind
    assert run["metrics"]["expression_verdict"] is True
    assert "成立" in by_kind["expression"]["detail"]

    # a rule the series cannot satisfy → verdict False, still an honest run
    run2 = _await_workflow_on_card(
        client, card["card_id"], monkeypatch,
        horizon_days=HORIZON, expression="hit_rate >= 100 AND best_return < 1",
    )
    assert run2["status"] == "completed"
    assert run2["metrics"]["expression_verdict"] is False
    assert "不成立" in {n["kind"]: n for n in run2["nodes"]}["expression"]["detail"]


def test_quant_expression_parse_failure_refuses_up_front(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    resp = client.post(
        "/api/v1/workflow-runs/from-card",
        json={"card_id": card["card_id"], "expression": "import os"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "workflow.expression_invalid"
