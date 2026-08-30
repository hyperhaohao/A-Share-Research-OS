"""Evidence persistence + dedup (任务书 §22/§73)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.evidence import EvidenceRecord, SourceManifest, utc_now
from app.storage.orm import EvidenceORM, SourceManifestORM


class EvidenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- evidence ------------------------------------------------------------
    def save(self, record: EvidenceRecord, *, manifest_id: str | None = None) -> tuple[str, bool]:
        """Insert one evidence atom. Returns (evidence_id, created).

        Dedup contract: re-saving the same (source, content_hash) returns the
        existing evidence_id and created=False — ingestion is idempotent.
        """
        existing = self._session.scalars(
            select(EvidenceORM).where(
                EvidenceORM.source == record.source,
                EvidenceORM.content_hash == record.content_hash,
            )
        ).first()
        if existing is not None:
            return existing.evidence_id, False

        row = EvidenceORM(
            evidence_id=record.evidence_id,
            content_hash=record.content_hash,
            instrument_id=record.instrument_id,
            evidence_type=record.evidence_type.value,
            title=record.title,
            summary=record.summary,
            excerpt=record.excerpt,
            source=record.source,
            source_type=record.source_type,
            source_url=record.source_url,
            source_document_id=record.source_document_id,
            authority_level=record.authority_level.value,
            fact_status=record.fact_status.value,
            event_time=record.event_time,
            available_time=record.available_time,
            ingested_time=record.ingested_time,
            revision_time=record.revision_time,
            confidence=record.confidence,
            metadata_json=record.metadata,
            manifest_id=manifest_id,
        )
        self._session.add(row)
        self._session.flush()
        return row.evidence_id, True

    def latest_by_type(
        self,
        instrument_id: str,
        *,
        evidence_type: str,
        visible_at: datetime | None = None,
        limit: int = 1,
    ) -> list[EvidenceRecord]:
        """Newest N evidence records of one type for an instrument.

        P1-02: LIMIT-based query — avoids loading the full evidence ledger
        when only the latest record(s) are needed (e.g. quote price)."""
        stmt = (
            select(EvidenceORM)
            .where(
                EvidenceORM.instrument_id == instrument_id,
                EvidenceORM.evidence_type == evidence_type,
            )
            .order_by(EvidenceORM.available_time.desc())
            .limit(limit)
        )
        if visible_at is not None:
            stmt = stmt.where(EvidenceORM.available_time <= visible_at)
            stmt = stmt.order_by(EvidenceORM.available_time.desc())
        return [_row_to_domain(row) for row in self._session.scalars(stmt)]

    def list_for_instrument(
        self,
        instrument_id: str,
        *,
        evidence_type: str | None = None,
        visible_at: datetime | None = None,
    ) -> list[EvidenceRecord]:
        """List evidence; ``visible_at`` applies the PIT filter (M5 will make
        historical runs always pass an as_of)."""
        stmt = select(EvidenceORM).where(EvidenceORM.instrument_id == instrument_id)
        if evidence_type is not None:
            stmt = stmt.where(EvidenceORM.evidence_type == evidence_type)
        if visible_at is not None:
            stmt = stmt.where(EvidenceORM.available_time <= visible_at)
        stmt = stmt.order_by(EvidenceORM.available_time.desc())
        return [_row_to_domain(row) for row in self._session.scalars(stmt)]

    def count(self) -> int:
        return len(self._session.scalars(select(EvidenceORM.id)).all())

    # -- manifests -----------------------------------------------------------
    def save_manifest(self, manifest: SourceManifest) -> str:
        row = SourceManifestORM(
            manifest_id=manifest.manifest_id,
            instrument_id=manifest.instrument_id,
            capability=manifest.capability,
            requested_as_of=manifest.requested_as_of,
            created_at=manifest.created_at,
            providers_attempted=list(manifest.providers_attempted),
            final_status=manifest.final_status,
            final_source=manifest.final_source,
            evidence_ids=list(manifest.evidence_ids),
            from_cache=manifest.from_cache,
        )
        self._session.add(row)
        self._session.flush()
        return row.manifest_id

    def get_manifest(self, manifest_id: str) -> SourceManifest | None:
        row = self._session.scalars(
            select(SourceManifestORM).where(SourceManifestORM.manifest_id == manifest_id)
        ).first()
        if row is None:
            return None
        return SourceManifest(
            manifest_id=row.manifest_id,
            instrument_id=row.instrument_id,
            capability=row.capability,
            requested_as_of=_ensure_utc(row.requested_as_of),
            created_at=_ensure_utc(row.created_at),
            providers_attempted=tuple(row.providers_attempted or ()),
            final_status=row.final_status,
            final_source=row.final_source,
            evidence_ids=tuple(row.evidence_ids or ()),
            from_cache=row.from_cache,
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    """SQLite loses tzinfo on round-trip; stored values are always UTC by
    convention, so naive reads are interpreted as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _row_to_domain(row: EvidenceORM) -> EvidenceRecord:
    return EvidenceRecord(
        instrument_id=row.instrument_id,
        evidence_type=row.evidence_type,  # type: ignore[arg-type]
        title=row.title,
        summary=row.summary,
        excerpt=row.excerpt,
        source=row.source,
        source_type=row.source_type,
        source_url=row.source_url,
        source_document_id=row.source_document_id,
        authority_level=row.authority_level,  # type: ignore[arg-type]
        fact_status=row.fact_status,  # type: ignore[arg-type]
        event_time=_ensure_utc(row.event_time),
        available_time=_ensure_utc(row.available_time),
        ingested_time=_ensure_utc(row.ingested_time),
        revision_time=_ensure_utc(row.revision_time),
        confidence=row.confidence,
        metadata=row.metadata_json or {},
    )
