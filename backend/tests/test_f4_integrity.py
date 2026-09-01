"""F4 — Integrity Migration（第三轮整改任务书 §7 P1-A）.

覆盖：
  - 可解释置信度模型（§7.1）：compute_claim_confidence 因素映射；
    extraction promote 不再产生固定 0.6；basis 落库可审计；
  - Source Independence（§7.2）：同稿转载/标题变化正文相似/镜像页/
    同通讯社/二次引用同原始来源 → 同组；corroboration 按独立组裁决；
  - Subject Swap Detection（§7.3）：Entity Dictionary + 主体偷换
    （中国稀土集团 ≠ 中国稀土股份）→ uncertain + 机器可读 reason code。
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


def _seed_evidence(
    session, ev_key: str, title: str, summary: str, *,
    instrument_id: str = "SZSE:000831",
    authority: AuthorityLevel = AuthorityLevel.A1,
    etype: EvidenceType = EvidenceType.ANNOUNCEMENT,
    publisher: str | None = None,
    canonical_url: str | None = None,
    source_group: str | None = None,
    original_source: str | None = None,
    source: str | None = None,
) -> str:
    at = NOW - timedelta(days=1)
    rec = EvidenceRecord(
        instrument_id=instrument_id,
        evidence_type=etype,
        title=title,
        summary=summary,
        source=source or f"provider_{ev_key}",
        source_type="media",
        authority_level=authority,
        fact_status=FactStatus.OFFICIAL_DISCLOSURE,
        event_time=at,
        available_time=at,
        ingested_time=at + timedelta(minutes=1),
        revision_time=at + timedelta(minutes=1),
        publisher=publisher,
        canonical_url=canonical_url,
        source_group=source_group,
        original_source=original_source,
    )
    evidence_id, _ = EvidenceRepository(session).save(rec)
    return evidence_id


# ── §7.1：可解释置信度 ───────────────────────────────────────────────────────


def test_confidence_model_factors():
    from app.domain.confidence import compute_claim_confidence

    t0 = compute_claim_confidence(
        supporting_trusts=["T0_primary_disclosure"],
        directness="direct_quote", evidence_age_days=1,
    )
    t3 = compute_claim_confidence(
        supporting_trusts=["T3_mainstream_media"],
        directness="derived", evidence_age_days=120,
    )
    # 不同信任层 → 不同数值（无固定默认值）
    assert t0.value > t3.value
    # 基础因素齐备且版本可追溯
    for oc in (t0, t3):
        assert oc.basis["source_trust_score"] > 0
        assert oc.model_version == "claim_confidence_v1"
        assert {"source_trust", "corroboration", "directness",
                "semantic_consistency", "freshness"} <= set(oc.basis)
    # 独立来源组加成
    solo = compute_claim_confidence(supporting_trusts=["T2_professional_research"])
    corr = compute_claim_confidence(
        supporting_trusts=["T2_professional_research", "T3_mainstream_media"],
        corroboration_groups=2,
    )
    assert corr.value > solo.value
    # 无支撑 → insufficient（不用默认值掩盖）
    empty = compute_claim_confidence(supporting_trusts=[])
    assert empty.level == "insufficient"
    assert empty.basis["notes"] == ["no_supporting_evidence"]


def test_promote_confidence_is_explainable_not_fixed(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev_a = _seed_evidence(
            session, "a1", "公司公告",
            "公司正在筹划重大资产重组事项，股票停牌",
            authority=AuthorityLevel.A1,
        )
        ev_b = _seed_evidence(
            session, "b2", "媒体转载",
            "据媒体报道，该公司或筹划重大资产重组事项",
            authority=AuthorityLevel.C2, etype=EvidenceType.NEWS,
        )
        session.commit()
    finally:
        session.close()

    snap = client.post("/api/v1/snapshots?instrument=SZSE%3A000831", json={})
    assert snap.status_code in (200, 201), snap.text
    snap_id = snap.json()["snapshot"]["snapshot_id"]

    claim_ids = []
    for ev, stmt in (
        (ev_a, "公司正在筹划重大资产重组事项"),
        (ev_b, "该公司或筹划重大资产重组事项"),
    ):
        created = client.post("/api/v1/extractions", json={
            "source_evidence_id": ev,
            "statement": stmt,
            "support_span": stmt,
            "instrument_id": "SZSE:000831",
        })
        assert created.status_code == 201, created.text
        ext = created.json()["extraction"]
        assert ext["verdict"] == "accepted", ext
        promoted = client.post(
            f"/api/v1/extractions/{ext['extraction_id']}/promote",
            params={"snapshot_id": snap_id},
        )
        assert promoted.status_code == 201, promoted.text
        claim_ids.append(promoted.json()["claim_id"])

    # 断言：两条 Claim 置信度不同（信任层驱动），且 basis 落库（§7.4）
    from sqlalchemy import select
    from app.storage.research_orm import ClaimORM

    session = factory()
    try:
        rows = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id.in_(claim_ids))
        ).all()
        values = {r.confidence for r in rows}
        assert len(values) == 2, values  # T0 直接引用 ≠ T3 转载
        assert not any(abs(v - 0.6) < 1e-9 for v in values)
        for r in rows:
            assert r.confidence_level in ("high", "medium", "low", "insufficient")
            basis = r.confidence_basis_json or {}
            assert basis.get("model_version") == "claim_confidence_v1"
            assert "source_trust" in basis and "corroboration" in basis
    finally:
        session.close()


# ── §7.2：来源独立性 ─────────────────────────────────────────────────────────


def test_source_independence_grouping():
    from app.services.source_independence import (
        corroboration_check,
        independent_group_count,
    )

    class Row:
        def __init__(self, ev_id, **kw):
            self.evidence_id = ev_id
            self.content_hash = kw.get("content_hash")
            self.title = kw.get("title")
            self.summary = kw.get("summary")
            self.source = kw.get("source", "")
            self.source_url = kw.get("source_url")
            self.canonical_url = kw.get("canonical_url")
            self.source_document_id = kw.get("source_document_id")
            self.original_source = kw.get("original_source")
            self.source_group = kw.get("source_group")
            self.publisher = kw.get("publisher")

    body = "广晟控股集团拟减持公司股份不超过1061.22万股，减持计划为期三个月"
    # 1) 同一篇稿件不同站点转载（content_hash 相同）
    a = Row("evA", content_hash="h1", title="甲站：广晟减持", summary=body, source="siteA",
            publisher="甲站财经", canonical_url="https://a.example/news/1")
    b = Row("evB", content_hash="h1", title="乙站转载", summary=body, source="siteB")
    # 2) 标题变化但正文相同（规范化正文哈希）
    c = Row("evC", content_hash="h9", title="突发！公告全文", summary=body + "。",
            source="siteC")
    # 3) 完全独立来源
    d = Row("evD", content_hash="h2", title="独立报道", summary="公司披露年报业绩",
            source="siteD", publisher="独立日报", canonical_url="https://d.example/news/9")
    # 4) 同一通讯社稿件
    e = Row("evE", content_hash="h3", title="通稿一", summary="另一篇内容", source="siteE",
            source_group="xinhua")
    f = Row("evF", content_hash="h4", title="通稿二", summary="又一篇内容", source="siteF",
            source_group="xinhua")
    # 5) 二次报道引用同一原始来源
    g = Row("evG", content_hash="h5", title="引述一", summary="引述内容一", source="siteG",
            original_source="announcement:1234")
    h = Row("evH", content_hash="h6", title="引述二", summary="引述内容二", source="siteH",
            original_source="announcement:1234")

    rows = [a, b, c, d, e, f, g, h]
    assert independent_group_count(rows) == 4  # {a,b,c} {d} {e,f} {g,h}

    # 「≥2 独立来源」裁决：a+b 两行但只有 1 组 → 不满足（§7.2 核心语义）
    verdict_ab = corroboration_check([a, b])
    assert verdict_ab["satisfied"] is False
    assert verdict_ab["reason_code"] == "insufficient_independent_sources"
    assert verdict_ab["independent_groups"] == 1
    # a+d：两行两组 → 满足
    verdict_ad = corroboration_check([a, d])
    assert verdict_ad["satisfied"] is True
    assert verdict_ad["reason_code"] == "satisfied"


def test_corroboration_degraded_fields_disclosed():
    """独立性字段缺失 → 判定降级显式披露，不冒充通过。"""
    from app.services.source_independence import corroboration_check

    class Row:
        def __init__(self, ev_id, ch):
            self.evidence_id = ev_id
            self.content_hash = ch
            self.title = "t"
            self.summary = "s"
            self.source = "src"
            self.source_url = None
            self.canonical_url = None
            self.source_document_id = None
            self.original_source = None
            self.source_group = None
            self.publisher = None

    verdict = corroboration_check([Row("x1", "c1"), Row("x2", "c2")])
    assert verdict["reason_code"] == "degraded_fields"
    assert verdict["satisfied"] is False


# ── §7.3：主体偷换检测（Entity Dictionary） ──────────────────────────────────


def test_subject_swap_detection(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _seed_evidence(
            session, "group", "集团动态",
            "中国稀土集团正在研究资产整合方案，尚未形成具体安排",
            authority=AuthorityLevel.B1,
        )
        session.commit()
    finally:
        session.close()

    # 反例（§7.3）：statement 把「集团公司」说成「上市公司」→ uncertain
    swap = client.post("/api/v1/extractions", json={
        "source_evidence_id": ev,
        "statement": "中国稀土股份正在筹划重大资产重组",
        "support_span": "中国稀土集团正在研究资产整合方案",
        "instrument_id": "SZSE:000831",
    })
    assert swap.status_code == 201, swap.text
    body = swap.json()["extraction"]
    assert body["verdict"] == "uncertain", body
    assert "subject_entity_mismatch" in body["reject_reason"], body
    assert "group_company" in body["reject_reason"] and "listed_company" in body["reject_reason"]

    # 对照：主体一致（集团公司 → 集团公司）→ accepted
    same = client.post("/api/v1/extractions", json={
        "source_evidence_id": ev,
        "statement": "中国稀土集团正在研究资产整合方案",
        "support_span": "中国稀土集团正在研究资产整合方案",
        "instrument_id": "SZSE:000831",
    })
    assert same.status_code == 201, same.text
    assert same.json()["extraction"]["verdict"] == "accepted", same.text


def test_uncertain_extraction_cannot_be_promoted(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _seed_evidence(
            session, "group2", "集团动态",
            "中国稀土集团正在研究资产整合方案，尚未形成具体安排",
            authority=AuthorityLevel.B1,
        )
        session.commit()
    finally:
        session.close()

    snap = client.post("/api/v1/snapshots?instrument=SZSE%3A000831", json={})
    snap_id = snap.json()["snapshot"]["snapshot_id"]

    swap = client.post("/api/v1/extractions", json={
        "source_evidence_id": ev,
        "statement": "中国稀土股份正在筹划重大资产重组",
        "support_span": "中国稀土集团正在研究资产整合方案",
        "instrument_id": "SZSE:000831",
    })
    ext_id = swap.json()["extraction"]["extraction_id"]
    promoted = client.post(
        f"/api/v1/extractions/{ext_id}/promote", params={"snapshot_id": snap_id}
    )
    assert promoted.status_code == 422  # uncertain 不进正式 Research State
