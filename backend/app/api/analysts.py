"""Analyst API (M8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.market_analyst import MarketAnalyst
from app.storage.agent_repo import AgentRepository, ResearchRequestStatus

router = APIRouter(prefix="/analysts", tags=["analysts"])


def _brief_payload(brief) -> dict:
    return {
        "brief_id": brief.brief_id,
        "analyst_type": brief.analyst_type.value,
        "instrument_id": brief.instrument_id,
        "snapshot_id": brief.snapshot_id,
        "conclusions": list(brief.conclusions),
        "claim_refs": list(brief.claim_refs),
        "evidence_refs": list(brief.evidence_refs),
        "missing_data": [m.model_dump(mode="json") for m in brief.missing_data],
        "confidence": brief.confidence,
        "key_questions": list(brief.key_questions),
        "risks": list(brief.risks),
        "created_at": brief.created_at.isoformat(),
    }


@router.post("/market/run")
def run_market_analyst(
    snapshot_id: str = Query(min_length=8, max_length=32),
    run_id: str | None = Query(default=None, max_length=64),
    collect_missing: bool = Query(default=True),
    session: Session = Depends(get_session),
) -> dict:
    try:
        outcome = MarketAnalyst().analyze(
            snapshot_id, session=session, run_id=run_id, collect_missing=collect_missing
        )
    except KeyError:
        raise AppError("snapshot.not_found", status_code=404) from None
    return {
        "brief": _brief_payload(outcome.brief),
        "created_claim_ids": list(outcome.created_claim_ids),
        "open_request_ids": list(outcome.open_requests),
    }


@router.get("/briefs")
def list_briefs(
    snapshot_id: str = Query(min_length=8, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    briefs = AgentRepository(session).list_briefs(snapshot_id)
    return {"count": len(briefs), "results": [_brief_payload(b) for b in briefs]}


@router.get("/research-requests")
def list_research_requests(
    instrument_id: str = Query(min_length=3, max_length=32),
    status: str | None = Query(default=None, max_length=16),
    session: Session = Depends(get_session),
) -> dict:
    status_enum = ResearchRequestStatus(status) if status else None
    requests = AgentRepository(session).list_requests(instrument_id, status=status_enum)
    return {
        "count": len(requests),
        "results": [
            {
                "request_id": r.request_id,
                "instrument_id": r.instrument_id,
                "capability": r.capability,
                "reason": r.reason,
                "requested_by": r.requested_by,
                "snapshot_id": r.snapshot_id,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in requests
        ],
    }
