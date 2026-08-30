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


class FromReportIn(BaseModel):
    report_id: str = Field(min_length=6, max_length=32)
    quant_expression: str | None = Field(default=None, max_length=200)


@router.post("/from-report", status_code=201)
def create_from_report(payload: FromReportIn, session: Session = Depends(get_session)) -> dict:
    try:
        card = ExperienceService(session).create_from_report(
            payload.report_id, quant_expression=payload.quant_expression
        )
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


@router.post("/{card_id}/refine-structured", status_code=200)
def refine_structured(card_id: str, session: Session = Depends(get_session)) -> dict:
    """R6 方案 §12.2：LLM 九字段结构化精炼（无 KEY → 422 显形）。"""
    try:
        card = ExperienceService(session).refine_structured(card_id)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.refine_unavailable", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"card": card}


class NonQuantIn(BaseModel):
    method: str = Field(min_length=4, max_length=40)
    note: str | None = Field(default=None, max_length=300)


@router.post("/{card_id}/validate-non-quant", status_code=201)
def validate_non_quant(card_id: str, payload: NonQuantIn, session: Session = Depends(get_session)) -> dict:
    """R6 方案 §12.3：非量化验证（反例搜索/历史证据/跨公司/人工复核）。"""
    try:
        validation = ExperienceService(session).validate_non_quant(
            card_id, payload.method, note=payload.note
        )
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ExperienceRefusal as exc:
        raise AppError("experience.validation_refused", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"validation": validation}


@router.get("/playbook/search")
def playbook_search(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    """R6 方案 §12.4：研究 Playbook（已批准经验检索）。

    Playbook 条目是研究启发/方法，不是 Evidence —— 检索结果不携带
    authority/fact_status（那是 Evidence 字段），防止当事实引用。"""
    results = ExperienceService(session).playbook_search(q, limit=limit)
    return {"count": len(results), "results": results}


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
