"""G5 — Experience-driven Smart Screening（观澜语义迁移任务书 §G5）.

覆盖：
  - 未批准 Experience → 编译 422（§G5.1）；
  - 编译确定性：preconditions/invalidators → 可检查规则；机制不同 → 规则不同；
  - 发布需人工确认（未确认 422；draft 运行 422）；
  - PIT 执行：证据 available_time ≤ as_of；Current Thesis Selector；
  - 候选逐规则解释 + 因子值 + ranking 公式版本；排除按 instrument 去重；
  - precondition 变化 → 候选结果可解释变化；
  - ScreenRun Artifact（universe + 结果完整落档）。
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
from app.application.experience import (
    ExperienceCardORM,
    ExperienceCardVersionORM,
)
from app.services.experience_service import ExperienceService
from app.services.industry_graph_service import seed_rare_earth_chain


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


def _make_card(client, *, preconditions: list[str], status: str = "VALIDATING",
               invalidators: list[str] | None = None) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        card = ExperienceCardORM(
            card_id=f"exp_g5{abs(hash(tuple(preconditions))) % 10 ** 10:010d}",
            instrument_id="SZSE:000831",
            title="减持供给压力经验",
            category="research_pattern",
            statement="股东减持计划披露后股价承压",
            mechanism="减持增加股份供给；供给增加压制股价",
            applicable_conditions_json=preconditions,
            invalid_conditions_json=invalidators or [],
            status=status,
            current_version=1,
            source_report_id="rpt_g5000000001",
            source_report_version_id="rpv_g500000001",
            source_snapshot_id="snap_g500000001",
            source_claim_ids_json=[],
            source_evidence_ids_json=[],
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(card)
        session.add(ExperienceCardVersionORM(
            card_id=card.card_id, version_no=1,
            statement=card.statement, mechanism=card.mechanism,
            applicable_conditions_json=preconditions,
            invalid_conditions_json=invalidators or [],
            confidence=0.6, method="deterministic", created_at=NOW,
        ))
        session.commit()
        return card.card_id
    finally:
        session.close()


def _approve(client, card_id: str) -> None:
    """经 G3 语义批准（反例搜索 pass → approve；G3.3 语义由 test_g3 覆盖）。"""
    factory = client.app.state._test_factory
    from app.application.experience import (
        ExperienceRepository,
        ExperienceValidationORM,
    )
    session = factory()
    try:
        ExperienceRepository(session).add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{abs(hash(card_id)) % 10 ** 12:012d}",
                card_id=card_id, method="counterexample_search",
                verdict="pass", cases_json=[],
                summary="语料 0 反例 → pass", created_at=NOW,
            )
        )
        session.commit()
    finally:
        session.close()
    # R2.2：创建持久确认（digest 绑定 card_id+card_version）→ 批准 → 消费
    from app.application.experience import ExperienceCardORM

    session2 = factory()
    try:
        row = session2.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()
        card_version = row.current_version
    finally:
        session2.close()
    conf = client.post("/api/v1/command/confirmations", json={
        "tool_name": "approve_experience_card",
        "arguments": {"card_id": card_id, "card_version": card_version},
    }).json()["confirmation"]
    client.post(f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
                json={"decision": "approved"})
    session = factory()
    try:
        from app.services.experience_service import ExperienceService

        ExperienceService(session).approve(
            card_id, verdict="approved",
            confirmation_id=conf["confirmation_id"], consume=True)
        session.commit()
    finally:
        session.close()


def _seed_evidence(client, summary: str, *, instrument_id: str = "SZSE:000831") -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id=instrument_id,
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


# ── §G5.1：未批准 Experience → 422 ──────────────────────────────────────────


def test_compile_requires_approved_experience(client):
    card_id = _make_card(client, preconditions=["减持比例 ≥1%"], status="VALIDATING")
    r = client.post("/api/v1/screening-v2/definitions", json={
        "name": "未批准来源", "card_id": card_id,
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "screen.source_not_approved"


# ── §G5.2：机制不同 → 规则不同 ───────────────────────────────────────────────


def test_different_experiences_compile_to_different_rules(client):
    card_a = _make_card(client, preconditions=["减持比例 ≥1%", "无对冲安排"])
    card_b = _make_card(client, preconditions=["营收增长", "稀土价格上行"])
    _approve(client, card_a)
    _approve(client, card_b)

    d1 = client.post("/api/v1/screening-v2/definitions", json={
        "name": "A 机制筛选", "card_id": card_a}).json()["definition"]
    d2 = client.post("/api/v1/screening-v2/definitions", json={
        "name": "B 机制筛选", "card_id": card_b}).json()["definition"]
    kinds_a = sorted(r["kind"] for r in d1["rules"])
    kinds_b = sorted(r["kind"] for r in d2["rules"])
    assert kinds_a != kinds_b
    assert "holding_reduction" in kinds_a
    assert "earnings_positive" in kinds_b
    # source_card_version 记录（§G5 ScreenDefinition 字段）
    assert d1["source_card_id"] == card_a


# ── 发布门 + draft 运行 422 ─────────────────────────────────────────────────


def test_publish_gate_and_draft_run_refused(client):
    card_id = _make_card(client, preconditions=["减持比例 ≥1%"])
    _approve(client, card_id)
    d = client.post("/api/v1/screening-v2/definitions", json={
        "name": "发布门测试", "card_id": card_id}).json()["definition"]

    # 未确认 → 422（§G5.3 人工确认）
    r = client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/publish",
                    json={"confirm": False})
    assert r.status_code == 422
    assert r.json()["error_code"] == "screen.publish_needs_confirmation"

    # draft 运行 → 422
    r = client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/run")
    assert r.status_code == 422
    assert r.json()["error_code"] == "screen.not_published"

    # 确认发布
    pub = client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/publish",
                      json={"confirm": True})
    assert pub.status_code == 200
    assert pub.json()["definition"]["status"] == "published"


# ── PIT 执行 + 候选/排除解释 ────────────────────────────────────────────────


def test_pit_execution_candidates_and_exclusions(client):
    chain_id = seed_rare_earth_chain.__globals__  # noqa: F401 (import guard)
    client.post("/api/v1/industry-graph/seed/rare-earth", json={"confirm": True})
    graph = client.get(
        "/api/v1/industry-graph/chains", params={}
    ).json()["results"]
    # 用 G1 链上的公司作为 universe（链上需有位置）：登记 000831 + 600259
    graph_list = client.get("/api/v1/industry-graph/chains").json()["results"]
    chain_id = graph_list[0]["chain_id"]
    segments = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/graph"
    ).json()["segments"]
    refine = next(s for s in segments if s["name"] == "冶炼分离")
    for iid in ("SZSE:000831", "SZSE:600259"):
        client.post("/api/v1/industry-graph/positions", json={
            "instrument_id": iid, "chain_id": chain_id,
            "segment_id": refine["segment_id"], "role": "processor",
        })

    # 000831 有减持证据（满足 holding_reduction）；600259 无
    _seed_evidence(client, "公司股东披露减持计划，拟减持2%股份")
    _seed_evidence(client, "公司冶炼分离产能爬坡")

    card_id = _make_card(client, preconditions=["减持比例 ≥1%"])
    _approve(client, card_id)
    d = client.post("/api/v1/screening-v2/definitions", json={
        "name": "减持供给筛选", "card_id": card_id,
        "universe": {"kind": "industry_chain", "name": "稀土产业链"},
    }).json()["definition"]
    client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/publish",
                json={"confirm": True})
    run = client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/run").json()["run"]

    # 000831 有减持证据 → 候选（含解释/因子值/rank/公式版本）
    cands = [c for c in run["candidates"]
             if c["instrument_id"] == "SZSE:000831"]
    assert cands, run
    c0 = cands[0]
    assert c0["rank"] >= 1
    assert c0["ranking_formula_version"]
    assert c0["factors"]["evidence_freshness"] == 1.0  # 证据 1 天前 → 满档
    assert any("precondition" in e for e in c0["explanations"])
    # 600259 无减持证据 → 排除（按 instrument 去重，保留原因）
    excl = [e for e in run["exclusions"]
            if e["instrument_id"] == "SZSE:600259"]
    assert excl and excl[0]["reasons"]
    # Artifact 注册（§G5.9）
    assert run["artifact_id"]


def test_precondition_change_changes_results(client):
    client.post("/api/v1/industry-graph/seed/rare-earth", json={"confirm": True})
    graph_list = client.get("/api/v1/industry-graph/chains").json()["results"]
    chain_id = graph_list[0]["chain_id"]
    segments = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/graph"
    ).json()["segments"]
    refine = next(s for s in segments if s["name"] == "冶炼分离")
    client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": chain_id,
        "segment_id": refine["segment_id"], "role": "processor",
    })
    # 减持 0.5%（不满足 ≥1% 前提）
    _seed_evidence(client, "公司股东披露减持计划，拟减持0.5%股份")

    card_loose = _make_card(client, preconditions=["减持比例 ≥0.3%"])
    card_tight = _make_card(client, preconditions=["减持比例 ≥1%"])
    _approve(client, card_loose)
    _approve(client, card_tight)

    results = {}
    for name, card in (("loose", card_loose), ("tight", card_tight)):
        d = client.post("/api/v1/screening-v2/definitions", json={
            "name": name, "card_id": card,
            "universe": {"kind": "industry_chain", "name": "稀土产业链"},
        }).json()["definition"]
        client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/publish",
                    json={"confirm": True})
        run = client.post(
            f"/api/v1/screening-v2/definitions/{d['def_id']}/run").json()["run"]
        results[name] = [c["instrument_id"] for c in run["candidates"]]

    # 前提变化 → 候选可解释变化（宽松含 000831，严格排除）
    assert "SZSE:000831" in results["loose"]
    assert "SZSE:000831" not in results["tight"]
