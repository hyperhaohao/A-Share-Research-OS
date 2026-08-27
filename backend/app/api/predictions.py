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
from app.services.validation_service import ValidationService
from app.storage.prediction_repo import (
    PredictionORM,
    PredictionRepository,
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
    instrument_id = resolve_instrument_id(payload.instrument)
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
    return {"prediction": _payload(saved)}


@router.get("")
def list_predictions(
    instrument_id: str = Query(min_length=3, max_length=32),
    session: Session = Depends(get_session),
) -> dict:
    orm_rows = session.scalars(
        select(PredictionORM).where(PredictionORM.instrument_id == instrument_id)
    ).all()
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
    service = ValidationService(session)
    try:
        record = service.validate(prediction_id)
    except KeyError:
        raise AppError("prediction.not_found", status_code=404) from None
    except ValueError as exc:
        raise AppError(
            "prediction.validation_premature", status_code=422, detail=str(exc)
        ) from None
    prediction = PredictionRepository(session).get(prediction_id)
    assert prediction is not None
    return {"prediction": _payload(prediction, record)}


@router.get("/due")
def due_predictions(session: Session = Depends(get_session)) -> dict:
    service = ValidationService(session)
    due = service.due_unvalidated()
    return {"count": len(due), "results": [_payload(p) for p in due]}
