"""Command center API (V2 Phase B, 总纲 §38/§42/§71).

对话 → ResearchPlan → 执行 → Artifact → 右栏报告。用户文本先做确定性
解析；无法识别标的时记录一轮显式拒绝回复（不是 500，也不是猜一个标的）。
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.conversation import ConversationRepository
from app.db import get_session, session_scope
from app.services.commander import (
    INTENT_TITLES,
    ResearchCommander,
    build_plan_steps,
    find_registry_name_in_text,
    interpret_command,
)

router = APIRouter(prefix="/command", tags=["command"])


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/sessions", status_code=201)
def create_session(session: Session = Depends(get_session)) -> dict:
    created = ConversationRepository(session).create_session("研究对话")
    session.commit()
    return {"session": created}


@router.get("/sessions")
def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    results = ConversationRepository(session).list_sessions(limit=limit)
    return {"count": len(results), "results": results}


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: str,
    session: Session = Depends(get_session),
) -> dict:
    repo = ConversationRepository(session)
    detail = repo.get_session(session_id)
    if detail is None:
        from app.core.errors import AppError

        raise AppError("session.not_found", status_code=404)
    return {
        "session": detail,
        "turns": repo.list_turns(session_id),
        "plans": repo.list_plans(session_id),
    }


@router.post("/sessions/{session_id}/turns", status_code=202)
def post_turn(
    session_id: str,
    payload: TurnIn,
    session: Session = Depends(get_session),
) -> dict:
    """One user command → deterministic interpretation → ResearchPlan →
    background execution (202; progress via GET /command/plans/{id})."""
    from app.core.errors import AppError

    repo = ConversationRepository(session)
    if repo.get_session(session_id) is None:
        raise AppError("session.not_found", status_code=404)

    text = payload.text.strip()
    user_turn = repo.add_turn(session_id, role="user", text=text)

    interp = interpret_command(text)
    if interp.instrument_hint is None:
        interp.instrument_hint = find_registry_name_in_text(session, text)
    if interp.instrument_hint is None:
        # explicit refusal — never guess an instrument (红线 8 显形)
        reply = (
            "无法从这句话识别研究标的。请给出 6 位代码或股票名称，"
            "例如：研究中国稀土最近的资产重组迹象。"
        )
        refusal = repo.add_turn(session_id, role="commander", text=reply)
        session.commit()
        return {"turn": user_turn, "reply": refusal, "plan": None}

    steps = build_plan_steps(interp)
    plan = repo.create_plan(
        title=f"{INTENT_TITLES[interp.intent]} {interp.instrument_hint}",
        steps=steps,
        session_id=session_id,
    )
    reply_text = "已创建研究计划：" + " → ".join(s.title for s in steps)
    commander_turn = repo.add_turn(
        session_id, role="commander", text=reply_text, plan_id=plan["plan_id"]
    )
    # commit before the worker thread opens its own session (cross-connection
    # visibility — same contract as POST /tasks/{id}/run)
    session.commit()
    thread = threading.Thread(
        target=_execute_plan_in_background,
        args=(session.get_bind(), plan["plan_id"]),
        daemon=True,
    )
    thread.start()
    return {"turn": user_turn, "reply": commander_turn, "plan": plan}


def _execute_plan_in_background(engine, plan_id: str) -> None:
    """Worker thread: own session on the same engine (mirror run-now)."""
    from sqlalchemy.orm import sessionmaker

    from app.application.conversation import ConversationRepository

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        plan = ConversationRepository(worker_session).get_plan(plan_id)
        if plan is None:
            return
        try:
            ResearchCommander(worker_session).execute(plan)
        except Exception:  # noqa: BLE001 — never kill the process on a plan
            worker_session.rollback()
            ConversationRepository(worker_session).update_plan(
                plan_id, lambda p: {**p, "status": "failed", "error": "plan execution crashed"}
            )


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, session: Session = Depends(get_session)) -> dict:
    from app.core.errors import AppError

    plan = ConversationRepository(session).get_plan(plan_id)
    if plan is None:
        raise AppError("plan.not_found", status_code=404)
    return {"plan": plan}


@router.get("/plans")
def list_plans(
    session_id: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    results = ConversationRepository(session).list_plans(session_id, limit=limit)
    return {"count": len(results), "results": results}
