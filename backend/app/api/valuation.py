"""Valuation API (M10): deterministic computation, persisted results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.domain.valuation import ValuationMethod
from app.storage.valuation_repo import ValuationIn, ValuationRepository, compute

router = APIRouter(prefix="/valuations", tags=["valuation"])

@router.post("/compute", status_code=201)
def compute_valuation(payload: ValuationIn, session: Session = Depends(get_session)) -> dict:
    """Run a deterministic valuation; missing inputs persist as explicit gaps."""
    result = compute(payload.method, payload.inputs)
    repo = ValuationRepository(session)
    valuation_id = repo.save(result, payload)
    _ = valuation_id
    listed = repo.list_for(payload.instrument_id, snapshot_id=payload.snapshot_id)
    saved = next(
        v
        for v in listed
        if v["method"] == payload.method.value
        and v["inputs"] == result.inputs_used
        and v["computable"] == result.computable
    )
    return {"valuation": saved}


@router.get("")
def list_valuations(
    instrument_id: str = Query(min_length=3, max_length=32),
    snapshot_id: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    rows = ValuationRepository(session).list_for(instrument_id, snapshot_id=snapshot_id)
    return {"count": len(rows), "results": rows}
