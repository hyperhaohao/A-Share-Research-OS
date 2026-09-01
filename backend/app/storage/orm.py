"""SQLAlchemy ORM models (M4: evidence + source manifests).

ORM rows are storage shapes; the domain contract lives in
``app/domain/evidence.py``. Repositories translate between them.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EvidenceORM(Base):
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32), index=True)

    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(128), index=True)
    source_type: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # F4: 来源独立性字段（第三轮整改任务书 §7.2）
    publisher: Mapped[str | None] = mapped_column(String(128), nullable=True)
    origin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    authority_level: Mapped[str] = mapped_column(String(2))
    fact_status: Mapped[str] = mapped_column(String(32))

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    available_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    manifest_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)

    __table_args__ = (
        # Dedup: the same fact from the same source is stored once.
        UniqueConstraint("source", "content_hash", name="uq_evidence_source_content"),
        Index("ix_evidence_instrument_time", "instrument_id", "available_time"),
    )


class SnapshotORM(Base):
    __tablename__ = "evidence_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64))

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    items_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # A stored snapshot is immutable: one row per (instrument, as_of).
        UniqueConstraint("instrument_id", "as_of", name="uq_snapshot_instrument_asof"),
    )


class ResearchRunORM(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run_type: Mapped[str] = mapped_column(String(32), default="full_research")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WatchlistORM(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceManifestORM(Base):
    __tablename__ = "source_manifests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manifest_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    capability: Mapped[str] = mapped_column(String(64))
    requested_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    providers_attempted: Mapped[list] = mapped_column(JSON, default=list)
    final_status: Mapped[str] = mapped_column(String(32))
    final_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    from_cache: Mapped[bool] = mapped_column(default=False)
