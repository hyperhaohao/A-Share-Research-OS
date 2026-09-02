"""Experience-driven Screening API（G5，观澜语义迁移任务书 §G5）."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session

router = APIRouter(prefix="/screening-v2", tags=["screening-v2"])


class CompileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    card_id: str = Field(min_length=6, max_length=40)
    universe: dict | None = None


class PublishIn(BaseModel):
    confirm: bool = Field(default=False)


@router.post("/definitions", status_code=201)
def compile_definition(payload: CompileIn,
                       session: Session = Depends(get_session)) -> dict:
    """Approved Experience → ScreenDefinition Vn（未批准 422；§G5.1）。"""
    from app.services.experience_screening import ExperienceScreenService

    try:
        out = ExperienceScreenService(session).compile_definition(
            name=payload.name, card_id=payload.card_id,
            universe=payload.universe,
        )
    except AppError:
        raise
    session.commit()
    return {"definition": out}


@router.get("/definitions")
def list_definitions(status: str | None = Query(default=None, max_length=16),
                     session: Session = Depends(get_session)) -> dict:
    from app.services.experience_screening import ExperienceScreenService

    results = ExperienceScreenService(session).list_definitions(status=status)
    return {"count": len(results), "results": results}


@router.post("/definitions/{def_id}/publish")
def publish_definition(def_id: str, payload: PublishIn,
                       session: Session = Depends(get_session)) -> dict:
    """发布定义（§G5.3：人工确认后发布；经 F7 确认门工具调用时 confirm=True）。"""
    if not payload.confirm:
        raise AppError(
            "screen.publish_needs_confirmation", status_code=422,
            detail="publishing is a human-confirmed action (§G5.3)",
        ) from None
    from app.services.experience_screening import ExperienceScreenService

    out = ExperienceScreenService(session).publish_definition(def_id)
    session.commit()
    return {"definition": out}


@router.post("/definitions/{def_id}/run", status_code=202)
def run_definition(def_id: str,
                   session: Session = Depends(get_session)) -> dict:
    """PIT 执行已发布定义 → ScreenRun（未发布 422）。"""
    from app.services.experience_screening import ExperienceScreenService

    out = ExperienceScreenService(session).execute_definition(def_id)
    session.commit()
    return {"run": out}


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    from app.services.experience_screening import ExperienceScreenService

    out = ExperienceScreenService(session).get_run(run_id)
    if out is None:
        raise AppError("screen.run_not_found", status_code=404)
    return {"run": out}
