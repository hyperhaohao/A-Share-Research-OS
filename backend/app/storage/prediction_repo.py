"""Prediction + validation persistence (M19)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.evidence import utc_now
from app.domain.prediction import PredictionRecord, ValidationRecord
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base


class PredictionORM(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prediction_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    research_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    horizon: Mapped[str] = mapped_column(String(8))
    benchmark: Mapped[str] = mapped_column(String(32))

    expected_direction: Mapped[str] = mapped_column(String(8))
    expected_return_min: Mapped[float] = mapped_column(Float)
    expected_return_max: Mapped[float] = mapped_column(Float)
    expected_excess_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_excess_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    confidence: Mapped[float] = mapped_column(Float)
    supporting_thesis_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    trigger_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    invalidate_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ValidationORM(Base):
    __tablename__ = "validations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    validation_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    prediction_id: Mapped[str] = mapped_column(String(24), index=True)

    instrument_return_pct: Mapped[float] = mapped_column(Float)
    benchmark_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    excess_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[bool | None] = mapped_column(nullable=True)
    range_hit: Mapped[bool] = mapped_column(default=False)

    start_price: Mapped[float] = mapped_column(Float)
    end_price: Mapped[float] = mapped_column(Float)
    benchmark_start_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_end_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("prediction_id"),)


class PredictionRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(self, prediction: PredictionRecord) -> str:
        row = PredictionORM(
            prediction_id=prediction.prediction_id,
            instrument_id=prediction.instrument_id,
            research_run_id=prediction.research_run_id,
            as_of=prediction.as_of,
            due_at=prediction.due_at,
            horizon=prediction.horizon.value,
            benchmark=prediction.benchmark,
            expected_direction=prediction.expected_direction.value,
            expected_return_min=prediction.expected_return_range[0],
            expected_return_max=prediction.expected_return_range[1],
            expected_excess_min=prediction.expected_excess_return_range[0]
            if prediction.expected_excess_return_range
            else None,
            expected_excess_max=prediction.expected_excess_return_range[1]
            if prediction.expected_excess_return_range
            else None,
            confidence=prediction.confidence,
            supporting_thesis_id=prediction.supporting_thesis_id,
            trigger_conditions_json=list(prediction.trigger_conditions),
            invalidate_conditions_json=list(prediction.invalidate_conditions),
            created_at=prediction.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.prediction_id

    def get(self, prediction_id: str) -> PredictionRecord | None:
        row = self._session.scalars(
            select(PredictionORM).where(PredictionORM.prediction_id == prediction_id)
        ).first()
        return None if row is None else self._row_to_domain(row)

    def due(self, now: datetime, *, validated_ids: set[str] | None = None) -> list[PredictionRecord]:
        validated_ids = validated_ids or set()
        rows = self._session.scalars(
            select(PredictionORM).where(PredictionORM.due_at <= now)
        ).all()
        return [self._row_to_domain(r) for r in rows if r.prediction_id not in validated_ids]

    def _row_to_domain(self, r: PredictionORM) -> PredictionRecord:
        excess = None
        if r.expected_excess_min is not None and r.expected_excess_max is not None:
            excess = (r.expected_excess_min, r.expected_excess_max)
        return PredictionRecord(
            prediction_id=r.prediction_id,
            instrument_id=r.instrument_id,
            research_run_id=r.research_run_id,
            as_of=_ensure_utc(r.as_of),
            horizon=r.horizon,  # type: ignore[arg-type]
            benchmark=r.benchmark,
            expected_direction=r.expected_direction,  # type: ignore[arg-type]
            expected_return_range=(r.expected_return_min, r.expected_return_max),
            expected_excess_return_range=excess,
            confidence=r.confidence,
            supporting_thesis_id=r.supporting_thesis_id,
            trigger_conditions=tuple(r.trigger_conditions_json or ()),
            invalidate_conditions=tuple(r.invalidate_conditions_json or ()),
            created_at=_ensure_utc(r.created_at),
        )


class ValidationRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(self, record: ValidationRecord) -> str:
        row = ValidationORM(
            validation_id=record.validation_id,
            prediction_id=record.prediction_id,
            instrument_return_pct=record.instrument_return_pct,
            benchmark_return_pct=record.benchmark_return_pct,
            excess_return_pct=record.excess_return_pct,
            direction_correct=record.direction_correct,
            range_hit=record.range_hit,
            start_price=record.start_price,
            end_price=record.end_price,
            benchmark_start_price=record.benchmark_start_price,
            benchmark_end_price=record.benchmark_end_price,
            evidence_refs_json=list(record.evidence_refs),
            validated_at=record.validated_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.validation_id

    def get_for_prediction(self, prediction_id: str) -> ValidationRecord | None:
        row = self._session.scalars(
            select(ValidationORM).where(ValidationORM.prediction_id == prediction_id)
        ).first()
        if row is None:
            return None
        return ValidationRecord(
            validation_id=row.validation_id,
            prediction_id=row.prediction_id,
            instrument_return_pct=row.instrument_return_pct,
            benchmark_return_pct=row.benchmark_return_pct,
            excess_return_pct=row.excess_return_pct,
            direction_correct=row.direction_correct,
            range_hit=row.range_hit,
            start_price=row.start_price,
            end_price=row.end_price,
            benchmark_start_price=row.benchmark_start_price,
            benchmark_end_price=row.benchmark_end_price,
            evidence_refs=tuple(row.evidence_refs_json or ()),
            validated_at=_ensure_utc(row.validated_at),
        )

    def validated_prediction_ids(self) -> set[str]:
        return {
            row.prediction_id
            for row in self._session.scalars(select(ValidationORM.prediction_id)).all()
        }
