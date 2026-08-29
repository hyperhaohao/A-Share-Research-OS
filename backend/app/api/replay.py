"""Replay feedback API (V2 Phase J, 总纲 §79)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.replay_service import ReplayFeedbackService, ReplayRefusal

router = APIRouter(prefix="/reviews", tags=["replay"])


class FeedbackIn(BaseModel):
    decision_id: str = Field(min_length=6, max_length=32)


@router.post("/feedback", status_code=201)
def feedback_from_decision(payload: FeedbackIn, session: Session = Depends(get_session)) -> dict:
    try:
        result = ReplayFeedbackService(session).feedback_from_decision(payload.decision_id)
    except KeyError:
        raise AppError("monitor.not_found", status_code=404) from None
    except ReplayRefusal as exc:
        raise AppError("replay.chain_incomplete", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"feedback": result}
