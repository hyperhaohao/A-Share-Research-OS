"""G4 存储层：workflow node I/O 账本（不可变，按 attempt 追加）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class WorkflowNodeIOORM(Base):
    __tablename__ = "workflow_node_io"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    io_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(24), index=True)
    node_id: Mapped[str] = mapped_column(String(48))
    kind: Mapped[str] = mapped_column(String(32))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), index=True)
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
