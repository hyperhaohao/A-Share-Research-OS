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
    """应用 diff → 新 Thesis 行（append-only：旧 Thesis 永不覆盖）。

    新 Thesis 继承旧 Thesis 的 claims + 追加窗口内新证据引用；
    注册 Artifact（generated_from 旧 Thesis）+ RunEvent 落库。
    """
    from app.application.artifacts import ArtifactService, RelationType
    from app.domain.research import InvestmentThesis
    from app.storage.research_repo import (
        ReferenceNotFoundError,
        ResearchRepository,
    )

    diff = _thesis_diff(session, payload.instrument_id, payload.since)
    if not diff["new_evidence"]:
        raise AppError(
            "inbox.no_new_evidence", status_code=422,
            detail="no new evidence since the window — nothing to apply",
        ) from None

    old_thesis = session.scalars(
        select(ThesisORM).where(ThesisORM.instrument_id == payload.instrument_id)
    ).first()
    if old_thesis is None:
        raise AppError("thesis.not_found", status_code=404) from None

    # 新 Thesis 钉在旧 Thesis 的快照上（claims 引用完整性：claim 属于旧
    # 快照）—— 新证据留给下一研究周期的新快照（PIT 纪律）
    thesis = InvestmentThesis(
        instrument_id=payload.instrument_id,
        snapshot_id=old_thesis.snapshot_id,
        title=(old_thesis.title + " · 修订 " + datetime.now(timezone.utc).strftime("%m-%d %H:%M"))[:200],
        description=payload.revised_statement,
        supporting_claims=tuple(old_thesis.supporting_claims_json or []),
        opposing_claims=tuple(old_thesis.opposing_claims_json or []),
        confidence=old_thesis.confidence,
    )
    try:
        thesis_id = ResearchRepository(session).save_thesis(thesis)
    except ReferenceNotFoundError as exc:
        raise AppError("thesis.claims_not_found", status_code=422, detail=str(exc)) from None

    # artifact + provenance（generated_from 旧 Thesis）
    service = ArtifactService(session)
    new_artifact = service.register(
        artifact_type="thesis",
        domain_type="Thesis",
        domain_id=thesis_id,
        title=f"{old_thesis.title} · Thesis Diff 修订",
        instrument_ids=(payload.instrument_id,),
        created_by="thesis_diff",
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
        session, f"run_thesisdiff_{uuid4().hex[:8]}", "thesis_diff_applied",
        {"old_thesis": old_thesis.thesis_id, "new_thesis": thesis_id,
         "new_evidence": [e["evidence_id"] for e in diff["new_evidence"]]},
    )
    session.commit()
    return {"thesis_id": thesis_id, "diff": diff}
# [removed stray heredoc marker]