"""Research repository with referential integrity (任务书 §28/§29, AGENTS §14).

Claims must reference existing evidence; theses must reference existing
claims. Violations raise ``ReferenceNotFoundError`` — traceability is
enforced at write time, not audited after the fact.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.research import (
    Claim,
    CorporateEvent,
    InvestmentThesis,
)
from app.storage.orm import EvidenceORM
from app.storage.research_orm import ClaimORM, CorporateEventORM, ThesisORM


class ReferenceNotFoundError(ValueError):
    """A cited object does not exist — refuse to create the citing object."""


class CrossInstrumentError(ReferenceNotFoundError):
    """A cited evidence belongs to a different instrument."""


class CrossSnapshotError(ReferenceNotFoundError):
    """A cited evidence is not pinned by the specified snapshot."""

def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


class ResearchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- corporate events ----------------------------------------------------
    def save_event(
        self, event: CorporateEvent, *, validate_evidence: bool = True
    ) -> str:
        if validate_evidence:
            self._require_evidence(event.evidence_refs)
        row = CorporateEventORM(
            event_id=event.event_id,
            instrument_id=event.instrument_id,
            event_type=event.event_type.value,
            title=event.title,
            description=event.description,
            occurred_at=event.occurred_at,
            announced_at=event.announced_at,
            evidence_refs_json=list(event.evidence_refs),
            created_at=event.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.event_id

    def list_events(self, instrument_id: str) -> list[CorporateEvent]:
        rows = self._session.scalars(
            select(CorporateEventORM)
            .where(CorporateEventORM.instrument_id == instrument_id)
            .order_by(CorporateEventORM.occurred_at.desc())
        ).all()
        return [
            CorporateEvent(
                event_id=r.event_id,
                instrument_id=r.instrument_id,
                event_type=r.event_type,  # type: ignore[arg-type]
                title=r.title,
                description=r.description,
                occurred_at=_ensure_utc(r.occurred_at),
                announced_at=_ensure_utc(r.announced_at),
                evidence_refs=tuple(r.evidence_refs_json or ()),
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]

    # -- claims --------------------------------------------------------------
    def save_claim(self, claim: Claim, *, validate_refs: bool = True) -> str:
        if validate_refs:
            self._require_snapshot_evidence(
                claim.instrument_id, claim.snapshot_id,
                claim.supporting_evidence_refs + claim.opposing_evidence_refs,
            )
        row = ClaimORM(
            claim_id=claim.claim_id,
            instrument_id=claim.instrument_id,
            snapshot_id=claim.snapshot_id,
            statement=claim.statement,
            claim_type=claim.claim_type.value,
            supporting_evidence_refs_json=list(claim.supporting_evidence_refs),
            opposing_evidence_refs_json=list(claim.opposing_evidence_refs),
            fact_status=claim.fact_status.value,
            confidence=claim.confidence,
            status=claim.status.value,
            created_at=claim.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.claim_id

    def list_claims(
        self,
        instrument_id: str,
        *,
        snapshot_id: str | None = None,
        status: str | None = None,
    ) -> list[Claim]:
        stmt = select(ClaimORM).where(ClaimORM.instrument_id == instrument_id)
        if snapshot_id is not None:
            stmt = stmt.where(ClaimORM.snapshot_id == snapshot_id)
        if status is not None:
            stmt = stmt.where(ClaimORM.status == status)
        rows = self._session.scalars(stmt.order_by(ClaimORM.created_at.desc())).all()
        return [
            Claim(
                claim_id=r.claim_id,
                instrument_id=r.instrument_id,
                snapshot_id=r.snapshot_id,
                statement=r.statement,
                claim_type=r.claim_type,  # type: ignore[arg-type]
                supporting_evidence_refs=tuple(r.supporting_evidence_refs_json or ()),
                opposing_evidence_refs=tuple(r.opposing_evidence_refs_json or ()),
                fact_status=r.fact_status,  # type: ignore[arg-type]
                confidence=r.confidence,
                status=r.status,  # type: ignore[arg-type]
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]

    def get_claim(self, claim_id: str) -> Claim | None:
        row = self._session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id == claim_id)
        ).first()
        if row is None:
            return None
        return Claim(
            claim_id=row.claim_id,
            instrument_id=row.instrument_id,
            snapshot_id=row.snapshot_id,
            statement=row.statement,
            claim_type=row.claim_type,  # type: ignore[arg-type]
            supporting_evidence_refs=tuple(row.supporting_evidence_refs_json or ()),
            opposing_evidence_refs=tuple(row.opposing_evidence_refs_json or ()),
            fact_status=row.fact_status,  # type: ignore[arg-type]
            confidence=row.confidence,
            status=row.status,  # type: ignore[arg-type]
            created_at=_ensure_utc(row.created_at),
        )

    def get_thesis(self, thesis_id: str) -> InvestmentThesis | None:
        row = self._session.scalars(
            select(ThesisORM).where(ThesisORM.thesis_id == thesis_id)
        ).first()
        if row is None:
            return None
        return InvestmentThesis(
            thesis_id=row.thesis_id,
            instrument_id=row.instrument_id,
            snapshot_id=row.snapshot_id,
            title=row.title,
            description=row.description,
            supporting_claims=tuple(row.supporting_claims_json or ()),
            opposing_claims=tuple(row.opposing_claims_json or ()),
            confidence=row.confidence,
            catalysts=tuple(row.catalysts_json or ()),
            risks=tuple(row.risks_json or ()),
            trigger_conditions=tuple(row.trigger_conditions_json or ()),
            invalidate_conditions=tuple(row.invalidate_conditions_json or ()),
            status=row.status,  # type: ignore[arg-type]
            created_at=_ensure_utc(row.created_at),
        )

    # -- theses --------------------------------------------------------------
    def save_thesis(self, thesis: InvestmentThesis, *, validate_refs: bool = True) -> str:
        if validate_refs:
            self._require_snapshot_claims(
                thesis.instrument_id, thesis.snapshot_id,
                thesis.supporting_claims + thesis.opposing_claims,
            )
        row = ThesisORM(
            thesis_id=thesis.thesis_id,
            instrument_id=thesis.instrument_id,
            snapshot_id=thesis.snapshot_id,
            title=thesis.title,
            description=thesis.description,
            supporting_claims_json=list(thesis.supporting_claims),
            opposing_claims_json=list(thesis.opposing_claims),
            confidence=thesis.confidence,
            catalysts_json=list(thesis.catalysts),
            risks_json=list(thesis.risks),
            trigger_conditions_json=list(thesis.trigger_conditions),
            invalidate_conditions_json=list(thesis.invalidate_conditions),
            status=thesis.status.value,
            created_at=thesis.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.thesis_id

    def list_theses(self, instrument_id: str, *, snapshot_id: str | None = None) -> list[InvestmentThesis]:
        stmt = select(ThesisORM).where(ThesisORM.instrument_id == instrument_id)
        if snapshot_id is not None:
            stmt = stmt.where(ThesisORM.snapshot_id == snapshot_id)
        rows = self._session.scalars(stmt.order_by(ThesisORM.created_at.desc())).all()
        theses: list[InvestmentThesis] = []
        for r in rows:
            theses.append(
                InvestmentThesis(
                    thesis_id=r.thesis_id,
                    instrument_id=r.instrument_id,
                    snapshot_id=r.snapshot_id,
                    title=r.title,
                    description=r.description,
                    supporting_claims=tuple(r.supporting_claims_json or ()),
                    opposing_claims=tuple(r.opposing_claims_json or ()),
                    confidence=r.confidence,
                    catalysts=tuple(r.catalysts_json or ()),
                    risks=tuple(r.risks_json or ()),
                    trigger_conditions=tuple(r.trigger_conditions_json or ()),
                    invalidate_conditions=tuple(r.invalidate_conditions_json or ()),
                    status=r.status,  # type: ignore[arg-type]
                    created_at=_ensure_utc(r.created_at),
                )
            )
        return theses

    # -- integrity helpers ---------------------------------------------------
    def _require_evidence(self, evidence_ids) -> None:
        ids = list(dict.fromkeys(evidence_ids))
        if not ids:
            return
        existing = set(
            self._session.scalars(
                select(EvidenceORM.evidence_id).where(EvidenceORM.evidence_id.in_(ids))
            ).all()
        )
        missing = [i for i in ids if i not in existing]
        if missing:
            raise ReferenceNotFoundError(f"evidence not found: {missing}")

    def _require_claims(self, claim_ids) -> None:
        ids = list(dict.fromkeys(claim_ids))
        if not ids:
            return
        existing = set(
            self._session.scalars(
                select(ClaimORM.claim_id).where(ClaimORM.claim_id.in_(ids))
            ).all()
        )
        missing = [i for i in ids if i not in existing]
        if missing:
            raise ReferenceNotFoundError(f"claims not found: {missing}")

    def _require_snapshot_evidence(
        self, instrument_id: str, snapshot_id: str, evidence_ids
    ) -> None:
        """PIT integrity (P0-06): evidence must belong to the same instrument
        AND be pinned by the specified snapshot."""
        self._require_evidence(evidence_ids)
        from app.storage.snapshot_repo import SnapshotRepository as _SR

        snap = _SR(self._session).get(snapshot_id)
        if snap is None:
            raise CrossSnapshotError(f"snapshot {snapshot_id} not found")
        if snap.instrument_id != instrument_id:
            raise CrossInstrumentError(
                f"snapshot belongs to {snap.instrument_id}, not {instrument_id}"
            )
        pinned = set(snap.evidence_ids)
        for eid in evidence_ids:
            if eid not in pinned:
                raise CrossSnapshotError(
                    f"evidence {eid} not pinned by snapshot {snapshot_id}"
                )

    def _require_snapshot_claims(
        self, instrument_id: str, snapshot_id: str, claim_ids
    ) -> None:
        """Claims must belong to the same instrument and snapshot (P0-06)."""
        self._require_claims(claim_ids)
        for cid in claim_ids:
            c = self.get_claim(cid)
            if c is None:
                continue
            if c.instrument_id != instrument_id:
                raise CrossInstrumentError(
                    f"claim {cid} belongs to {c.instrument_id}, not {instrument_id}"
                )
            if c.snapshot_id != snapshot_id:
                raise CrossSnapshotError(
                    f"claim {cid} belongs to snapshot {c.snapshot_id}, not {snapshot_id}"
                )
