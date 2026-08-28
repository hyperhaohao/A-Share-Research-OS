"""Artifact / lineage / run-event replay / handoff APIs (V2 Phase A, §62)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.artifacts import ArtifactService
from app.application.handoff import HandoffService, ResearchContext
from app.application.run_events import list_run_events
from app.core.errors import AppError
from app.db import get_session

router = APIRouter(tags=["artifacts"])


@router.get("/artifacts")
def list_artifacts(
    query: str = Query(default="", max_length=128),
    artifact_type: str | None = Query(default=None, max_length=32),
    instrument_id: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    results = ArtifactService(session).search(
        query, artifact_type=artifact_type, instrument_id=instrument_id, limit=limit
    )
    return {"count": len(results), "results": results}


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, session: Session = Depends(get_session)) -> dict:
    artifact = ArtifactService(session).get(artifact_id)
    if artifact is None:
        raise AppError("artifact.not_found", status_code=404)
    return {"artifact": artifact}


@router.get("/artifacts/{artifact_id}/upstream")
def artifact_upstream(
    artifact_id: str,
    max_depth: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    service = ArtifactService(session)
    if service.get(artifact_id) is None:
        raise AppError("artifact.not_found", status_code=404)
    return {"artifact_id": artifact_id, "results": service.neighbors(artifact_id, "upstream", max_depth=max_depth)}


@router.get("/artifacts/{artifact_id}/downstream")
def artifact_downstream(
    artifact_id: str,
    max_depth: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    service = ArtifactService(session)
    if service.get(artifact_id) is None:
        raise AppError("artifact.not_found", status_code=404)
    return {"artifact_id": artifact_id, "results": service.neighbors(artifact_id, "downstream", max_depth=max_depth)}


@router.get("/artifacts/{artifact_id}/lineage")
def artifact_lineage(
    artifact_id: str,
    max_depth: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    service = ArtifactService(session)
    if service.get(artifact_id) is None:
        raise AppError("artifact.not_found", status_code=404)
    return service.lineage(artifact_id, max_depth=max_depth)


@router.get("/research-runs/{run_id}/events")
def research_run_events(run_id: str, session: Session = Depends(get_session)) -> dict:
    """Full replay of one run's persisted events (chronological)."""
    results = list_run_events(session, run_id)
    if not results:
        raise AppError("run.events_not_found", status_code=404)
    return {"run_id": run_id, "count": len(results), "results": results}


# -- handoffs ------------------------------------------------------------------


class HandoffIn(BaseModel):
    source_module: str = Field(min_length=2, max_length=32)
    target_module: str = Field(min_length=2, max_length=32)
    action: str = Field(min_length=2, max_length=64)
    artifact_ids: list[str] = Field(min_length=1, max_length=20)
    context: ResearchContext = Field(default_factory=ResearchContext)
    message: str | None = Field(default=None, max_length=500)


@router.post("/handoffs", status_code=201)
def create_handoff(payload: HandoffIn, session: Session = Depends(get_session)) -> dict:
    service = HandoffService(session)
    try:
        envelope = service.record(
            source_module=payload.source_module,
            target_module=payload.target_module,
            action=payload.action,
            artifact_ids=tuple(payload.artifact_ids),
            context=payload.context,
            message=payload.message,
        )
    except ValueError as exc:
        raise AppError("handoff.invalid", status_code=422, detail=str(exc)) from None
    return {"handoff": envelope}


@router.get("/handoffs")
def list_handoffs(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = HandoffService(session).list_recent(limit=limit)
    return {"count": len(results), "results": results}
