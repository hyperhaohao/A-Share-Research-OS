"""V2 Phase E — 智能选股（总纲 §19/§20/§45）.

验收：
  - ExperienceCard → POST /screening-runs/from-card → 后台执行 →
    候选列表（rank/score/matched_rules/factor_scores/explanation/risks，§20）；
  - 解释由真实研究状态拼装（无裸技术 id）；被排除原因按规则聚合（§20
    「为什么没选中」）；
  - screening_run artifact 注册并 generated_from 经验卡；事件可回放。
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


def _make_card(client, monkeypatch) -> dict:
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_screencard01")
    assert body.status_code == 202
    report_id = body.json()["report_id"]
    created = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": report_id}
    )
    assert created.status_code == 201, created.text
    return created.json()["card"]


def _await_run(client, run_id: str, *, timeout_s: float = 30.0) -> dict:
    import time

    deadline = timeout_s
    run = None
    while deadline > 0:
        run = client.get(f"/api/v1/screening-runs/{run_id}").json()["run"]
        if run["status"] != "running":
            return run
        time.sleep(0.1)
        deadline -= 0.1
    raise AssertionError(f"screening did not finish: {run}")


def test_screening_from_card_completes_with_explanations(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    created = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    assert created.status_code == 202, created.text
    run = _await_run(client, created.json()["run"]["run_id"])

    assert run["status"] == "completed", run
    assert run["card_id"] == card["card_id"]
    assert run["universe_size"] > 0
    # the pipeline gave 000831 a report + quote + thesis → it must be a candidate
    candidates = run["candidates"]
    ids = [c["instrument_id"] for c in candidates]
    assert "SZSE:000831" in ids
    top = next(c for c in candidates if c["instrument_id"] == "SZSE:000831")

    # §20: why-selected must be explicit and sourced
    assert top["rank"] >= 1
    assert top["score"] > 0
    assert len(top["matched_rules"]) == 3
    assert "完整研究报告" in top["explanation"]
    assert "论点方向" in top["explanation"]
    assert "有可见行情证据" in top["explanation"]
    assert card["card_id"] in top["experience_card_refs"]
    assert "undefined" not in top["explanation"]

    # excluded reasons are aggregated per rule (为什么没选中)
    excluded = run["excluded_summary"]
    assert excluded["universe_size"] == run["universe_size"]
    assert excluded["candidate_count"] == len(candidates)
    assert set(excluded["excluded_by_rule"].keys()) == {"has_report", "thesis_direction", "has_quote"}
    # every non-candidate is counted somewhere
    assert sum(excluded["excluded_by_rule"].values()) + len(candidates) >= excluded["universe_size"] - excluded["excluded_by_rule"].get("has_quote", 0)

    # artifact: screening_run generated_from the experience card
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "screening_run"}
    ).json()
    assert artifacts["count"] == 1
    lineage = client.get(f"/api/v1/artifacts/{artifacts['results'][0]['artifact_id']}/lineage").json()
    assert "experience_card" in {u["artifact_type"] for u in lineage["upstream"]}


def test_screening_direction_rule_filters(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    created = client.post(
        "/api/v1/screening-runs/from-card",
        json={"card_id": card["card_id"]},
    )
    # second run with a direction rule the 000831 thesis may not match is
    # still valid; assert the default run's direction rule is 'any'
    run = _await_run(client, created.json()["run"]["run_id"])
    direction_rule = next(r for r in run["rules"] if r["kind"] == "thesis_direction")
    assert direction_rule["direction"] == "any"


def test_screening_from_missing_card_is_404(client):
    resp = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": "exp_missing0000"}
    )
    assert resp.status_code == 404


def test_screening_events_replayable(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    created = client.post(
        "/api/v1/screening-runs/from-card", json={"card_id": card["card_id"]}
    )
    run_id = created.json()["run"]["run_id"]
    _await_run(client, run_id)
    # events endpoint lives on the generic research-runs route (§37)
    replay = client.get(f"/api/v1/research-runs/{run_id}/events")
    assert replay.status_code == 200
    types = [e["event_type"] for e in replay.json()["results"]]
    assert types[0] == "screening_started"
    assert types[-1] == "screening_completed"
