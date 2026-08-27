"""Research graph API (M17)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.market_data import resolve_instrument_id
from app.core.errors import AppError
from app.db import get_session
from app.services.research_graph import ResearchGraph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph(
    instrument: str = Query(min_length=4, max_length=64),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    graph = ResearchGraph(session).build_for_instrument(instrument_id)
    return {"instrument_id": instrument_id, **graph.to_dict()}


@router.get("/trace")
def trace_node(
    instrument: str = Query(min_length=4, max_length=64),
    node_id: str = Query(min_length=3, max_length=128),
    direction: str = Query(default="upstream", pattern="^(upstream|downstream)$"),
    max_depth: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)

    graph = ResearchGraph(session).build_for_instrument(instrument_id)
    if node_id not in graph.nodes:
        raise AppError("graph.node_not_found", status_code=404)
    return graph.trace(node_id, direction, max_depth=max_depth)
