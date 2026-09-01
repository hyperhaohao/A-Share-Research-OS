"""F9 存储层：后台任务跑道 + 会话记忆（任务书 §8.8/§8.9）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class BackgroundTaskORM(Base):
    __tablename__ = "command_background_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    command_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    arguments_json: Mapped[dict] = mapped_column(JSON, default=dict)
    arguments_digest: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("task_id", name="uq_cmd_bg_task_id"),
    )


class SessionMemoryORM(Base):
    __tablename__ = "command_session_memory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_conclusions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    open_questions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_version: Mapped[int] = mapped_column(Integer, default=0)
    compacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
