"""Cost accounting API (任务书 §70).

Per-run cost = LLM calls (zero in the deterministic pipeline) + source
calls (from manifests) + wall-clock duration. Dashboard-aggregatable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.storage.manifest_repo import _ensure_utc
from app.storage.orm import ResearchRunORM, SourceManifestORM

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("")
def cost_report(
    instrument_id: str | None = Query(default=None, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    runs_stmt = select(ResearchRunORM)
    if instrument_id:
        runs_stmt = runs_stmt.where(ResearchRunORM.instrument_id == instrument_id)
    runs = session.scalars(runs_stmt.order_by(ResearchRunORM.started_at.desc()).limit(100)).all()

    manifest_stmt = select(SourceManifestORM)
    if instrument_id:
        manifest_stmt = manifest_stmt.where(SourceManifestORM.instrument_id == instrument_id)
    manifests = session.scalars(manifest_stmt.limit(500)).all()

    results = []
    total_llm_calls = 0
    total_source_calls = 0
    total_duration_ms = 0
    for run in runs:
        started = _ensure_utc(run.started_at)
        finished = _ensure_utc(run.finished_at)
        duration_ms = (
            int((finished - started).total_seconds() * 1000)
            if started and finished
            else None
        )
        source_calls = sum(
            1
            for m in manifests
            if m.instrument_id == run.instrument_id and m.created_at == run.started_at
        )
        llm_calls = 0  # deterministic pipeline; LLM call accounting lands with M11+ LLM analysts
        total_llm_calls += llm_calls
        total_source_calls += source_calls
        total_duration_ms += duration_ms or 0
        results.append(
            {
                "run_id": run.run_id,
                "instrument_id": run.instrument_id,
                "run_type": run.run_type,
                "status": run.status,
                "llm_calls": llm_calls,
                "source_calls": source_calls,
                "duration_ms": duration_ms,
            }
        )

    return {
        "runs": results,
        "totals": {
            "runs": len(results),
            "llm_calls": total_llm_calls,
            "source_calls": total_source_calls,
            "duration_ms": total_duration_ms,
        },
    }
