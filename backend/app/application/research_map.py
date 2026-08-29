"""Industry Map + Global Context snapshots (V2 Phase H, 总纲 §11/§52/§77).

它们不是孤立 Dashboard，而是 Research Inputs（§52）：视图由真实证据层
组装（PIT as_of），注册为 Artifact 供报告/经验卡/策略引用；页面通过
open_with_context 信封进入标的研究上下文，上下文不丢失。

诚实边界：
  - 产业链上下游/同业关系源未接入 → 相关公司由「证据文本共现」推导
    （真实、可溯源），peers 状态显式披露 pending_relationship_source；
  - 官方宏观数据源未接入 → 全球视图当前为政策/宏观资讯层（真实资讯，
    显式披露），绝不伪造利率/汇率数值。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _short_hex() -> str:
    return uuid4().hex[:12]


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class IndustryMapSnapshotORM(Base):
    __tablename__ = "industry_map_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    map_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    industry_label: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    industry_chain_json: Mapped[list] = mapped_column(JSON, default=list)
    main_business: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    related_instruments_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    disclosures_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GlobalContextSnapshotORM(Base):
    __tablename__ = "global_context_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    topic: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    themes_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    disclosures_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _map_to_dict(row: IndustryMapSnapshotORM) -> dict:
    return {
        "map_id": row.map_id,
        "instrument_id": row.instrument_id,
        "industry_label": row.industry_label,
        "as_of": _ensure_utc(row.as_of).isoformat() if row.as_of else None,
        "industry_chain": list(row.industry_chain_json or []),
        "main_business": row.main_business,
        "related_instruments": list(row.related_instruments_json or []),
        "evidence_ids": list(row.evidence_ids_json or []),
        "disclosures": dict(row.disclosures_json or {}),
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


def _context_to_dict(row: GlobalContextSnapshotORM) -> dict:
    return {
        "snapshot_id": row.snapshot_id,
        "instrument_id": row.instrument_id,
        "topic": row.topic,
        "as_of": _ensure_utc(row.as_of).isoformat() if row.as_of else None,
        "themes": [dict(t) for t in (row.themes_json or [])],
        "evidence_ids": list(row.evidence_ids_json or []),
        "disclosures": dict(row.disclosures_json or {}),
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


class ResearchMapRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_map(self, row: IndustryMapSnapshotORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _map_to_dict(row)

    def latest_map(self, instrument_id: str) -> dict | None:
        row = self._session.scalars(
            select(IndustryMapSnapshotORM)
            .where(IndustryMapSnapshotORM.instrument_id == instrument_id)
            .order_by(IndustryMapSnapshotORM.as_of.desc(), IndustryMapSnapshotORM.id.desc())
            .limit(1)
        ).first()
        return None if row is None else _map_to_dict(row)

    def add_context(self, row: GlobalContextSnapshotORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _context_to_dict(row)

    def latest_context(self, instrument_id: str) -> dict | None:
        row = self._session.scalars(
            select(GlobalContextSnapshotORM)
            .where(GlobalContextSnapshotORM.instrument_id == instrument_id)
            .order_by(GlobalContextSnapshotORM.as_of.desc(), GlobalContextSnapshotORM.id.desc())
            .limit(1)
        ).first()
        return None if row is None else _context_to_dict(row)
