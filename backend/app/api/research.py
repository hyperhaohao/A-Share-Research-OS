"""Research domain API: corporate events, claims, theses (M6)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.research import (
    Claim,
    ClaimStatus,
    ClaimType,
    CorporateEvent,
    EventType,
    InvestmentThesis,
    ThesisStatus,
)
from app.storage.research_repo import ReferenceNotFoundError, ResearchRepository

router = APIRouter(tags=["research"])


class ClaimIn(BaseModel):
    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)
    statement: str = Field(min_length=1, max_length=2000)
    claim_type: ClaimType
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    opposing_evidence_refs: list[str] = Field(default_factory=list)
    fact_status: str
    confidence: float = Field(ge=0.0, le=1.0)


class ThesisIn(BaseModel):
    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4000)
    supporting_claims: list[str] = Field(default_factory=list)
    opposing_claims: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    trigger_conditions: list[str] = Field(default_factory=list)
    invalidate_conditions: list[str] = Field(default_factory=list)


class EventIn(BaseModel):
    instrument_id: str = Field(min_length=3, max_length=32)
    event_type: EventType
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4000)
    occurred_at: datetime
    announced_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)


def _claim_payload(claim: Claim) -> dict:
    return {
        "claim_id": claim.claim_id,
        "instrument_id": claim.instrument_id,
        "snapshot_id": claim.snapshot_id,
        "statement": claim.statement,
        "claim_type": claim.claim_type.value,
        "supporting_evidence_refs": list(claim.supporting_evidence_refs),
        "opposing_evidence_refs": list(claim.opposing_evidence_refs),
        "fact_status": claim.fact_status.value,
        "confidence": claim.confidence,
        "status": claim.status.value,
        "created_at": claim.created_at.isoformat(),
    }


def _thesis_payload(thesis: InvestmentThesis) -> dict:
    return {
        "thesis_id": thesis.thesis_id,
        "instrument_id": thesis.instrument_id,
        "snapshot_id": thesis.snapshot_id,
        "title": thesis.title,
        "description": thesis.description,
        "supporting_claims": list(thesis.supporting_claims),
        "opposing_claims": list(thesis.opposing_claims),
        "confidence": thesis.confidence,
        "catalysts": list(thesis.catalysts),
        "risks": list(thesis.risks),
        "trigger_conditions": list(thesis.trigger_conditions),
        "invalidate_conditions": list(thesis.invalidate_conditions),
        "status": thesis.status.value,
        "created_at": thesis.created_at.isoformat(),
    }


def _event_payload(event: CorporateEvent) -> dict:
    return {
        "event_id": event.event_id,
        "instrument_id": event.instrument_id,
        "event_type": event.event_type.value,
        "title": event.title,
        "description": event.description,
        "occurred_at": event.occurred_at.isoformat(),
        "announced_at": event.announced_at.isoformat(),
        "evidence_refs": list(event.evidence_refs),
    }


@router.post("/claims", status_code=201)
def create_claim(payload: ClaimIn, session: Session = Depends(get_session)) -> dict:
    repo = ResearchRepository(session)
    claim = Claim(
        instrument_id=payload.instrument_id,
        snapshot_id=payload.snapshot_id,
        statement=payload.statement,
        claim_type=payload.claim_type,
        supporting_evidence_refs=tuple(payload.supporting_evidence_refs),
        opposing_evidence_refs=tuple(payload.opposing_evidence_refs),
        fact_status=payload.fact_status,  # type: ignore[arg-type]
        confidence=payload.confidence,
        status=ClaimStatus.PROPOSED,
    )
    try:
        claim_id = repo.save_claim(claim)
    except ReferenceNotFoundError as exc:
        raise AppError("claim.evidence_not_found", status_code=422, detail=str(exc)) from None
    saved = repo.get_claim(claim_id)
    assert saved is not None
    return {"claim": _claim_payload(saved)}


@router.get("/claims")
def list_claims(
    instrument_id: str = Query(min_length=3, max_length=32),
    snapshot_id: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    claims = ResearchRepository(session).list_claims(
        instrument_id, snapshot_id=snapshot_id
    )
    return {"count": len(claims), "results": [_claim_payload(c) for c in claims]}


@router.post("/theses", status_code=201)
def create_thesis(payload: ThesisIn, session: Session = Depends(get_session)) -> dict:
    repo = ResearchRepository(session)
    thesis = InvestmentThesis(
        instrument_id=payload.instrument_id,
        snapshot_id=payload.snapshot_id,
        title=payload.title,
        description=payload.description,
        supporting_claims=tuple(payload.supporting_claims),
        opposing_claims=tuple(payload.opposing_claims),
        confidence=payload.confidence,
        catalysts=tuple(payload.catalysts),
        risks=tuple(payload.risks),
        trigger_conditions=tuple(payload.trigger_conditions),
        invalidate_conditions=tuple(payload.invalidate_conditions),
        status=ThesisStatus.ACTIVE,
    )
    try:
        thesis_id = repo.save_thesis(thesis)
    except ReferenceNotFoundError as exc:
        raise AppError("thesis.claims_not_found", status_code=422, detail=str(exc)) from None
    saved = next(
        t for t in repo.list_theses(payload.instrument_id) if t.thesis_id == thesis_id
    )
    return {"thesis": _thesis_payload(saved)}


@router.get("/theses")
def list_theses(
    instrument_id: str = Query(min_length=3, max_length=32),
    snapshot_id: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    theses = ResearchRepository(session).list_theses(
        instrument_id, snapshot_id=snapshot_id
    )
    return {"count": len(theses), "results": [_thesis_payload(t) for t in theses]}


@router.post("/corporate-events", status_code=201)
def create_event(payload: EventIn, session: Session = Depends(get_session)) -> dict:
    repo = ResearchRepository(session)
    if payload.announced_at < payload.occurred_at:
        raise AppError("event.bad_times", status_code=422)
    event = CorporateEvent(
        instrument_id=payload.instrument_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        occurred_at=payload.occurred_at,
        announced_at=payload.announced_at,
        evidence_refs=tuple(payload.evidence_refs),
    )
    try:
        event_id = repo.save_event(event)
    except ReferenceNotFoundError as exc:
        raise AppError("event.evidence_not_found", status_code=422, detail=str(exc)) from None
    saved = next(
        e for e in repo.list_events(payload.instrument_id) if e.event_id == event_id
    )
    return {"event": _event_payload(saved)}


@router.get("/corporate-events")
def list_events(
    instrument_id: str = Query(min_length=3, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    events = ResearchRepository(session).list_events(instrument_id)
    return {"count": len(events), "results": [_event_payload(e) for e in events]}
