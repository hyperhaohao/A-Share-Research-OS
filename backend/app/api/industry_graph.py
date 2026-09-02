"""Industry Graph API（G1，观澜语义迁移任务书 §G1）.

真实产业链图谱：与行业分类分路由（/industry-graph/* vs /views/industry/*）。
GET 均为纯读（as_of 可重放，不触发采集）；写操作显式 Command。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session

router = APIRouter(prefix="/industry-graph", tags=["industry-graph"])


class ChainIn(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=2000)


class SegmentIn(BaseModel):
    chain_id: str = Field(min_length=6, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    stage_order: int = Field(default=0, ge=0, le=100)
    description: str = Field(default="", max_length=2000)


class EdgeIn(BaseModel):
    chain_id: str = Field(min_length=6, max_length=32)
    source_segment_id: str = Field(min_length=6, max_length=32)
    target_segment_id: str = Field(min_length=6, max_length=32)
    relation_type: str = Field(min_length=3, max_length=32)
    input_product_ids: list[str] = Field(default_factory=list, max_length=10)
    output_product_ids: list[str] = Field(default_factory=list, max_length=10)
    transmission_metric: str = Field(default="", max_length=200)
    direction: str = Field(default="positive", max_length=16)
    lag_min_days: int = Field(default=0, ge=0, le=3650)
    lag_max_days: int = Field(default=0, ge=0, le=3650)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    snapshot_id: str | None = Field(default=None, max_length=32)
    as_of: str | None = Field(default=None, max_length=40)


class EdgeEvidenceIn(BaseModel):
    evidence_id: str = Field(min_length=6, max_length=32)
    stance: str = Field(default="support", max_length=16)
    as_of: str | None = Field(default=None, max_length=40)


class PositionIn(BaseModel):
    instrument_id: str = Field(min_length=4, max_length=32)
    chain_id: str = Field(min_length=6, max_length=32)
    segment_id: str = Field(min_length=6, max_length=32)
    role: str = Field(min_length=3, max_length=24)
    revenue_exposure_pct: float | None = Field(default=None, ge=0, le=100)
    profit_exposure_pct: float | None = Field(default=None, ge=0, le=100)
    capacity_note: str = Field(default="", max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    snapshot_id: str | None = Field(default=None, max_length=32)


def _parse_as_of(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AppError("industry_graph.bad_as_of", status_code=422) from None


@router.get("/chains")
def list_chains(session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    results = IndustryGraphService(session).list_chains()
    return {"count": len(results), "results": results}


@router.post("/chains", status_code=201)
def create_chain(payload: ChainIn, session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).create_chain(payload.name, payload.description)
    session.commit()
    return {"chain": out}


@router.get("/chains/{chain_id}/graph")
def chain_graph(
    chain_id: str,
    as_of: str | None = Query(default=None, max_length=40),
    session: Session = Depends(get_session),
) -> dict:
    """链图谱（as_of 可重放：未来结构/证据不进入历史状态；纯读不采集）。"""
    from app.services.industry_graph_service import IndustryGraphService

    return IndustryGraphService(session).chain_graph(chain_id, as_of=_parse_as_of(as_of))


@router.post("/segments", status_code=201)
def create_segment(payload: SegmentIn, session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).create_segment(
        payload.chain_id, payload.name, payload.stage_order, payload.description
    )
    session.commit()
    return {"segment": out}


@router.post("/edges", status_code=201)
def create_edge(payload: EdgeIn, session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).create_edge(
        chain_id=payload.chain_id,
        source_segment_id=payload.source_segment_id,
        target_segment_id=payload.target_segment_id,
        relation_type=payload.relation_type,
        input_product_ids=payload.input_product_ids,
        output_product_ids=payload.output_product_ids,
        transmission_metric=payload.transmission_metric,
        direction=payload.direction,
        lag_min_days=payload.lag_min_days,
        lag_max_days=payload.lag_max_days,
        evidence_ids=payload.evidence_ids,
        snapshot_id=payload.snapshot_id,
        as_of=_parse_as_of(payload.as_of),
    )
    session.commit()
    return {"edge": out}


@router.get("/edges/{edge_id}")
def get_edge(edge_id: str, session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    return {"edge": IndustryGraphService(session).get_edge(edge_id)}


@router.post("/edges/{edge_id}/evidence", status_code=201)
def attach_edge_evidence(
    edge_id: str,
    payload: EdgeEvidenceIn,
    session: Session = Depends(get_session),
) -> dict:
    """边证据挂载（Ownership Gate：存在 + PIT + 产业归属）。"""
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).attach_edge_evidence(
        edge_id, payload.evidence_id, stance=payload.stance,
        as_of=_parse_as_of(payload.as_of),
    )
    session.commit()
    return out


@router.delete("/edges/{edge_id}/evidence/{evidence_id}")
def remove_edge_evidence(
    edge_id: str,
    evidence_id: str,
    stance: str = Query(default="support", max_length=16),
    session: Session = Depends(get_session),
) -> dict:
    """删除边证据 → 自动重算置信（关键证据缺失自动降级，§G1 DoD）。"""
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).remove_edge_evidence(
        edge_id, evidence_id, stance=stance
    )
    session.commit()
    return {"edge": out}


@router.post("/positions", status_code=201)
def create_position(payload: PositionIn, session: Session = Depends(get_session)) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    out = IndustryGraphService(session).create_position(
        instrument_id=payload.instrument_id,
        chain_id=payload.chain_id,
        segment_id=payload.segment_id,
        role=payload.role,
        revenue_exposure_pct=payload.revenue_exposure_pct,
        profit_exposure_pct=payload.profit_exposure_pct,
        capacity_note=payload.capacity_note,
        evidence_ids=payload.evidence_ids,
        snapshot_id=payload.snapshot_id,
    )
    session.commit()
    return {"position": out}


@router.get("/instruments/{instrument_id}/positions")
def instrument_positions(
    instrument_id: str,
    as_of: str | None = Query(default=None, max_length=40),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.industry_graph_service import IndustryGraphService

    results = IndustryGraphService(session).company_positions(
        instrument_id, as_of=_parse_as_of(as_of)
    )
    return {"count": len(results), "results": results}


@router.get("/instruments/{instrument_id}/peers")
def instrument_peers(
    instrument_id: str,
    chain_id: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    """Peer = 同链同环节共位（明确关系；非关键词共现）。"""
    from app.services.industry_graph_service import IndustryGraphService

    results = IndustryGraphService(session).peer_companies(
        instrument_id, chain_id=chain_id
    )
    return {"count": len(results), "results": results}


class SeedIn(BaseModel):
    confirm: bool = Field(default=False)


@router.post("/seed/rare-earth")
def seed_rare_earth(payload: SeedIn, session: Session = Depends(get_session)) -> dict:
    """稀土 Golden 链种子（显式 Command；幂等；不伪造证据）。"""
    if not payload.confirm:
        raise AppError(
            "industry_graph.seed_needs_confirm", status_code=422,
            detail="POST {\"confirm\": true} to run the deterministic seed",
        ) from None
    from app.services.industry_graph_service import seed_rare_earth_chain

    out = seed_rare_earth_chain(session)
    session.commit()
    return out
