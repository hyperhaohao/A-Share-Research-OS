"""Research graph tests (任务书 §47/§95)."""

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


def _seed_full_state(client, monkeypatch):
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
        },
    ).json()["thesis"]
    report = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    return {
        "snapshot": snapshot,
        "evidence_id": evidence_id,
        "claim": claim,
        "thesis": thesis,
        "report": report,
    }


def test_graph_contains_full_chain(client, monkeypatch):
    state = _seed_full_state(client, monkeypatch)
    graph = client.get("/api/v1/graph", params={"instrument": "600519"}).json()

    node_ids = {n["node_id"] for n in graph["nodes"]}
    assert f"evidence:{state['evidence_id']}" in node_ids
    assert f"claim:{state['claim']['claim_id']}" in node_ids
    assert f"thesis:{state['thesis']['thesis_id']}" in node_ids
    assert f"snapshot:{state['snapshot']['snapshot_id']}" in node_ids
    assert any(n["kind"] == "source" for n in graph["nodes"])

    # edges: evidence → claim → thesis exist
    edge_pairs = {(e["src"], e["dst"]) for e in graph["edges"]}
    assert (
        f"claim:{state['claim']['claim_id']}",
        f"thesis:{state['thesis']['thesis_id']}",
    ) in edge_pairs
    assert (
        f"evidence:{state['evidence_id']}",
        f"claim:{state['claim']['claim_id']}",
    ) in edge_pairs


def test_upstream_trace_from_thesis_reaches_source(client, monkeypatch):
    """§95: 这条结论来自哪里 — upstream from thesis reaches source & evidence."""
    state = _seed_full_state(client, monkeypatch)
    client.post(
        f"/api/v1/reports/{state['report']['report_id']}/versions",
        json={"language": "zh-CN", "markdown": state["report"]["markdown"]},
    )
    trace = client.get(
        "/api/v1/graph/trace",
        params={
            "instrument": "600519",
            "node_id": f"thesis:{state['thesis']['thesis_id']}",
            "direction": "upstream",
        },
    ).json()
    kinds = {n["kind"] for n in trace["nodes"]}
    assert "claim" in kinds
    assert "evidence" in kinds
    assert "source" in kinds


def test_downstream_trace_from_evidence_reaches_thesis(client, monkeypatch):
    """§95: 它影响了什么 — downstream from evidence reaches thesis/report."""
    state = _seed_full_state(client, monkeypatch)
    client.post(
        f"/api/v1/reports/{state['report']['report_id']}/versions",
        json={"language": "zh-CN", "markdown": state["report"]["markdown"]},
    )
    trace = client.get(
        "/api/v1/graph/trace",
        params={
            "instrument": "600519",
            "node_id": f"evidence:{state['evidence_id']}",
            "direction": "downstream",
        },
    ).json()
    kinds = {n["kind"] for n in trace["nodes"]}
    assert "claim" in kinds
    assert "thesis" in kinds
    assert "report_version" in kinds


def test_trace_unknown_node_404(client, monkeypatch):
    _seed_full_state(client, monkeypatch)
    resp = client.get(
        "/api/v1/graph/trace",
        params={"instrument": "600519", "node_id": "thesis:ths_nope"},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "graph.node_not_found"
