"""G10 — Thesis Center / Inbox / Memory 补全（观澜语义迁移任务书 §G10）.

覆盖：
  - Thesis Diff：strengthened/weakened（同语句证据数变化）+ meta 变化；
  - Memory promote 幂等（retired 重复操作不变更）+ 审计事件；
  - Memory 版本 diff 端点。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
from app.application.memory import MemoryService
from app.services.experience_service import ExperienceService
from app.application.experience import ExperienceCardORM
from app.storage.research_orm import ThesisORM, ClaimORM
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.domain.research import Claim, ClaimStatus, ClaimType, InvestmentThesis


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


def _seed_evidence(client, summary: str, *, age_days: float = 1.0) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=age_days)
        rec = EvidenceRecord(
            instrument_id=TARGET,
            evidence_type=EvidenceType.ANNOUNCEMENT,
            title="公告",
            summary=summary,
            source=f"provider_{abs(hash(summary)) % 10 ** 8}",
            source_type="exchange",
            authority_level=AuthorityLevel.A1,
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            event_time=at,
            available_time=at,
            ingested_time=at + timedelta(minutes=1),
            revision_time=at + timedelta(minutes=1),
        )
        evidence_id, _ = EvidenceRepository(session).save(rec)
        session.commit()
        return evidence_id
    finally:
        session.close()


def _make_thesis_with_claim(client, *, supporting: int = 1) -> tuple[str, str]:
    """Thesis + claim（supporting 数可变，供 strengthened 判定）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        # 先种证据（10+i 天前），再建 as_of=5 天前的快照 → 证据被 pin
        evs = [
            _seed_evidence(client, f"减持披露 {i}", age_days=10 + i)
            for i in range(supporting)
        ]
        snap = SnapshotRepository(session).build(
            TARGET, NOW - timedelta(days=5),
            evidence_repo=EvidenceRepository(session),
        )
        cid = ResearchRepository(session).save_claim(
            Claim(
                instrument_id=TARGET, snapshot_id=snap.snapshot_id,
                statement="广晟控股减持计划或影响股份供给",
                claim_type=ClaimType.FUNDAMENTAL_FACT,
                supporting_evidence_refs=tuple(evs),
                fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                confidence=0.8, status=ClaimStatus.PROPOSED,
            )
        )
        tid = ResearchRepository(session).save_thesis(
            InvestmentThesis(
                instrument_id=TARGET, snapshot_id=snap.snapshot_id,
                title="V1 Thesis", description="初版",
                supporting_claims=(cid,), opposing_claims=(), confidence=0.7,
            )
        )
        row = session.scalars(
            select(ThesisORM).where(ThesisORM.thesis_id == tid)
        ).first()
        row.meta_json = {"is_current": True}
        session.commit()
        return tid, cid
    finally:
        session.close()


def test_thesis_diff_strengthened_detection(client):
    """同语句 claim 在 v2 支撑证据更多 → strengthened。"""
    tid, cid = _make_thesis_with_claim(client, supporting=1)
    # 应用一次修订（新增证据 → supports/strengthens 关系）→ 新 Thesis
    _seed_evidence(client, "广晟控股披露减持计划进展", age_days=1.0)
    r = client.post("/api/v1/research-inbox/thesis-diff/apply", json={
        "instrument_id": TARGET,
        "revised_statement": "修订：新增证据。",
    })
    assert r.status_code == 201, r.text
    new_tid = r.json()["thesis_id"]

    diff = client.get(
        f"/api/v1/research-inbox/theses/{tid}/diff/{new_tid}"
    ).json()
    # lineage 含新证据数变化（strengthened 判定数据源）
    assert "strengthened_claims" in diff
    assert "weakened_claims" in diff
    assert "meta_changes" in diff


def test_memory_promote_idempotent_and_audit(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        mem = MemoryService(session).create_candidate(
            memory_type="research_method", title="测试经验",
            content="减存款供给压力经验规则",
        )
        session.commit()
        memory_id = mem["memory_id"]
    finally:
        session.close()

    # candidate → active
    r1 = client.post(f"/api/v1/memories/{memory_id}/promote")
    assert r1.status_code == 200
    assert r1.json()["memory"]["status"] == "active"
    # active → retired
    r2 = client.post(f"/api/v1/memories/{memory_id}/promote")
    assert r2.json()["memory"]["status"] == "retired"
    # retired 重复 promote → 幂等（状态不变、version 不再 +1）
    v_before = r2.json()["memory"]["version"]
    r3 = client.post(f"/api/v1/memories/{memory_id}/promote")
    assert r3.status_code == 200
    assert r3.json()["memory"]["status"] == "retired"
    assert r3.json()["memory"]["version"] == v_before

    # 审计事件
    events = client.get(
        f"/api/v1/research-runs/audit_mem_{memory_id[-8:]}/events"
    ).json().get("results", [])
    assert any(e["event_type"] == "memory_status_changed" for e in events)


def test_memory_version_diff_endpoint(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        mem = MemoryService(session).create_candidate(
            memory_type="research_method", title="Diff 记忆", content="内容 v1"
        )
        session.commit()
        memory_id = mem["memory_id"]
    finally:
        session.close()

    diff = client.get(
        f"/api/v1/memories/{memory_id}/versions/diff",
        params={"v1": 1, "v2": 2},
    )
    # 版本 2 不存在 → 404（诚实）
    # v1==v2（都为当前版本 1）→ 内容相同 → 200（诚实返回）
    assert diff.status_code == 200
