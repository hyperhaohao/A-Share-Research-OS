"""Regression review + research experience (任务书 §52/§53).

RegressionReview attributes a wrong prediction to at least one concrete
dimension — a bare "market changed" is never the whole answer (§52):
market_regime attribution requires corroborating benchmark movement.

ResearchExperience (§53) is an append-only lesson store; the system never
auto-modifies its own prompts from it (first version records only).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.evidence import utc_now


class AttributionDimension(str, Enum):
    EVIDENCE = "evidence"
    CLAIM = "claim"
    THESIS = "thesis"
    VALUATION = "valuation"
    CATALYST = "catalyst"
    RISK = "risk"
    TIMING = "timing"
    MARKET_REGIME = "market_regime"
    # G8（任务书 §G8.3）：七类归因补全
    RULE_ERROR = "rule_error"
    EXECUTION_ERROR = "execution_error"
    INSUFFICIENT_DATA = "insufficient_data"


class Attribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: AttributionDimension
    note: str = Field(min_length=1, max_length=1000)


class RegressionReview(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    review_id: str = Field(default_factory=lambda: f"reg_{uuid4().hex[:16]}")
    validation_id: str = Field(min_length=8, max_length=24)
    prediction_id: str = Field(min_length=8, max_length=24)

    attributions: tuple[Attribution, ...] = Field(min_length=1)
    lesson_summary: str = Field(min_length=1, max_length=2000)

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "RegressionReview":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class ResearchExperience(BaseModel):
    """Append-only lesson (任务书 §53) — never rewritten, prompts untouched."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    experience_id: str = Field(default_factory=lambda: f"exp_{uuid4().hex[:16]}")
    context: str = Field(min_length=1, max_length=2000)
    lesson: str = Field(min_length=1, max_length=2000)
    related_research_type: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_validations: tuple[str, ...] = ()

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "ResearchExperience":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class RegressionReviewService:
    """Deterministic attribution over a ValidationRecord (§52)."""

    #: benchmark move that may justify a market_regime attribution
    REGIME_MOVE_PCT = 3.0
    #: evidence staleness that justifies an evidence attribution
    STALE_DAYS = 14

    def review(self, prediction, validation, *, evidence_lookup: dict | None = None) -> RegressionReview:
        attributions: list[Attribution] = []

        wrong_direction = (
            validation.direction_correct is False
        )
        missed_range = validation.range_hit is False

        # market_regime: needs corroborating benchmark movement in the same
        # direction as the instrument's miss (a bare market excuse is banned).
        if (
            validation.benchmark_return_pct is not None
            and abs(validation.benchmark_return_pct) >= self.REGIME_MOVE_PCT
            and wrong_direction
        ):
            same_side = (validation.instrument_return_pct < 0) == (
                validation.benchmark_return_pct < 0
            )
            if same_side:
                attributions.append(
                    Attribution(
                        dimension=AttributionDimension.MARKET_REGIME,
                        note=(
                            f"benchmark moved {validation.benchmark_return_pct:.2f}% "
                            "and dragged the instrument the same way"
                        ),
                    )
                )

        # evidence staleness
        if evidence_lookup:
            for ref in validation.evidence_refs:
                ev = evidence_lookup.get(ref)
                if ev is not None and ev.available_time is not None:
                    age = (utc_now() - ev.available_time).days
                    if age > self.STALE_DAYS:
                        attributions.append(
                            Attribution(
                                dimension=AttributionDimension.EVIDENCE,
                                note=f"cited evidence {ref} was {age}d old",
                            )
                        )

        # low-confidence claim
        if wrong_direction and prediction.confidence < 0.5:
            attributions.append(
                Attribution(
                    dimension=AttributionDimension.CLAIM,
                    note=f"supporting confidence was only {prediction.confidence}",
                )
            )

        # timing: direction right but range missed
        if not wrong_direction and missed_range:
            attributions.append(
                Attribution(
                    dimension=AttributionDimension.TIMING,
                    note=(
                        f"direction correct but return {validation.instrument_return_pct:.2f}% "
                        "fell outside the predicted band"
                    ),
                )
            )

        # G8（§G8.3）：规则错误 —— 方向错误且回撤显著 → 止损/入场规则问题
        # （确定性：|回撤| ≥ 3% 且方向错误 → RULE_ERROR）
        adverse_excursion = abs(validation.instrument_return_pct or 0.0)
        if wrong_direction and adverse_excursion >= 3.0:
            attributions.append(
                Attribution(
                    dimension=AttributionDimension.RULE_ERROR,
                    note=(
                        f"adverse excursion {adverse_excursion:.2f}% exceeded typical "
                        "risk thresholds — entry/stop rules need tightening"
                    ),
                )
            )

        # G8：执行/数据不足类（有据才判，无据不造）
        if validation.instrument_return_pct is None:
            attributions.append(
                Attribution(
                    dimension=AttributionDimension.INSUFFICIENT_DATA,
                    note="validation lacks instrument return data",
                )
            )

        if not attributions:
            # guaranteed non-empty fallback with a concrete dimension
            attributions.append(
                Attribution(
                    dimension=AttributionDimension.THESIS,
                    note="thesis logic did not hold; no corroborating regime/evidence cause found",
                )
            )

        lesson = "; ".join(f"{a.dimension.value}: {a.note}" for a in attributions)
        return RegressionReview(
            validation_id=validation.validation_id,
            prediction_id=prediction.prediction_id,
            attributions=tuple(attributions),
            lesson_summary=lesson[:2000],
        )
