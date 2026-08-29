"""ExperienceCard persistence (V2 Phase C, 总纲 §12/§13/§43).

经验卡不是笔记：它是由研究报告的结构化研究状态（thesis/claims/evidence）
确定性提炼出的可验证、可版本化研究经验，保留完整来源
（report_id / report_version_id / claim_ids / evidence_ids，§43）。
状态机：DRAFT → REFINED → VALIDATING → APPROVED / REJECTED（§12）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, String, select
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


class ExperienceStatus:
    DRAFT = "DRAFT"
    REFINED = "REFINED"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DOUBTFUL = "DOUBTFUL"
    SUPERSEDED = "SUPERSEDED"


class ExperienceCardORM(Base):
    __tablename__ = "experience_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32), default="research_pattern")

    statement: Mapped[str] = mapped_column(String(2000))
    mechanism: Mapped[str] = mapped_column(String(4000))
    applicable_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    invalid_conditions_json: Mapped[list] = mapped_column(JSON, default=list)

    # 来源（§43 必须保留）
    source_report_id: Mapped[str] = mapped_column(String(32), index=True)
    source_report_version_id: Mapped[str] = mapped_column(String(32))
    source_snapshot_id: Mapped[str] = mapped_column(String(32))
    source_claim_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    source_evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(16), default=ExperienceStatus.DRAFT, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    verdict: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_version: Mapped[int] = mapped_column(default=1)
    refine_method: Mapped[str] = mapped_column(String(16), default="deterministic")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExperienceCardVersionORM(Base):
    """Immutable snapshots of card content across refinements (§12)."""

    __tablename__ = "experience_card_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(24), index=True)
    version_no: Mapped[int] = mapped_column(default=1)
    statement: Mapped[str] = mapped_column(String(2000))
    mechanism: Mapped[str] = mapped_column(String(4000))
    applicable_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    invalid_conditions_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    method: Mapped[str] = mapped_column(String(16), default="deterministic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExperienceValidationORM(Base):
    """One validation run on a card (v1: case study on the source snapshot)."""

    __tablename__ = "experience_validations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    validation_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    card_id: Mapped[str] = mapped_column(String(24), index=True)
    method: Mapped[str] = mapped_column(String(16))  # case | quant
    cases_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _card_to_dict(row: ExperienceCardORM, *, versions: int | None = None) -> dict:
    data = {
        "card_id": row.card_id,
        "instrument_id": row.instrument_id,
        "title": row.title,
        "category": row.category,
        "statement": row.statement,
        "mechanism": row.mechanism,
        "applicable_conditions": list(row.applicable_conditions_json or []),
        "invalid_conditions": list(row.invalid_conditions_json or []),
        "source_report_id": row.source_report_id,
        "source_report_version_id": row.source_report_version_id,
        "source_snapshot_id": row.source_snapshot_id,
        "source_claim_ids": list(row.source_claim_ids_json or []),
        "source_evidence_ids": list(row.source_evidence_ids_json or []),
        "status": row.status,
        "confidence": row.confidence,
        "verdict": row.verdict,
        "current_version": row.current_version,
        "refine_method": row.refine_method,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
        "updated_at": _ensure_utc(row.updated_at).isoformat() if row.updated_at else None,
    }
    if versions is not None:
        data["version_count"] = versions
    return data


def _version_to_dict(row: ExperienceCardVersionORM) -> dict:
    return {
        "version_no": row.version_no,
        "statement": row.statement,
        "mechanism": row.mechanism,
        "applicable_conditions": list(row.applicable_conditions_json or []),
        "invalid_conditions": list(row.invalid_conditions_json or []),
        "confidence": row.confidence,
        "method": row.method,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


def _validation_to_dict(row: ExperienceValidationORM) -> dict:
    return {
        "validation_id": row.validation_id,
        "card_id": row.card_id,
        "method": row.method,
        "cases": list(row.cases_json or []),
        "summary": row.summary,
        "created_at": _ensure_utc(row.created_at).isoformat() if row.created_at else None,
    }


class ExperienceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- cards -------------------------------------------------------------------

    def add_card(self, row: ExperienceCardORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _card_to_dict(row)

    def get_card(self, card_id: str) -> dict | None:
        row = self._session.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()
        return None if row is None else _card_to_dict(row)

    def get_card_row(self, card_id: str) -> ExperienceCardORM | None:
        return self._session.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()

    def list_cards(self, *, limit: int = 50) -> list[dict]:
        rows = self._session.scalars(
            select(ExperienceCardORM)
            .order_by(ExperienceCardORM.created_at.desc(), ExperienceCardORM.id.desc())
            .limit(limit)
        ).all()
        return [_card_to_dict(r) for r in rows]

    def save_card(self, row: ExperienceCardORM) -> dict:
        self._session.flush()
        return _card_to_dict(row)

    # -- versions ------------------------------------------------------------------

    def add_version(self, row: ExperienceCardVersionORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _version_to_dict(row)

    def list_versions(self, card_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(ExperienceCardVersionORM)
            .where(ExperienceCardVersionORM.card_id == card_id)
            .order_by(ExperienceCardVersionORM.version_no)
        ).all()
        return [_version_to_dict(r) for r in rows]

    # -- validations -----------------------------------------------------------------

    def add_validation(self, row: ExperienceValidationORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _validation_to_dict(row)

    def list_validations(self, card_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(ExperienceValidationORM)
            .where(ExperienceValidationORM.card_id == card_id)
            .order_by(ExperienceValidationORM.created_at)
        ).all()
        return [_validation_to_dict(r) for r in rows]
