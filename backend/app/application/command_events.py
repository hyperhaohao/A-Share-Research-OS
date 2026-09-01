"""帷幄 Commander Event Protocol（F5，第三轮整改任务书 §8.3/§8.4）.

统一、append-only、可回放的事件协议：

  - Envelope：event_id / session_id / sequence / event_type / created_at /
    correlation_id / plan_id / task_id / status / payload / artifact_ids /
    provenance；
  - 每个 Session 内 sequence 单调递增（唯一约束 + 追加重试保证并发安全）；
  - 事件只能追加，不提供覆写/删除路径；
  - Tool Call 与 Tool Result 通过 correlation_id 关联；
  - Artifact 可反查产生它的事件（artifact_ids 落事件 + 事件查询）；
  - payload 携带 schema_version（版本化）；
  - 敏感字段不进入明文事件（submit 前过滤）；
  - 重放事件不重复执行副作用（回放是纯读，见 command_events API/SSE）。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.command_events_orm import CommandEventORM

EVENT_SCHEMA_VERSION = "v1"

# §8.3 最低事件类型
EVENT_TYPES: tuple[str, ...] = (
    "user_message",
    "assistant_delta",
    "assistant_message",
    "plan_created",
    "plan_updated",
    "step_started",
    "step_updated",
    "tool_call",
    "tool_result",
    "tool_error",
    "artifact_created",
    "workbench_open_requested",
    "confirmation_requested",
    "confirmation_decided",
    "task_started",
    "task_progress",
    "task_completed",
    "task_failed",
    "memory_compacted",
    "run_completed",
    "run_failed",
    # 系统级补充（会话治理/恢复）
    "session_created",
)

# 敏感字段不得进入明文事件日志（任务书 §8.3/§15）
_SENSITIVE_KEYS = {"api_key", "password", "token", "secret", "authorization", "cookie"}

_emitter_lock = threading.Lock()


def _sanitize(payload: dict) -> dict:
    """递归剔除敏感键（明文事件日志红线）。"""
    out: dict = {}
    for key, value in (payload or {}).items():
        if str(key).lower() in _SENSITIVE_KEYS:
            out[str(key)] = "[redacted]"
        elif isinstance(value, dict):
            out[str(key)] = _sanitize(value)
        else:
            out[str(key)] = value
    return out


def _to_envelope(row: CommandEventORM) -> dict:
    return {
        "event_id": row.event_id,
        "session_id": row.session_id,
        "sequence": row.sequence,
        "event_type": row.event_type,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "correlation_id": row.correlation_id,
        "plan_id": row.plan_id,
        "task_id": row.task_id,
        "status": row.status,
        "payload": dict(row.payload_json or {}),
        "artifact_ids": list(row.artifact_ids_json or []),
        "provenance": dict(row.provenance_json or {}),
    }


def append_event(
    session: Session,
    session_id: str,
    event_type: str,
    *,
    payload: dict | None = None,
    correlation_id: str | None = None,
    plan_id: str | None = None,
    task_id: str | None = None,
    status: str | None = None,
    artifact_ids: list[str] | None = None,
    provenance: dict | None = None,
) -> dict:
    """追加一个事件（session 内 sequence 单调递增；并发下唯一约束重试）。"""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown command event_type: {event_type}")

    clean_payload = _sanitize(dict(payload or {}))
    clean_payload.setdefault("schema_version", EVENT_SCHEMA_VERSION)
    last_err: Exception | None = None
    for _attempt in range(5):
        try:
            with _emitter_lock:
                next_seq = (
                    session.scalar(
                        select(func.max(CommandEventORM.sequence)).where(
                            CommandEventORM.session_id == session_id
                        )
                    )
                    or 0
                ) + 1
                row = CommandEventORM(
                    event_id=f"evt_{uuid4().hex[:24]}",
                    session_id=session_id,
                    sequence=next_seq,
                    event_type=event_type,
                    created_at=datetime.now(timezone.utc),
                    correlation_id=correlation_id,
                    plan_id=plan_id,
                    task_id=task_id,
                    status=status,
                    payload_json=clean_payload,
                    artifact_ids_json=list(artifact_ids or []),
                    provenance_json=dict(provenance or {}),
                )
                session.add(row)
                session.flush()
                return _to_envelope(row)
        except Exception as exc:  # noqa: BLE001 — 唯一约束竞争 → 重试
            last_err = exc
            session.rollback()
    raise RuntimeError(f"command event append failed after retries: {last_err}")


def list_events(
    session: Session,
    session_id: str,
    *,
    after_sequence: int = 0,
    limit: int = 200,
) -> list[dict]:
    """回放：after_sequence 之后的事件（升序；重放为纯读，无副作用）。"""
    stmt = (
        select(CommandEventORM)
        .where(CommandEventORM.session_id == session_id)
        .where(CommandEventORM.sequence > after_sequence)
        .order_by(CommandEventORM.sequence.asc())
        .limit(limit)
    )
    return [_to_envelope(r) for r in session.scalars(stmt).all()]


def latest_sequence(session: Session, session_id: str) -> int:
    return (
        session.scalar(
            select(func.max(CommandEventORM.sequence)).where(
                CommandEventORM.session_id == session_id
            )
        )
        or 0
    )


def events_for_artifact(session: Session, artifact_id: str) -> list[dict]:
    """Artifact 反查产生它的事件（§8.3：Artifact 必须可反查事件与工具）。"""
    stmt = (
        select(CommandEventORM)
        .where(CommandEventORM.artifact_ids_json.contains([artifact_id]))
        .order_by(CommandEventORM.created_at.asc())
        .limit(20)
    )
    return [_to_envelope(r) for r in session.scalars(stmt).all()]


def encode_sse(event: dict) -> str:
    """SSE 帧：id=sequence（重连续点）、event=type、data=完整 envelope。"""
    data = json.dumps(event, ensure_ascii=False)
    return f"id: {event['sequence']}\nevent: {event['event_type']}\ndata: {data}\n\n"
