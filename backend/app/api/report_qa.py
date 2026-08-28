"""Report ask API (M13): mode=explain | refresh, strictly separated."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.report_qa import ReportQAService
from app.storage.report_repo import ReportRepository

router = APIRouter(prefix="/reports", tags=["reports-qa"])


class AskIn(BaseModel):
    question: str = Field(default="", max_length=2000)
    mode: str = Field(pattern="^(explain|refresh)$")
    copilot: bool = Field(default=False, description="compose the answer with the LLM when configured")


@router.post("/{report_id}/ask")
def ask_report(
    report_id: str,
    payload: AskIn,
    session: Session = Depends(get_session),
) -> dict:
    repo = ReportRepository(session)
    report_row = repo.get(report_id)
    if report_row is None:
        raise AppError("report.not_found", status_code=404)

    service = ReportQAService(session)
    try:
        if payload.mode == "explain":
            if payload.copilot:
                answer = service.explain_with_llm(report_row, payload.question)
            else:
                answer = service.explain(report_row, payload.question)
        else:
            answer = service.refresh(report_row)
    except KeyError:
        raise AppError("snapshot.not_found", status_code=404) from None

    ask_id = service.log_ask(report_id, payload.mode, payload.question, answer)
    return {"ask_id": ask_id, "report_id": report_id, **answer}
