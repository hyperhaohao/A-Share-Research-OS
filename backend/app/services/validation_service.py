"""Prediction validation service (任务书 §51).

Math is deterministic and covered by fixed-number tests (§80):

    instrument_return = P_end / P_start − 1
    benchmark_return  = B_end / B_start − 1   (when benchmark prices exist)
    excess_return     = instrument_return − benchmark_return
    direction_correct = sign(return) matches expected direction
    range_hit         = expected_return_range contains instrument_return

Prices come from quote evidence of the instrument (and benchmark index
evidence when available) at or before the as_of / due timestamps.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.evidence import EvidenceType, utc_now
from app.domain.prediction import (
    Direction,
    PredictionRecord,
    ValidationRecord,
)
from app.storage.prediction_repo import PredictionRepository, ValidationRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


def _price_at(
    evidence: list, *, at: datetime, instrument_id: str
) -> tuple[float, str] | None:
    """Newest quote price with available_time <= at for the instrument."""
    candidates = [
        e
        for e in evidence
        if e.evidence_type is EvidenceType.MARKET_QUOTE
        and e.instrument_id == instrument_id
        and e.available_time <= at
        and (e.metadata or {}).get("price") is not None
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda e: e.available_time)
    return float(latest.metadata["price"]), latest.evidence_id


def compute_validation(
    prediction: PredictionRecord,
    *,
    start_price: float,
    end_price: float,
    benchmark_start_price: float | None,
    benchmark_end_price: float | None,
    evidence_refs: tuple[str, ...] = (),
) -> ValidationRecord:
    """Pure math — deterministic, unit-testable without any storage.

    All derived values are computed from the ROUNDED returns so the stored
    record is internally consistent (§80 determinism).
    """
    instrument_return = round((end_price / start_price - 1) * 100, 6)

    benchmark_return: float | None = None
    excess: float | None = None
    if benchmark_start_price and benchmark_end_price:
        benchmark_return = round((benchmark_end_price / benchmark_start_price - 1) * 100, 6)
        excess = round(instrument_return - benchmark_return, 6)

    if prediction.expected_direction is Direction.NEUTRAL:
        direction_correct = None
    elif prediction.expected_direction is Direction.UP:
        direction_correct = instrument_return > 0
    else:
        direction_correct = instrument_return < 0

    lo, hi = prediction.expected_return_range
    range_hit = lo <= instrument_return <= hi

    return ValidationRecord(
        prediction_id=prediction.prediction_id,
        instrument_return_pct=instrument_return,
        benchmark_return_pct=benchmark_return,
        excess_return_pct=excess,
        direction_correct=direction_correct,
        range_hit=range_hit,
        start_price=start_price,
        end_price=end_price,
        benchmark_start_price=benchmark_start_price,
        benchmark_end_price=benchmark_end_price,
        evidence_refs=evidence_refs,
        validated_at=utc_now(),
    )


class ValidationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._predictions = PredictionRepository(session)
        self._validations = ValidationRepository(session)
        self._evidence = EvidenceRepository(session)

    def validate(self, prediction_id: str, *, now: datetime | None = None) -> ValidationRecord:
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            raise KeyError(prediction_id)
        existing = self._validations.get_for_prediction(prediction_id)
        if existing is not None:
            return existing  # validation is one-shot like the prediction

        now = now or utc_now()
        # validate at the due date when due, else "mark-to-market" at now
        as_of_target = prediction.due_at if now >= prediction.due_at else now

        evidence = self._evidence.list_for_instrument(
            prediction.instrument_id, visible_at=as_of_target
        )
        start = _price_at(evidence, at=prediction.as_of, instrument_id=prediction.instrument_id)
        end = _price_at(evidence, at=as_of_target, instrument_id=prediction.instrument_id)
        if start is None or end is None:
            raise ValueError("missing quote evidence for validation window")

        # Benchmark series (IDX quote evidence) is ingested from M20 onward;
        # until then excess return stays explicitly None rather than guessed.
        record = compute_validation(
            prediction,
            start_price=start[0],
            end_price=end[0],
            benchmark_start_price=None,
            benchmark_end_price=None,
            evidence_refs=tuple({start[1], end[1]}),
        )
        self._validations.save(record)
        return record

    def due_unvalidated(self, *, now: datetime | None = None) -> list[PredictionRecord]:
        now = now or utc_now()
        validated = self._validations.validated_prediction_ids()
        return self._predictions.due(now, validated_ids=validated)
