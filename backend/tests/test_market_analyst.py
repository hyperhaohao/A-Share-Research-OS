"""Market analyst: deterministic briefs + missing-data loop (任务书 §30)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.agent_repo import AgentRepository, ResearchRequestStatus
from app.storage.orm import Base

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()



RAW_OK = (
    'v_sh600519="1~贵州茅台~600519~1648.00~1651.00~1655.00~32924~85755~24354~'
    "1648.00~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "1648.10~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "1648.00/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    "1648.00/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _seed_snapshot(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    ).json()["snapshot"]
    return snapshot


def test_market_analyst_produces_cited_brief_and_claim(client, monkeypatch):
    snapshot = _seed_snapshot(client, monkeypatch)
    body = client.post(
        "/api/v1/analysts/market/run",
        params={"snapshot_id": snapshot["snapshot_id"], "collect_missing": False},
    )
    assert body.status_code == 200, body.text
    brief = body.json()["brief"]

    # conclusions derived from real quote evidence, fully cited
    assert brief["evidence_refs"], "brief must cite evidence"
    metrics = {c["metric"] for c in brief["conclusions"]}
    assert {"price", "change_pct", "total_market_cap_yuan"} <= metrics
    assert brief["claim_refs"], "analyst should have created a fact claim"
    assert brief["confidence"] >= 0.8

    # missing-data disclosure: financials/announcements are not in snapshot
    missing = {m["capability"] for m in brief["missing_data"]}
    assert "financials" in missing and "announcements" in missing

    # the created claim exists and is traceable
    claims = client.get(
        "/api/v1/claims",
        params={"instrument_id": "SSE:600519", "snapshot_id": snapshot["snapshot_id"]},
    ).json()
    assert claims["count"] == 1
    assert claims["results"][0]["claim_id"] == brief["claim_refs"][0]
    # claim cites the same quote evidence the brief cites
    assert set(claims["results"][0]["supporting_evidence_refs"]) <= set(brief["evidence_refs"])


def test_missing_data_creates_open_research_requests(client, monkeypatch):
    snapshot = _seed_snapshot(client, monkeypatch)
    client.post(
        "/api/v1/analysts/market/run",
        params={"snapshot_id": snapshot["snapshot_id"], "collect_missing": False},
    )
    requests = client.get(
        "/api/v1/analysts/research-requests",
        params={"instrument_id": "SSE:600519", "status": "open"},
    ).json()
    assert requests["count"] >= 2
    capabilities = {r["capability"] for r in requests["results"]}
    assert "financials" in capabilities and "announcements" in capabilities


def test_missing_data_loop_closes_across_runs(client, monkeypatch):
    """missing_data → ResearchRequest → collector → next run sees the data."""
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)

    # Build a snapshot for a moment BEFORE any evidence existed: the analyst
    # finds nothing, discloses market_data as missing, and the collector runs.
    empty = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2020-01-01T00:00:00+00:00"},
    ).json()["snapshot"]
    first = client.post(
        "/api/v1/analysts/market/run",
        params={"snapshot_id": empty["snapshot_id"], "collect_missing": True},
    ).json()
    assert first["brief"]["conclusions"] == []
    assert first["open_request_ids"]

    # The collector ran for the missing market_data capability: real quote
    # evidence now exists in the database (PIT: available_time = now).
    later_snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    ).json()["snapshot"]
    assert later_snapshot["evidence_count"] >= 1

    # A later analyst run over that snapshot produces a cited brief.
    second = client.post(
        "/api/v1/analysts/market/run",
        params={"snapshot_id": later_snapshot["snapshot_id"], "collect_missing": False},
    ).json()
    assert second["brief"]["conclusions"]
    assert second["brief"]["evidence_refs"]
def test_brief_integrity_only_cites_pinned_evidence(client, monkeypatch):
    """An analyst run against an empty-future snapshot cites nothing."""
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    # collect evidence but build snapshot strictly BEFORE it existed
    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
    empty = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2020-01-01T00:00:00+00:00"},
    ).json()["snapshot"]
    body = client.post(
        "/api/v1/analysts/market/run",
        params={"snapshot_id": empty["snapshot_id"], "collect_missing": False},
    ).json()
    assert body["brief"]["evidence_refs"] == []
    assert body["brief"]["claim_refs"] == []
    assert body["brief"]["conclusions"] == []
    assert body["brief"]["confidence"] <= 0.2
    assert body["brief"]["missing_data"][0]["capability"] == "market_data"
