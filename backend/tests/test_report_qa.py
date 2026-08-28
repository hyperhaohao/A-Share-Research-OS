"""Report Q&A tests: Explain is frozen-state-only; Refresh collects (§42)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base, EvidenceORM, SourceManifestORM
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

    holder = {}

    def override_session():
        session = factory()
        holder["session"] = session
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    reset_runtime()
    holder["app"] = TestClient(app)
    yield holder
    reset_runtime()


def _counts(session) -> tuple[int, int]:
    evidence = session.scalars(select(func.count()).select_from(EvidenceORM)).one()
    manifests = session.scalars(select(func.count()).select_from(SourceManifestORM)).one()
    return evidence, manifests


def _seed_report(holder, monkeypatch):
    client = holder["app"]
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)

    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    ).json()["snapshot"]
    evidence_id = snapshot["evidence_ids"][0]

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
            "risks": ["消费疲软"],
        },
    )
    report = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    return report, claim


def test_explain_uses_frozen_state_and_touches_nothing(client, monkeypatch):
    holder = client
    client = holder["app"]
    report, claim = _seed_report(holder, monkeypatch)
    session = holder["session"]
    before = _counts(session)

    body = client.post(
        f"/api/v1/reports/{report['report_id']}/ask",
        json={"question": "估值修复 论点 依据是什么？", "mode": "explain"},
    )
    assert body.status_code == 200, body.text
    answer = body.json()

    assert answer["mode"] == "explain"
    assert "no source calls" in answer["data_policy"]
    # the thesis + claim chain is cited with evidence ids
    assert claim["claim_id"] in [c["claim_id"] for c in answer["claims"]]
    assert claim["supporting_evidence_refs"][0] in answer["citations"]

    # frozen-state guarantee: no evidence or manifest rows were created
    after = _counts(session)
    assert after == before


def test_explain_unmatched_question_still_answers_from_state(client, monkeypatch):
    holder = client
    client = holder["app"]
    report, _ = _seed_report(holder, monkeypatch)
    answer = client.post(
        f"/api/v1/reports/{report['report_id']}/ask",
        json={"question": "完全无关的提问xyz", "mode": "explain"},
    ).json()
    # falls back to the full claim/thesis inventory of the snapshot
    assert answer["claims"] or answer["theses"]


def test_refresh_collects_and_reports_impact(client, monkeypatch):
    holder = client
    client = holder["app"]
    report, _ = _seed_report(holder, monkeypatch)
    session = holder["session"]
    before = _counts(session)

    # The market moved: a fresh quote with a different price arrives.
    fresh = RAW_OK.replace("1648.00~1651.00", "1600.00~1651.00", 1)
    responses = iter([httpx.Response(200, content=fresh.encode("gbk"))])
    monkeypatch.setattr(
        httpx, "get", lambda url, timeout: next(responses, httpx.Response(200, content=b"pv_none=1;"))
    )

    body = client.post(
        f"/api/v1/reports/{report['report_id']}/ask",
        json={"question": "用最新数据重新检查", "mode": "refresh"},
    )
    assert body.status_code == 200, body.text
    answer = body.json()

    assert answer["mode"] == "refresh"
    assert answer["manifest_ids"], "refresh must have run the collector"
    # genuinely new content → new content-addressed evidence
    assert answer["new_evidence_ids"], "fresh quote should be new vs the old snapshot"
    assert answer["old_snapshot_id"] != answer["new_snapshot_id"]

    after = _counts(session)
    assert after[0] > before[0]


def test_explain_never_collects_even_when_stale(client, monkeypatch):
    """Explain on an old snapshot must not backfill anything."""
    holder = client
    client = holder["app"]
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
    snapshot = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2020-01-01T00:00:00+00:00"},
    ).json()["snapshot"]
    report = client.post(
        "/api/v1/reports/compile",
        params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
    ).json()["report"]
    session = holder["session"]
    before = _counts(session)

    answer = client.post(
        f"/api/v1/reports/{report['report_id']}/ask",
        json={"question": "当前行情如何", "mode": "explain"},
    ).json()
    assert answer["citations"] == []  # nothing was visible at 2020 as_of
    assert _counts(session) == before
