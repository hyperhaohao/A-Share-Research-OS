"""Compiled report persistence (M11; version chain arrives in M12)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base


class ReportORM(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(8), index=True)

    gate_status: Mapped[str] = mapped_column(String(16), default="not_run")
    published: Mapped[bool] = mapped_column(default=False)
    product_type: Mapped[str] = mapped_column(String(32), default="COMPANY_DEEP_DIVE", index=True)

    markdown: Mapped[str] = mapped_column(default="")
    html: Mapped[str] = mapped_column(default="")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(
        self,
        *,
        instrument_id: str,
        snapshot_id: str,
        language: str,
        gate_status: str,
        published: bool,
        markdown: str,
        html: str,
        content: dict,
        product_type: str = "COMPANY_DEEP_DIVE",
    ) -> str:
        row = ReportORM(
            report_id=f"rpt_{uuid4().hex[:16]}",
            instrument_id=instrument_id,
            snapshot_id=snapshot_id,
            language=language,
            gate_status=gate_status,
            published=published,
            markdown=markdown,
            html=html,
            content_json=content,
            product_type=product_type,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return row.report_id

    def get(self, report_id: str) -> dict | None:
        row = self._session.scalars(
            select(ReportORM).where(ReportORM.report_id == report_id)
        ).first()
        return None if row is None else self._row_to_dict(row)

    def list_for(self, instrument_id: str, *, language: str | None = None) -> list[dict]:
        stmt = select(ReportORM).where(ReportORM.instrument_id == instrument_id)
        if language:
            stmt = stmt.where(ReportORM.language == language)
        rows = self._session.scalars(stmt.order_by(ReportORM.created_at.desc())).all()
        return [self._row_to_dict(r) for r in rows]

    def list_recent(self, *, limit: int = 50) -> list[dict]:
        """All reports, newest first (报告库 product list)."""
        rows = self._session.scalars(
            select(ReportORM).order_by(ReportORM.created_at.desc()).limit(limit)
        ).all()
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(r: ReportORM) -> dict:
        return {
            "report_id": r.report_id,
            "instrument_id": r.instrument_id,
            "snapshot_id": r.snapshot_id,
            "language": r.language,
            "gate_status": r.gate_status,
            "published": r.published,
            "markdown": r.markdown,
            "html": r.html,
            "content_json": r.content_json or {},
            "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None,
        }
