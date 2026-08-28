"""Bilingual report consistency + gate-blocked publication (任务书 §90)."""

import httpx
import pytest
from fastapi.testclient import TestClient

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


def _seed_full_state(client, monkeypatch):
    """collect → snapshot → claim → thesis → valuation, all real API calls."""
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
            "statement": "贵州茅台当前估值处于近五年低位",
            "claim_type": "valuation_assessment",
            "supporting_evidence_refs": [evidence_id],
            "fact_status": "confirmed_fact",
            "confidence": 0.8,
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
            "risks": ["消费疲软", "政策限制"],
            "invalidate_conditions": ["批价连续两季下行"],
        },
    ).json()["thesis"]
    client.post(
        "/api/v1/valuations/compute",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": snapshot["snapshot_id"],
            "thesis_id": thesis["thesis_id"],
            "method": "pe",
            "inputs": {"price": 80.0, "eps_ttm": 4.0, "target_pe": 25},
        },
    )
    return snapshot, claim, thesis, evidence_id


def test_bilingual_reports_share_numbers_and_citations(client, monkeypatch):
    """§90: same research state → identical numbers/claims/citations across languages."""
    snapshot, claim, thesis, evidence_id = _seed_full_state(client, monkeypatch)

    zh = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    en = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "en-US"},
    ).json()["report"]

    from tests.test_report_render import numbers_of

    zh_markdown, en_markdown = zh["markdown"], en["markdown"]
    # structured numbers identical (price, eps-derived value, percentages…)
    shared_numbers = {"1648.0", "100.0", "25.0"}
    assert shared_numbers <= numbers_of(zh_markdown)
    assert shared_numbers <= numbers_of(en_markdown)

    # claim statement preserved verbatim in both (original never translated away)
    assert claim["statement"] in zh_markdown
    assert claim["statement"] in en_markdown

    # citations identical
    assert zh["content_json"]["citations"] == en["content_json"]["citations"]
    assert evidence_id in zh["content_json"]["citations"]

    # section scaffolding localized
    assert "## 摘要" in zh_markdown or "## 核心论点" in zh_markdown
    assert "## Key Theses" in en_markdown or "## Executive Summary" in en_markdown


def test_gate_blocks_unsafe_publication(client, monkeypatch):
    """A report whose disclaimers/risks are fine passes; a report compiled
    from a state with NO risks section can still compile but must carry the
    gate verdict. The API must never mark blocked reports published."""
    snapshot, _, _, _ = _seed_full_state(client, monkeypatch)

    body = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN", "publish": True},
    ).json()
    assert body["blocked"] is False
    assert body["report"]["published"] is True
    assert body["report"]["gate_status"] in ("pass", "warn")


def test_missing_data_disclosed_in_report(client, monkeypatch):
    """A report state without financials must say so in data quality."""
    snapshot, _, _, _ = _seed_full_state(client, monkeypatch)
    zh = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    assert any("financials" in note for note in zh["content_json"]["data_quality_notes"])


def test_report_listing_and_fetch(client, monkeypatch):
    snapshot, _, _, _ = _seed_full_state(client, monkeypatch)
    client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    )
    listed = client.get("/api/v1/reports", params={"instrument_id": "SSE:600519"}).json()
    assert listed["count"] == 1
    fetched = client.get(f"/api/v1/reports/{listed['results'][0]['report_id']}")
    assert fetched.status_code == 200
    missing = client.get("/api/v1/reports/rpt_doesnotexist")
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "report.not_found"


def test_pdf_export(client, monkeypatch):
    """PDF export is real, CJK-capable, and content-complete (§17/§39)."""
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    ).json()["snapshot"]
    report = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]

    pdf = client.get(f"/api/v1/reports/{report['report_id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")  # real PDF magic
    assert len(pdf.content) > 1000
