"""帷幄会话治理 + 双层记忆 + 长对话压缩（F9，任务书 §8.9 P0-WEIWO）.

会话治理：
  - 重命名 / 归档（status=active|archived）/ 状态与最后活动时间；
  - 关联 Instrument / Thesis / Plan / Task（经 plans/workbench/tasks 反查）。

双层记忆：
  - Session Memory（command_session_memory）：当前目标、已确认参数、
    关键结论、未决问题；
  - Research Memory：既有的 research_memories（R7，candidate→active→retired）。

长对话压缩：
  - 达到轮次阈值 → 生成**确定性**结构化摘要（实体/计划/产物/未决问题）；
  - 摘要版本可追溯（summary_version 单调 + compacted_at）；
  - 原始事件仍可审计（append-only 事件不动）；
  - 压缩显形为 memory_compacted 事件（Memory 注入在事件中披露，§8.9）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.background_orm import SessionMemoryORM
from app.application.command_events import append_event
from app.application.conversation import ConversationRepository, ConversationTurnORM
from app.storage.research_orm import ThesisORM


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 会话治理 ─────────────────────────────────────────────────────────────────


def rename_session(session: Session, session_id: str, title: str) -> dict | None:
    from app.application.conversation import ConversationSessionORM

    row = session.scalars(
        select(ConversationSessionORM).where(ConversationSessionORM.session_id == session_id)
    ).first()
    if row is None:
        return None
    row.title = title[:128]
    row.last_activity_at = _now()
    session.flush()
    return {"session_id": session_id, "title": row.title, "status": row.status}


def archive_session(session: Session, session_id: str, *, archived: bool = True) -> dict | None:
    from app.application.conversation import ConversationSessionORM

    row = session.scalars(
        select(ConversationSessionORM).where(ConversationSessionORM.session_id == session_id)
    ).first()
    if row is None:
        return None
    row.status = "archived" if archived else "active"
    row.last_activity_at = _now()
    session.flush()
    return {"session_id": session_id, "status": row.status}


def touch_session(session: Session, session_id: str) -> None:
    from app.application.conversation import ConversationSessionORM

    row = session.scalars(
        select(ConversationSessionORM).where(ConversationSessionORM.session_id == session_id)
    ).first()
    if row is not None:
        row.last_activity_at = _now()
        session.flush()


def session_overview(session: Session, session_id: str) -> dict | None:
    """会话治理概览：状态 + 关联对象（Instrument/Thesis/Plan/Workbench/Task）。"""
    from app.application.background_orm import BackgroundTaskORM
    from app.services.workbench import list_tabs

    from app.application.conversation import ConversationSessionORM

    row = session.scalars(
        select(ConversationSessionORM).where(ConversationSessionORM.session_id == session_id)
    ).first()
    if row is None:
        return None
    plans = ConversationRepository(session).list_plans(session_id, limit=20)
    instruments = sorted({p["instrument_id"] for p in plans if p.get("instrument_id")})
    current_theses = {}
    for instrument_id in instruments[:5]:
        thesis = session.scalars(
            select(ThesisORM)
            .where(ThesisORM.instrument_id == instrument_id)
            .order_by(ThesisORM.created_at.desc(), ThesisORM.id.desc())
            .limit(1)
        ).first()
        if thesis is not None:
            current_theses[instrument_id] = thesis.thesis_id
    tasks = session.scalars(
        select(BackgroundTaskORM)
        .where(BackgroundTaskORM.command_session_id == session_id)
        .order_by(BackgroundTaskORM.created_at.desc(), BackgroundTaskORM.id.desc())
        .limit(20)
    ).all()
    return {
        "session_id": session_id,
        "title": row.title,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_activity_at": (
            row.last_activity_at.isoformat() if row.last_activity_at else None
        ),
        "instruments": instruments,
        "current_theses": current_theses,
        "plans": [{"plan_id": p["plan_id"], "title": p["title"], "status": p["status"]} for p in plans],
        "workbench_tabs": list_tabs(session, session_id),
        "tasks": [
            {"task_id": t.task_id, "tool_name": t.tool_name, "status": t.status}
            for t in tasks
        ],
    }


# ── 双层记忆：Session Memory ─────────────────────────────────────────────────


def get_memory(session: Session, session_id: str) -> dict:
    row = session.scalars(
        select(SessionMemoryORM).where(SessionMemoryORM.session_id == session_id)
    ).first()
    if row is None:
        return {
            "session_id": session_id, "goal": None, "confirmed_params": {},
            "key_conclusions": [], "open_questions": [], "summary_text": None,
            "summary_version": 0, "compacted_at": None,
        }
    return {
        "session_id": session_id,
        "goal": row.goal,
        "confirmed_params": dict(row.confirmed_params_json or {}),
        "key_conclusions": list(row.key_conclusions_json or []),
        "open_questions": list(row.open_questions_json or []),
        "summary_text": row.summary_text,
        "summary_version": row.summary_version,
        "compacted_at": row.compacted_at.isoformat() if row.compacted_at else None,
    }


def upsert_memory(session: Session, session_id: str, **fields) -> dict:
    """更新会话记忆（goal/confirmed_params/key_conclusions/open_questions）。"""
    row = session.scalars(
        select(SessionMemoryORM).where(SessionMemoryORM.session_id == session_id)
    ).first()
    if row is None:
        row = SessionMemoryORM(
            session_id=session_id, summary_version=0, updated_at=_now(),
            confirmed_params_json={}, key_conclusions_json=[], open_questions_json=[],
        )
        session.add(row)
    if "goal" in fields and fields["goal"] is not None:
        row.goal = str(fields["goal"])[:4000]
    if "confirmed_params" in fields and fields["confirmed_params"] is not None:
        row.confirmed_params_json = dict(fields["confirmed_params"])
    if "key_conclusions" in fields and fields["key_conclusions"] is not None:
        row.key_conclusions_json = [str(x)[:500] for x in fields["key_conclusions"]]
    if "open_questions" in fields and fields["open_questions"] is not None:
        row.open_questions_json = [str(x)[:500] for x in fields["open_questions"]]
    row.updated_at = _now()
    session.flush()
    return get_memory(session, session_id)


# ── 长对话压缩 ───────────────────────────────────────────────────────────────


def maybe_compact(
    session: Session,
    session_id: str,
    *,
    threshold_turns: int = 50,
    force: bool = False,
) -> dict:
    """达到轮次阈值 → 确定性结构化压缩；摘要版本可追溯，原始事件不动。"""
    repo = ConversationRepository(session)
    turns = session.scalars(
        select(ConversationTurnORM)
        .where(ConversationTurnORM.session_id == session_id)
        .order_by(ConversationTurnORM.created_at.asc())
        .limit(500)
    ).all()
    if not force and len(turns) < threshold_turns:
        return {"compacted": False, "turn_count": len(turns),
                "reason": f"below threshold ({threshold_turns})"}

    plans = repo.list_plans(session_id, limit=50)
    memory = get_memory(session, session_id)
    user_intents = [t.text[:120] for t in turns if t.role == "user"][-10:]
    refusal_turns = [
        t.text[:120] for t in turns
        if t.role == "commander" and "无法" in (t.text or "")
    ][-5:]
    summary = {
        "turn_count": len(turns),
        "user_requests": user_intents,
        "plans": [
            {"title": p["title"], "status": p["status"], "run_id": p.get("run_id")}
            for p in plans
        ],
        "artifacts": sorted(
            {
                aid
                for t in turns
                for aid in (t.artifact_ids_json or [])
            }
        )[-20:],
        "key_conclusions": memory.get("key_conclusions", []),
        "open_questions": memory.get("open_questions", [])
        + [r for r in refusal_turns if r not in memory.get("open_questions", [])],
        "instruments": sorted({p["instrument_id"] for p in plans if p.get("instrument_id")}),
    }

    row = session.scalars(
        select(SessionMemoryORM).where(SessionMemoryORM.session_id == session_id)
    ).first()
    if row is None:
        row = SessionMemoryORM(
            session_id=session_id, summary_version=0, updated_at=_now(),
            confirmed_params_json={}, key_conclusions_json=[], open_questions_json=[],
        )
        session.add(row)
    row.summary_text = str(summary)[:8000]
    row.summary_version = (row.summary_version or 0) + 1
    row.compacted_at = _now()
    row.updated_at = _now()
    session.flush()

    append_event(
        session, session_id, "memory_compacted",
        payload={
            "summary_version": row.summary_version,
            "turn_count": len(turns),
            "note": "原始事件仍可审计（append-only）；摘要在事件中披露注入",
        },
    )
    return {
        "compacted": True,
        "summary_version": row.summary_version,
        "turn_count": len(turns),
        "summary": summary,
    }
