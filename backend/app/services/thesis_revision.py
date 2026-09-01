"""Thesis Revision Service（F2，第三轮整改任务书 §5 P0-B）.

正确链路（方案第二轮 §4.2 + 任务书 §5.1）：

    Old Current Thesis
        ↓ New Evidence
    New PIT Snapshot（pins ALL currently visible evidence）
        ↓
    Carry Forward Unaffected Claims（版本链：carried_forward）
    + Revise Affected Claims（按 ClaimImpact 七关系）
    + Add New Claims（结构化 Claim Builder，非裸截断）
    + Preserve Opposing Claims
        ↓
    New Thesis Version
        ↓
    Atomic Current Switch（任一步失败 → 全事务回滚，Current 不切换）

七关系 Apply 语义（任务书 §5.2）：
    supports      新证据进入 supporting evidence，Claim 仍为 supporting
    strengthens   新证据进入 supporting evidence，并记录强度变化
    weakens       新证据进入 opposing evidence；不悄悄保留为纯 supporting
    contradicts   Claim 进入 opposing，并记录冲突
    supersedes    创建新 Claim Version，旧版本标记 superseded，保留 parent chain
    updates       创建 revised Claim Version（带 parent chain），不只写 metadata
    irrelevant    不进入 Thesis，不制造 Claim
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.evidence import FactStatus
from app.domain.research import Claim, ClaimStatus, ClaimType, InvestmentThesis
from app.domain.source_trust import SourceTrust, trust_for_evidence
from app.storage.orm import EvidenceORM
from app.storage.research_orm import ClaimORM, ThesisORM
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository

# 版本类型（claims.revision_kind）
KIND_CARRIED_FORWARD = "carried_forward"
KIND_SUPERSEDES = "supersedes"
KIND_UPDATED = "updated"

# Claim Builder 版本（statement 构造可追溯；任务书 §5.3.3）
CLAIM_BUILDER_VERSION = "evidence_claim_builder_v1"

# 信任层 → 排序用数值（非概率；由可解释因素计算，F4 将带完整 basis）
_TRUST_NUMERIC: dict[str, float] = {
    "T0": 0.85,
    "T1": 0.75,
    "T2": 0.65,
    "T3": 0.50,
    "T4": 0.30,
}

# relation 优先级：同 claim 多条 impact 时 relation 元数据取最重者
_RELATION_SEVERITY = {
    "contradicts": 6,
    "supersedes": 5,
    "updates": 4,
    "weakens": 3,
    "strengthens": 2,
    "supports": 1,
    "irrelevant": 0,
}


def trust_numeric_confidence(authority_level, evidence_type) -> tuple[float, str]:
    """信任层 → 数值置信度（排序用途；可解释，非固定默认值）。

    返回 (value, basis) —— basis 记录来源信任层，供审计。
    """
    tier = trust_for_evidence(authority_level, evidence_type)
    prefix = tier.value.split("_", 1)[0]  # "T2"
    return _TRUST_NUMERIC.get(prefix, 0.30), f"source_trust={tier.value}"


# ── Thesis Diff（由 API 移入服务层，行为不变） ────────────────────────────────


def compute_thesis_diff(session: Session, instrument_id: str, since_dt: datetime | None) -> dict:
    """Thesis Diff（方案 §14.3）：窗口内新证据 → 影响分析 → 建议修订。

    确定性规则（不编造）：
      - new_evidence = available_time > since 的证据（PIT 可见）；
      - affected_claims = ClaimImpact 分析（七关系）；
      - affected_theses = 引用受影响 claims 的 theses；
      - suggested_action 由确定性规则给出（新非引用证据 → DELTA；无变化 → none）。
    """
    now = datetime.now(timezone.utc)
    if since_dt is None:
        since_dt = now - timedelta(days=7)

    new_ev = session.scalars(
        select(EvidenceORM)
        .where(EvidenceORM.instrument_id == instrument_id)
        .where(EvidenceORM.available_time > since_dt)
        .order_by(EvidenceORM.available_time.desc())
        .limit(20)
    ).all()
    from app.services.claim_impact import ClaimImpactService

    impact_svc = ClaimImpactService(session)
    evidence_view = [
        {
            "evidence_id": e.evidence_id,
            "kind": e.evidence_type,
            "title": e.title,
            "summary": e.summary,
            "at": e.available_time.isoformat(),
        }
        for e in new_ev
    ]
    impact_result = impact_svc.analyze(instrument_id, evidence_view)

    suggested_action = "none"
    if new_ev:
        non_quote = [e for e in new_ev if e.evidence_type != "market_quote"]
        suggested_action = "delta_research" if non_quote else "monitor_only"

    return {
        "instrument_id": instrument_id,
        "since": since_dt.isoformat(),
        "new_evidence": evidence_view,
        "affected_claims": impact_result["affected_claims"],
        "affected_theses": impact_result["affected_theses"],
        "impacts": impact_result["impacts"],
        "irrelevant_count": impact_result["irrelevant_count"],
        "suggested_action": suggested_action,
    }


# ── 结构化 Claim Builder（任务书 §5.3.3：禁止裸「[新发现] + summary 截断」） ──


def build_evidence_claim(
    *,
    instrument_id: str,
    snapshot_id: str,
    evidence: dict,
) -> Claim:
    """由证据构造结构化 Claim。

    statement = f"[{kind}] {title} — {summary}"（完整文本，不静默截断；
    超 2000 字符时显式截断并记录 truncated=True 于 metadata）。
    metadata.statement_basis 记录 builder 版本、证据 id、kind、来源，
    保证研究陈述可审计。
    """
    kind = str(evidence.get("kind") or "unknown")
    title = str(evidence.get("title") or "").strip()
    summary = str(evidence.get("summary") or "").strip()
    ev_id = str(evidence.get("evidence_id") or "").strip()
    core = f"{title} — {summary}" if title and summary and title != summary else (title or summary)
    statement = f"[{kind}] {core}"
    truncated = False
    if len(statement) > 2000:
        statement = statement[:2000]
        truncated = True

    return Claim(
        instrument_id=instrument_id,
        snapshot_id=snapshot_id,
        statement=statement,
        claim_type=ClaimType.FUNDAMENTAL_FACT,
        supporting_evidence_refs=(ev_id,),
        opposing_evidence_refs=(),
        fact_status=FactStatus.ANALYST_INFERENCE,
        confidence=0.0,  # 由调用方按 trust 填写（trust_numeric_confidence）
        status=ClaimStatus.PROPOSED,
        metadata={
            "statement_basis": {
                "builder": CLAIM_BUILDER_VERSION,
                "evidence_id": ev_id,
                "kind": kind,
                "title": title,
                "truncated": truncated,
            },
        },
    )


# ── Apply（原子修订） ────────────────────────────────────────────────────────


def _claim_row(session: Session, claim_id: str) -> ClaimORM:
    row = session.scalars(select(ClaimORM).where(ClaimORM.claim_id == claim_id)).first()
    if row is None:
        raise AppError(
            "thesis_revision.claim_missing", status_code=500,
            detail=f"claim {claim_id} disappeared during revision",
        ) from None
    return row


def apply_thesis_revision(
    session: Session,
    *,
    instrument_id: str,
    revised_statement: str,
    since_dt: datetime | None = None,
) -> dict:
    """原子 Thesis 修订。任一步失败 → 全事务回滚，Current Thesis 不切换。"""
    from app.application.artifacts import ArtifactService, RelationType
    from app.application.run_events import record_run_event
    from app.services.claim_impact import ClaimImpactService
    from app.services.current_thesis import demote_other_currents, get_current_thesis

    now = datetime.now(timezone.utc)
    if since_dt is None:
        since_dt = now - timedelta(days=7)

    try:
        return _apply_inner(
            session, instrument_id=instrument_id, revised_statement=revised_statement,
            since_dt=since_dt, now=now,
        )
    except AppError:
        session.rollback()
        raise
    except Exception as exc:  # noqa: BLE001 — 任一失败即回滚，不留半成品（§5.3.2）
        session.rollback()
        raise AppError(
            "thesis_revision.failed", status_code=500,
            detail=f"revision rolled back: {type(exc).__name__}: {exc}",
        ) from exc


def _apply_inner(
    session: Session,
    *,
    instrument_id: str,
    revised_statement: str,
    since_dt: datetime,
    now: datetime,
) -> dict:
    from app.services.claim_impact import ClaimImpactService
    from app.services.current_thesis import demote_other_currents, get_current_thesis

    # ---- 1) Thesis Diff + 已消费证据过滤（幂等：重复提交不无限造 Claim） ------
    diff_data = compute_thesis_diff(session, instrument_id, since_dt)
    old_thesis = get_current_thesis(session, instrument_id)
    if old_thesis is None:
        raise AppError("thesis.not_found", status_code=404) from None

    old_meta = dict(old_thesis.meta_json or {})
    consumed = set(old_meta.get("added_evidence_ids") or [])
    new_ev_view = [
        ev for ev in diff_data["new_evidence"] if ev["evidence_id"] not in consumed
    ]
    if not new_ev_view:
        raise AppError(
            "inbox.no_new_evidence", status_code=422,
            detail="no unconsumed new evidence since the window — nothing to apply",
        ) from None

    # ---- 2) New PIT snapshot（pins ALL currently visible evidence） ----------
    new_snapshot = SnapshotRepository(session).build(
        instrument_id, now, evidence_repo=EvidenceRepository(session)
    )
    new_snap_id = new_snapshot.snapshot_id
    old_snap_id = old_thesis.snapshot_id
    if new_snap_id == old_snap_id:
        raise AppError(
            "inbox.no_new_evidence", status_code=422,
            detail="new snapshot identical to old — no new evidence to revise",
        ) from None

    # ---- 3) ClaimImpact -------------------------------------------------------
    impact_svc = ClaimImpactService(session)
    impact_result = impact_svc.analyze(instrument_id, new_ev_view)
    impacts_by_claim: dict[str, list[dict]] = {}
    for imp in impact_result["impacts"]:
        impacts_by_claim.setdefault(imp["claim_id"], []).append(imp)
    covered_evs = {imp["new_evidence_id"] for imp in impact_result["impacts"]}

    research_repo = ResearchRepository(session)

    # ---- 4) Carry Forward ALL old claims（版本链：carried_forward） -----------
    # 不得静默丢 Claim（§5.3.1）：任一保存失败 → 异常上抛 → 全事务回滚。
    old_claim_ids = sorted(
        set(old_thesis.supporting_claims_json or [])
        | set(old_thesis.opposing_claims_json or [])
    )
    old_claim_rows = session.scalars(
        select(ClaimORM).where(ClaimORM.claim_id.in_(old_claim_ids))
    ).all() if old_claim_ids else []
    missing = [cid for cid in old_claim_ids if cid not in {r.claim_id for r in old_claim_rows}]
    if missing:
        raise AppError(
            "thesis_revision.claim_missing", status_code=500,
            detail=f"old thesis references missing claims: {missing}",
        ) from None

    carried_forward: dict[str, str] = {}  # old_claim_id → new claim_id
    supporting_ids: list[str] = []
    opposing_ids: list[str] = []
    added_evidence_ids: list[str] = []

    for oc in old_claim_rows:
        was_supporting = oc.claim_id in (old_thesis.supporting_claims_json or [])
        new_claim = Claim(
            instrument_id=oc.instrument_id,
            snapshot_id=new_snap_id,
            statement=oc.statement,
            claim_type=oc.claim_type,  # type: ignore[arg-type]
            supporting_evidence_refs=tuple(oc.supporting_evidence_refs_json or []),
            opposing_evidence_refs=tuple(oc.opposing_evidence_refs_json or []),
            fact_status=oc.fact_status,  # type: ignore[arg-type]
            confidence=oc.confidence,
            status=ClaimStatus.PROPOSED,
            parent_claim_id=oc.claim_id,
            revision_kind=KIND_CARRIED_FORWARD,
            revision_reason="thesis revision: carried forward to new PIT snapshot",
            source_impact_relation=None,
            carried_forward=True,
        )
        new_cid = research_repo.save_claim(new_claim)
        carried_forward[oc.claim_id] = new_cid
        if was_supporting:
            supporting_ids.append(new_cid)
        else:
            opposing_ids.append(new_cid)

    # ---- 5) 按七关系修订 carried claims（§5.2） --------------------------------
    revised_claim_ids: list[str] = []
    superseded_claim_ids: list[str] = []

    for old_cid, impacts in impacts_by_claim.items():
        new_cid = carried_forward.get(old_cid)
        if new_cid is None:
            continue
        cf_row = _claim_row(session, new_cid)
        notes: list[str] = []

        for imp in impacts:
            relation = imp["relation"]
            ev_id = imp["new_evidence_id"]
            if relation == "irrelevant":
                continue

            # relation 元数据：同 claim 多 impact 时保留最重者（可审计）
            current_rel = cf_row.source_impact_relation
            if current_rel is None or _RELATION_SEVERITY.get(
                relation, 0
            ) > _RELATION_SEVERITY.get(current_rel, -1):
                cf_row.source_impact_relation = relation

            if relation in ("supports", "strengthens"):
                refs = list(cf_row.supporting_evidence_refs_json or [])
                if ev_id not in refs:
                    refs.append(ev_id)
                    cf_row.supporting_evidence_refs_json = refs
                if relation == "strengthens":
                    notes.append(
                        f"strength_change: +1 supporting evidence（同事件加固，"
                        f"现 {len(refs)} 条支撑）"
                    )
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            elif relation in ("weakens", "contradicts"):
                # 新证据进入 opposing；不得悄悄保留为纯 supporting（§5.2）
                refs = list(cf_row.opposing_evidence_refs_json or [])
                if ev_id not in refs:
                    refs.append(ev_id)
                    cf_row.opposing_evidence_refs_json = refs
                if new_cid in supporting_ids:
                    supporting_ids.remove(new_cid)
                if new_cid not in opposing_ids:
                    opposing_ids.append(new_cid)
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            elif relation in ("supersedes", "updates"):
                # 旧版本标记 superseded；创建新 Claim Version（parent chain，§5.2）
                cf_row.status = ClaimStatus.SUPERSEDED.value
                superseded_claim_ids.append(new_cid)
                ev_title = ""
                for ev in new_ev_view:
                    if ev["evidence_id"] == ev_id:
                        ev_title = ev.get("title") or ev.get("summary") or ""
                        break
                tag = "更正" if relation == "supersedes" else "更新"
                old_refs_sup = list(cf_row.supporting_evidence_refs_json or [])
                old_refs_opp = list(cf_row.opposing_evidence_refs_json or [])
                if ev_id not in old_refs_sup:
                    old_refs_sup.append(ev_id)
                version_kind = KIND_SUPERSEDES if relation == "supersedes" else KIND_UPDATED
                # 语句含证据 id 尾码：同证据多 claim 更新时不串行冲突
                suffix = f"（{tag}：{ev_title[:160]} · {ev_id[-8:]}）" if ev_title else f"（{tag}·{ev_id[-8:]}）"
                version_claim = Claim(
                    instrument_id=cf_row.instrument_id,
                    snapshot_id=new_snap_id,
                    statement=(cf_row.statement + suffix)[:2000],
                    claim_type=cf_row.claim_type,  # type: ignore[arg-type]
                    supporting_evidence_refs=tuple(old_refs_sup),
                    opposing_evidence_refs=tuple(old_refs_opp),
                    fact_status=cf_row.fact_status,  # type: ignore[arg-type]
                    confidence=cf_row.confidence,
                    status=ClaimStatus.PROPOSED,
                    parent_claim_id=new_cid,
                    revision_kind=version_kind,
                    revision_reason=imp.get("reason") or relation,
                    source_impact_relation=relation,
                    carried_forward=False,
                )
                # 冲突安全：同 (snapshot, statement) 已存在 → 复用该行（幂等）
                existing_version = session.scalars(
                    select(ClaimORM).where(
                        ClaimORM.snapshot_id == new_snap_id,
                        ClaimORM.statement == version_claim.statement,
                    )
                ).first()
                if existing_version is not None:
                    vid = existing_version.claim_id
                else:
                    vid = research_repo.save_claim(version_claim)
                revised_claim_ids.append(vid)
                # 版本 claim 取代 carried 行在 Thesis 中的位置
                if new_cid in supporting_ids:
                    supporting_ids.remove(new_cid)
                    if vid not in supporting_ids:
                        supporting_ids.append(vid)
                if new_cid in opposing_ids:
                    opposing_ids.remove(new_cid)
                    if vid not in opposing_ids:
                        opposing_ids.append(vid)
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            # revision_reason 累积修订原因与强度变化（可审计）
            notes.append(imp.get("reason") or relation)
        if notes:
            cf_row.revision_reason = "; ".join(
                filter(None, [cf_row.revision_reason, *notes])
            )[:500]

    # ---- 6) irrelevant 证据不制造 Claim（§5.2） --------------------------------
    # 旧 Thesis 有 claims 时，未命中任何 impact 的新证据 = 全量 irrelevant。
    irrelevant_ids = [
        ev["evidence_id"] for ev in new_ev_view
        if ev["evidence_id"] not in covered_evs
    ] if old_claim_ids else []

    # ---- 7) 未覆盖证据 → 结构化 Claim Builder（旧 Thesis 无 claims 时） --------
    for ev in new_ev_view:
        ev_id = ev["evidence_id"]
        if ev_id in added_evidence_ids or ev_id in irrelevant_ids:
            continue
        ev_row = session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id == ev_id)
        ).first()
        value, basis = trust_numeric_confidence(
            ev_row.authority_level if ev_row else None,
            ev_row.evidence_type if ev_row else None,
        )
        new_claim = build_evidence_claim(
            instrument_id=instrument_id, snapshot_id=new_snap_id, evidence=ev,
        )
        new_claim = new_claim.model_copy(
            update={
                "confidence": value,
                "metadata": {
                    **new_claim.metadata,
                    "confidence_basis": basis,
                },
            }
        )
        existing = session.scalars(
            select(ClaimORM).where(
                ClaimORM.snapshot_id == new_snap_id,
                ClaimORM.statement == new_claim.statement,
            )
        ).first()
        new_cid = existing.claim_id if existing is not None else research_repo.save_claim(new_claim)
        if new_cid not in supporting_ids and new_cid not in opposing_ids:
            supporting_ids.append(new_cid)
        if ev_id not in added_evidence_ids:
            added_evidence_ids.append(ev_id)

    # ---- 8) New Thesis on NEW snapshot + 原子 Current 切换 --------------------
    new_thesis = InvestmentThesis(
        instrument_id=instrument_id,
        snapshot_id=new_snap_id,
        title=f"{old_thesis.title} · 修订 {uuid4().hex[:8]}"[:200],
        description=revised_statement,
        supporting_claims=tuple(supporting_ids),
        opposing_claims=tuple(opposing_ids),
        confidence=old_thesis.confidence,
    )
    new_thesis_id = research_repo.save_thesis(new_thesis)

    new_row = session.scalars(
        select(ThesisORM).where(ThesisORM.thesis_id == new_thesis_id)
    ).first()
    if new_row is not None:
        new_row.meta_json = {
            "parent_thesis_id": old_thesis.thesis_id,
            "root_thesis_id": old_meta.get("root_thesis_id", old_thesis.thesis_id),
            "is_current": True,
            "revision_reason": revised_statement[:300],
            "revision_at": now.isoformat(),
            "old_snapshot_id": old_snap_id,
            "new_snapshot_id": new_snap_id,
            "added_evidence_ids": added_evidence_ids,
            "irrelevant_evidence_ids": irrelevant_ids,
            "carried_forward_claims": list(carried_forward.values()),
            "carried_forward_map": carried_forward,
            "revised_claim_ids": revised_claim_ids,
            "superseded_claim_ids": superseded_claim_ids,
            "impacts": impact_result["impacts"],
            "affected_claim_count": len(impact_result["affected_claims"]),
            "irrelevant_count": impact_result["irrelevant_count"],
            "suggested_action": diff_data["suggested_action"],
            "claim_builder": CLAIM_BUILDER_VERSION,
        }
    demote_other_currents(session, instrument_id, new_thesis_id)
    old_row = session.scalars(
        select(ThesisORM).where(ThesisORM.thesis_id == old_thesis.thesis_id)
    ).first()
    if old_row is not None:
        om = dict(old_row.meta_json or {})
        om["is_current"] = False
        old_row.meta_json = om

    # ---- 9) Artifact + Provenance + 事件 ---------------------------------------
    from app.application.artifacts import ArtifactService, RelationType
    from app.application.run_events import record_run_event

    service = ArtifactService(session)
    new_artifact = service.register(
        artifact_type="thesis",
        domain_type="Thesis",
        domain_id=new_thesis_id,
        title=f"{old_thesis.title} · Thesis Revision",
        instrument_ids=(instrument_id,),
        created_by="thesis_revision",
        route=f"/instrument/{instrument_id}",
    )
    old_artifact = service.by_domain("Thesis", old_thesis.thesis_id)
    if old_artifact is not None:
        service.link(
            from_artifact_id=new_artifact,
            to_artifact_id=old_artifact["artifact_id"],
            relation=RelationType.GENERATED_FROM,
        )

    record_run_event(
        session, f"run_revision_{uuid4().hex[:8]}", "thesis_revision_applied",
        {
            "old_thesis": old_thesis.thesis_id,
            "new_thesis": new_thesis_id,
            "new_snapshot": new_snap_id,
            "old_snapshot": old_snap_id,
            "added_evidence": added_evidence_ids,
            "irrelevant_evidence": irrelevant_ids,
            "carried_forward": list(carried_forward.values()),
            "revised_claims": revised_claim_ids,
            "superseded_claims": superseded_claim_ids,
            "supporting_count": len(supporting_ids),
            "opposing_count": len(opposing_ids),
        },
    )

    session.commit()

    return {
        "thesis_id": new_thesis_id,
        "old_thesis_id": old_thesis.thesis_id,
        "new_snapshot_id": new_snap_id,
        "old_snapshot_id": old_snap_id,
        "added_evidence_ids": added_evidence_ids,
        "irrelevant_evidence_ids": irrelevant_ids,
        "carried_forward_claims": list(carried_forward.values()),
        "carried_forward_map": carried_forward,
        "revised_claim_ids": revised_claim_ids,
        "superseded_claim_ids": superseded_claim_ids,
        "supporting_count": len(supporting_ids),
        "opposing_count": len(opposing_ids),
        "affected_claim_count": len(impact_result["affected_claims"]),
        "irrelevant_count": impact_result["irrelevant_count"],
    }
