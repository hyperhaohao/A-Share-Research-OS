"""Multi-instrument E2E regression (任务书 §71): four boards, full pipeline.

Each instrument type from §71 runs the complete flow through the real API:
collect (mocked source) → PIT snapshot → claim → thesis → valuations →
gated bilingual report → timeline. No mocks in the business path — only the
HTTP transport is faked with realistic bodies.
"""

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

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


# Remediation R0.7 classification: this file exercises full API flows against a
# TestClient with monkeypatched source transport — it is an API Integration E2E,
# NOT a Live Research E2E (live runs in R5).
pytestmark = pytest.mark.api_integration

# (code, name, exchange_prefix, price)
INSTRUMENTS = [
    ("600519", "贵州茅台", "sh", "1648.00"),   # 沪市主板 · 消费
    ("000001", "平安银行", "sz", "11.59"),     # 深市主板 · 金融
    ("300750", "宁德时代", "sz", "188.00"),    # 创业板 · 新能源/成长
    ("688981", "中芯国际", "sh", "46.20"),     # 科创板 · 科技
]


def _body(code: str, prefix: str, price: str) -> str:
    return (
        f'v_{prefix}{code}="1~NAME~{code}~{price}~{price}~{price}~32924~85755~24354~'
        f"{price}~12~{price}~8~{price}~21~{price}~4~{price}~100~"
        f"{price}~15~{price}~6~{price}~9~{price}~7~"
        f"{price}/34~20260828150123~0.00~0.00~{price}~{price}~"
        f"{price}/54280/895070000~54280~89507~2.34~20.86~~{price}~{price}~"
        '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
    )


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


@pytest.mark.parametrize(("code", "name", "prefix", "price"), INSTRUMENTS)
def test_full_research_pipeline_per_board(client, monkeypatch, code, name, prefix, price):
    """E2E: search → collect → claim → thesis → valuation → report → timeline."""
    resp = httpx.Response(200, content=_body(code, prefix, price).encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)

    # 1) instrument resolution by name
    found = client.get("/api/v1/instruments", params={"query": name}).json()
    assert found["count"] == 1
    instrument_id = found["results"][0]["instrument"]["instrument_id"]

    # 2) real collection → evidence with full provenance
    collected = client.post("/api/v1/evidence/collect", params={"instrument": code}).json()
    assert collected["created"] == 1
    evidence_id = collected["evidence"][0]["evidence_id"]

    # 3) PIT snapshot
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": code, "as_of": _pit_as_of()},
    ).json()["snapshot"]
    assert snapshot["evidence_count"] == 1

    # 4) claim over the evidence
    claim = client.post(
        "/api/v1/claims",
        json={
            "instrument_id": instrument_id,
            "snapshot_id": snapshot["snapshot_id"],
            "statement": f"{name}研究状态成立测试",
            "claim_type": "fundamental_fact",
            "supporting_evidence_refs": [evidence_id],
            "fact_status": "confirmed_fact",
            "confidence": 0.8,
        },
    ).json()["claim"]

    # 5) thesis over the claim
    thesis = client.post(
        "/api/v1/theses",
        json={
            "instrument_id": instrument_id,
            "snapshot_id": snapshot["snapshot_id"],
            "title": f"{name}核心论点",
            "description": "E2E 回归论点",
            "supporting_claims": [claim["claim_id"]],
            "confidence": 0.7,
            "risks": ["测试风险"],
        },
    ).json()["thesis"]

    # 6) deterministic valuation
    valuation = client.post(
        "/api/v1/valuations/compute",
        json={
            "instrument_id": instrument_id,
            "snapshot_id": snapshot["snapshot_id"],
            "thesis_id": thesis["thesis_id"],
            "method": "pe",
            "inputs": {"price": float(price), "eps_ttm": 1.0, "target_pe": 20},
        },
    ).json()["valuation"]
    assert valuation["computable"] is True

    # 7) gated bilingual reports
    for language, section_label in (("zh-CN", "核心论点"), ("en-US", "Key Theses")):
        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": language},
        ).json()["report"]
        assert report["gate_status"] in ("pass", "warn")
        assert section_label in report["markdown"]
        assert evidence_id in report["content_json"]["citations"]

    # 8) timeline records the run
    timeline = client.get("/api/v1/timeline", params={"instrument": code}).json()
    kinds = {e["kind"] for e in timeline["results"]}
    assert "market_event" in kinds and "claim_changed" in kinds and "thesis_changed" in kinds

    # 9) graph traces claim upstream to its source
    trace = client.get(
        "/api/v1/graph/trace",
        params={
            "instrument": code,
            "node_id": f"claim:{claim['claim_id']}",
            "direction": "upstream",
        },
    ).json()
    trace_kinds = {n["kind"] for n in trace["nodes"]}
    assert {"evidence", "source"} <= trace_kinds


def test_multi_instrument_reports_are_isolated(client, monkeypatch):
    """Each instrument's report cites only its own evidence (no cross-leak)."""
    bodies = {code: _body(code, prefix, price) for code, name, prefix, price in INSTRUMENTS}

    def fake_get(url, timeout):
        for code, body in bodies.items():
            if code in url:
                return httpx.Response(200, content=body.encode("gbk"))
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(httpx, "get", fake_get)

    report_ids = []
    for code, name, _prefix, _price in INSTRUMENTS:
        client.post("/api/v1/evidence/collect", params={"instrument": code})
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": code, "as_of": _pit_as_of()},
        ).json()["snapshot"]
        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
        ).json()["report"]
        report_ids.append((code, report["report_id"], report["content_json"]["citations"]))

    # every citation belongs to exactly one instrument's evidence
    cited_owners = [(code, citation) for code, _, citations in report_ids for citation in citations]
    assert len(cited_owners) == len({c for _, c in cited_owners})
