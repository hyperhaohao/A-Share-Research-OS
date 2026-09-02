"""Prediction / Validation domain (任务书 §50/§51).

A PredictionRecord is immutable once created (§50): no update path exists —
only validation appends an outcome. Due dates use A-share trading days
(weekdays; holidays noted as a known limitation until a calendar source is
wired in M3+).

Validation math is deterministic and covered by fixed-number tests (§80).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.evidence import utc_now


class Horizon(str, Enum):
    D5 = "5D"
    D20 = "20D"
    D60 = "60D"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


def add_trading_days(start: datetime, days: int) -> datetime:
    """Advance by A-share trading days (Mon-Fri; holidays not yet modeled)."""
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


class PredictionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # immutable (§50)

    prediction_id: str = Field(default_factory=lambda: f"prd_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    research_run_id: str | None = None
    as_of: datetime

    horizon: Horizon
    benchmark: str = Field(default="CSI300", max_length=32)

    expected_direction: Direction
    expected_return_range: tuple[float, float]  # percent, [min, max]
    expected_excess_return_range: tuple[float, float] | None = None

    confidence: float = Field(ge=0.0, le=1.0)
    supporting_thesis_id: str | None = None
    # G8（任务书 §G8.1）：因果引用 —— Prediction 直接引用其来源 Decision
    decision_id: str | None = None
    trigger_conditions: tuple[str, ...] = ()
    invalidate_conditions: tuple[str, ...] = ()

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "PredictionRecord":
        for name in ("as_of", "created_at"):
            value = getattr(self, name)
            if value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        lo, hi = self.expected_return_range
        if lo > hi:
            raise ValueError("expected_return_range must be [min, max]")
        if self.expected_excess_return_range is not None:
            elo, ehi = self.expected_excess_return_range
            if elo > ehi:
                raise ValueError("excess range must be [min, max]")
        return self

    @property
    def due_at(self) -> datetime:
        return add_trading_days(self.as_of, int(self.horizon.value[:-1]))


class ValidationRecord(BaseModel):
    """Deterministic outcome of one prediction (任务书 §51)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    validation_id: str = Field(default_factory=lambda: f"val_{uuid4().hex[:16]}")
    prediction_id: str = Field(min_length=8, max_length=24)

    instrument_return_pct: float
    benchmark_return_pct: float | None
    excess_return_pct: float | None

    direction_correct: bool | None  # None when direction is NEUTRAL
    range_hit: bool

    start_price: float
    end_price: float
    benchmark_start_price: float | None = None
    benchmark_end_price: float | None = None

    evidence_refs: tuple[str, ...] = ()
    validated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "ValidationRecord":
        if self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware")
        return self
