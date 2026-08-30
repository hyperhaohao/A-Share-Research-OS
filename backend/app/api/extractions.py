"""Extraction API（R2，方案 §8.4/§8.5）.

POST /extractions        抽取提交 + 引用反查（accept/reject 均落档）
GET  /extractions        抽取列表（按 instrument 过滤）
POST /extractions/{id}/promote   accepted 抽取 → 正式 Claim（走既有 Claim domain）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.extraction import ExtractionRepository, ExtractionService
from app.core.errors import AppError
from app.db import get_session
from app.domain.extraction import ExtractionInput
from app.storage.orm import EvidenceORM

router = APIRouter(prefix="/extractions", tags=["extractions"])


class ExtractionIn(BaseModel):
    source_evidence_id: str = Field(min_length=6, max_length=32)
    statement: str = Field(min_length=4, max_length=500)
    support_span: str = Field(min_length=2, max_length=2000)
    fact_status: str = Field(default="analyst_inference", max_length=32)
    claim_type: str = Field(default="fundamental_fact", max_length=32)
    confidence_basis: str = Field(default="", max_length=300)
    extractor: str = Field(default="deterministic", max_length=40)
    prompt_version: str = Field(default="v0", max_length=24)
    instrument_id: str = Field(min_length=3, max_length=32)


@router.post("", status_code=201)
def submit_extraction(payload: ExtractionIn, session: Session = Depends(get_session)) -> dict:
    row = session.scalars(
        select(EvidenceORM).where(EvidenceORM.evidence_id == payload.source_evidence_id)
    ).first()
    if row is None:
        raise AppError("evidence.not_found", status_code=404)
    service = ExtractionService(session)
    record = service.submit(
        ExtractionInput(
            source_evidence_id=payload.source_evidence_id,
            statement=payload.statement,
            support_span=payload.support_span,
            fact_status=payload.fact_status,
            claim_type=payload.claim_type,
            confidence_basis=payload.confidence_basis,
            extractor=payload.extractor,
            prompt_version=payload.prompt_version,
        ),
        evidence=row,
        instrument_id=payload.instrument_id,
    )
    session.commit()
    return {"extraction": record}



@router.get("")
def list_extractions(
    instrument_id: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = ExtractionRepository(session).list(instrument_id=instrument_id, limit=limit)
    return {"count": len(results), "results": results}


@router.post("/{extraction_id}/promote", status_code=201)
def promote_extraction(
    extraction_id: str,
    snapshot_id: str = Query(min_length=6, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    service = ExtractionService(session)
    try:
        result = service.promote_to_claim(extraction_id, snapshot_id=snapshot_id)
    except KeyError as exc:
        raise AppError("extraction.not_found", status_code=404) from None
    except ValueError as exc:
        raise AppError("extraction.rejected_not_promotable", status_code=422, detail=str(exc)) from None
    session.commit()
    return result
