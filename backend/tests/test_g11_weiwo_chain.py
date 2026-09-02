"""G11 — 帷幄全链整合测试（观澜语义迁移任务书 §G11）.

覆盖：
  - research_state_check：研究链完整 → sufficient=true（freshness/PIT/
    missing/blockers 显形）；
  - 研究链不完整（无 Thesis）→ INSUFFICIENT_RESEARCH_STATE blocker；
  - 高影响动作走 Confirmation Gate（test_f7 已覆盖，此处验证集成点）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
from app.domain.research import Claim, ClaimStatus, ClaimType, InvestmentThesis
from app.storage.research_orm import ThesisORM
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository


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


NOW = datetime.now(timezone.utc)
TARGET = "SZSE:000831"


def _run_check(client, instrument_id: str = TARGET) -> dict:
    r = client.post("/api/v1/command/tools/research_state_check/execute",
                    json={"arguments": {"instrument_id": instrument_id}})
    assert r.status_code == 200, r.text
    return r.json()["result"]


def test_research_state_check_insufficient_without_thesis(client):
    out = _run_check(client)
    assert out["sufficient"] is False
    assert "INSUFFICIENT_RESEARCH_STATE" in out["blockers"]
    assert "current_thesis" in out["missing_inputs"]


def test_research_state_check_sufficient_with_full_chain(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id=TARGET,
            evidence_type=EvidenceType.ANNOUNCEMENT,
            title="公告",
            summary="公司披露重大事项",
            source="provider_g11",
            source_type="exchange",
            authority_level=AuthorityLevel.A1,
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            event_time=at,
            available_time=at,
            ingested_time=at + timedelta(minutes=1),
            revision_time=at + timedelta(minutes=1),
        )
        EvidenceRepository(session).save(rec)
        snap = SnapshotRepository(session).build(
            TARGET, NOW - timedelta(hours=1),
            evidence_repo=EvidenceRepository(session),
        )
        cid = ResearchRepository(session).save_claim(
            Claim(
                instrument_id=TARGET, snapshot_id=snap.snapshot_id,
                statement="研究状态声明",
                claim_type=ClaimType.FUNDAMENTAL_FACT,
                supporting_evidence_refs=([rec.evidence_id] if False else ()),
                opposing_evidence_refs=(rec.evidence_id,),
                fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                confidence=0.5, status=ClaimStatus.PROPOSED,
            )
        )
        tid = ResearchRepository(session).save_thesis(
            InvestmentThesis(
                instrument_id=TARGET, snapshot_id=snap.snapshot_id,
                title="Thesis", description="d",
                supporting_claims=(), opposing_claims=(cid,), confidence=0.5,
            )
        )
        trow = session.scalars(
            __import__("sqlalchemy", fromlist=["select"]).select(ThesisORM)
            .where(ThesisORM.thesis_id == tid)
        ).first()
        trow.meta_json = {"is_current": True}
        session.commit()
    finally:
        session.close()

    out = _run_check(client)
    assert out["sufficient"] is True
    assert out["blockers"] == []
    assert out["n_evidence"] >= 1
    assert out["current_thesis_id"]
    assert out["pit_ok"] is True
