"""Handoff envelopes + ResearchContext (V2 Phase A, 总纲 §34/§35).

跨模块动作走信封：artifact 携带 + 上下文 + 动作。目标动作必须先注册
（未知 action → 显式 422，不静默）。Context 只描述当前研究上下文，
不是业务真数据（红线 4/5）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


class ResearchContext(BaseModel):
    """Current research context (V2 §34) — descriptive, never source-of-truth."""

    model_config = ConfigDict(extra="forbid")

    context_id: str = Field(default_factory=lambda: f"ctx_{uuid4().hex[:12]}")
    instrument_ids: tuple[str, ...] = ()
    primary_instrument_id: str | None = None
    as_of_time: datetime | None = None
    snapshot_id: str | None = None
    research_run_id: str | None = None
    report_version_id: str | None = None
    selected_artifact_ids: tuple[str, ...] = ()
    locale: str = "zh-CN"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Registered actions: (source_module, target_module, action). A handoff is
# only recorded when the triple exists here — dead envelopes are refused,
# not silently stored (红线 8).
HANDOFF_ACTIONS: set[tuple[str, str, str]] = {
    ("report", "prediction", "create_prediction"),
    ("report", "experience", "create_experience_draft"),
    ("experience", "workflow", "run_validation"),
    ("report", "workspace", "open_workspace"),
    ("prediction", "workspace", "open_with_context"),
}


class HandoffORM(Base):
    __tablename__ = "handoffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    handoff_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    source_module: Mapped[str] = mapped_column(String(32))
    target_module: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    artifact_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HandoffService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        source_module: str,
        target_module: str,
        action: str,
        artifact_ids: tuple[str, ...],
        context: ResearchContext,
        message: str | None = None,
    ) -> dict:
        if (source_module, target_module, action) not in HANDOFF_ACTIONS:
            raise ValueError(
                f"unregistered handoff action: {source_module}->{target_module}:{action}"
            )
        if not artifact_ids:
            raise ValueError("handoff must carry at least one artifact")
        from app.application.artifacts import ArtifactService

        artifacts = ArtifactService(self._session)
        for artifact_id in artifact_ids:
            if artifacts.get(artifact_id) is None:
                raise ValueError(f"artifact not found: {artifact_id}")
        handoff_id = f"ho_{uuid4().hex[:12]}"
        self._session.add(
            HandoffORM(
                handoff_id=handoff_id,
                source_module=source_module,
                target_module=target_module,
                action=action,
                artifact_ids_json=list(artifact_ids),
                context_json=context.model_dump(mode="json"),
                message=message,
                created_at=datetime.now(timezone.utc),
            )
        )
        self._session.flush()
        return {
            "handoff_id": handoff_id,
            "source_module": source_module,
            "target_module": target_module,
            "action": action,
            "artifact_ids": list(artifact_ids),
            "context": context.model_dump(mode="json"),
            "message": message,
        }

    def list_recent(self, *, limit: int = 50) -> list[dict]:
        from sqlalchemy import select

        from app.storage.agent_repo import _ensure_utc

        rows = self._session.scalars(
            select(HandoffORM).order_by(HandoffORM.created_at.desc()).limit(limit)
        ).all()
        return [
            {
                "handoff_id": r.handoff_id,
                "source_module": r.source_module,
                "target_module": r.target_module,
                "action": r.action,
                "artifact_ids": list(r.artifact_ids_json or []),
                "context": r.context_json or {},
                "message": r.message,
                "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None,
            }
            for r in rows
        ]
