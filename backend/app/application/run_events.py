"""RunEvent persistence (V2 Phase A, 总纲 §37).

Every SSE event published by a research run is ALSO stored, so task
history / research replay / failure analysis work without the live
stream. The in-memory bus behavior is unchanged (PW1 frontend keeps
consuming the stream); persistence is opt-in per publish site.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base

# 现有事件名 → §37 统一 Stage（映射表见 docs/v2/ARCHITECTURE-V2.md §5）
EVENT_STAGE = {
    "run_started": "PLANNING",
    "source_progress": "COLLECTING",
    "evidence_ready": "COLLECTING",
    "snapshot_built": "VALIDATING",
    "quality_gate": "VALIDATING",
    "analyst_progress": "ANALYZING",
    "claims_compiled": "SYNTHESIZING",
    "thesis_ready": "SYNTHESIZING",
    "debate_ready": "SYNTHESIZING",
    "valuation_ready": "SYNTHESIZING",
    "scenario_ready": "SYNTHESIZING",
    "risk_ready": "SYNTHESIZING",
    "report_ready": "REPORTING",
    "run_completed": "COMPLETED",
    "run_failed": "FAILED",
}

# 业务可读标题（中文为用户语言基线；前端本地化层可再映射）
EVENT_TITLE = {
    "run_started": "研究启动",
    "source_progress": "数据采集",
    "evidence_ready": "证据就绪",
    "snapshot_built": "证据快照",
    "quality_gate": "质量检查",
    "analyst_progress": "分析",
    "claims_compiled": "主张汇总",
    "thesis_ready": "论点构建",
    "debate_ready": "多空辩论",
    "valuation_ready": "估值计算",
    "scenario_ready": "情景分析",
    "risk_ready": "风险评估",
    "report_ready": "报告生成",
    "run_completed": "研究完成",
    "run_failed": "研究失败",
}


class RunEventORM(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(16), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def record_run_event(session: Session, run_id: str, event: str, payload: dict) -> str:
    """Persist one run event; unknown event names keep the raw type as stage."""
    row = RunEventORM(
        event_id=f"evt_{uuid4().hex[:16]}",
        run_id=run_id,
        stage=EVENT_STAGE.get(event, event.upper()),
        event_type=event,
        status=payload.get("status"),
        title=EVENT_TITLE.get(event),
        summary=_summarize(event, payload),
        payload_json=payload,
        at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    return row.event_id


def list_run_events(session: Session, run_id: str) -> list[dict]:
    """Full replay for one run, chronological."""
    from app.storage.agent_repo import _ensure_utc

    rows = session.scalars(
        select(RunEventORM).where(RunEventORM.run_id == run_id).order_by(RunEventORM.at)
    ).all()
    return [
        {
            "event_id": r.event_id,
            "run_id": r.run_id,
            "stage": r.stage,
            "event_type": r.event_type,
            "status": r.status,
            "title": r.title,
            "summary": r.summary,
            "payload": r.payload_json or {},
            "at": _ensure_utc(r.at).isoformat() if r.at else None,
        }
        for r in rows
    ]


def _summarize(event: str, payload: dict) -> str | None:
    if event == "evidence_ready":
        return f"{payload.get('capability')}: {payload.get('created', 0)} 条新证据"
    if event == "analyst_progress":
        return payload.get("analyst")
    if event == "claims_compiled":
        return f"{payload.get('count', 0)} 条主张"
    if event == "run_failed":
        return payload.get("error")
    return None
