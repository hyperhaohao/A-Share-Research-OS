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
    """Thesis Diff（方案 §14.3）— 实现移入 app/services/thesis_revision.py（F2）。"""
    from app.services.thesis_revision import compute_thesis_diff

    return compute_thesis_diff(session, instrument_id, since_dt)


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
    """F2（P0-B）：原子 Thesis 修订 — New Evidence → New Snapshot →
    Carry Forward + 七关系修订 → New Thesis → Atomic Current Switch。

    语义与事务保证见 app/services/thesis_revision.py（任务书 §5）：
    任一步失败 → 全事务回滚，Current Thesis 不切换；不静默丢 Claim。
    """
    from datetime import timedelta

    from app.services.thesis_revision import apply_thesis_revision

    since_dt = None
    if payload.since:
        try:
            since_dt = datetime.fromisoformat(payload.since.replace("Z", "+00:00"))
        except ValueError:
            raise AppError("inbox.bad_since", status_code=422) from None
    if since_dt is None:
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)

    return apply_thesis_revision(
        session,
        instrument_id=payload.instrument_id,
        revised_statement=payload.revised_statement,
        since_dt=since_dt,
    )
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
    """F3（P0-C）：正式 Signal 评估 — BUILTIN_SIGNAL_RULES + 完整门迹。

    后端自动：Evidence Load → Instrument Ownership Gate → Source Trust →
    Evidence Type → Entity Resolution（Instrument Registry）→
    BUILTIN_SIGNAL_RULES → Negative/State Transition Gate → Result + Provenance。
    调用方只传 instrument_id + evidence_ids，不能自定义 A/B 规则。
    返回含 trust_gate/type_gate/entity_gate/state_transition/rejected_reasons
    （任务书 §6.3）。实现：app/services/signal_production.py。
    """
    from app.services.signal_production import evaluate_production_signals

    return evaluate_production_signals(session, instrument_id, evidence_ids)
