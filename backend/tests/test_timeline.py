"""Timeline aggregation tests (任务书 §46)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


@pytest.fixture()
def client():
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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _seed_full_state(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2026-08-28T15:00:00+00:00"},
    ).json()["snapshot"]
    evidence_id = collected["evidence"][0]["evidence_id"]
    claim = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "statement": "贵州茅台当前估值处于近五年低位",
            "claim_type": "valuation_assessment",
            "supporting_evidence_refs": [evidence_id],
            "fact_status": "confirmed_fact",
            "confidence": 0.8,
        },
    ).json()["claim"]
    client.post(
        "/api/v1/theses",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "title": "估值修复论点",
            "description": "低估值与稳定基本面",
            "supporting_claims": [claim["claim_id"]],
            "confidence": 0.75,
        },
    )
    client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    )
    client.post("/api/v1/research-runs", params={"instrument": "600519"})


def test_timeline_aggregates_all_kinds(client, monkeypatch):
    _seed_full_state(client, monkeypatch)
    timeline = client.get("/api/v1/timeline", params={"instrument": "600519"}).json()
    kinds = {e["kind"] for e in timeline["results"]}
    assert {"market_event", "claim_changed", "thesis_changed", "research_run"} <= kinds
    # sorted newest first
    times = [e["occurred_at"] for e in timeline["results"]]
    assert times == sorted(times, reverse=True)


def test_timeline_kinds_filter(client, monkeypatch):
    _seed_full_state(client, monkeypatch)
    filtered = client.get(
        "/api/v1/timeline",
        params={"instrument": "600519", "kinds": "claim_changed"},
    ).json()
    assert filtered["count"] >= 1
    assert all(e["kind"] == "claim_changed" for e in filtered["results"])


def test_timeline_pagination(client, monkeypatch):
    _seed_full_state(client, monkeypatch)
    page1 = client.get("/api/v1/timeline", params={"instrument": "600519", "limit": 2}).json()
    assert page1["count"] == 2
    page2 = client.get(
        "/api/v1/timeline",
        params={"instrument": "600519", "limit": 2, "offset": 2},
    ).json()
    assert page2["count"] >= 1
    ids1 = {e["ref_id"] for e in page1["results"]}
    ids2 = {e["ref_id"] for e in page2["results"]}
    assert not (ids1 & ids2)


def test_timeline_unknown_instrument_404(client):
    resp = client.get("/api/v1/timeline", params={"instrument": "NOPE9999"})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "instrument.not_found"
