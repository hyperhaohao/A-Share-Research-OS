"""ExtractionRecord 持久化（R2，方案 §8.4/§8.5）.

为什么独立表（方案 §17 三问）：
  1. 独立生命周期：rejected 抽取必须留档（审计「抽取器试过什么、为何被拒」），
     accepted 抽取在晋升为 Claim 前是暂存研究对象；
  2. 被 Claim 引用（promoted_claim_id 反查）+ 将进 Graph（evidence→extraction→claim 链）；
  3. 不是 Evidence 的复制——只存抽取元数据 + 裁决，原文仍在 Evidence 层。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.domain.extraction import (
    VALID_CLAIM_TYPES,
    ExtractionInput,
    ExtractionVerdict,
    verify_extraction,
)
from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class ExtractionRecordORM(Base):
    __tablename__ = "extraction_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extraction_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    source_evidence_id: Mapped[str] = mapped_column(String(32), index=True)
    statement: Mapped[str] = mapped_column(String(500))
    support_span: Mapped[str] = mapped_column(String(2000))
    fact_status: Mapped[str] = mapped_column(String(32))
    claim_type: Mapped[str] = mapped_column(String(32), default="fundamental_fact")
    confidence_basis: Mapped[str] = mapped_column(String(300), default="")
    extractor: Mapped[str] = mapped_column(String(40), default="deterministic")
    prompt_version: Mapped[str] = mapped_column(String(24), default="v0")
    verdict: Mapped[str] = mapped_column(String(12), index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    verdict_basis: Mapped[str] = mapped_column(String(24), default="deterministic")
    trust_level: Mapped[str] = mapped_column(String(32))
    evidence_authority: Mapped[str] = mapped_column(String(4))
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    promoted_claim_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _to_dict(row: ExtractionRecordORM) -> dict:
    return {
        "extraction_id": row.extraction_id,
        "source_evidence_id": row.source_evidence_id,
        "statement": row.statement,
        "support_span": row.support_span,
        "fact_status": row.fact_status,
        "claim_type": row.claim_type,
        "confidence_basis": row.confidence_basis,
        "extractor": row.extractor,
        "prompt_version": row.prompt_version,
        "verdict": row.verdict,
        "reject_reason": row.reject_reason,
        "verdict_basis": row.verdict_basis,
        "trust_level": row.trust_level,
        "evidence_authority": row.evidence_authority,
        "instrument_id": row.instrument_id,
        "promoted_claim_id": row.promoted_claim_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class ExtractionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: ExtractionRecordORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return _to_dict(row)

    def get(self, extraction_id: str) -> dict | None:
        row = self._session.scalars(
            select(ExtractionRecordORM).where(
                ExtractionRecordORM.extraction_id == extraction_id
            )
        ).first()
        return None if row is None else _to_dict(row)

    def list(self, *, instrument_id: str | None = None, limit: int = 50) -> list[dict]:
        stmt = (
            select(ExtractionRecordORM)
            .order_by(ExtractionRecordORM.created_at.desc(), ExtractionRecordORM.id.desc())
            .limit(limit)
        )
        if instrument_id:
            stmt = stmt.where(ExtractionRecordORM.instrument_id == instrument_id)
        rows = self._session.scalars(stmt).all()
        return [_to_dict(r) for r in rows]

    def mark_promoted(self, extraction_id: str, claim_id: str) -> None:
        row = self._session.scalars(
            select(ExtractionRecordORM).where(
                ExtractionRecordORM.extraction_id == extraction_id
            )
        ).first()
        if row is not None:
            row.promoted_claim_id = claim_id


class ExtractionService:
    """Extract → Verify → Persist → (promote) 流程（R2 方案 §8.4/§8.5）."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ExtractionRepository(session)

    def submit(self, item: ExtractionInput, *, evidence: Any, instrument_id: str) -> dict:
        """校验 + 持久化。evidence 为 EvidenceRecord（authority/summary/excerpt）。"""
        evidence_text = " ".join(
            part for part in [evidence.summary or "", evidence.excerpt or ""] if part
        )
        verdict: ExtractionVerdict = verify_extraction(
            item,
            evidence_text=evidence_text,
            evidence_authority=evidence.authority_level,
        )
        row = ExtractionRecordORM(
            extraction_id="ext_" + uuid4().hex[:12],
            source_evidence_id=item.source_evidence_id,
            statement=item.statement.strip(),
            support_span=item.support_span.strip(),
            fact_status=item.fact_status,
            claim_type=(item.claim_type if item.claim_type in VALID_CLAIM_TYPES else "fundamental_fact"),
            confidence_basis=item.confidence_basis[:300],
            extractor=item.extractor[:40],
            prompt_version=item.prompt_version[:24],
            verdict=verdict.verdict,
            reject_reason=None if verdict.reason == "ok" else verdict.reason,
            verdict_basis=verdict.verdict_basis,
            trust_level=verdict.trust_level,
            evidence_authority=str(evidence.authority_level or ""),
            instrument_id=instrument_id,
            created_at=_utc(),
        )
        saved = self._repo.add(row)
        saved["evidence_summary"] = evidence_text[:200]
        return saved

    def promote_to_claim(self, extraction_id: str, *, snapshot_id: str) -> dict:
        """accepted 抽取 → 正式 Claim（走既有 Claim domain，引用完整性继承）。"""
        from app.domain.evidence import FactStatus
        from app.domain.research import Claim, ClaimStatus
        from app.storage.research_repo import ResearchRepository

        record = self._repo.get(extraction_id)
        if record is None:
            raise KeyError(extraction_id)
        if record["verdict"] != "accepted":
            raise ValueError("extraction was rejected; cannot promote")
        if record["promoted_claim_id"]:
            return {"claim_id": record["promoted_claim_id"], "already_promoted": True}

        evidence_id = record["source_evidence_id"]
        from app.storage.orm import EvidenceORM

        row = self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id == evidence_id)
        ).first()
        if row is None:
            raise KeyError(evidence_id)

        class _EvView:
            """EvidenceRecord 视图（promote 只需 authority/summary/excerpt）。"""

            authority_level = row.authority_level
            summary = row.summary
            excerpt = row.excerpt

        evidence = _EvView()

        claim = Claim(
            instrument_id=record["instrument_id"],
            snapshot_id=snapshot_id,
            statement=record["statement"],
            claim_type=record["claim_type"],
            supporting_evidence_refs=(evidence_id,),
            opposing_evidence_refs=(),
            fact_status=FactStatus(record["fact_status"]),
            confidence=0.6,
            status=ClaimStatus.PROPOSED,
        )
        claim_id = ResearchRepository(self._session).save_claim(claim)
        self._repo.mark_promoted(extraction_id, claim_id)
        return {"claim_id": claim_id, "trust_level": record["trust_level"]}
