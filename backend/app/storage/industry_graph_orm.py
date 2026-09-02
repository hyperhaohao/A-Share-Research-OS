"""G1 存储层：industry graph 六表（IndustryChain/Segment/Edge/Product/
EdgeEvidenceLink/CompanyIndustryPosition）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


class IndustryChainORM(Base):
    __tablename__ = "industry_chains"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chain_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("name", "version", name="uq_industry_chain_name_version"),)


class IndustrySegmentORM(Base):
    __tablename__ = "industry_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    segment_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    chain_id: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(128))
    stage_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IndustryProductORM(Base):
    __tablename__ = "industry_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    unit: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IndustryEdgeORM(Base):
    __tablename__ = "industry_edges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    chain_id: Mapped[str] = mapped_column(String(24), index=True)
    source_segment_id: Mapped[str] = mapped_column(String(24), index=True)
    target_segment_id: Mapped[str] = mapped_column(String(24), index=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True)
    input_product_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    output_product_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    transmission_metric: Mapped[str] = mapped_column(String(200), default="")
    direction: Mapped[str] = mapped_column(String(16), default="positive")
    lag_min_days: Mapped[int] = mapped_column(Integer, default=0)
    lag_max_days: Mapped[int] = mapped_column(Integer, default=0)
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(16), default="insufficient")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="insufficient", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    snapshot_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IndustryEdgeEvidenceORM(Base):
    __tablename__ = "industry_edge_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    link_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    edge_id: Mapped[str] = mapped_column(String(24), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    stance: Mapped[str] = mapped_column(String(16), default="support")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[str] = mapped_column(String(64), default="industry_graph")

    __table_args__ = (
        UniqueConstraint("edge_id", "evidence_id", "stance", name="uq_edge_evidence"),
    )


class CompanyIndustryPositionORM(Base):
    __tablename__ = "company_industry_positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    chain_id: Mapped[str] = mapped_column(String(24), index=True)
    segment_id: Mapped[str] = mapped_column(String(24), index=True)
    role: Mapped[str] = mapped_column(String(24), default="producer")
    revenue_exposure_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_exposure_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_note: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
