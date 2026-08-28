"""Monitor + materiality API (M15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.api.market_data import resolve_instrument_id
from app.services.monitor import MaterialityRepository, MonitorService

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/run")
def run_monitor(
    instrument: str = Query(min_length=4, max_length=64),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = resolve_instrument_id(instrument, session)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    decision = MonitorService(session).run_monitor(instrument_id)
    return {
        "decision": {
            "decision_id": decision.decision_id,
            "instrument_id": decision.instrument_id,
            "decision": decision.decision.value,
            "old_snapshot_id": decision.old_snapshot_id,
            "new_snapshot_id": decision.new_snapshot_id,
            "added_count": len(decision.added_evidence_ids),
            "removed_count": len(decision.removed_evidence_ids),
            "price_change_pct": decision.price_change_pct,
            "reasons": list(decision.reasons),
            "created_at": decision.created_at.isoformat(),
        }
    }


@router.get("/decisions")
def list_decisions(
    instrument_id: str = Query(min_length=3, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    decisions = MaterialityRepository(session).list_for(instrument_id)
    return {
        "count": len(decisions),
        "results": [
            {
                "decision_id": d.decision_id,
                "decision": d.decision.value,
                "old_snapshot_id": d.old_snapshot_id,
                "new_snapshot_id": d.new_snapshot_id,
                "price_change_pct": d.price_change_pct,
                "reasons": list(d.reasons),
                "created_at": d.created_at.isoformat(),
            }
            for d in decisions
        ],
    }
