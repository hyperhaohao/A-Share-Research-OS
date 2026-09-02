"""G9 存储层：research product compile 版本（Artifact/PIT/Provenance）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class ResearchProductCompileORM(Base):
    __tablename__ = "research_product_compiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compile_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    product_type: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provenance_status: Mapped[str] = mapped_column(String(32), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
