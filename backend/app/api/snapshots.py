"""Snapshot + research-run API (M5)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.evidence import utc_now
from app.domain.snapshot import ResearchRunType
from app.api.market_data import resolve_instrument_id
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import ResearchRunRepository, SnapshotRepository
from app.domain.code_norm import InvalidInstrumentCode, normalize_code

router = APIRouter(tags=["research"])


def _parse_as_of(raw: str | None) -> datetime:
    if not raw:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise AppError("common.validation_error", status_code=422, detail="bad as_of") from None
    if parsed.tzinfo is None:
        raise AppError("common.validation_error", status_code=422, detail="as_of needs offset")
    return parsed


def _resolve_or_404(raw: str) -> str:
    """Accept instrument_id directly or any resolvable form."""
    if ":" in raw:
        return raw.upper()
    try:
        code, exchange, _board = normalize_code(raw)
    except InvalidInstrumentCode:
        instrument_id = resolve_instrument_id(raw)
        if instrument_id is None:
            raise AppError("instrument.not_found", status_code=404) from None
        return instrument_id
    return f"{exchange.value}:{code}"


def _snapshot_payload(snapshot) -> dict:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "content_hash": snapshot.content_hash,
        "instrument_id": snapshot.instrument_id,
        "as_of": snapshot.as_of.isoformat(),
        "created_at": snapshot.created_at.isoformat(),
        "evidence_count": len(snapshot.items),
        "evidence_ids": list(snapshot.evidence_ids),
    }


@router.post("/snapshots")
def build_snapshot(
    instrument: str = Query(min_length=4, max_length=64),
    as_of: str | None = Query(default=None, description="ISO datetime with offset"),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = _resolve_or_404(instrument)
    snapshot = SnapshotRepository(session).build(
        instrument_id, _parse_as_of(as_of), evidence_repo=EvidenceRepository(session)
    )
    return {"snapshot": _snapshot_payload(snapshot)}


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str, session: Session = Depends(get_session)) -> dict:
    snapshot = SnapshotRepository(session).get(snapshot_id)
    if snapshot is None:
        raise AppError("snapshot.not_found", status_code=404)
    return {"snapshot": _snapshot_payload(snapshot)}


@router.post("/research-runs")
def create_research_run(
    instrument: str = Query(min_length=4, max_length=64),
    as_of: str | None = Query(default=None),
    run_type: ResearchRunType = Query(default=ResearchRunType.FULL),
    session: Session = Depends(get_session),
) -> dict:
    instrument_id = _resolve_or_404(instrument)
    as_of_dt = _parse_as_of(as_of)

    snapshot_repo = SnapshotRepository(session)
    snapshot = snapshot_repo.build(
        instrument_id, as_of_dt, evidence_repo=EvidenceRepository(session)
    )
    from uuid import uuid4

    run = ResearchRunRepository(session).create(
        run_id=f"run_{uuid4().hex[:12]}",
        instrument_id=instrument_id,
        as_of=as_of_dt,
        run_type=run_type,
        snapshot_id=snapshot.snapshot_id,
    )
    return {
        "run": {
            "run_id": run.run_id,
            "instrument_id": run.instrument_id,
            "as_of": run.as_of.isoformat(),
            "run_type": run.run_type.value,
            "status": run.status.value,
            "snapshot_id": run.snapshot_id,
        },
        "snapshot": _snapshot_payload(snapshot),
    }
