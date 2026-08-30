"""Research Memory API（R7，方案 §13）.

POST /memories                          创建 candidate（不自动 active）
GET  /memories                          检索（type/scope/q）
GET  /memories/{id}                     单条
POST /memories/{id}/promote             candidate→active / active→retired
POST /memories/from-experience/{card}   已批准经验 → candidate Memory
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.memory import MemoryService
from app.core.errors import AppError
from app.db import get_session

router = APIRouter(prefix="/memories", tags=["memory"])


class MemoryIn(BaseModel):
    memory_type: str = Field(min_length=4, max_length=24)
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=4000)
    instrument_id: str | None = Field(default=None, max_length=32)
    industry_id: str | None = Field(default=None, max_length=64)
    event_type: str | None = Field(default=None, max_length=32)
    intent: str | None = Field(default=None, max_length=24)
    tags: list[str] = Field(default_factory=list, max_length=8)
    source_artifacts: list[str] = Field(default_factory=list, max_length=8)
    source_experiences: list[str] = Field(default_factory=list, max_length=8)


@router.post("", status_code=201)
def create_memory(payload: MemoryIn, session: Session = Depends(get_session)) -> dict:
    try:
        memory = MemoryService(session).create_candidate(
            memory_type=payload.memory_type,
            title=payload.title,
            content=payload.content,
            scope={
                "instrument_id": payload.instrument_id,
                "industry_id": payload.industry_id,
                "event_type": payload.event_type,
                "intent": payload.intent,
                "tags": payload.tags,
            },
            source_artifacts=payload.source_artifacts,
            source_experiences=payload.source_experiences,
        )
    except ValueError as exc:
        raise AppError("memory.unknown_type", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"memory": memory}


@router.get("")
def search_memories(
    memory_type: str | None = Query(default=None, max_length=24),
    status: str = Query(default="active", max_length=16),
    instrument_id: str | None = Query(default=None, max_length=32),
    industry_id: str | None = Query(default=None, max_length=64),
    event_type: str | None = Query(default=None, max_length=32),
    intent: str | None = Query(default=None, max_length=24),
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    results = MemoryService(session).search(
        memory_type=memory_type, status=status or None,
        instrument_id=instrument_id, industry_id=industry_id,
        event_type=event_type, intent=intent, q=q, limit=limit,
    )
    return {"count": len(results), "results": results}


@router.get("/{memory_id}")
def get_memory(memory_id: str, session: Session = Depends(get_session)) -> dict:
    memory = MemoryService(session)._repo.get(memory_id)  # noqa: SLF001 — read-only
    if memory is None:
        raise AppError("memory.not_found", status_code=404)
    return {"memory": memory}


@router.post("/{memory_id}/promote", status_code=200)
def promote_memory(memory_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        memory = MemoryService(session).promote(memory_id)
    except KeyError:
        raise AppError("memory.not_found", status_code=404) from None
    session.commit()
    return {"memory": memory}


@router.post("/from-experience/{card_id}", status_code=201)
def memory_from_experience(card_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        memory = MemoryService(session).from_experience(card_id)
    except KeyError:
        raise AppError("experience.not_found", status_code=404) from None
    except ValueError as exc:
        raise AppError("memory.not_approved", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"memory": memory}
