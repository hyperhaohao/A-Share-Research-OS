"""R8 API — Research Inbox + Thesis Diff + Signal Ladder（方案 §14）.

GET  /research-inbox                       收件箱聚合（只读投影）
GET  /research-inbox/thesis-diff           Thesis Diff（新证据 → 影响分析）
POST /research-inbox/thesis-diff/apply     应用 diff → 新 Thesis（append-only）
POST /signal-ladder/evaluate               A/B 信号分级（证据引用强制）
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.application.run_events import record_run_event
from app.services.research_inbox import (
    ResearchInboxService,
    SignalLadder,
)
from app.storage.orm import EvidenceORM, SnapshotORM
from app.storage.research_orm import ClaimORM, ThesisORM


router = APIRouter(prefix="/research-inbox", tags=["research-inbox"])


@router.get("")
def research_inbox(
    window_hours: int = Query(default=48, ge=1, le=720),
    limit_per: int = Query(default=8, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    return {"inbox": ResearchInboxService(session).inbox(window_hours=window_hours, limit_per=limit_per)}


class LadderObsIn(BaseModel):
    observation_id: str = Field(min_length=1, max_length=48)
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)


class LadderIn(BaseModel):
    ladder: list[dict] = Field(min_length=1, max_length=8)
    observations: list[LadderObsIn] = Field(min_length=1, max_length=50)


@router.post("/signal-ladder/evaluate")
def evaluate_signal_ladder(payload: LadderIn, session: Session = Depends(get_session)) -> dict:
    """A/B 信号分级：确定性规则 + 证据引用强制（每次命中带 evidence_ids）。"""
    # 证据引用必须真实存在（引用反查精神延伸）
    for obs in payload.observations:
        for eid in obs.evidence_ids:
            row = session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == eid)
            ).first()
            if row is None:
                raise AppError(
                    "signal_ladder.evidence_not_found", status_code=422,
                    detail=f"evidence {eid} not found",
                ) from None
    results = SignalLadder.evaluate(
        [o.model_dump() for o in payload.observations], payload.ladder
    )
    return {"count": len(results), "results": results}


class ThesisDiffIn(BaseModel):
    instrument_id: str = Field(min_length=4, max_length=32)
    since: str | None = Field(default=None, max_length=40)


def _thesis_diff(session: Session, instrument_id: str, since_dt: datetime | None) -> dict:
    """Thesis Diff（方案 §14.3）：窗口内新证据 → 影响分析 → 建议修订。

    确定性规则（不编造）：
      - new_evidence = available_time > since 的证据（PIT 可见）；
      - affected_claims = 支撑/反对引用包含「已被移除证据」或与新增证据同
        instrument 的 claims；
      - affected_theses = 引用受影响 claims 的 theses；
      - suggested_action 由确定性规则给出（新非引用证据 → DELTA；无变化 → none）。
    """
    now = datetime.now(timezone.utc)
    if since_dt is None:
        from datetime import timedelta

        since_dt = now - timedelta(days=7)

    new_ev = session.scalars(
        select(EvidenceORM)
        .where(EvidenceORM.instrument_id == instrument_id)
        .where(EvidenceORM.available_time > since_dt)
        .order_by(EvidenceORM.available_time.desc())
        .limit(20)
    ).all()
    # R8-C1（P0-01）：Claim Impact 分析替代「旧∉新=stale」错误算法
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


@router.get("/thesis-diff")
def thesis_diff(
    instrument_id: str = Query(min_length=4, max_length=32),
    since: str | None = Query(default=None, max_length=40),
    session: Session = Depends(get_session),
) -> dict:
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise AppError("inbox.bad_since", status_code=422) from None
    return {"diff": _thesis_diff(session, instrument_id, since_dt)}






class ThesisDiffApplyIn(BaseModel):
    instrument_id: str = Field(min_length=4, max_length=32)
    since: str | None = Field(default=None, max_length=40)
    revised_statement: str = Field(min_length=4, max_length=400)


@router.post("/thesis-diff/apply", status_code=201)
def apply_thesis_diff(payload: ThesisDiffApplyIn, session: Session = Depends(get_session)) -> dict:
    """F3-REVIEW（P0-A）：New Evidence → New Snapshot → Carry Forward + Revise Claims → New Thesis.

    正确链路（方案第二轮 §4.2）：
      1. Build new PIT snapshot（pins ALL currently visible evidence）
      2. ClaimImpact 分析
      3. Carry Forward ALL old claims → 新快照上新建同文 Claim 行
      4. For impacted claims: 按 relation 修订（追加 evidence / opposing）
      5. Separate into supporting vs opposing（按 relation 方向）
      6. Create new thesis on new snapshot
      7. Set new thesis is_current=true, demote old
    """
    from datetime import timedelta

    from app.application.artifacts import ArtifactService, RelationType
    from app.application.run_events import record_run_event
    from app.domain.evidence import FactStatus
    from app.domain.research import Claim, ClaimStatus, InvestmentThesis
    from app.domain.source_trust import confidence_level
    from app.services.claim_impact import ClaimImpactService
    from app.services.current_thesis import demote_other_currents, get_current_thesis
    from app.storage.research_repo import ResearchRepository
    from app.storage.repository import EvidenceRepository
    from app.storage.snapshot_repo import SnapshotRepository

    now = datetime.now(timezone.utc)
    since_dt = None
    if payload.since:
        try:
            since_dt = datetime.fromisoformat(payload.since.replace("Z", "+00:00"))
        except ValueError:
            raise AppError("inbox.bad_since", status_code=422) from None
    if since_dt is None:
        since_dt = now - timedelta(days=7)

    # ---- 1) ClaimImpact 分析 ------------------------------------------------
    diff_data = _thesis_diff(session, payload.instrument_id, since_dt)
    new_ev_rows = diff_data["new_evidence"]
    if not new_ev_rows:
        raise AppError(
            "inbox.no_new_evidence", status_code=422,
            detail="no new evidence since the window — nothing to apply",
        ) from None

    old_thesis = get_current_thesis(session, payload.instrument_id)
    if old_thesis is None:
        raise AppError("thesis.not_found", status_code=404) from None

    # ---- 2) Build NEW PIT snapshot ------------------------------------------
    new_snapshot = SnapshotRepository(session).build(
        payload.instrument_id, now, evidence_repo=EvidenceRepository(session)
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
    new_ev_view = [
        {
            "evidence_id": e["evidence_id"], "kind": e["kind"],
            "title": e["title"], "summary": e.get("summary", ""),
            "at": e.get("at", ""),
        }
        for e in diff_data["new_evidence"]
    ]
    impact_result = impact_svc.analyze(payload.instrument_id, new_ev_view)

    # Build impact lookup: claim_id → list of impacts
    impacts_by_claim: dict[str, list[dict]] = {}
    for imp in impact_result["impacts"]:
        impacts_by_claim.setdefault(imp["claim_id"], []).append(imp)

    research_repo = ResearchRepository(session)

    # ---- 4) Carry Forward ALL old claims to NEW snapshot ----------------------
    # 每条旧 Claim 在新快照上新建同文行（statement/evidence_refs 不变，
    # snapshot_id = new_snap_id）。然后根据 impact 修订。
    old_claim_ids = sorted(
        set(old_thesis.supporting_claims_json or [])
        | set(old_thesis.opposing_claims_json or [])
    )
    old_claims = session.scalars(
        select(ClaimORM).where(ClaimORM.claim_id.in_(old_claim_ids))
    ).all() if old_claim_ids else []
    old_claim_by_id = {c.claim_id: c for c in old_claims}

    # new snapshot 上 claim_id → 新 claim_id 的映射
    carried_forward: dict[str, str] = {}  # old_claim_id → new_claim_id
    supporting_ids: list[str] = []
    opposing_ids: list[str] = []
    added_evidence_ids: list[str] = []
    revised_claim_ids: list[str] = []

    for oc in old_claims:
        # 确定 old claim 属于 supporting 还是 opposing
        was_supporting = oc.claim_id in (old_thesis.supporting_claims_json or [])
        # 复制到新快照
        new_claim = Claim(
            instrument_id=oc.instrument_id,
            snapshot_id=new_snap_id,
            statement=oc.statement,
            claim_type=oc.claim_type,
            supporting_evidence_refs=tuple(oc.supporting_evidence_refs_json or []),
            opposing_evidence_refs=tuple(oc.opposing_evidence_refs_json or []),
            fact_status=oc.fact_status,
            confidence=oc.confidence,
            status=ClaimStatus.PROPOSED,
        )
        try:
            new_cid = research_repo.save_claim(new_claim)
            carried_forward[oc.claim_id] = new_cid
            if was_supporting:
                supporting_ids.append(new_cid)
            else:
                opposing_ids.append(new_cid)
        except Exception:
            continue

    # ---- 5) Apply ClaimImpact relations to carried-forward claims -------------
    for old_cid, impacts in impacts_by_claim.items():
        new_cid = carried_forward.get(old_cid)
        if new_cid is None:
            continue
        # 找到 carried-forward claim 的行
        cf_row = session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == new_cid)
        ).first()
        if cf_row is None:
            continue

        for imp in impacts:
            relation = imp["relation"]
            ev_id = imp["new_evidence_id"]
            if relation == "irrelevant":
                continue

            if relation in ("supports", "strengthens"):
                # 追加 supporting evidence
                refs = list(cf_row.supporting_evidence_refs_json or [])
                if ev_id not in refs:
                    refs.append(ev_id)
                    cf_row.supporting_evidence_refs_json = refs
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            elif relation in ("weakens", "contradicts"):
                # 追加 opposing evidence
                refs = list(cf_row.opposing_evidence_refs_json or [])
                if ev_id not in refs:
                    refs.append(ev_id)
                    cf_row.opposing_evidence_refs_json = refs
                # 移到 opposing 列表
                if new_cid in supporting_ids:
                    supporting_ids.remove(new_cid)
                if new_cid not in opposing_ids:
                    opposing_ids.append(new_cid)
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            elif relation == "supersedes":
                # 标记旧 claim superseded，创建新 claim
                cf_row.status = "superseded"
                revised_claim_ids.append(new_cid)
                # 新 claim 会在下面通过 new evidence 创建
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

            elif relation == "updates":
                revised_claim_ids.append(new_cid)
                if ev_id not in added_evidence_ids:
                    added_evidence_ids.append(ev_id)

    # ---- 6) Create NEW claims for new evidence not covered by old claims ------
    covered_evs = {imp["new_evidence_id"] for imp in impact_result["impacts"]}
    for ev in new_ev_view:
        ev_id = ev["evidence_id"]
        if ev_id in added_evidence_ids:
            continue
        # 新证据未被任何旧 claim 覆盖 → 创建新 claim
        new_claim = Claim(
            instrument_id=payload.instrument_id,
            snapshot_id=new_snap_id,
            statement=f"[新发现] {(ev.get('summary') or '')[:300]}",
            claim_type="fundamental_fact",
            supporting_evidence_refs=(ev_id,),
            opposing_evidence_refs=(),
            fact_status=FactStatus.ANALYST_INFERENCE,
            confidence=0.6,
            status=ClaimStatus.PROPOSED,
        )
        try:
            new_cid = research_repo.save_claim(new_claim)
            supporting_ids.append(new_cid)
            if ev_id not in added_evidence_ids:
                added_evidence_ids.append(ev_id)
        except Exception:
            pass

    # ---- 7) Create New Thesis on NEW snapshot ---------------------------------
    old_meta = dict(old_thesis.meta_json or {})
    new_thesis = InvestmentThesis(
        instrument_id=payload.instrument_id,
        snapshot_id=new_snap_id,
        title=f"{old_thesis.title} · 修订 {uuid4().hex[:8]}"[:200],
        description=payload.revised_statement,
        supporting_claims=tuple(supporting_ids),
        opposing_claims=tuple(opposing_ids),
        confidence=old_thesis.confidence,
    )
    new_thesis_id = research_repo.save_thesis(new_thesis)

    # ---- 8) Set Current: new=true, old=false -----------------------------------
    new_row = session.scalars(
        select(ThesisORM).where(ThesisORM.thesis_id == new_thesis_id)
    ).first()
    if new_row is not None:
        new_row.meta_json = {
            "parent_thesis_id": old_thesis.thesis_id,
            "root_thesis_id": old_meta.get("root_thesis_id", old_thesis.thesis_id),
            "is_current": True,
            "revision_reason": payload.revised_statement[:300],
            "revision_at": now.isoformat(),
            "old_snapshot_id": old_snap_id,
            "new_snapshot_id": new_snap_id,
            "added_evidence_ids": added_evidence_ids,
            "carried_forward_claims": list(carried_forward.values()),
            "revised_claim_ids": revised_claim_ids,
            "affected_claim_count": len(impact_result["affected_claims"]),
            "irrelevant_count": impact_result["irrelevant_count"],
            "suggested_action": diff_data["suggested_action"],
        }
    demote_other_currents(session, payload.instrument_id, new_thesis_id)
    old_row = session.scalars(
        select(ThesisORM).where(ThesisORM.thesis_id == old_thesis.thesis_id)
    ).first()
    if old_row is not None:
        om = dict(old_row.meta_json or {})
        om["is_current"] = False
        old_row.meta_json = om

    # ---- 9) Artifact + Provenance ----------------------------------------------
    service = ArtifactService(session)
    new_artifact = service.register(
        artifact_type="thesis",
        domain_type="Thesis",
        domain_id=new_thesis_id,
        title=f"{old_thesis.title} · Thesis Revision",
        instrument_ids=(payload.instrument_id,),
        created_by="thesis_revision",
        route=f"/instrument/{payload.instrument_id}",
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
            "carried_forward": list(carried_forward.values()),
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
        "carried_forward_claims": list(carried_forward.values()),
        "supporting_count": len(supporting_ids),
        "opposing_count": len(opposing_ids),
        "affected_claim_count": len(impact_result["affected_claims"]),
        "irrelevant_count": impact_result["irrelevant_count"],
    }
@router.get("/theses/current/{instrument_id}")
def get_current_thesis_api(instrument_id: str, session: Session = Depends(get_session)) -> dict:
    """F1（P0-A1）：Current Thesis 唯一选择器。"""
    from app.services.current_thesis import get_current_thesis

    thesis = get_current_thesis(session, instrument_id)
    if thesis is None:
        raise AppError("thesis.not_found", status_code=404) from None
    return {
        "thesis_id": thesis.thesis_id,
        "title": thesis.title,
        "snapshot_id": thesis.snapshot_id,
        "meta": dict(thesis.meta_json or {}),
        "created_at": thesis.created_at.isoformat() if thesis.created_at else None,
    }


@router.get("/theses/history/{instrument_id}")
def thesis_history(instrument_id: str, session: Session = Depends(get_session)) -> dict:
    """F1：Thesis 版本链（parent/reason/revision_at）。"""
    rows = session.scalars(
        select(ThesisORM)
        .where(ThesisORM.instrument_id == instrument_id)
        .order_by(ThesisORM.created_at.desc())
        .limit(30)
    ).all()
    current = get_current_thesis(session, instrument_id)
    return {
        "current_thesis_id": current.thesis_id if current else None,
        "versions": [
            {
                "thesis_id": r.thesis_id,
                "title": r.title,
                "snapshot_id": r.snapshot_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "meta": dict(r.meta_json or {}),
                "is_current": r.thesis_id == (current.thesis_id if current else None),
            }
            for r in rows
        ],
    }


@router.get("/theses/{thesis_id}/diff/{other_id}")
def thesis_diff_detail(thesis_id: str, other_id: str, session: Session = Depends(get_session)) -> dict:
    """两版 Thesis 差异对比。"""
    t1 = session.scalars(select(ThesisORM).where(ThesisORM.thesis_id == thesis_id)).first()
    t2 = session.scalars(select(ThesisORM).where(ThesisORM.thesis_id == other_id)).first()
    if t1 is None or t2 is None:
        raise AppError("thesis.not_found", status_code=404) from None
    sup1 = set(t1.supporting_claims_json or [])
    sup2 = set(t2.supporting_claims_json or [])
    return {
        "added_claims": sorted(sup2 - sup1),
        "removed_claims": sorted(sup1 - sup2),
        "unchanged_claims": sorted(sup1 & sup2),
        "t1": {"thesis_id": t1.thesis_id, "title": t1.title, "snapshot_id": t1.snapshot_id},
        "t2": {"thesis_id": t2.thesis_id, "title": t2.title, "snapshot_id": t2.snapshot_id},
    }


@router.post("/signal-ladder/evaluate-evidence")
def evaluate_evidence_signals(
    instrument_id: str = Query(min_length=4, max_length=32),
    evidence_ids: list[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """F4（P0-B）：正式 Signal 评估 — BUILTIN_SIGNAL_RULES + 自动加载。

    后端自动：Load Evidence → Load Source Trust → Load Evidence Type →
    Extract Entities → Load BUILTIN_SIGNAL_RULES → Evaluate。
    调用方只传 instrument_id + evidence_ids，不能自定义 A/B 规则。
    """
    from app.domain.evidence import EvidenceType
    from app.domain.signal_rules import BUILTIN_SIGNAL_RULES, SignalResult
    from app.domain.source_trust import trust_for_evidence
    from app.services.research_inbox import SignalLadder

    if not evidence_ids:
        # default: latest evidence for instrument
        rows = session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.instrument_id == instrument_id)
            .order_by(EvidenceORM.available_time.desc())
            .limit(20)
        ).all()
        evidence_ids = [r.evidence_id for r in rows]

    observations = []
    trust_map = {}
    entity_map = {}
    for eid in evidence_ids:
        row = session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id == eid)
        ).first()
        if row is None:
            continue
        trust = trust_for_evidence(row.authority_level, row.evidence_type)
        trust_map[eid] = trust.value
        # entity extraction: instrument name + key phrases from summary
        entities = []
        if row.summary:
            for ent in ("中国稀土", "广晟控股", "稀土集团", "国资委", "工信部",
                        "证监会", "发改委", "北方稀土"):
                if ent in row.summary:
                    entities.append(ent)
        entity_map[eid] = entities
        observations.append({
            "observation_id": eid,
            "text": row.summary or "",
            "evidence_ids": [eid],
        })

    results = SignalLadder.evaluate_rules(
        observations,
        BUILTIN_SIGNAL_RULES,
        evidence_trust=trust_map,
        evidence_entities=entity_map,
    )
    return {"count": len(results), "results": results}
