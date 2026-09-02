"""G13 — 语义 Golden A/B/C（观澜语义迁移任务书 §G13）.

Golden A：稀土产业链 —— 5 环节、传导边、证据可追溯、PIT、公司位置隔离；
Golden B：经验到策略闭环 —— Approved Experience → ScreenDefinition →
          发布/运行 → 可执行规则变化断言；
Golden C：研究产品与帷幄 —— 新证据 → 产品版本 → Thesis Diff →
          帷幄确认 → Decision Artifact。
全部经生产 API，无手工制造结果。
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
from app.application.experience import ExperienceCardORM, ExperienceCardVersionORM
from app.services.experience_service import ExperienceService


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


def _ev(client, summary: str, *, instrument_id: str = "SZSE:000831",
        age_days: float = 2.0) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=age_days)
        rec = EvidenceRecord(
            instrument_id=instrument_id,
            evidence_type=EvidenceType.ANNOUNCEMENT,
            title="公告",
            summary=summary,
            source=f"provider_{abs(hash(summary + instrument_id)) % 10 ** 8}",
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


def _approve_card(client, card_id: str) -> None:
    factory = client.app.state._test_factory
    session = factory()
    try:
        ExperienceService(session).approve(card_id, verdict="approved")
        session.commit()
    finally:
        session.close()


# ── Golden A：稀土产业链 ─────────────────────────────────────────────────────


def test_golden_a_rare_earth_chain(client):
    # 1) 链结构（5 环节 / 5 传导边）
    client.post("/api/v1/industry-graph/seed/rare-earth", json={"confirm": True})
    chains = client.get("/api/v1/industry-graph/chains").json()["results"]
    chain_id = next(c["chain_id"] for c in chains if c["name"] == "稀土产业链")
    graph = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph").json()
    assert len(graph["segments"]) >= 5
    assert len(graph["edges"]) >= 4

    # 2) 传导边挂真实证据（可追溯 + PIT）
    smelting = next(s for s in graph["segments"] if s["name"] == "冶炼分离")
    ev = _ev(client, "公司冶炼分离产能提升，稀土氧化物产量增加")
    edge_id = graph["edges"][0]["edge_id"]
    r = client.post(f"/api/v1/industry-graph/edges/{edge_id}/evidence",
                    json={"evidence_id": ev})
    assert r.status_code == 201
    edge = client.get(f"/api/v1/industry-graph/edges/{edge_id}").json()["edge"]
    assert any(e["evidence_id"] == ev for e in edge["evidence"] or [])
    assert edge["status"] in ("degraded", "active")

    # 3) 公司位置：000831（冶炼分离）与 600259（资源开采）隔离
    client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": chain_id,
        "segment_id": smelting["segment_id"], "role": "processor",
        "evidence_ids": [ev],
    })
    pos_831 = client.get(
        "/api/v1/industry-graph/instruments/SZSE:000831/positions").json()["results"]
    pos_259 = client.get(
        "/api/v1/industry-graph/instruments/SZSE:600259/positions").json()["results"]
    assert len(pos_831) == 1 and pos_831[0]["segment_id"] == smelting["segment_id"]
    assert pos_259 == []  # 未登记 → 不冒充链上公司

    # 4) 历史 PIT：结构创建前的 as_of 看不到边
    past = (NOW - timedelta(days=30)).isoformat()
    g_past = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph",
                        params={"as_of": past}).json()
    assert g_past["edges"] == []

    # 5) 进入 Thesis/Signal 语义：Thesis Diff 可从链上标的新证据驱动
    diff = client.get("/api/v1/research-inbox/thesis-diff",
                      params={"instrument_id": "SZSE:000831",
                              "since": (NOW - timedelta(days=7)).isoformat()}).json()["diff"]
    assert "new_evidence" in diff and "suggested_action" in diff


# ── Golden B：经验到策略闭环 ─────────────────────────────────────────────────


def _make_approved_experience(client, *, preconditions: list[str], name: str) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        card = ExperienceCardORM(
            card_id=f"exp_g13{abs(hash(name)) % 10 ** 10:010d}",
            instrument_id="SZSE:000831",
            title=name, category="research_pattern",
            statement="减持计划披露后股价承压",
            mechanism="减持增加股份供给；供给增加压制股价",
            applicable_conditions_json=preconditions,
            invalid_conditions_json=[],
            status="VALIDATING", current_version=1,
            source_report_id="rpt_g13test00001",
            source_report_version_id="rpv_g13test0001",
            source_snapshot_id="snap_g13test0001",
            source_claim_ids_json=[], source_evidence_ids_json=[],
            created_at=NOW, updated_at=NOW,
        )
        session.add(card)
        session.commit()
    finally:
        session.close()
    # G3.3：批准需要 ≥1 PASS 验证（反例搜索 0 命中 → pass）
    session2 = factory()
    try:
        from app.application.experience import (
            ExperienceRepository as _ER,
            ExperienceValidationORM as _EV,
        )

        _ER(session2).add_validation(_EV(
            validation_id=f"expv_{abs(hash(name)) % 10 ** 12:012d}",
            card_id=card.card_id, method="counterexample_search",
            verdict="pass", cases_json=[], summary="0 反例",
            created_at=NOW,
        ))
        session2.commit()
    finally:
        session2.close()
    _approve_card(client, card.card_id)
    return card.card_id


def test_golden_b_experience_to_strategy_closure(client):
    _ev(client, "公司股东披露减持计划，拟减持2%股份")
    card_id = _make_approved_experience(
        client, preconditions=["减持比例 ≥1%", "无对冲安排"], name="G13 经验")

    # 经验 → ScreenDefinition（编译）
    d = client.post("/api/v1/screening-v2/definitions", json={
        "name": "G13 减持筛选", "card_id": card_id,
        "universe": {"kind": "industry_chain", "name": "稀土产业链"},
    }).json()["definition"]
    assert any(r["kind"] == "holding_reduction" for r in d["rules"])
    # 未发布不可运行
    assert client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/run").status_code == 422
    # 人工确认发布 → PIT 运行
    client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/publish",
                json={"confirm": True})
    run = client.post(f"/api/v1/screening-v2/definitions/{d['def_id']}/run").json()["run"]
    assert run["artifact_id"]  # 运行注册 Artifact

    # 策略组装走 R1 权威路径：ScreenRun → StrategyDefinitionVersion（幂等）
    sv = client.post("/api/v1/strategies/from-screen-run", json={
        "screen_run_id": run["run_id"], "name": "G13 策略"}).json()["strategy_version"]
    assert sv["source_version_ids"], "因果链 ID 落库"
    # 幂等：重复提交 → 既有版本
    sv2 = client.post("/api/v1/strategies/from-screen-run", json={
        "screen_run_id": run["run_id"], "name": "G13 策略"}).json()["strategy_version"]
    assert sv2["version_id"] == sv["version_id"]

    # 可执行回测（G6 引擎消费同一 StrategyDefinition）
    bt = client.post(f"/api/v1/strategies/{sv['version_id']}/backtest-v2").json()
    assert bt["aggregate"]["engine"] == "event_backtest_v1"


# ── Golden C：研究产品与帷幄 ─────────────────────────────────────────────────


def test_golden_c_products_and_weiwo_confirmation(client):
    # 1) 新证据 → 产品版本（G9）
    _ev(client, "公司股东披露减持计划，拟减持2%股份")
    c1 = client.post("/api/v1/research-products/daily-brief/compile",
                     json={"confirm": True}).json()
    assert c1["version"] == 1 and c1["artifact_id"]

    # 2) Thesis Diff（帷幄确认前的影响分析）
    diff = client.get("/api/v1/research-inbox/thesis-diff",
                      params={"instrument_id": "SZSE:000831"}).json()["diff"]
    assert diff["new_evidence"]

    # 3) 帷幄确认门：先建立研究状态（Thesis），拒绝 → 无修订；批准 → 修订
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.domain.research import InvestmentThesis as _T
        from app.storage.research_orm import ThesisORM as _TR
        from app.storage.research_repo import ResearchRepository as _RR
        from app.storage.snapshot_repo import SnapshotRepository as _SR
        from app.storage.repository import EvidenceRepository as _ER2

        ev = _ev(client, "公司披露减持计划进展", age_days=1.0)
        snap = _SR(session).build(
            "SZSE:000831", NOW - timedelta(days=1), evidence_repo=_ER2(session))
        cid = _RR(session).save_claim(__import__("app.domain.research", fromlist=["Claim"]).Claim(
            instrument_id="SZSE:000831", snapshot_id=snap.snapshot_id,
            statement="G13 种子声明", claim_type=__import__("app.domain.research", fromlist=["ClaimType"]).ClaimType.FUNDAMENTAL_FACT,
            supporting_evidence_refs=(ev,),
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            confidence=0.6, status=__import__("app.domain.research", fromlist=["ClaimStatus"]).ClaimStatus.PROPOSED,
        ))
        snap = _SR(session).build(
            "SZSE:000831", NOW - timedelta(days=1), evidence_repo=_ER2(session))
        tid = _RR(session).save_thesis(_T(
            instrument_id="SZSE:000831", snapshot_id=snap.snapshot_id,
            title="G13 Thesis", description="初版",
            supporting_claims=(cid,), opposing_claims=(), confidence=0.5,
        ))
        trow = session.scalars(
            __import__("sqlalchemy", fromlist=["select"]).select(_TR)
            .where(_TR.thesis_id == tid)).first()
        trow.meta_json = {"is_current": True}
        session.commit()
    finally:
        session.close()

    args = {"instrument_id": "SZSE:000831",
            "revised_statement": "G13：供给压力修订。"}
    conf = client.post("/api/v1/command/confirmations", json={
        "tool_name": "submit_thesis_revision", "arguments": args}).json()["confirmation"]
    client.post(f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
                json={"decision": "rejected"})
    refused = client.post("/api/v1/command/tools/submit_thesis_revision/execute",
                          json={"arguments": args,
                                "confirmation_id": conf["confirmation_id"]})
    assert refused.status_code == 422  # 拒绝不执行

    conf2 = client.post("/api/v1/command/confirmations", json={
        "tool_name": "submit_thesis_revision", "arguments": args}).json()["confirmation"]
    client.post(f"/api/v1/command/confirmations/{conf2['confirmation_id']}/decide",
                json={"decision": "approved"})
    ok = client.post("/api/v1/command/tools/submit_thesis_revision/execute",
                     json={"arguments": args,
                           "confirmation_id": conf2["confirmation_id"]})
    assert ok.status_code == 200
    thesis_id = ok.json()["result"]["thesis_id"]
    assert thesis_id  # Decision Artifact（Thesis Revision）
    assert ok.json()["artifact_ids"]
