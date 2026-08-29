"""Predictions API (M19): immutable creation + one-shot validation."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.prediction import Direction, Horizon, PredictionRecord
from app.api.market_data import resolve_instrument_id
from app.services.validation_service import PredictionNotMatured, ValidationService
from app.storage.prediction_repo import (
    PredictionORM,
    PredictionRepository,
    ValidationRecord,
    ValidationRepository,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionIn(BaseModel):
    instrument: str = Field(min_length=4, max_length=64)
    research_run_id: str | None = None
    as_of: datetime
    horizon: Horizon
    benchmark: str = "CSI300"
    expected_direction: Direction
    expected_return_min: float
    expected_return_max: float
    expected_excess_return_min: float | None = None
    expected_excess_return_max: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_thesis_id: str | None = None
    trigger_conditions: list[str] = Field(default_factory=list)
    invalidate_conditions: list[str] = Field(default_factory=list)


def _register_prediction(session: Session, prediction: PredictionRecord) -> str:
    """Artifact registration (V2 §85): one prediction = one artifact."""
    from app.application.artifacts import ArtifactService

    name = prediction.instrument_id
    try:
        from app.services.instrument_service import InstrumentService

        profile = InstrumentService(session).get_profile(
            prediction.instrument_id, allow_remote=False
        )
        if profile:
            name = f"{profile.name} · {profile.code}"
    except Exception:  # noqa: BLE001 — identity must not block registration
        pass
    return ArtifactService(session).register(
        artifact_type="prediction",
        domain_type="PredictionRecord",
        domain_id=prediction.prediction_id,
        title=f"{name} · {prediction.horizon.value} 预测",
        summary=f"{prediction.expected_direction.value} "
                f"[{prediction.expected_return_range[0]}, {prediction.expected_return_range[1]}]%",
        instrument_ids=(prediction.instrument_id,),
        as_of_time=prediction.as_of,
        created_by="api",
        route="/predictions",
    )


def _payload(p: PredictionRecord, validation: ValidationRecord | None = None) -> dict:
    data = {
        "prediction_id": p.prediction_id,
        "instrument_id": p.instrument_id,
        "research_run_id": p.research_run_id,
        "as_of": p.as_of.isoformat(),
        "due_at": p.due_at.isoformat(),
        "horizon": p.horizon.value,
        "benchmark": p.benchmark,
        "expected_direction": p.expected_direction.value,
        "expected_return_range": list(p.expected_return_range),
        "expected_excess_return_range": (
            list(p.expected_excess_return_range) if p.expected_excess_return_range else None
        ),
        "confidence": p.confidence,
        "supporting_thesis_id": p.supporting_thesis_id,
        "trigger_conditions": list(p.trigger_conditions),
        "invalidate_conditions": list(p.invalidate_conditions),
        "created_at": p.created_at.isoformat(),
    }
    if validation is not None:
        data["validation"] = {
            "validation_id": validation.validation_id,
            "instrument_return_pct": validation.instrument_return_pct,
            "benchmark_return_pct": validation.benchmark_return_pct,
            "excess_return_pct": validation.excess_return_pct,
            "direction_correct": validation.direction_correct,
            "range_hit": validation.range_hit,
            "validated_at": validation.validated_at.isoformat(),
        }
    return data


@router.post("", status_code=201)
def create_prediction(payload: PredictionIn, session: Session = Depends(get_session)) -> dict:
    instrument_id = resolve_instrument_id(payload.instrument, session)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)
    excess = None
    if payload.expected_excess_return_min is not None and payload.expected_excess_return_max is not None:
        excess = (payload.expected_excess_return_min, payload.expected_excess_return_max)
    prediction = PredictionRecord(
        instrument_id=instrument_id,
        research_run_id=payload.research_run_id,
        as_of=payload.as_of,
        horizon=payload.horizon,
        benchmark=payload.benchmark,
        expected_direction=payload.expected_direction,
        expected_return_range=(payload.expected_return_min, payload.expected_return_max),
        expected_excess_return_range=excess,
        confidence=payload.confidence,
        supporting_thesis_id=payload.supporting_thesis_id,
        trigger_conditions=tuple(payload.trigger_conditions),
        invalidate_conditions=tuple(payload.invalidate_conditions),
    )
    prediction_id = PredictionRepository(session).save(prediction)
    saved = PredictionRepository(session).get(prediction_id)
    assert saved is not None
    _register_prediction(session, saved)
    return {"prediction": _payload(saved)}


class PredictionFromReportIn(BaseModel):
    report_id: str = Field(min_length=6, max_length=32)
    horizon: Horizon


@router.post("/from-report", status_code=201)
def create_prediction_from_report(
    payload: PredictionFromReportIn, session: Session = Depends(get_session)
) -> dict:
    """PredictionBuilder: derive a prediction from one report's research state.

    Refuses explicitly (422 prediction.underivable) when the research state
    lacks a thesis, a visible quote, or a computable valuation — ranges are
    never invented."""
    from app.services.prediction_builder import PredictionBuilder, PredictionNotDerivable

    try:
        prediction = PredictionBuilder(session).build_and_save(
            payload.report_id, payload.horizon
        )
    except KeyError:
        raise AppError("report.not_found", status_code=404) from None
    except PredictionNotDerivable as exc:
        raise AppError(
            "prediction.underivable", status_code=422, detail=str(exc)
        ) from None

    from app.application.artifacts import ArtifactService, RelationType

    service = ArtifactService(session)
    prediction_artifact = _register_prediction(session, prediction)
    # Reuse the pipeline-registered report artifact when it exists — a fresh
    # registration here would overwrite its business title with a generic one.
    report_artifact = service.by_domain("Report", payload.report_id)
    if report_artifact is None:
        report_artifact_id = service.register(
            artifact_type="report",
            domain_type="Report",
            domain_id=payload.report_id,
            title=f"完整研究报告 {payload.report_id[:16]}",
            instrument_ids=(prediction.instrument_id,),
            created_by="api",
            route=f"/reports/{payload.report_id}",
        )
    else:
        report_artifact_id = report_artifact["artifact_id"]
    service.link(
        from_artifact_id=prediction_artifact,
        to_artifact_id=report_artifact_id,
        relation=RelationType.GENERATED_FROM,
    )
    return {"prediction": _payload(prediction)}


@router.get("")
def list_predictions(
    instrument_id: str | None = Query(default=None, min_length=3, max_length=32),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(PredictionORM).order_by(PredictionORM.created_at.desc()).limit(limit)
    if instrument_id is not None:
        stmt = stmt.where(PredictionORM.instrument_id == instrument_id)
    orm_rows = session.scalars(stmt).all()
    results = []
    for row in orm_rows:
        prediction = PredictionRepository(session).get(row.prediction_id)
        validation = ValidationRepository(session).get_for_prediction(row.prediction_id)
        results.append(_payload(prediction, validation))
    return {"count": len(results), "results": results}


@router.post("/{prediction_id}/validate")
def validate_prediction(
    prediction_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """FINAL validation — only after maturity (P0-04)."""
    service = ValidationService(session)
    try:
        record = service.validate(prediction_id)
    except KeyError:
        raise AppError("prediction.not_found", status_code=404) from None
    except PredictionNotMatured as exc:
        raise AppError(
            "prediction.not_matured", status_code=422, detail=str(exc)
        ) from None
    except ValueError as exc:
        raise AppError(
            "prediction.validation_no_data", status_code=422, detail=str(exc)
        ) from None
    prediction = PredictionRepository(session).get(prediction_id)
    assert prediction is not None
    from app.application.artifacts import ArtifactService, RelationType

    service = ArtifactService(session)
    prediction_artifact = service.by_domain("PredictionRecord", prediction_id)
    if prediction_artifact is not None:
        validation_artifact = service.register(
            artifact_type="validation",
            domain_type="ValidationRecord",
            domain_id=record.validation_id,
            title=f"验证结果 {record.instrument_return_pct:+.2f}%",
            instrument_ids=(prediction.instrument_id,),
            as_of_time=record.validated_at,
            created_by="api",
            route="/predictions",
        )
        service.link(
            from_artifact_id=prediction_artifact["artifact_id"],
            to_artifact_id=validation_artifact,
            relation=RelationType.VALIDATED_BY,
        )
    return {"prediction": _payload(prediction, record)}


@router.get("/{prediction_id}/mark-to-market")
def mark_to_market(
    prediction_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Read-only current P&L view. Does NOT create a ValidationRecord."""
    service = ValidationService(session)
    try:
        result = service.mark_to_market(prediction_id)
    except KeyError:
        raise AppError("prediction.not_found", status_code=404) from None
    return result


@router.get("/due")
def due_predictions(session: Session = Depends(get_session)) -> dict:
    service = ValidationService(session)
    due = service.due_unvalidated()
    return {"count": len(due), "results": [_payload(p) for p in due]}
