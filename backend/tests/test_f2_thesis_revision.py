"""F2 — Thesis Revision Research State（第三轮整改任务书 §5.2 / §5.4）.

覆盖：
  - irrelevant 证据不进入 Thesis、不制造 Claim（10+3 场景）；
  - supports：原 Claim 继承且增加 supporting evidence；
  - contradicts：不进入 supporting-only，进入 opposing 并记录冲突；
  - supersedes：旧 Claim 可回溯（parent chain），新 Claim 成为有效版本；
  - updates：创建 revised Claim Version（带 parent chain），不只写 metadata；
  - Carry-forward 第 N 条写入失败：全事务回滚，Current 不切换；
  - 并发/脏状态：唯一 Current；
  - 重复提交相同 Evidence：幂等（422），不制造重复 Claim；
  - Claim Version lineage 字段落库（§5.3.4）。

驱动方式：真实 API（TestClient）+ 真实仓储种子数据；不做 Mock 注入。
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
from app.domain.research import Claim, ClaimStatus, ClaimType, InvestmentThesis
from app.storage.research_orm import ClaimORM, ThesisORM
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.services.current_thesis import get_current_thesis


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


INSTRUMENT = "SZSE:000831"
NOW = datetime.now(timezone.utc)


def _make_evidence(
    session, ev_id: str, title: str, summary: str, *, age_days: float = 10.0,
    etype: EvidenceType = EvidenceType.ANNOUNCEMENT,
    authority: AuthorityLevel = AuthorityLevel.A2,
) -> str:
    at = NOW - timedelta(days=age_days)
    rec = EvidenceRecord(
        instrument_id=INSTRUMENT,
        evidence_type=etype,
        title=title,
        summary=summary,
        source=f"provider_{ev_id}",
        source_type="exchange",
        authority_level=authority,
        fact_status=FactStatus.OFFICIAL_DISCLOSURE,
        event_time=at,
        available_time=at,
        ingested_time=at + timedelta(minutes=1),
        revision_time=at + timedelta(minutes=1),
    )
    evidence_id, _ = EvidenceRepository(session).save(rec)
    return evidence_id


def _make_claim(
    session, snapshot_id: str, claim_key: str, statement: str,
    supporting_refs: tuple[str, ...], opposing_refs: tuple[str, ...] = (),
) -> str:
    return ResearchRepository(session).save_claim(
        Claim(
            instrument_id=INSTRUMENT,
            snapshot_id=snapshot_id,
            statement=statement,
            claim_type=ClaimType.FUNDAMENTAL_FACT,
            supporting_evidence_refs=supporting_refs,
            opposing_evidence_refs=opposing_refs,
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            confidence=0.8,
            status=ClaimStatus.PROPOSED,
        )
    )


def seed_thesis(
    client, *, n_support: int = 10, n_oppose: int = 3,
    statement: str = "广晟控股减持计划或影响股份供给",
    old_ev_summary: str = "广晟控股集团有限公司持有公司9.48%股份",
    snapshot_as_of: datetime | None = None,
    extra_evidence: tuple[tuple[str, str, str, float], ...] = (),
) -> dict:
    """种子：旧证据（默认 10 天前，窗口外）+ 快照 + claims + current thesis。

    extra_evidence: (ev_id, title, summary, age_days) —— 在快照之前创建
    （可被旧快照 pin，供 updates 场景的 claim 直接引用）。
    返回 {"old_thesis_id", "old_snap_id", "old_claim_ids", "factory", "extra"}。
    """
    factory = client.app.state._test_factory
    session = factory()
    try:
        extra: dict[str, str] = {}
        for ev_id, title, summary, age in extra_evidence:
            extra[ev_id] = _make_evidence(session, ev_id, title, summary, age_days=age)

        sup_evs, opp_evs, sup_claims, opp_claims = [], [], [], []
        for i in range(n_support):
            ev_id = _make_evidence(
                session, f"ev_sup_{i:02d}",
                f"股东减持披露 {i}",
                f"{old_ev_summary}（第{i}条）广晟控股集团持股比例披露",
            )
            sup_evs.append(ev_id)
        for i in range(n_oppose):
            ev_id = _make_evidence(
                session, f"ev_opp_{i:02d}",
                f"稀土价格下行观察 {i}",
                f"稀土价格氧化镨钕下跌，板块盈利预期承压（第{i}条）",
            )
            opp_evs.append(ev_id)

        old_snap = SnapshotRepository(session).build(
            INSTRUMENT, snapshot_as_of or (NOW - timedelta(days=5)),
            evidence_repo=EvidenceRepository(session),
        )

        for i in range(n_support):
            sup_claims.append(_make_claim(
                session, old_snap.snapshot_id, f"clm_sup_{i:02d}",
                f"{statement}（{i}）", (sup_evs[i],),
            ))
        for i in range(n_oppose):
            opp_claims.append(_make_claim(
                session, old_snap.snapshot_id, f"clm_opp_{i:02d}",
                f"稀土价格下行压制盈利预期（{i}）", (opp_evs[i],),
            ))

        thesis = InvestmentThesis(
            instrument_id=INSTRUMENT,
            snapshot_id=old_snap.snapshot_id,
            title="中国稀土 研究综合论点",
            description="广晟减持观察 + 价格承压",
            supporting_claims=tuple(sup_claims),
            opposing_claims=tuple(opp_claims),
            confidence=0.7,
        )
        thesis_id = ResearchRepository(session).save_thesis(thesis)
        row = session.scalars(
            select(ThesisORM).where(ThesisORM.thesis_id == thesis_id)
        ).first()
        row.meta_json = {"is_current": True, "added_evidence_ids": []}
        session.commit()
        return {
            "old_thesis_id": thesis_id,
            "old_snap_id": old_snap.snapshot_id,
            "old_claim_ids": sup_claims + opp_claims,
            "factory": factory,
            "extra": extra,
        }
    finally:
        session.close()


def _current_thesis(factory) -> ThesisORM | None:
    session = factory()
    try:
        return get_current_thesis(session, INSTRUMENT)
    finally:
        session.close()


# ── §5.4-1：irrelevant 证据 → 新 Thesis 仍为 10+3，不制造 Claim ──────────────


def test_irrelevant_evidence_keeps_thesis_10_plus_3(client):
    st = seed_thesis(client)
    factory = st["factory"]
    # 新证据（1 天前，窗口内）：无事件关键词、无否定/更正标记 → 全量 irrelevant
    session = factory()
    try:
        ev_irr = _make_evidence(
            session, "ev_irr_00", "投资者关系活动记录",
            "中国稀土发布投资者关系活动记录表，接待多家机构调研",
            age_days=1.0,
        )
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：新增调研记录不改变研究结论。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # 新 Thesis 仍为 10 + 3
    assert body["supporting_count"] == 10
    assert body["opposing_count"] == 3
    # irrelevant 证据：不进入 Thesis、不制造 Claim、不进入 added
    assert body["added_evidence_ids"] == []
    assert body["irrelevant_evidence_ids"] == [ev_irr]
    # 新快照上的 claims = 恰好 13 条 carry-forward，无多余
    session = factory()
    try:
        carried = session.scalars(
            select(ClaimORM).where(ClaimORM.snapshot_id == body["new_snapshot_id"])
        ).all()
        assert len(carried) == 13
        assert all(c.carried_forward for c in carried)
        assert all(c.parent_claim_id in st["old_claim_ids"] for c in carried)
        assert all(c.revision_kind == "carried_forward" for c in carried)
    finally:
        session.close()


# ── §5.4-2：supports → 原 Claim 继承且增加 supporting evidence ───────────────


def test_supports_relation_extends_supporting_evidence(client):
    st = seed_thesis(client, n_support=1, n_oppose=0)
    factory = st["factory"]
    session = factory()
    try:
        ev_new = _make_evidence(
            session, "ev_sup_new",
            "减持计划进展",
            "广晟控股集团披露减持计划，拟减持不超过1%股份",
            age_days=1.0,
        )
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：减持计划进展披露。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["added_evidence_ids"] == [ev_new]

    session = factory()
    try:
        old_cid = st["old_claim_ids"][0]
        carried_id = body["carried_forward_map"][old_cid]
        row = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        # 原 Claim 继承 + 新 evidence 进入 supporting
        assert ev_new in (row.supporting_evidence_refs_json or [])
        # Claim 仍为 supporting
        assert carried_id in _current_thesis(factory).supporting_claims_json
        assert row.source_impact_relation == "supports"
    finally:
        session.close()


# ── §5.4-3：contradicts → 不得进入 supporting-only ───────────────────────────


def test_contradicts_moves_claim_to_opposing(client):
    st = seed_thesis(client, n_support=1, n_oppose=0,
                     statement="公司筹划重大资产重组事宜",
                     old_ev_summary="市场关注资产注入预期")
    factory = st["factory"]
    session = factory()
    try:
        ev_contra = _make_evidence(
            session, "ev_contra",
            "澄清公告",
            "公司澄清公告：不存在筹划重大资产重组的情形",
            age_days=1.0,
        )
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：澄清公告改变重组预期。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    session = factory()
    try:
        old_cid = st["old_claim_ids"][0]
        carried_id = body["carried_forward_map"][old_cid]
        row = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        current = _current_thesis(factory)
        # 不进入 supporting-only：移入 opposing
        assert carried_id not in (current.supporting_claims_json or [])
        assert carried_id in (current.opposing_claims_json or [])
        # 冲突证据进入 opposing refs，relation 落库
        assert ev_contra in (row.opposing_evidence_refs_json or [])
        assert row.source_impact_relation == "contradicts"
        assert ("方向冲突" in (row.revision_reason or "")) or (
            "contradicts" in (row.revision_reason or "")
        )
    finally:
        session.close()


# ── §5.4-4：supersedes → 旧 Claim 可回溯，新 Claim 成为有效版本 ───────────────


def test_supersedes_creates_version_chain(client):
    st = seed_thesis(client, n_support=1, n_oppose=0,
                     statement="广晟拟减持1061万股",
                     old_ev_summary="广晟控股披露减持意向")
    factory = st["factory"]
    session = factory()
    try:
        _make_evidence(
            session, "ev_supersede",
            "更正公告",
            "更正公告：广晟控股减持数量更正为500万股",
            age_days=1.0,
        )
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：减持数量更正。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    session = factory()
    try:
        old_cid = st["old_claim_ids"][0]
        carried_id = body["carried_forward_map"][old_cid]
        carried = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        # 旧版本标记 superseded
        assert carried.status == "superseded"
        # 新 Claim Version 落库：parent chain 完整（§5.3.4）
        version = session.scalars(
            select(ClaimORM).where(ClaimORM.parent_claim_id == carried_id)
        ).first()
        assert version is not None
        assert version.revision_kind == "supersedes"
        assert version.source_impact_relation == "supersedes"
        assert version.parent_claim_id == carried_id
        assert carried.parent_claim_id == old_cid  # 可回溯到最初版本
        # 新版本成为有效版本（旧版本从 supporting 退位）
        current = _current_thesis(factory)
        assert version.claim_id in (current.supporting_claims_json or [])
        assert carried.claim_id not in (current.supporting_claims_json or [])
        assert version.claim_id in body["revised_claim_ids"]
        assert carried.claim_id in body["superseded_claim_ids"]
    finally:
        session.close()


# ── §5.4-5：updates → 创建 revised Claim（不只写 metadata） ──────────────────


def test_updates_relation_creates_revised_claim(client):
    # ev_upd 在快照之前创建（1 天前，快照 as_of=12 小时前 → 被 pin；
    # 同时仍在 7 天 diff 窗口内 → 触发 updates：claim 已直接引用该证据）
    st = seed_thesis(
        client, n_support=1, n_oppose=0,
        statement="公司基本面观察",
        old_ev_summary="公司经营情况平稳",
        snapshot_as_of=NOW - timedelta(hours=12),
        extra_evidence=(("ev_upd", "补充经营数据", "公司披露主要经营数据补充说明", 1.0),),
    )
    factory = st["factory"]
    ev_new = st["extra"]["ev_upd"]
    session = factory()
    try:
        # claim 直接引用新证据（updates 判定：claim 已直接引用该证据）
        cid = _make_claim(
            session, st["old_snap_id"], "clm_upd",
            "公司基本面观察", (ev_new,),
        )
        thesis_row = session.scalars(
            select(ThesisORM).where(ThesisORM.thesis_id == st["old_thesis_id"])
        ).first()
        sup = list(thesis_row.supporting_claims_json or [])
        sup.append(cid)
        thesis_row.supporting_claims_json = sup
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：经营数据补充。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    session = factory()
    try:
        carried_id = body["carried_forward_map"][cid]
        carried = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        version = session.scalars(
            select(ClaimORM).where(ClaimORM.parent_claim_id == carried_id)
        ).first()
        assert version is not None
        assert version.revision_kind == "updated"
        assert version.source_impact_relation == "updates"
        # revised claim 携带新证据，不只是 metadata
        assert ev_new in (version.supporting_evidence_refs_json or [])
        assert version.claim_id in (body["revised_claim_ids"])
    finally:
        session.close()


# ── §5.2：strengthens → 记录强度变化 ─────────────────────────────────────────


def test_strengthens_relation_records_strength_change(client):
    # 旧证据已覆盖同一事件（减持）→ 新证据同事件加固 = strengthens
    st = seed_thesis(client, n_support=1, n_oppose=0,
                     statement="广晟控股减持计划或影响股份供给",
                     old_ev_summary="广晟控股披露减持计划")
    factory = st["factory"]
    session = factory()
    try:
        ev_streng = _make_evidence(session, "ev_streng", "减持计划进展",
                                   "广晟控股集团披露减持计划实施进展",
                                   age_days=1.0)
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：减持计划进展加固支撑。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    session = factory()
    try:
        old_cid = st["old_claim_ids"][0]
        carried_id = body["carried_forward_map"][old_cid]
        row = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        # 新证据进入 supporting evidence
        assert ev_streng in (row.supporting_evidence_refs_json or [])
        assert row.source_impact_relation == "strengthens"
        # 记录强度变化
        assert "加固" in (row.revision_reason or "") or "strength" in (
            row.revision_reason or ""
        )
        current = _current_thesis(factory)
        assert carried_id in (current.supporting_claims_json or [])
    finally:
        session.close()


# ── §5.2：weakens → 不悄悄保留为纯 supporting ────────────────────────────────


def test_weakens_relation_moves_to_opposing(client):
    # claim 含否定语义（未筹划），新证据正向（筹划进展）→ weakens
    st = seed_thesis(client, n_support=1, n_oppose=0,
                     statement="公司未筹划重大资产重组",
                     old_ev_summary="公司经营情况说明")
    factory = st["factory"]
    session = factory()
    try:
        ev_weak = _make_evidence(session, "ev_weaken", "重组进展",
                                 "公司公告披露重大资产重组进展事项",
                                 age_days=1.0)
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：重组进展削弱原判断。"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    session = factory()
    try:
        old_cid = st["old_claim_ids"][0]
        carried_id = body["carried_forward_map"][old_cid]
        row = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == carried_id)
        ).first()
        current = _current_thesis(factory)
        # 不得悄悄保留为纯 supporting
        assert carried_id not in (current.supporting_claims_json or [])
        assert carried_id in (current.opposing_claims_json or [])
        assert ev_weak in (row.opposing_evidence_refs_json or [])
        assert row.source_impact_relation == "weakens"
    finally:
        session.close()


# ── §5.4-6：Carry-forward 第 N 条失败 → 全事务回滚，Current 不切换 ────────────


def test_carry_forward_failure_rolls_back_whole_revision(client, monkeypatch):
    st = seed_thesis(client)  # 13 条 claims
    factory = st["factory"]
    # 触发 carry-forward 的新证据（irrelevant 即可，走 carry-forward 主路径）
    session = factory()
    try:
        _make_evidence(session, "ev_rollback", "投资者关系活动记录",
                       "中国稀土发布投资者关系活动记录表，接待机构调研",
                       age_days=1.0)
        session.commit()
    finally:
        session.close()

    real_save = ResearchRepository.save_claim
    calls = {"n": 0}

    def flaky_save(self, claim, **kw):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated storage failure at claim #3")
        return real_save(self, claim, **kw)

    monkeypatch.setattr(ResearchRepository, "save_claim", flaky_save)

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：应当失败并回滚。"},
    )
    assert resp.status_code == 500
    assert resp.json()["error_code"] == "thesis_revision.failed"

    # 回滚完整性：无新 Thesis、无 carried claims、Current 不切换
    session = factory()
    try:
        theses = session.scalars(select(ThesisORM)).all()
        assert len(theses) == 1
        assert theses[0].thesis_id == st["old_thesis_id"]
        assert (theses[0].meta_json or {}).get("is_current") is True
        claims = session.scalars(select(ClaimORM)).all()
        assert len(claims) == 13
        assert not any(c.carried_forward for c in claims)
    finally:
        session.close()


# ── §5.4-7：并发/脏状态 → 唯一 Current ────────────────────────────────────────


def test_unique_current_after_revision_with_corrupt_state(client):
    st = seed_thesis(client)
    factory = st["factory"]
    # 制造脏状态：两个 is_current（并发场景的最终状态等价物）
    session = factory()
    try:
        ghost = ThesisORM(
            thesis_id="ths_ghost0000000001",
            instrument_id=INSTRUMENT,
            snapshot_id=st["old_snap_id"],
            title="并发幽灵 Thesis",
            description="stale concurrent revision",
            supporting_claims_json=[],
            opposing_claims_json=[],
            confidence=0.5,
            meta_json={"is_current": True},
            status="active",
            created_at=NOW,
        )
        session.add(ghost)
        session.commit()
    finally:
        session.close()

    session = factory()
    try:
        _make_evidence(session, "ev_irr_conc", "投资者关系活动记录",
                       "中国稀土发布投资者关系活动记录表，接待机构调研",
                       age_days=1.0)
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：并发后唯一 Current。"},
    )
    assert resp.status_code == 201, resp.text
    new_thesis_id = resp.json()["thesis_id"]

    session = factory()
    try:
        currents = [
            t for t in session.scalars(select(ThesisORM)).all()
            if (t.meta_json or {}).get("is_current")
        ]
        assert len(currents) == 1
        assert currents[0].thesis_id == new_thesis_id
        assert get_current_thesis(session, INSTRUMENT).thesis_id == new_thesis_id
    finally:
        session.close()


# ── §5.4-8：重复提交相同 Evidence → 幂等（422），不制造重复 Claim ─────────────


def test_reapply_same_evidence_is_idempotent(client):
    st = seed_thesis(client, n_support=1, n_oppose=0)
    factory = st["factory"]
    session = factory()
    try:
        _make_evidence(session, "ev_sup_new", "减持计划进展",
                       "广晟控股集团披露减持计划，拟减持不超过1%股份",
                       age_days=1.0)
        session.commit()
    finally:
        session.close()

    first = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：第一次应用。"},
    )
    assert first.status_code == 201, first.text

    session = factory()
    try:
        n_claims_after_first = len(session.scalars(select(ClaimORM)).all())
        n_theses_after_first = len(session.scalars(select(ThesisORM)).all())
    finally:
        session.close()

    # 重复提交：证据已被消费 → 422，不再造 Claim / Thesis
    second = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={"instrument_id": INSTRUMENT,
              "revised_statement": "修订：重复提交相同证据。"},
    )
    assert second.status_code == 422
    assert second.json()["error_code"] == "inbox.no_new_evidence"

    session = factory()
    try:
        assert len(session.scalars(select(ClaimORM)).all()) == n_claims_after_first
        assert len(session.scalars(select(ThesisORM)).all()) == n_theses_after_first
    finally:
        session.close()
