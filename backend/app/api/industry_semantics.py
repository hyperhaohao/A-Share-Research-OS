"""Industry Semantic API（R3，方案 §9/§24）.

POST /industry-semantics/{type}         创建/更新（append-only 新版本）
GET  /industry-semantics/{type}         最新版本列表（可按 industry/instrument 过滤）
GET  /industry-semantics/{type}/{key}   单对象全版本历史
GET  /industry-semantics/narratives/{key}/temperature   可复算温度
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.industry_semantic import IndustrySemanticService
from app.core.errors import AppError
from app.db import get_session

router = APIRouter(prefix="/industry-semantics", tags=["industry-semantics"])

_TYPES = ("driver", "transmission", "narrative", "position")


class ClaimIn(BaseModel):
    evidence_id: str = Field(min_length=6, max_length=32)
    support_span: str = Field(min_length=2, max_length=2000)
    observed_at: str | None = Field(default=None, max_length=40)


class SemanticUpsertIn(BaseModel):
    object_key: str = Field(min_length=2, max_length=48)
    industry_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=2, max_length=200)
    mechanism: str = Field(default="", max_length=2000)
    status: str = Field(min_length=2, max_length=24)
    direction: str | None = Field(default=None, max_length=16)
    instrument_id: str | None = Field(default=None, max_length=32)
    as_of: str | None = Field(default=None, max_length=40)
    evidence_claims: list[ClaimIn] = Field(min_length=1, max_length=12)
    axis: str | None = Field(default=None, max_length=32)
    position: str | None = Field(default=None, max_length=32)
    reason: str | None = Field(default=None, max_length=500)
    # G2：图谱链接 + 反对证据（§G2.1/§G2.2）
    chain_id: str | None = Field(default=None, max_length=32)
    segment_id: str | None = Field(default=None, max_length=32)
    edge_id: str | None = Field(default=None, max_length=32)
    contrary_evidence_claims: list[ClaimIn] = Field(default_factory=list, max_length=12)


def _svc(session: Session) -> IndustrySemanticService:
    return IndustrySemanticService(session)


@router.post("/{object_type}", status_code=201)
def upsert_semantic(object_type: str, payload: SemanticUpsertIn, session: Session = Depends(get_session)) -> dict:
    if object_type not in _TYPES:
        raise AppError("industry_semantic.unknown_type", status_code=404)
    as_of = None
    if payload.as_of:
        try:
            as_of = datetime.fromisoformat(payload.as_of.replace("Z", "+00:00"))
        except ValueError:
            raise AppError("industry_semantic.bad_as_of", status_code=422) from None
    try:
        extra = None
        if object_type == "position":
            extra = {"axis": payload.axis, "position": payload.position, "reason": payload.reason}
        record = _svc(session).upsert(
            object_type,
            object_key=payload.object_key.strip(),
            industry_id=payload.industry_id.strip(),
            title=payload.title,
            mechanism=payload.mechanism,
            status=payload.status,
            direction=payload.direction,
            evidence_claims=[c.model_dump() for c in payload.evidence_claims],
            instrument_id=payload.instrument_id,
            as_of=as_of,
            extra_payload=extra,
            chain_id=payload.chain_id,
            segment_id=payload.segment_id,
            edge_id=payload.edge_id,
            contrary_evidence_claims=[c.model_dump() for c in payload.contrary_evidence_claims],
        )
    except ValueError as exc:
        raise AppError("industry_semantic.citation_failed", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"object": record}


@router.get("/{object_type}")
def list_semantics(
    object_type: str,
    industry_id: str | None = Query(default=None, max_length=64),
    instrument_id: str | None = Query(default=None, max_length=32),
    as_of: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    if object_type not in _TYPES:
        raise AppError("industry_semantic.unknown_type", status_code=404)
    results = _svc(session).latest_by_type(
        object_type, industry_id=industry_id, instrument_id=instrument_id, limit=limit
    )
    as_of_dt = None
    if as_of:
        try:
            as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError:
            raise AppError("industry_semantic.bad_as_of", status_code=422) from None
    if as_of_dt is not None:
        # PIT 重放：as_of 之后创建的版本不可见（纯读，不触发采集）
        results = [r for r in results
                   if (r.get("created_at") or "") <= as_of_dt.isoformat()]
    return {"count": len(results), "results": results,
            "as_of": as_of_dt.isoformat() if as_of_dt else None}


@router.get("/{object_type}/{object_key}")
def get_semantic(object_type: str, object_key: str, session: Session = Depends(get_session)) -> dict:
    versions = _svc(session).get_versions(object_type, object_key)
    if not versions:
        raise AppError("industry_semantic.not_found", status_code=404)
    return {"versions": versions, "latest": versions[-1]}


@router.get("/narrative/{object_key}/temperature")
def narrative_temperature(object_key: str, session: Session = Depends(get_session)) -> dict:
    return _svc(session).narrative_temperature(object_key)
