"""Regression attribution + experience tests (任务书 §52/§53)."""

from datetime import datetime, timezone

import pytest

from app.domain.prediction import Direction, Horizon, PredictionRecord
from app.domain.regression import (
    AttributionDimension,
    RegressionReviewService,
    ResearchExperience,
)
from app.domain.prediction import ValidationRecord


def _prediction(direction=Direction.UP, confidence=0.8) -> PredictionRecord:
    return PredictionRecord(
        instrument_id="SSE:600519",
        as_of=datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc),
        horizon=Horizon.D5,
        expected_direction=direction,
        expected_return_range=(0.0, 10.0),
        confidence=confidence,
    )


def _validation(**kw) -> ValidationRecord:
    params = dict(
        prediction_id="prd_test000000000001",
        instrument_return_pct=-4.0,
        benchmark_return_pct=None,
        excess_return_pct=None,
        direction_correct=False,
        range_hit=False,
        start_price=100.0,
        end_price=96.0,
        evidence_refs=("ev_1",),
    )
    params.update(kw)
    return ValidationRecord(**params)


class TestAttribution:
    def test_market_regime_requires_benchmark_corroboration(self):
        """§52: bare 'market changed' without a benchmark move is banned."""
        review = RegressionReviewService().review(
            _prediction(), _validation(benchmark_return_pct=None)
        )
        assert all(
            a.dimension is not AttributionDimension.MARKET_REGIME
            for a in review.attributions
        )
        assert len(review.attributions) >= 1

    def test_market_regime_with_benchmark_move(self):
        review = RegressionReviewService().review(
            _prediction(),
            _validation(
                benchmark_return_pct=-3.5,
                excess_return_pct=-0.5,
                direction_correct=False,
            ),
        )
        assert any(
            a.dimension is AttributionDimension.MARKET_REGIME
            for a in review.attributions
        )

    def test_timing_when_direction_right_but_range_missed(self):
        review = RegressionReviewService().review(
            _prediction(),
            _validation(
                instrument_return_pct=7.0,
                direction_correct=True,
                range_hit=False,
            ),
        )
        assert any(a.dimension is AttributionDimension.TIMING for a in review.attributions)

    def test_low_confidence_claim_attribution(self):
        review = RegressionReviewService().review(
            _prediction(confidence=0.3), _validation()
        )
        assert any(a.dimension is AttributionDimension.CLAIM for a in review.attributions)

    def test_always_at_least_one_dimension(self):
        review = RegressionReviewService().review(_prediction(), _validation())
        assert len(review.attributions) >= 1


class TestExperience:
    def test_experience_is_append_only_model(self):
        exp = ResearchExperience(
            context="5D 方向预测在财报周失效",
            lesson="财报周应降低 5D 方向预测置信度",
            related_research_type="direction_prediction",
            confidence=0.6,
            supporting_validations=("val_1", "val_2"),
        )
        assert exp.experience_id.startswith("exp_")
        assert len(exp.supporting_validations) == 2

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ResearchExperience(
                context="c",
                lesson="l",
                related_research_type="t",
                confidence=1.5,
            )
