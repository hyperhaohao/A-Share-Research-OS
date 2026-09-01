"""Command Confirmation ORM（F7 审批门存储层）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class CommandConfirmationORM(Base):
    __tablename__ = "command_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    confirmation_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    command_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    arguments_json: Mapped[dict] = mapped_column(JSON, default=dict)
    arguments_digest: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
