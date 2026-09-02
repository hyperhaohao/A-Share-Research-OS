"""帷幄 Dynamic Workbench（F8，第三轮整改任务书 §8.7 P0-WEIWO）.

右栏不再是固定信息卡：Artifact / Tool Result 返回受控 Handoff，
页面来自**注册表白名单**（禁任意 URL 注入），每会话独立 Tab 状态，
刷新后恢复；Artifact 自动打开对应页面（不只生成链接）。

Handoff 契约（§8.7）：

    {"page": "thesis-center", "route": "/thesis-center",
     "title": "...", "payload": {...}, "artifact_ids": [...],
     "open_mode": "workbench_tab"}

页面收到 payload 后加载真实数据并复算（route 为真实产品路由，
携带 handoff/context 参数 → 现有 §44 Handoff 机制）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.command_events import append_event
from app.application.workbench_orm import WorkbenchTabORM
from app.core.errors import AppError

# ── 页面注册表白名单（§8.7：page 必须来自注册表） ─────────────────────────────

PAGE_REGISTRY: dict[str, dict] = {
    "instrument-workspace": {"route": "/instrument/{instrument_id}"},
    "research-report": {"route": "/reports/{report_id}"},
    "thesis-center": {"route": "/thesis"},
    "industry-map": {"route": "/industry-map"},
    "global-macro": {"route": "/global-macro"},
    "experience-card": {"route": "/experience/{card_id}"},
    "workflow-run": {"route": "/workflows/{run_id}"},
    "workflow-studio": {"route": "/workflow-studio"},
    "screening-result": {"route": "/screening/{run_id}"},
    "strategy-lab": {"route": "/strategy"},
    "strategy-monitor": {"route": "/monitoring/{monitor_id}"},
    "research-graph": {"route": "/research-graph"},
    "reports-library": {"route": "/reports"},
    "daily-brief": {"route": "/research-products"},
    "mainline-radar": {"route": "/research-products"},
    "overseas-mapping": {"route": "/research-products"},
    "experience-library": {"route": "/experience"},
    "monitoring-list": {"route": "/monitoring"},
    "screening-list": {"route": "/screening"},
    "command-center": {"route": "/"},
}

# Artifact 类型 → 页面（Artifact 自动打开对应页面，§8.7）
ARTIFACT_PAGE_MAP: dict[str, str] = {
    "report": "research-report",
    "report_version": "research-report",
    "thesis": "thesis-center",
    "experience_card": "experience-card",
    "workflow_run": "workflow-run",
    "screening_run": "screening-result",
    "screening_candidate": "screening-result",
    "strategy_version": "strategy-lab",
    "strategy_backtest": "strategy-lab",
    "strategy_monitor": "strategy-monitor",
    "prediction": "instrument-workspace",
    "research_run": "instrument-workspace",
    "industry_map": "industry-map",
    "global_context": "global-macro",
    "industry_driver": "industry-map",
    "industry_transmission": "industry-map",
    "industry_narrative": "industry-map",
    "industry_position": "industry-map",
    "review": "instrument-workspace",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row: WorkbenchTabORM) -> dict:
    return {
        "tab_id": row.tab_id,
        "session_id": row.session_id,
        "page": row.page,
        "title": row.title,
        "payload": dict(row.payload_json or {}),
        "artifact_id": row.artifact_id,
        "is_active": bool(row.is_active),
        "route": PAGE_REGISTRY.get(row.page, {}).get("route", "/"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def resolve_artifact_handoff(session: Session, artifact_id: str) -> dict:
    """Artifact → 受控 Handoff（page/route/title/payload；§8.7 契约）。"""
    from app.application.artifacts import ArtifactService

    art = ArtifactService(session).get(artifact_id)
    if art is None:
        raise AppError("workbench.artifact_not_found", status_code=404,
                       detail=f"artifact {artifact_id} not found")
    page_key = ARTIFACT_PAGE_MAP.get(art["artifact_type"])
    if page_key is None:
        raise AppError("workbench.page_unmapped", status_code=422,
                       detail=f"artifact type {art['artifact_type']} has no workbench page")
    domain = art.get("domain_type") or ""
    domain_id = art.get("domain_id") or ""
    payload: dict = {
        "artifact_id": artifact_id,
        "artifact_type": art["artifact_type"],
        "instrument_ids": list(art.get("instrument_ids") or []),
    }
    if domain == "Report":
        payload["report_id"] = domain_id
    elif domain == "Thesis":
        payload["thesis_id"] = domain_id
    elif domain == "ExperienceCard":
        payload["card_id"] = domain_id
    elif domain == "WorkflowRun":
        payload["run_id"] = domain_id
    elif domain == "ScreeningRun":
        payload["run_id"] = domain_id
    elif domain in ("StrategyVersion", "StrategyBacktest"):
        payload["version_id"] = domain_id
    elif domain == "StrategyMonitor":
        payload["monitor_id"] = domain_id
    elif domain == "Prediction":
        payload["prediction_id"] = domain_id
    return {
        "page": page_key,
        "route": PAGE_REGISTRY[page_key]["route"],
        "title": art.get("title") or page_key,
        "payload": payload,
        "artifact_ids": [artifact_id],
        "open_mode": "workbench_tab",
    }


def open_tab(
    session: Session,
    session_id: str,
    *,
    artifact_id: str | None = None,
    page: str | None = None,
    payload: dict | None = None,
    title: str | None = None,
) -> dict:
    """打开 Workbench Tab：artifact 自动映射页面；同 artifact 复用已开 Tab。"""
    from app.application.workbench_orm import WorkbenchTabORM as ORM

    if artifact_id:
        existing = session.scalars(
            select(ORM)
            .where(ORM.session_id == session_id)
            .where(ORM.artifact_id == artifact_id)
        ).first()
        if existing is not None:
            _activate(session, existing)
            tab = _row_to_dict(existing)
            append_event(
                session, session_id, "workbench_open_requested",
                correlation_id=existing.tab_id, payload={"tab": {k: tab[k] for k in ("page", "title")}},
                artifact_ids=[artifact_id],
            )
            return tab
        handoff = resolve_artifact_handoff(session, artifact_id)
        page = handoff["page"]
        payload = handoff["payload"]
        title = handoff["title"]
    else:
        if page not in PAGE_REGISTRY:
            raise AppError("workbench.page_not_allowed", status_code=422,
                           detail=f"page not in registry: {page}")
        title = title or page
        payload = payload or {}

    # 单激活模型：新 Tab 激活，其余取消激活
    for row in session.scalars(
        select(ORM).where(ORM.session_id == session_id, ORM.is_active.is_(True))
    ).all():
        row.is_active = False
    row = ORM(
        tab_id=f"tab_{uuid4().hex[:24]}",
        session_id=session_id,
        page=page,
        title=(title or page)[:200],
        payload_json=dict(payload or {}),
        artifact_id=artifact_id,
        is_active=True,
        created_at=_now(),
    )
    session.add(row)
    session.flush()
    append_event(
        session, session_id, "workbench_open_requested",
        correlation_id=row.tab_id,
        payload={"page": page, "title": row.title, "payload": dict(payload or {})},
        artifact_ids=[artifact_id] if artifact_id else [],
    )
    return _row_to_dict(row)


def _activate(session: Session, row: WorkbenchTabORM) -> None:
    for other in session.scalars(
        select(WorkbenchTabORM)
        .where(WorkbenchTabORM.session_id == row.session_id)
        .where(WorkbenchTabORM.is_active.is_(True))
    ).all():
        other.is_active = False
    row.is_active = True
    session.flush()


def list_tabs(session: Session, session_id: str) -> list[dict]:
    rows = session.scalars(
        select(WorkbenchTabORM)
        .where(WorkbenchTabORM.session_id == session_id)
        .order_by(WorkbenchTabORM.created_at.desc(), WorkbenchTabORM.id.desc())
        .limit(20)
    ).all()
    return [_row_to_dict(r) for r in rows]


def close_tab(session: Session, session_id: str, tab_id: str) -> dict | None:
    row = session.scalars(
        select(WorkbenchTabORM)
        .where(WorkbenchTabORM.session_id == session_id)
        .where(WorkbenchTabORM.tab_id == tab_id)
    ).first()
    if row is None:
        return None
    was_active = row.is_active
    session.delete(row)
    session.flush()
    if was_active:
        latest = session.scalars(
            select(WorkbenchTabORM)
            .where(WorkbenchTabORM.session_id == session_id)
            .order_by(WorkbenchTabORM.created_at.desc(), WorkbenchTabORM.id.desc())
            .limit(1)
        ).first()
        if latest is not None:
            _activate(session, latest)
    return {"closed": tab_id}


def activate_tab(session: Session, session_id: str, tab_id: str) -> dict | None:
    row = session.scalars(
        select(WorkbenchTabORM)
        .where(WorkbenchTabORM.session_id == session_id)
        .where(WorkbenchTabORM.tab_id == tab_id)
    ).first()
    if row is None:
        return None
    _activate(session, row)
    return _row_to_dict(row)


def open_for_artifacts(session: Session, session_id: str, artifact_ids: list[str]) -> list[dict]:
    """Artifact 自动打开对应页面（§8.7：自动打开，非仅链接）。"""
    opened: list[dict] = []
    for artifact_id in artifact_ids:
        try:
            opened.append(open_tab(session, session_id, artifact_id=artifact_id))
        except AppError:
            # 未映射类型诚实跳过（不冒充已打开）
            continue
    return opened
