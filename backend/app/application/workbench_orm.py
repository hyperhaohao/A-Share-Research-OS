"""Command Workbench Tab ORM（F8 存储层）—— 每会话独立动态 Tab 状态."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class WorkbenchTabORM(Base):
    __tablename__ = "command_workbench_tabs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tab_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    page: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("session_id", "artifact_id", name="uq_workbench_session_artifact"),
    )
