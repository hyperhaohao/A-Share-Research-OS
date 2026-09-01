"""Command Event ORM（F5，帷幄事件协议 §8.3）—— append-only 存储层."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class CommandEventORM(Base):
    __tablename__ = "command_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    plan_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_command_events_session_sequence"),
    )
