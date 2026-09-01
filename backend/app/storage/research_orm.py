"""Research ORM: corporate events, claims, theses."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class CorporateEventORM(Base):
    __tablename__ = "corporate_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClaimORM(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)

    statement: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(32), index=True)
    supporting_evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    opposing_evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    fact_status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # F2: Claim Version lineage（第三轮整改任务书 §5.3.4）
    parent_claim_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    revision_kind: Mapped[str | None] = mapped_column(String(24), nullable=True)
    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_impact_relation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    carried_forward: Mapped[bool | None] = mapped_column(Boolean, nullable=True, server_default=false())

    # A claim is unique within its research state by its content.
    __table_args__ = (
        UniqueConstraint("snapshot_id", "statement", name="uq_claim_snapshot_statement"),
        Index("ix_claims_instrument_snapshot", "instrument_id", "snapshot_id"),
    )


class ThesisORM(Base):
    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thesis_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)

    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    supporting_claims_json: Mapped[list] = mapped_column(JSON, default=list)
    opposing_claims_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)

    catalysts_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    trigger_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    invalidate_conditions_json: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("snapshot_id", "title", name="uq_thesis_snapshot_title"),
    )
