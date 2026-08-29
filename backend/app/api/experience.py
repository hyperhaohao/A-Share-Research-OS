"""Experience Card API (V2 Phase C, 总纲 §12/§13/§43/§72).

原 → 炼 → 验 → 用。所有拒绝都是显式的（experience.* 错误码），
流程门槛（验证后才可批准）不可绕过。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.experience_service import ExperienceRefusal, ExperienceService

router = APIRouter(prefix="/experience-cards", tags=["experience"])


class VerdictIn(BaseModel):
    verdict: str | None = Field(default=None, max_length=500)


@router.post("/from-report", status_code=201)
def create_from_report(payload: dict, session: Session = Depends(get_session)) -> dict:
    report_id = (payload or {}).get("report_id", "")
    if not isinstance(report_id, str) or len(report_id) < 6:
        raise AppError("experience.invalid", status_code=422, detail="report_id required")
    try:
        card = ExperienceService(session).create_from_report(report_id)
    except KeyError:
        raise AppError("report.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.underivable", status_code=422, detail=str(exc)) from None
    return {"card": card}


@router.get("")
def list_cards(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = ExperienceService(session).list_cards(limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{card_id}")
def get_card(card_id: str, session: Session = Depends(get_session)) -> dict:
    detail = ExperienceService(session).get_card_detail(card_id)
    if detail is None:
        raise AppError("experience.not_found", status_code=404)
    return {"card": detail}


@router.post("/{card_id}/refine", status_code=200)
def refine_card(card_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        card = ExperienceService(session).refine_with_llm(card_id)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.llm_unavailable", status_code=422, detail=str(exc)) from None
    return {"card": card}


@router.post("/{card_id}/validate", status_code=201)
def validate_card(card_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        validation = ExperienceService(session).validate_case(card_id)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.validation_no_data", status_code=422, detail=str(exc)) from None
    return {"validation": validation}


@router.post("/{card_id}/approve")
def approve_card(card_id: str, payload: VerdictIn, session: Session = Depends(get_session)) -> dict:
    try:
        card = ExperienceService(session).approve(card_id, payload.verdict)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.approve_blocked", status_code=422, detail=str(exc)) from None
    return {"card": card}


@router.post("/{card_id}/reject")
def reject_card(card_id: str, payload: VerdictIn, session: Session = Depends(get_session)) -> dict:
    try:
        card = ExperienceService(session).reject(card_id, payload.verdict)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    return {"card": card}
