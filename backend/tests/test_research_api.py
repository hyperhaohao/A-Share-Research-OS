"""Research API: claims/theses/events end-to-end with traceability."""

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


def test_claim_then_thesis_full_chain(client, monkeypatch):
    """Create real evidence, then a claim and a thesis over it via the API."""
    import httpx as hx

    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(hx, "get", lambda url, timeout: resp)
    collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2026-08-28T15:00:00+00:00"},
    ).json()["snapshot"]
    evidence_id = collected["evidence"][0]["evidence_id"]
    _ = evidence_id

    claim_body = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "statement": "贵州茅台当前估值处于近五年低位",
            "claim_type": "valuation_assessment",
            "supporting_evidence_refs": [evidence_id],
            "opposing_evidence_refs": [],
            "fact_status": "confirmed_fact",
            "confidence": 0.8,
        },
    )
    assert claim_body.status_code == 201, claim_body.text
    claim = claim_body.json()["claim"]
    assert claim["claim_id"].startswith("clm_")
    assert claim["status"] == "proposed"

    thesis_body = client.post(
        "/api/v1/theses",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "title": "估值修复论点",
            "description": "基于低估值与稳定基本面",
            "supporting_claims": [claim["claim_id"]],
            "confidence": 0.75,
            "catalysts": ["批价回升"],
            "risks": ["消费疲软"],
            "trigger_conditions": ["批价连续回升一个月"],
            "invalidate_conditions": ["批价连续两季下行"],
        },
    )
    assert thesis_body.status_code == 201, thesis_body.text
    thesis = thesis_body.json()["thesis"]
    assert thesis["thesis_id"].startswith("ths_")
    assert thesis["supporting_claims"] == [claim["claim_id"]]

    # traceability listing
    claims = client.get(
        "/api/v1/claims",
        params={"instrument_id": "SSE:600519", "snapshot_id": snapshot["snapshot_id"]},
    ).json()
    assert claims["count"] == 1
    theses = client.get("/api/v1/theses", params={"instrument_id": "SSE:600519"}).json()
    assert theses["count"] == 1


def test_claim_with_fake_evidence_is_422(client):
    resp = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": "snap_test000000000000",
            "statement": "无证据断言应被拒绝",
            "claim_type": "fundamental_fact",
            "supporting_evidence_refs": ["ev_fakesdfsdfdsfdsfdsf"],
            "fact_status": "confirmed_fact",
            "confidence": 0.9,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "claim.evidence_not_found"


def test_thesis_with_fake_claims_is_422(client):
    resp = client.post(
        "/api/v1/theses",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": "snap_test000000000000",
            "title": "引用不存在主张",
            "description": "应被拒绝",
            "supporting_claims": ["clm_nope"],
            "confidence": 0.5,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "thesis.claims_not_found"
