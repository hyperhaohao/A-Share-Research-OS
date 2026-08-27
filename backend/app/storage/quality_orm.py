"""Quality gate persistence (M7)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.orm import Base


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


class QualityGateResultORM(Base):
    __tablename__ = "quality_gate_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    result_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    gate: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(8), index=True)
    findings_json: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_gate_results_snapshot_gate", "snapshot_id", "gate"),
    )
