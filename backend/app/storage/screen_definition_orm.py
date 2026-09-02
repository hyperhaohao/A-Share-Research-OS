"""G5 存储层：ScreenDefinition + Definition Run."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class ScreenDefinitionORM(Base):
    __tablename__ = "screen_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    def_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    source_card_id: Mapped[str] = mapped_column(String(24), index=True)
    source_card_version: Mapped[int] = mapped_column(Integer)
    universe_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_json: Mapped[list] = mapped_column(JSON, default=list)
    ranking_json: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_data_policy: Mapped[str] = mapped_column(String(16), default="exclude")
    as_of_policy: Mapped[str] = mapped_column(String(16), default="now")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    compiled_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="screening")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScreenDefinitionRunORM(Base):
    __tablename__ = "screen_definition_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    def_id: Mapped[str] = mapped_column(String(24), index=True)
    def_version: Mapped[int] = mapped_column(Integer)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    universe_json: Mapped[dict] = mapped_column(JSON, default=dict)
    candidates_json: Mapped[list] = mapped_column(JSON, default=list)
    exclusions_json: Mapped[list] = mapped_column(JSON, default=list)
    artifact_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
