"""Command center API (V2 Phase B, 总纲 §38/§42/§71).

对话 → ResearchPlan → 执行 → Artifact → 右栏报告。用户文本先做确定性
解析；无法识别标的时记录一轮显式拒绝回复（不是 500，也不是猜一个标的）。
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.command_events_orm import CommandEventORM  # noqa: F401 — 注册 Base metadata（create_all/迁移前置）
from app.application.conversation import ConversationRepository
from app.db import get_session, session_scope
from app.services.commander import (
    INTENT_TITLES,
    ResearchCommander,
    build_plan_steps,
    find_registry_name_in_text,
    build_plan_meta,
    interpret_command,
)

router = APIRouter(prefix="/command", tags=["command"])


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/sessions", status_code=201)
def create_session(session: Session = Depends(get_session)) -> dict:
    from app.application.command_events import append_event

    created = ConversationRepository(session).create_session("研究对话")
    sid = created["session_id"]
    append_event(session, sid, "session_created",
                 payload={"title": created.get("title")})
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
    from app.application.command_events import append_event

    append_event(session, session_id, "user_message",
                 payload={"text": text, "turn_id": user_turn["turn_id"]})

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
        append_event(session, session_id, "assistant_message",
                     payload={"text": reply, "refusal": True})
        session.commit()
        return {"turn": user_turn, "reply": refusal, "plan": None}

    steps = build_plan_steps(interp)
    plan = repo.create_plan(
        title=f"{INTENT_TITLES[interp.intent]} {interp.instrument_hint}",
        steps=steps,
        session_id=session_id,
        meta=build_plan_meta(interp),
    )
    reply_text = "已创建研究计划：" + " → ".join(s.title for s in steps)
    commander_turn = repo.add_turn(
        session_id, role="commander", text=reply_text, plan_id=plan["plan_id"]
    )
    append_event(
        session, session_id, "plan_created",
        plan_id=plan["plan_id"],
        payload={"plan_id": plan["plan_id"], "title": plan["title"],
                 "steps": [
                     {"step_id": st["step_id"], "title": st["title"],
                      "action": st.get("action")}
                     for st in plan["steps"]
                 ]},
    )
    append_event(
        session, session_id, "assistant_message",
        plan_id=plan["plan_id"], payload={"text": reply_text},
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


# ── F5：帷幄事件回放 / Snapshot / Live SSE（任务书 §8.3/§8.4） ────────────────


@router.get("/sessions/{session_id}/events")
def list_session_events(
    session_id: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
) -> dict:
    """事件回放（纯读；重放不重复执行副作用）。"""
    from app.application.command_events import latest_sequence, list_events

    results = list_events(session, session_id, after_sequence=after_sequence, limit=limit)
    return {
        "session_id": session_id,
        "latest_sequence": latest_sequence(session, session_id),
        "count": len(results),
        "results": results,
    }


@router.get("/sessions/{session_id}/snapshot")
def session_snapshot(
    session_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """连接快照：会话 + 对话 + 计划 + 事件断点（刷新恢复的数据源）。"""
    from app.application.command_events import latest_sequence

    repo = ConversationRepository(session)
    detail = repo.get_session(session_id)
    if detail is None:
        from app.core.errors import AppError

        raise AppError("session.not_found", status_code=404)
    return {
        "session": detail,
        "turns": repo.list_turns(session_id),
        "plans": repo.list_plans(session_id, limit=50),
        "latest_sequence": latest_sequence(session, session_id),
    }


@router.get("/sessions/{session_id}/stream")
def stream_session_events(
    session_id: str,
    after_sequence: int = Query(default=0, ge=0),
    max_seconds: int = Query(default=120, ge=5, le=3600),
    session: Session = Depends(get_session),
):
    """Live SSE（任务书 §8.4）：

    Connect → Session Snapshot 校验 → Replay(after_sequence) → Live Events →
    Heartbeat →（断线）以 last sequence 重连续传。sequence 单调 → 不丢事件、
    不重复展示。每轮 poll 独立短会话（跨连接可见已提交事件）；每轮回放有界
    （limit 500）构成慢客户端背压；达时长上限发 stream_end 注释帧。
    """
    import time

    from fastapi.responses import StreamingResponse
    from sqlalchemy.orm import sessionmaker

    from app.application.command_events import encode_sse, latest_sequence, list_events

    engine = session.get_bind()
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def poll() -> tuple[bool, list[dict], int]:
        from app.application.conversation import ConversationRepository

        with session_scope(factory) as db:
            exists = ConversationRepository(db).get_session(session_id) is not None
            if not exists:
                return False, [], 0
            events = list_events(db, session_id, after_sequence=_cursor[0], limit=500)
            return True, events, latest_sequence(db, session_id)

    from app.application.conversation import ConversationRepository as _CR

    with session_scope(factory) as db:
        if _CR(db).get_session(session_id) is None:
            from app.core.errors import AppError

            raise AppError("session.not_found", status_code=404)

    _cursor = [after_sequence]

    def event_stream():
        yield "retry: 3000\n\n"
        deadline = time.monotonic() + max_seconds
        idle = False
        while time.monotonic() < deadline:
            ok, events, latest = poll()
            if not ok:
                yield "event: run_failed\ndata: {\"error\":\"session.not_found\"}\n\n"
                return
            if events:
                idle = False
                for ev in events:
                    _cursor[0] = max(_cursor[0], ev["sequence"])
                    sent = yield encode_sse(ev)
                    if sent is False:  # client disconnected
                        return
            else:
                _cursor[0] = max(_cursor[0], latest)
                if not idle:
                    idle = True
                time.sleep(0.6)
                yield ": heartbeat\n\n"
        yield ": stream_end\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── F6：帷幄 Tool Registry（任务书 §8.5） ─────────────────────────────────────


@router.get("/tools")
def list_registry_tools() -> dict:
    """工具清单（白名单 + schema + 风险分级；不暴露 executor）。"""
    from app.services.tool_registry import list_tools

    results = list_tools()
    return {"count": len(results), "results": results}


class ToolExecuteIn(BaseModel):
    arguments: dict = Field(default_factory=dict)
    command_session_id: str | None = Field(default=None, max_length=40)
    correlation_id: str | None = Field(default=None, max_length=48)
    confirmation_token: str | None = Field(default=None, max_length=80)


@router.post("/tools/{name}/execute")
def execute_registry_tool(
    name: str,
    payload: ToolExecuteIn,
    session: Session = Depends(get_session),
) -> dict:
    """执行白名单工具：schema 校验 → 确认门 → executor → 结构化结果 + 事件。"""
    from app.services.tool_registry import execute_tool, get_tool

    spec = get_tool(name)
    if spec is None:
        from app.core.errors import AppError

        raise AppError("tool.not_found", status_code=404, detail=f"unknown tool: {name}")

    out = execute_tool(
        session, name, payload.arguments,
        command_session_id=payload.command_session_id,
        correlation_id=payload.correlation_id,
        confirmation_token=payload.confirmation_token,
    )
    session.commit()
    status_code = 200 if out.get("ok") else {
        "tool.not_found": 404,
        "tool.arguments_invalid": 422,
        "tool.confirmation_required": 422,
        "tool.confirmation_invalid": 422,
    }.get(out.get("error_code"), 500)
    return JSONResponse(status_code=status_code, content=out)


# fastapi.responses 导入（模块尾部统一引用）
from fastapi.responses import JSONResponse  # noqa: E402
