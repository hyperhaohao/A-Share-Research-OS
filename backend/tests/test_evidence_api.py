"""Evidence API: real collection pipeline + traceable listing."""

from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


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
        poolclass=StaticPool,  # single shared connection for the in-memory DB
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


def test_collect_creates_evidence_with_provenance(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    body = client.post(
        "/api/v1/evidence/collect",
        params={"instrument": "600519", "capability": "market_data"},
    ).json()

    assert body["created"] == 1
    assert body["deduped"] == 0
    manifest = body["manifest"]
    assert manifest["instrument_id"] == "SSE:600519"
    assert manifest["final_status"] == "success"
    assert manifest["final_source"] == "tencent_quote"

    evidence = body["evidence"][0]
    # Full provenance chain on the API surface (任务书 §22)
    assert evidence["evidence_id"]
    assert evidence["content_hash"]
    assert evidence["source"] == "tencent_quote"
    assert evidence["authority_level"] == "B2"
    assert evidence["fact_status"] == "confirmed_fact"
    assert evidence["event_time"] is not None
    assert evidence["metadata"]["price"] == 1648.0


def test_collect_is_idempotent_on_repeat(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)

    first = client.post(
        "/api/v1/evidence/collect", params={"instrument": "600519"}
    ).json()
    second = client.post(
        "/api/v1/evidence/collect", params={"instrument": "600519"}
    ).json()

    # Same real-world fact → same content-addressed evidence, no duplicate rows.
    assert first["evidence"][0]["evidence_id"] == second["evidence"][0]["evidence_id"]
    assert second["created"] == 0
    assert second["deduped"] == 1


def test_list_evidence_after_collect(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})

    listed = client.get(
        "/api/v1/evidence", params={"instrument_id": "SSE:600519"}
    ).json()
    assert listed["count"] == 1
    record = listed["results"][0]
    assert record["evidence_type"] == "market_quote"
    assert record["source_url"]


def test_failed_collection_records_manifest_not_fake_data(client, monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectTimeout("down")

    monkeypatch.setattr(httpx, "get", boom)
    body = client.post(
        "/api/v1/evidence/collect", params={"instrument": "600519"}
    ).json()

    manifest = body["manifest"]
    assert manifest["final_status"] in ("network_error", "source_unavailable")
    assert manifest["final_source"] is None
    assert body["created"] == 0
    assert body["evidence"] == []

    listed = client.get(
        "/api/v1/evidence", params={"instrument_id": "SSE:600519"}
    ).json()
    assert listed["count"] == 0  # no evidence, and no fabricated placeholder


def test_unknown_instrument_collect_is_404(client):
    resp = client.post(
        "/api/v1/evidence/collect", params={"instrument": "NOPE9999"}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "instrument.not_found"


def test_live_collection_real_network(client):
    """Live: real quote → evidence in DB → traceable list (skips offline)."""
    outcome = client.post(
        "/api/v1/evidence/collect", params={"instrument": "600519"}
    )
    if outcome.status_code == 503:
        pytest.skip("network unreachable for live evidence collection")
    body = outcome.json()
    assert body["created"] >= 1
    listed = client.get("/api/v1/evidence", params={"instrument_id": "SSE:600519"}).json()
    assert listed["count"] >= 1
