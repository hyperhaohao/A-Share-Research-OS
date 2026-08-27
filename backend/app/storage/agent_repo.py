"""Analyst briefs + research requests: ORM and repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.agents import (
    AnalystBrief,
    AnalystType,
    MissingData,
    ResearchRequest,
    ResearchRequestStatus,
)
from app.storage.orm import Base


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


class AnalystBriefORM(Base):
    __tablename__ = "analyst_briefs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    brief_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    analyst_type: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    conclusions_json: Mapped[list] = mapped_column(JSON, default=list)
    claim_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_data_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    key_questions_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_briefs_snapshot_analyst", "snapshot_id", "analyst_type"),
    )


class ResearchRequestORM(Base):
    __tablename__ = "research_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    capability: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(64))
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    # -- briefs --------------------------------------------------------------
    def save_brief(self, brief: AnalystBrief) -> str:
        row = AnalystBriefORM(
            brief_id=brief.brief_id,
            analyst_type=brief.analyst_type.value,
            instrument_id=brief.instrument_id,
            snapshot_id=brief.snapshot_id,
            run_id=brief.run_id,
            conclusions_json=list(brief.conclusions),
            claim_refs_json=list(brief.claim_refs),
            evidence_refs_json=list(brief.evidence_refs),
            missing_data_json=[m.model_dump(mode="json") for m in brief.missing_data],
            confidence=brief.confidence,
            key_questions_json=list(brief.key_questions),
            risks_json=list(brief.risks),
            created_at=brief.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.brief_id

    def list_briefs(self, snapshot_id: str) -> list[AnalystBrief]:
        rows = self._session.scalars(
            select(AnalystBriefORM)
            .where(AnalystBriefORM.snapshot_id == snapshot_id)
            .order_by(AnalystBriefORM.created_at.desc())
        ).all()
        return [_brief_row_to_domain(r) for r in rows]

    # -- research requests ---------------------------------------------------
    def save_request(self, request: ResearchRequest) -> str:
        row = ResearchRequestORM(
            request_id=request.request_id,
            instrument_id=request.instrument_id,
            capability=request.capability,
            reason=request.reason,
            requested_by=request.requested_by,
            snapshot_id=request.snapshot_id,
            status=request.status.value,
            created_at=request.created_at,
            resolved_at=request.resolved_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.request_id

    def list_requests(
        self,
        instrument_id: str,
        *,
        status: ResearchRequestStatus | None = None,
    ) -> list[ResearchRequest]:
        stmt = select(ResearchRequestORM).where(
            ResearchRequestORM.instrument_id == instrument_id
        )
        if status is not None:
            stmt = stmt.where(ResearchRequestORM.status == status.value)
        rows = self._session.scalars(stmt.order_by(ResearchRequestORM.created_at.desc())).all()
        return [
            ResearchRequest(
                request_id=r.request_id,
                instrument_id=r.instrument_id,
                capability=r.capability,
                reason=r.reason,
                requested_by=r.requested_by,
                snapshot_id=r.snapshot_id,
                status=r.status,  # type: ignore[arg-type]
                created_at=_ensure_utc(r.created_at),
                resolved_at=_ensure_utc(r.resolved_at),
            )
            for r in rows
        ]

    def mark_fulfilled(self, request_id: str) -> None:
        row = self._session.scalars(
            select(ResearchRequestORM).where(
                ResearchRequestORM.request_id == request_id
            )
        ).first()
        if row is None:
            return
        row.status = ResearchRequestStatus.FULFILLED.value
        row.resolved_at = datetime.now(timezone.utc)
        self._session.flush()


def _brief_row_to_domain(r: AnalystBriefORM) -> AnalystBrief:
    return AnalystBrief(
        brief_id=r.brief_id,
        analyst_type=r.analyst_type,  # type: ignore[arg-type]
        instrument_id=r.instrument_id,
        snapshot_id=r.snapshot_id,
        run_id=r.run_id,
        conclusions=tuple(r.conclusions_json or ()),
        claim_refs=tuple(r.claim_refs_json or ()),
        evidence_refs=tuple(r.evidence_refs_json or ()),
        missing_data=tuple(MissingData(**m) for m in (r.missing_data_json or [])),
        confidence=r.confidence,
        key_questions=tuple(r.key_questions_json or ()),
        risks=tuple(r.risks_json or ()),
        created_at=_ensure_utc(r.created_at),
    )
