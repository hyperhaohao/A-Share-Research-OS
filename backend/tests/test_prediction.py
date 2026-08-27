"""Prediction math (fixed numbers, §80) + immutability (§50)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.prediction import (
    Direction,
    Horizon,
    PredictionRecord,
    add_trading_days,
)
from app.services.validation_service import compute_validation

BASE = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)  # a Friday


def _prediction(direction: Direction = Direction.UP, range_: tuple = (-5.0, 10.0)) -> PredictionRecord:
    return PredictionRecord(
        instrument_id="SSE:600519",
        as_of=BASE,
        horizon=Horizon.D5,
        expected_direction=direction,
        expected_return_range=range_,
        confidence=0.7,
    )


class TestTradingDays:
    def test_five_trading_days_skips_weekend(self):
        # Friday 2026-08-28 → +5 trading days = Friday 2026-09-04
        due = add_trading_days(BASE, 5)
        assert due == datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)

    def test_twenty_and_sixty(self):
        assert add_trading_days(BASE, 20) == datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)
        # 60 trading days ≈ 84 calendar days
        assert add_trading_days(BASE, 60) == datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)


class TestValidationMath:
    def test_up_direction_correct(self):
        record = compute_validation(
            _prediction(Direction.UP),
            start_price=100.0,
            end_price=105.0,
            benchmark_start_price=None,
            benchmark_end_price=None,
        )
        assert record.instrument_return_pct == pytest.approx(5.0)
        assert record.direction_correct is True
        assert record.range_hit is True  # 5.0 within [-5, 10]
        assert record.benchmark_return_pct is None  # explicit missing
        assert record.excess_return_pct is None

    def test_down_direction_wrong(self):
        record = compute_validation(
            _prediction(Direction.UP), start_price=100.0, end_price=95.0,
            benchmark_start_price=None, benchmark_end_price=None,
        )
        assert record.instrument_return_pct == pytest.approx(-5.0)
        assert record.direction_correct is False
        assert record.range_hit is True  # -5.0 within [-5, 10]

    def test_neutral_direction_is_none(self):
        record = compute_validation(
            _prediction(Direction.NEUTRAL), start_price=100.0, end_price=101.0,
            benchmark_start_price=None, benchmark_end_price=None,
        )
        assert record.direction_correct is None

    def test_excess_return_with_benchmark(self):
        record = compute_validation(
            _prediction(Direction.UP, range_=(0.0, 10.0)),
            start_price=100.0,
            end_price=105.0,
            benchmark_start_price=4000.0,
            benchmark_end_price=4100.0,
        )
        # benchmark 2.5%, instrument 5% → excess 2.5%
        assert record.benchmark_return_pct == pytest.approx(2.5)
        assert record.excess_return_pct == pytest.approx(2.5)

    def test_range_miss(self):
        record = compute_validation(
            _prediction(range_=(6.0, 10.0)), start_price=100.0, end_price=105.0,
            benchmark_start_price=None, benchmark_end_price=None,
        )
        assert record.range_hit is False


class TestImmutability:
    def test_prediction_is_frozen(self):
        p = _prediction()
        with pytest.raises(Exception):
            p.confidence = 0.99  # type: ignore[misc]

    def test_range_bounds_validated(self):
        with pytest.raises(Exception):
            _prediction(range_=(10.0, -5.0))

    def test_horizon_values(self):
        assert [h.value for h in Horizon] == ["5D", "20D", "60D"]
