"""V2 Phase A — Artifact Registry / Provenance / RunEvent persistence / Handoff.

验收（docs/v2/ARTIFACT-PROTOCOL.md §5 / HANDOFF-PROTOCOL.md §5）：
  - pipeline 运行后 ResearchRun/Report/ReportVersion 注册为 Artifact，
    run --produced--> report_version --derived_from--> report 边齐全；
  - run 事件全部落库（回放 == 实时事件数）；
  - from-report 预测注册并 generated_from 报告；lineage 可回溯；
  - Handoff 信封：合法动作落库，未注册动作显式 422。
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session, session_scope
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


def _run_full_pipeline(client, monkeypatch) -> dict:
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    outcome = client.post(
        "/api/v1/pipeline/run?instrument=000831&run_id=run_phaseatest001"
    )
    assert outcome.status_code == 202, outcome.text
    return outcome.json()


def test_pipeline_registers_artifacts_and_persists_events(client, monkeypatch):
    body = _run_full_pipeline(client, monkeypatch)

    # registry: run + report + report_version all registered
    run_id = body["run_id"]
    artifacts = client.get("/api/v1/artifacts", params={"query": "中国稀土"}).json()
    types = {a["artifact_type"] for a in artifacts["results"]}
    assert {"research_run", "report", "report_version"} <= types

    # provenance: run --produced--> version --derived_from--> report (handle)
    report_version = next(
        a for a in artifacts["results"] if a["artifact_type"] == "report_version"
    )
    lineage = client.get(f"/api/v1/artifacts/{report_version['artifact_id']}/lineage").json()
    upstream = {u["artifact_type"]: u["relation"] for u in lineage["upstream"]}
    assert upstream.get("research_run") == "produced"
    downstream = {d["artifact_type"]: d["relation"] for d in lineage["downstream"]}
    assert downstream.get("report") == "derived_from"

    # run events persisted: replay count == live event count
    replay = client.get(f"/api/v1/research-runs/{run_id}/events")
    assert replay.status_code == 200
    live_count = len(body["events"])
    assert replay.json()["count"] == live_count
    first = replay.json()["results"][0]
    assert first["event_type"] == "run_started"
    assert first["stage"] == "PLANNING"


def _seed_valuations(factory, snapshot_id: str) -> None:
    """The mocked pipeline run has no financials, so valuations must be
    seeded for the (honest) PredictionBuilder to derive a range."""
    from app.domain.valuation import ValuationMethod, ValuationResult
    from app.storage.valuation_repo import ValuationIn, ValuationRepository

    with session_scope(factory) as session:
        repo = ValuationRepository(session)
        for method, value in ((ValuationMethod.PE, 30.0), (ValuationMethod.PB, 27.314)):
            repo.save(
                ValuationResult(method=method, value=value, inputs_used={}, detail={}),
                ValuationIn(
                    instrument_id="SZSE:000831",
                    snapshot_id=snapshot_id,
                    method=method,
                ),
            )


def test_prediction_from_report_links_to_report_artifact(client, monkeypatch):
    body = _run_full_pipeline(client, monkeypatch)
    _seed_valuations(client.app.state._test_factory, body["snapshot_id"])
    created = client.post(
        "/api/v1/predictions/from-report",
        json={"report_id": body["report_id"], "horizon": "5D"},
    )
    assert created.status_code == 201, created.text

    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "prediction"}
    ).json()
    assert artifacts["count"] == 1
    prediction_artifact = artifacts["results"][0]

    lineage = client.get(f"/api/v1/artifacts/{prediction_artifact['artifact_id']}/lineage").json()
    upstream = {u["artifact_type"]: u["relation"] for u in lineage["upstream"]}
    assert upstream.get("report") == "generated_from"
    # transitive: run reachable two hops up
    types_up = {u["artifact_type"] for u in lineage["upstream"]}
    assert {"research_run", "report_version"} <= types_up

    # instrument-scoped artifact search works for the regression ticker
    scoped = client.get(
        "/api/v1/artifacts", params={"instrument_id": "SZSE:000831"}
    ).json()
    assert scoped["count"] >= 2


def test_handoff_records_envelope_and_refuses_unknown_action(client, monkeypatch):
    body = _run_full_pipeline(client, monkeypatch)
    report_artifact = client.get(
        "/api/v1/artifacts",
        params={"artifact_type": "report", "instrument_id": "SZSE:000831"},
    ).json()["results"][0]

    ok = client.post(
        "/api/v1/handoffs",
        json={
            "source_module": "report",
            "target_module": "prediction",
            "action": "create_prediction",
            "artifact_ids": [report_artifact["artifact_id"]],
            "context": {"primary_instrument_id": "SZSE:000831"},
            "message": "user clicked 生成预测",
        },
    )
    assert ok.status_code == 201
    envelope = ok.json()["handoff"]
    assert envelope["context"]["primary_instrument_id"] == "SZSE:000831"
    listed = client.get("/api/v1/handoffs").json()
    assert any(h["handoff_id"] == envelope["handoff_id"] for h in listed["results"])

    # unregistered action → explicit refusal
    bad = client.post(
        "/api/v1/handoffs",
        json={
            "source_module": "report",
            "target_module": "trade",
            "action": "place_order",
            "artifact_ids": [report_artifact["artifact_id"]],
        },
    )
    assert bad.status_code == 422
    assert bad.json()["error_code"] == "handoff.invalid"

    # missing artifact → explicit refusal
    ghost = client.post(
        "/api/v1/handoffs",
        json={
            "source_module": "report",
            "target_module": "prediction",
            "action": "create_prediction",
            "artifact_ids": ["art_does_not_exist__"],
        },
    )
    assert ghost.status_code == 422


def test_replay_404_for_unknown_run(client):
    resp = client.get("/api/v1/research-runs/run_missing000/events")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "run.events_not_found"
