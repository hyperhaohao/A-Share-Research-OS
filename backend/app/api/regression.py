"""Regression reviews + research experiences: persistence, aggregates, API (M20)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, Float, String, select
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.evidence import utc_now
from app.domain.regression import (
    Attribution,
    AttributionDimension,
    RegressionReview,
    RegressionReviewService,
    ResearchExperience,
)
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base
from app.storage.prediction_repo import PredictionRepository, ValidationRepository


# -- ORM ----------------------------------------------------------------------
class RegressionReviewORM(Base):
    __tablename__ = "regression_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    validation_id: Mapped[str] = mapped_column(String(24), index=True)
    prediction_id: Mapped[str] = mapped_column(String(24), index=True)
    attributions_json: Mapped[list] = mapped_column(JSON, default=list)
    lesson_summary: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchExperienceORM(Base):
    __tablename__ = "research_experiences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experience_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    context: Mapped[str] = mapped_column(default="")
    lesson: Mapped[str] = mapped_column(default="")
    related_research_type: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    supporting_validations_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# -- repositories ---------------------------------------------------------------
class RegressionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, review: RegressionReview) -> str:
        row = RegressionReviewORM(
            review_id=review.review_id,
            validation_id=review.validation_id,
            prediction_id=review.prediction_id,
            attributions_json=[a.model_dump(mode="json") for a in review.attributions],
            lesson_summary=review.lesson_summary,
            created_at=review.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.review_id

    def list_all(self, *, limit: int = 50) -> list[RegressionReview]:
        rows = self._session.scalars(
            select(RegressionReviewORM)
            .order_by(RegressionReviewORM.created_at.desc(), RegressionReviewORM.id.desc())
            .limit(limit)
        ).all()
        return [
            RegressionReview(
                review_id=r.review_id,
                validation_id=r.validation_id,
                prediction_id=r.prediction_id,
                attributions=tuple(Attribution(**a) for a in (r.attributions_json or [])),
                lesson_summary=r.lesson_summary,
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]


class ExperienceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, experience: ResearchExperience) -> str:
        row = ResearchExperienceORM(
            experience_id=experience.experience_id,
            context=experience.context,
            lesson=experience.lesson,
            related_research_type=experience.related_research_type,
            confidence=experience.confidence,
            supporting_validations_json=list(experience.supporting_validations),
            created_at=experience.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.experience_id

    def list_all(self, *, limit: int = 100) -> list[ResearchExperience]:
        rows = self._session.scalars(
            select(ResearchExperienceORM)
            .order_by(ResearchExperienceORM.created_at.desc(), ResearchExperienceORM.id.desc())
            .limit(limit)
        ).all()
        return [
            ResearchExperience(
                experience_id=r.experience_id,
                context=r.context,
                lesson=r.lesson,
                related_research_type=r.related_research_type,
                confidence=r.confidence,
                supporting_validations=tuple(r.supporting_validations_json or ()),
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]


# -- API --------------------------------------------------------------------------
router = APIRouter(prefix="/regression", tags=["regression"])


class ReviewIn(BaseModel):
    validation_id: str = Field(min_length=8, max_length=24)


class ExperienceIn(BaseModel):
    context: str = Field(min_length=1, max_length=2000)
    lesson: str = Field(min_length=1, max_length=2000)
    related_research_type: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_validations: list[str] = Field(default_factory=list)


def _review_payload(r: RegressionReview) -> dict:
    return {
        "review_id": r.review_id,
        "validation_id": r.validation_id,
        "prediction_id": r.prediction_id,
        "attributions": [a.model_dump(mode="json") for a in r.attributions],
        "lesson_summary": r.lesson_summary,
        "created_at": r.created_at.isoformat(),
    }


def _experience_payload(e: ResearchExperience) -> dict:
    return {
        "experience_id": e.experience_id,
        "context": e.context,
        "lesson": e.lesson,
        "related_research_type": e.related_research_type,
        "confidence": e.confidence,
        "supporting_validations": list(e.supporting_validations),
        "created_at": e.created_at.isoformat(),
    }


@router.post("/reviews", status_code=201)
def create_review(payload: ReviewIn, session: Session = Depends(get_session)) -> dict:
    predictions = PredictionRepository(session)
    validation_record = _find_validation_by_id(session, payload.validation_id)
    if validation_record is None:
        raise AppError("regression.validation_not_found", status_code=404)
    prediction = predictions.get(validation_record.prediction_id)
    assert prediction is not None
    review = RegressionReviewService().review(prediction, validation_record)
    review_id = RegressionRepository(session).save(review)
    saved = next(r for r in RegressionRepository(session).list_all() if r.review_id == review_id)
    return {"review": _review_payload(saved)}


@router.get("/reviews")
def list_reviews(session: Session = Depends(get_session)) -> dict:
    reviews = RegressionRepository(session).list_all()
    return {"count": len(reviews), "results": [_review_payload(r) for r in reviews]}


@router.post("/experiences", status_code=201)
def create_experience(payload: ExperienceIn, session: Session = Depends(get_session)) -> dict:
    experience = ResearchExperience(
        context=payload.context,
        lesson=payload.lesson,
        related_research_type=payload.related_research_type,
        confidence=payload.confidence,
        supporting_validations=tuple(payload.supporting_validations),
    )
    experience_id = ExperienceRepository(session).save(experience)
    saved = next(
        e for e in ExperienceRepository(session).list_all() if e.experience_id == experience_id
    )
    return {"experience": _experience_payload(saved)}


@router.get("/experiences")
def list_experiences(session: Session = Depends(get_session)) -> dict:
    experiences = ExperienceRepository(session).list_all()
    return {"count": len(experiences), "results": [_experience_payload(e) for e in experiences]}


@router.get("/performance")
def performance(session: Session = Depends(get_session)) -> dict:
    """Long-run statistics over validations (任务书 §51)."""
    from app.storage.prediction_repo import ValidationORM

    rows = session.scalars(select(ValidationORM)).all()
    total = len(rows)
    if total == 0:
        return {
            "total_validations": 0,
            "direction_accuracy": None,
            "average_excess_return_pct": None,
            "range_hit_rate": None,
        }
    directional = [r for r in rows if r.direction_correct is not None]
    direction_accuracy = (
        sum(1 for r in directional if r.direction_correct) / len(directional) * 100
        if directional
        else None
    )
    excesses = [r.excess_return_pct for r in rows if r.excess_return_pct is not None]
    avg_excess = sum(excesses) / len(excesses) if excesses else None
    range_hit_rate = sum(1 for r in rows if r.range_hit) / total * 100
    return {
        "total_validations": total,
        "direction_accuracy": round(direction_accuracy, 4) if direction_accuracy is not None else None,
        "average_excess_return_pct": round(avg_excess, 6) if avg_excess is not None else None,
        "range_hit_rate": round(range_hit_rate, 4),
    }


def _find_validation_by_id(session: Session, validation_id: str):
    from app.storage.prediction_repo import ValidationORM

    row = session.scalars(
        select(ValidationORM).where(ValidationORM.validation_id == validation_id)
    ).first()
    if row is None:
        return None
    from app.domain.prediction import ValidationRecord

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
