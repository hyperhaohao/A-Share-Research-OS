"""帷幄审批确认状态机（F7，第三轮整改任务书 §8.6 P0-WEIWO）.

状态机（§8.6）：

    pending → approved | rejected | expired | revoked → consumed

规则：
  - 前端卡片只展示服务端真实状态（状态只存在本表）；
  - 确认内容带参数摘要 digest —— 批准后参数不可被替换（防 TOCTOU）；
  - lease/timeout：pending 超过 expires_at → expired（读取/决定时惰性判定）；
  - 重复点击幂等：对非 pending 行重复 decide → 返回当前状态，无副作用；
  - 拒绝后不发生副作用（工具不执行）；
  - 所有决定落库（本表 decided_at/decided_by）+ 帷幄事件
    confirmation_requested / confirmation_decided（审计）；
  - approved 后一次性消费：执行成功即 consumed；未消费可 revoked。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.command_events import append_event
from app.services.tool_registry import get_tool

STATUSES = ("pending", "approved", "rejected", "expired", "revoked", "consumed")
DECISIONS = ("approved", "rejected", "revoked")

MIN_LEASE_S = 5
DEFAULT_LEASE_S = 300


def arguments_digest(tool_name: str, arguments: dict) -> str:
    """参数摘要（规范化排序 → sha256 前 64 hex；与工具执行绑定）。"""
    canonical = json.dumps(
        {"tool": tool_name, "arguments": arguments},
        ensure_ascii=False, sort_keys=True, default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CommandConfirmationORM:
    """ORM 在 confirmations_orm.py 定义；此处仅引用。"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row) -> dict:
    return {
        "confirmation_id": row.confirmation_id,
        "command_session_id": row.command_session_id,
        "tool_name": row.tool_name,
        "arguments": dict(row.arguments_json or {}),
        "arguments_digest": row.arguments_digest,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "consumed_at": row.consumed_at.isoformat() if row.consumed_at else None,
        "decided_by": row.decided_by,
    }


def _get_row(session: Session, confirmation_id: str):
    from app.application.confirmations_orm import CommandConfirmationORM as ORM

    return session.scalars(
        select(ORM).where(ORM.confirmation_id == confirmation_id)
    ).first()


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _expire_if_due(session: Session, row) -> None:
    expires = _ensure_aware(row.expires_at)
    if row.status == "pending" and expires is not None and expires <= _now():
        row.status = "expired"
        row.decided_at = _now()
        session.flush()


def create_confirmation(
    session: Session,
    *,
    tool_name: str,
    arguments: dict,
    command_session_id: str | None = None,
    lease_s: int = DEFAULT_LEASE_S,
    decided_by: str | None = None,
) -> dict:
    """为高风险工具创建 pending 确认（非高风险/未知工具 → ValueError）。"""
    from app.application.confirmations_orm import CommandConfirmationORM as ORM

    spec = get_tool(tool_name)
    if spec is None:
        raise ValueError(f"unknown tool: {tool_name}")
    if not spec.requires_confirmation:
        raise ValueError(f"tool does not require confirmation: {tool_name}")

    lease_s = max(int(lease_s), MIN_LEASE_S)
    now = _now()
    row = ORM(
        confirmation_id=f"cfm_{uuid4().hex[:24]}",
        command_session_id=command_session_id,
        tool_name=tool_name,
        arguments_json=dict(arguments or {}),
        arguments_digest=arguments_digest(tool_name, arguments or {}),
        status="pending",
        created_at=now,
        expires_at=now + timedelta(seconds=lease_s),
        decided_by=decided_by,
    )
    session.add(row)
    session.flush()
    if command_session_id:
        append_event(
            session, command_session_id, "confirmation_requested",
            correlation_id=row.confirmation_id, status="pending",
            payload={
                "tool": tool_name,
                "arguments": dict(arguments or {}),
                "arguments_digest": row.arguments_digest,
                "expires_at": row.expires_at.isoformat(),
            },
        )
    return _row_to_dict(row)


def decide_confirmation(
    session: Session,
    confirmation_id: str,
    decision: str,
    *,
    decided_by: str | None = None,
) -> dict:
    """批准/拒绝/撤销。幂等：终态重复决定返回当前状态（无副作用）。

    状态机（§8.6）：pending → approved|rejected|expired|revoked；
    approved（未消费）→ revoked；consumed/rejected/expired 为终态。
    """
    row = _get_row(session, confirmation_id)
    if row is None:
        raise LookupError(f"confirmation not found: {confirmation_id}")
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision: {decision}")

    _expire_if_due(session, row)

    if decision == "approved":
        if row.status != "pending":
            return _row_to_dict(row)  # 幂等：非 pending 不可批准
        row.status = "approved"
    elif decision == "rejected":
        if row.status != "pending":
            return _row_to_dict(row)  # 幂等：仅 pending 可拒绝
        row.status = "rejected"  # 拒绝后无副作用（工具不执行）
    else:  # revoked：pending 或 approved（未消费）可撤销；终态保持
        if row.status in ("consumed", "rejected", "expired"):
            return _row_to_dict(row)
        if row.status == "revoked":
            return _row_to_dict(row)
        row.status = "revoked"

    row.decided_at = _now()
    if decided_by:
        row.decided_by = decided_by
    session.flush()

    if row.command_session_id:
        append_event(
            session, row.command_session_id, "confirmation_decided",
            correlation_id=row.confirmation_id, status=row.status,
            payload={
                "tool": row.tool_name,
                "decision": row.status,
                "arguments_digest": row.arguments_digest,
            },
        )
    return _row_to_dict(row)


def get_confirmation(session: Session, confirmation_id: str) -> dict | None:
    row = _get_row(session, confirmation_id)
    if row is None:
        return None
    _expire_if_due(session, row)
    return _row_to_dict(row)


def list_confirmations(
    session: Session, *, status: str | None = None, limit: int = 50
) -> list[dict]:
    from app.application.confirmations_orm import CommandConfirmationORM as ORM

    # 惰性过期清理（本页可见范围）
    for row in session.scalars(
        select(ORM).where(ORM.status == "pending").limit(limit)
    ).all():
        _expire_if_due(session, row)
    stmt = select(ORM).order_by(ORM.created_at.desc(), ORM.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(ORM.status == status)
    return [_row_to_dict(r) for r in session.scalars(stmt).all()]


def consume_confirmation_record(
    session: Session,
    confirmation_id: str,
    *,
    tool_name: str,
    arguments_digest_value: str,
) -> tuple[bool, str | None]:
    """执行前消费：approved + digest 匹配 + 未过期未消费 → consumed。

    Returns: (ok, error_code)
    """
    row = _get_row(session, confirmation_id)
    if row is None:
        return False, "tool.confirmation_invalid"
    _expire_if_due(session, row)
    if row.status != "approved":
        return False, "tool.confirmation_invalid"
    if row.tool_name != tool_name or row.arguments_digest != arguments_digest_value:
        return False, "tool.confirmation_invalid"
    row.status = "consumed"
    row.consumed_at = _now()
    session.flush()
    return True, None
