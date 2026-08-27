"""Evidence API: real collection + traceable listing (M4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.evidence_collector import collect_capability_evidence
from app.storage.repository import EvidenceRepository

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _evidence_payload(record) -> dict:
    return {
        "evidence_id": record.evidence_id,
        "instrument_id": record.instrument_id,
        "evidence_type": record.evidence_type.value,
        "title": record.title,
        "summary": record.summary,
        "excerpt": record.excerpt,
        "source": record.source,
        "source_type": record.source_type,
        "source_url": record.source_url,
        "authority_level": record.authority_level.value,
        "fact_status": record.fact_status.value,
        "event_time": record.event_time.isoformat(),
        "available_time": record.available_time.isoformat(),
        "ingested_time": record.ingested_time.isoformat(),
        "revision_time": record.revision_time.isoformat(),
        "confidence": record.confidence,
        "content_hash": record.content_hash,
        "metadata": record.metadata,
    }


@router.post("/collect")
def collect_evidence(
    instrument: str = Query(min_length=4, max_length=64),
    capability: str = Query(default="market_data", max_length=64),
    session: Session = Depends(get_session),
) -> dict:
    """Run a real collection pass: source layer → evidence atoms + manifest."""
    from app.api.market_data import resolve_instrument_id

    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)

    outcome = collect_capability_evidence(
        instrument_id, capability, repo=EvidenceRepository(session)
    )
    manifest = outcome.manifest
    return {
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "instrument_id": manifest.instrument_id,
            "capability": manifest.capability,
            "final_status": manifest.final_status,
            "final_source": manifest.final_source,
            "from_cache": manifest.from_cache,
            "providers_attempted": list(manifest.providers_attempted),
            "evidence_ids": list(manifest.evidence_ids),
        },
        "created": len(outcome.created_ids),
        "deduped": outcome.deduped_count,
        "evidence": [_evidence_payload(e) for e in outcome.evidence],
    }


@router.get("")
def list_evidence(
    instrument_id: str = Query(min_length=3, max_length=32),
    evidence_type: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    repo = EvidenceRepository(session)
    records = repo.list_for_instrument(instrument_id, evidence_type=evidence_type)
    return {
        "instrument_id": instrument_id,
        "count": len(records),
        "results": [_evidence_payload(r) for r in records],
    }
