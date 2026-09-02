"""帷幄后台任务跑道（F9，第三轮整改任务书 §8.8 P0-WEIWO）.

长任务与对话解耦：

    Confirm → Background Task（持久化）→ Progress Events →
    用户继续对话 → Complete / Fail / Retry → Notification（事件流）→
    Artifact Auto-open → Archive

规则（§8.8）：
  - 任务持久化于 command_background_tasks —— 不依赖进程内 daemon thread
    （由 Scheduler Worker 循环泵执行；worker 重启后 lease 过期任务被恢复）；
  - 会话级 + 全局任务列表；
  - 进度（progress/current_step/started/耗时/重试次数）真实落库；
  - 同一昂贵任务合并（queued/running 且 digest 相同 → 返回既有任务）；
  - 失败自动重试（attempts < max_attempts → 重新入队），最终失败显形原因；
  - 可安全取消（queued/running → cancelled；worker 执行前校验租约）；
  - 完成 → 任务进会话事件流（task_completed）+ Artifact 自动打开 Workbench。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.background_orm import BackgroundTaskORM
from app.application.command_events import append_event
from app.services.confirmation_gate import arguments_digest, consume_confirmation_record
from app.services.tool_registry import execute_tool, get_tool

DEFAULT_LEASE_S = 120


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row: BackgroundTaskORM) -> dict:
    started = row.started_at.isoformat() if row.started_at else None
    finished = row.finished_at.isoformat() if row.finished_at else None
    elapsed_ms = None
    if row.started_at is not None and row.finished_at is not None:
        delta = row.finished_at - row.started_at
        elapsed_ms = int(delta.total_seconds() * 1000)
    return {
        "task_id": row.task_id,
        "command_session_id": row.command_session_id,
        "tool_name": row.tool_name,
        "arguments": dict(row.arguments_json or {}),
        "status": row.status,
        "progress": row.progress,
        "current_step": row.current_step,
        "attempts": row.attempts,
        "max_attempts": row.max_attempts,
        "worker_id": row.worker_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": started,
        "finished_at": finished,
        "elapsed_ms": elapsed_ms,
        "last_error": row.last_error,
        "result": dict(row.result_json or {}) if row.result_json else None,
    }


def _emit(session: Session, row: BackgroundTaskORM, event_type: str, **kw) -> None:
    if row.command_session_id:
        payload = {
            "task_id": row.task_id, "tool": row.tool_name,
            "status": row.status, "progress": row.progress,
            "current_step": row.current_step,
        }
        payload.update(kw.get("payload", {}))
        append_event(
            session, row.command_session_id, event_type,
            correlation_id=row.task_id, task_id=row.task_id,
            status=row.status, payload=payload,
        )


def submit_task(
    session: Session,
    *,
    tool_name: str,
    arguments: dict,
    command_session_id: str | None = None,
    confirmation_id: str | None = None,
    max_attempts: int = 3,
) -> dict:
    """提交后台任务（持久化 + 合并 + 高风险需已批准确认）。"""
    spec = get_tool(tool_name)
    if spec is None:
        raise LookupError(f"unknown tool: {tool_name}")
    if spec.risk_level == "high":
        if not confirmation_id:
            raise ValueError("high-risk tool requires a consumed confirmation first")
        ok, err = consume_confirmation_record(
            session, confirmation_id,
            tool_name=tool_name,
            arguments_digest_value=arguments_digest(tool_name, arguments or {}),
        )
        if not ok:
            raise ValueError(f"confirmation invalid: {err}")

    digest = arguments_digest(tool_name, arguments or {})
    # 合并策略：同 digest 的 queued/running 任务直接复用（§8.8 幂等/合并）
    existing = session.scalars(
        select(BackgroundTaskORM)
        .where(BackgroundTaskORM.tool_name == tool_name)
        .where(BackgroundTaskORM.arguments_digest == digest)
        .where(BackgroundTaskORM.status.in_(("queued", "running")))
        .limit(1)
    ).first()
    if existing is not None:
        return _row_to_dict(existing)

    row = BackgroundTaskORM(
        task_id=f"bgt_{uuid4().hex[:24]}",
        command_session_id=command_session_id,
        tool_name=tool_name,
        arguments_json=dict(arguments or {}),
        arguments_digest=digest,
        status="queued",
        max_attempts=max(1, int(max_attempts)),
        created_at=_now(),
    )
    session.add(row)
    session.flush()
    _emit(session, row, "task_started")
    return _row_to_dict(row)


def claim_next(session: Session, *, worker_id: str, lease_s: int = DEFAULT_LEASE_S) -> dict | None:
    """认领下一个任务：queued 或 lease 过期的 running（worker 重启恢复，§8.8）。"""
    now = _now()
    row = session.scalars(
        select(BackgroundTaskORM)
        .where(BackgroundTaskORM.status == "queued")
        .order_by(BackgroundTaskORM.created_at.asc())
        .limit(1)
    ).first()
    if row is None:
        # 恢复：lease 过期的 running（前一个 worker 崩溃/重启）
        row = session.scalars(
            select(BackgroundTaskORM)
            .where(BackgroundTaskORM.status == "running")
            .where(BackgroundTaskORM.lease_expires_at.is_not(None))
            .where(BackgroundTaskORM.lease_expires_at < now)
            .order_by(BackgroundTaskORM.started_at.asc())
            .limit(1)
        ).first()
    if row is None:
        return None
    row.status = "running"
    row.worker_id = worker_id
    row.lease_expires_at = now + timedelta(seconds=lease_s)
    row.heartbeat_at = now
    row.started_at = row.started_at or now
    row.attempts = (row.attempts or 0) + 1
    row.progress = max(row.progress or 0, 5)
    row.current_step = f"executing {row.tool_name}"
    session.flush()
    return _row_to_dict(row)


def run_one(session: Session, *, worker_id: str = "scheduler", lease_s: int = DEFAULT_LEASE_S) -> dict | None:
    """认领并执行一个后台任务（由 Scheduler.tick 泵驱动）。"""
    row_row = claim_next(session, worker_id=worker_id, lease_s=lease_s)
    if row_row is None:
        return None
    row = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == row_row["task_id"])
    ).first()
    if row is None:
        return None
    session.commit()  # 认领落库（跨连接可见）

    # 取消安全：取消后不再执行
    fresh = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == row.task_id)
    ).first()
    if fresh is None or fresh.status != "running":
        return _row_to_dict(row)

    out = execute_tool(
        session, row.tool_name, dict(row.arguments_json or {}),
        command_session_id=row.command_session_id,
        correlation_id=row.task_id,
    )
    finished = _now()
    fresh = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == row.task_id)
    ).first()
    if fresh is None:
        return None
    fresh.finished_at = finished
    fresh.lease_expires_at = None
    if out.get("ok"):
        fresh.status = "succeeded"
        fresh.progress = 100
        fresh.current_step = "done"
        fresh.result_json = dict(out.get("result") or {})
        fresh.attempts = (fresh.attempts or 0)
        _emit(session, fresh, "task_completed", payload={"elapsed_ms": out.get("duration_ms")})
        artifact_ids = list(out.get("artifact_ids") or [])
        if artifact_ids and fresh.command_session_id:
            from app.services.workbench import open_for_artifacts

            open_for_artifacts(session, fresh.command_session_id, artifact_ids)
    else:
        fresh.last_error = (out.get("detail") or "")[:500]
        if (fresh.attempts or 0) < (fresh.max_attempts or 1):
            fresh.status = "queued"  # 自动重试
            fresh.current_step = f"retry {fresh.attempts}/{fresh.max_attempts}"
            _emit(session, fresh, "task_progress",
                  payload={"retry": fresh.attempts, "error": fresh.last_error})
        else:
            fresh.status = "failed"
            fresh.current_step = "failed"
            fresh.dead_letter = True  # G12：超过重试上限 → dead-letter 标记
            _emit(session, fresh, "task_failed", payload={"error": fresh.last_error})
    session.commit()
    return _row_to_dict(fresh)


def cancel_task(session: Session, task_id: str) -> dict | None:
    """安全取消：queued/running → cancelled（已终态任务不可取消）。"""
    row = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
    ).first()
    if row is None:
        return None
    if row.status in ("queued", "running"):
        row.status = "cancelled"
        row.finished_at = _now()
        row.current_step = "cancelled"
        _emit(session, row, "task_failed", payload={"cancelled": True})
    session.flush()
    return _row_to_dict(row)


def retry_task(session: Session, task_id: str) -> dict | None:
    """手动恢复入口：failed/cancelled → queued（attempts 保留）。"""
    row = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
    ).first()
    if row is None:
        return None
    if row.status in ("failed", "cancelled"):
        row.status = "queued"
        row.progress = 0
        row.current_step = "requeued"
        _emit(session, row, "task_progress", payload={"requeued": True})
    session.flush()
    return _row_to_dict(row)


def pause_task(session: Session, task_id: str) -> dict | None:
    """G12：queued → paused（人工暂停；paused 不被泵认领）。"""
    row = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
    ).first()
    if row is None:
        return None
    if row.status == "queued":
        row.status = "paused"
        row.current_step = "paused"
        _emit(session, row, "task_progress", payload={"paused": True})
    session.flush()
    return _row_to_dict(row)


def resume_task(session: Session, task_id: str) -> dict | None:
    """paused → queued（恢复执行）。"""
    row = session.scalars(
        select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
    ).first()
    if row is None:
        return None
    if row.status == "paused":
        row.status = "queued"
        row.current_step = "resumed"
        _emit(session, row, "task_progress", payload={"resumed": True})
    session.flush()
    return _row_to_dict(row)


def list_tasks(session: Session, *, command_session_id: str | None = None, limit: int = 50) -> list[dict]:
    """会话级 + 全局任务列表（§8.8）。"""
    stmt = (
        select(BackgroundTaskORM)
        .order_by(BackgroundTaskORM.created_at.desc())
        .limit(limit)
    )
    if command_session_id:
        stmt = stmt.where(BackgroundTaskORM.command_session_id == command_session_id)
    return [_row_to_dict(r) for r in session.scalars(stmt).all()]
