"""Quality gate API (M7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.quality import ReportGateInput
from app.services.quality_service import QualityService

router = APIRouter(prefix="/quality-gates", tags=["quality"])


@router.post("/run")
def run_gates(
    snapshot_id: str = Query(min_length=8, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    service = QualityService(session)
    try:
        results = service.run_evidence_and_analysis_gates(snapshot_id)
    except KeyError:
        raise AppError("snapshot.not_found", status_code=404) from None
    return {
        "snapshot_id": snapshot_id,
        "results": [
            {
                "gate": r.gate.value,
                "status": r.status.value,
                "blocked": r.blocked,
                "findings": [f.model_dump(mode="json") for f in r.findings],
            }
            for r in results
        ],
    }


@router.post("/final-report")
def run_final_report_gate(
    report: ReportGateInput,
    session: Session = Depends(get_session),
) -> dict:
    _ = session  # symmetric dependency shape; the gate itself is pure
    result = QualityService(session).run_final_report_gate(report)
    return {
        "gate": result.gate.value,
        "status": result.status.value,
        "blocked": result.blocked,
        "findings": [f.model_dump(mode="json") for f in result.findings],
    }


@router.get("")
def gate_history(
    snapshot_id: str = Query(min_length=8, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    history = QualityService(session).history(snapshot_id)
    return {"count": len(history), "results": history}
