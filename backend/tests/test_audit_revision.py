"""Audit + revision accept/reject flow tests (任务书 §43/§44/§78)."""

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

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()



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


def _seed_report_with_claim(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    ).json()["snapshot"]
    evidence_id = collected["evidence"][0]["evidence_id"]
    claim = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "statement": "最新价为 1648.0",
            "claim_type": "fundamental_fact",
            "supporting_evidence_refs": [evidence_id],
            "fact_status": "confirmed_fact",
            "confidence": 0.9,
        },
    ).json()["claim"]
    thesis = client.post(
        "/api/v1/theses",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "title": "估值修复论点",
            "description": "低估值与稳定基本面",
            "supporting_claims": [claim["claim_id"]],
            "confidence": 0.75,
            "risks": ["消费疲软"],
        },
    ).json()["thesis"]
    report = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    client.post(
        f"/api/v1/reports/{report['report_id']}/versions",
        json={"language": "zh-CN", "markdown": report["markdown"]},
    )
    return report, claim, thesis, evidence_id


def test_claim_audit_detects_numeric_inconsistency(client, monkeypatch):
    report, claim, _, _ = _seed_report_with_claim(client, monkeypatch)
    # a claim whose number (999.9) traces to no evidence payload
    bad = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": report["snapshot_id"],
            "statement": "价格已达 999.9 元",
            "claim_type": "fundamental_fact",
            "supporting_evidence_refs": claim["supporting_evidence_refs"],
            "fact_status": "confirmed_fact",
            "confidence": 0.9,
        },
    ).json()["claim"]
    audit = client.post(
        f"/api/v1/reports/{report['report_id']}/audits",
        json={"level": "claim", "target_id": bad["claim_id"]},
    ).json()
    codes = {f["code"] for f in audit["findings"]}
    assert "audit.numeric_inconsistency" in codes
    assert audit["has_fail"] is True


def test_full_report_audit_clean_state_has_no_fail(client, monkeypatch):
    report, _, _, _ = _seed_report_with_claim(client, monkeypatch)
    audit = client.post(
        f"/api/v1/reports/{report['report_id']}/audits",
        json={"level": "full_report"},
    ).json()
    assert audit["has_fail"] is False


def test_revision_accept_creates_new_version_keeping_old(client, monkeypatch):
    """§44+§78: accept → V1.1 created from the proposal; V1.0 kept intact."""
    report, claim, _, _ = _seed_report_with_claim(client, monkeypatch)
    chain = client.get(f"/api/v1/reports/{report['report_id']}/versions").json()
    base_version = chain["results"][-1]

    proposal = client.post(
        f"/api/v1/reports/{report['report_id']}/revisions",
        json={
            "base_version_id": base_version["version_id"],
            "target_section": "executive_summary",
            "target_claim_id": claim["claim_id"],
            "original_text": report["content_json"]["section_items"]["executive_summary"][0]["text_zh"],
            "proposed_text": report["content_json"]["section_items"]["executive_summary"][0]["text_zh"] + "（经复核确认）",
            "reason": "accept revision:复核后确认表述",
            "affected_claims": [claim["claim_id"]],
            "confidence_change": 0.05,
        },
    ).json()["proposal"]
    assert proposal["status"] == "proposed"

    acc_r = client.post(f"/api/v1/revisions/{proposal['proposal_id']}/accept")
    accepted = acc_r.json()
    version = accepted["version"]
    assert version["version_no"] == 2
    assert version["parent_version_id"] == base_version["version_id"]
    assert version["changed_sections"] == ["executive_summary"]

    # old version still exists and is unchanged
    old = client.get(
        f"/api/v1/reports/{report['report_id']}/versions/{base_version['version_id']}"
    ).json()["version"]
    assert old["markdown"] == base_version["markdown"]
    assert "经复核确认" not in old["markdown"]

    # the proposal is accepted and cannot be accepted twice
    again = client.post(f"/api/v1/revisions/{proposal['proposal_id']}/accept")
    assert again.status_code == 422


def test_revision_reject_flow(client, monkeypatch):
    report, _, _, _ = _seed_report_with_claim(client, monkeypatch)
    chain = client.get(f"/api/v1/reports/{report['report_id']}/versions").json()
    base_version = chain["results"][-1]
    proposal = client.post(
        f"/api/v1/reports/{report['report_id']}/revisions",
        json={
            "base_version_id": base_version["version_id"],
            "target_section": "executive_summary",
            "original_text": "贵州茅台当前估值处于近五年低位",
            "proposed_text": "贵州茅台当前估值被高估",
            "reason": "reject test",
        },
    ).json()["proposal"]
    rejected = client.post(f"/api/v1/revisions/{proposal['proposal_id']}/reject").json()["proposal"]
    assert rejected["status"] == "rejected"
    # rejected proposal produced no new version
    chain_after = client.get(f"/api/v1/reports/{report['report_id']}/versions").json()
    assert chain_after["count"] == 1


def test_revision_with_fake_evidence_is_422(client, monkeypatch):
    report, _, _, _ = _seed_report_with_claim(client, monkeypatch)
    chain = client.get(f"/api/v1/reports/{report['report_id']}/versions").json()
    base_version = chain["results"][-1]
    resp = client.post(
        f"/api/v1/reports/{report['report_id']}/revisions",
        json={
            "base_version_id": base_version["version_id"],
            "target_section": "valuation",
            "original_text": "a",
            "proposed_text": "b",
            "reason": "fake evidence",
            "added_evidence_refs": ["ev_nonexistent"],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "revision.evidence_not_found"
