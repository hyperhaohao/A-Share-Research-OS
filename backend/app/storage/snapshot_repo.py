"""Snapshot + research-run persistence (M5).

Snapshot build is the PIT gate: only evidence with
``available_time <= as_of`` is eligible, and a stored snapshot is returned
as-is for the same (instrument_id, as_of) — later data never rewrites
history (任务书 §23/§24/§74).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.evidence import utc_now
from app.domain.snapshot import (
    ResearchRun,
    ResearchRunStatus,
    ResearchRunType,
    SnapshotItem,
    EvidenceSnapshot,
)
from app.storage.orm import ResearchRunORM, SnapshotORM


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- snapshots -----------------------------------------------------------
    def get(self, snapshot_id: str) -> EvidenceSnapshot | None:
        row = self._session.scalars(
            select(SnapshotORM).where(SnapshotORM.snapshot_id == snapshot_id)
        ).first()
        return None if row is None else _snapshot_row_to_domain(row)

    def get_for(self, instrument_id: str, as_of: datetime) -> EvidenceSnapshot | None:
        """Return the stored snapshot covering (instrument, as_of), if any.

        A snapshot is reused when it was built for an as_of at-or-after the
        request but reflects knowledge available at the request time... in
        fact the simple immutable contract: exact (instrument, as_of) match.
        """
        row = self._session.scalars(
            select(SnapshotORM).where(
                SnapshotORM.instrument_id == instrument_id,
                SnapshotORM.as_of == as_of,
            )
        ).first()
        return None if row is None else _snapshot_row_to_domain(row)

    def build(self, instrument_id: str, as_of: datetime, *, evidence_repo) -> EvidenceSnapshot:
        """Get-or-create the immutable snapshot for (instrument, as_of).

        PIT gate: candidate evidence is filtered by
        ``available_time <= as_of``; anything newer never enters the snapshot.
        """
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        as_of = as_of.astimezone(timezone.utc)  # canonical storage offset

        existing = self.get_for(instrument_id, as_of)
        if existing is not None:
            return existing

        candidates = evidence_repo.list_for_instrument(instrument_id, visible_at=as_of)
        items = tuple(
            SnapshotItem(evidence_id=r.evidence_id, content_hash=r.content_hash)
            for r in candidates
            if r.visible_at(as_of)  # domain-level double check of the gate
        )
        snapshot = EvidenceSnapshot(
            instrument_id=instrument_id,
            as_of=as_of,
            items=items,
            created_at=utc_now(),
        )
        row = SnapshotORM(
            snapshot_id=snapshot.snapshot_id,
            content_hash=snapshot.content_hash,
            instrument_id=snapshot.instrument_id,
            as_of=snapshot.as_of,
            items_json=[item.model_dump(mode="json") for item in snapshot.items],
            created_at=snapshot.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return snapshot


class ResearchRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        run_id: str,
        instrument_id: str,
        as_of: datetime,
        *,
        run_type: ResearchRunType = ResearchRunType.FULL,
        snapshot_id: str | None = None,
        started: bool = True,
    ) -> ResearchRun:
        now = utc_now()
        run = ResearchRun(
            run_id=run_id,
            instrument_id=instrument_id,
            as_of=as_of,
            run_type=run_type,
            status=ResearchRunStatus.RUNNING if started else ResearchRunStatus.PENDING,
            snapshot_id=snapshot_id,
            started_at=now if started else None,
        )
        self._session.add(
            ResearchRunORM(
                run_id=run.run_id,
                instrument_id=run.instrument_id,
                as_of=run.as_of,
                run_type=run.run_type.value,
                status=run.status.value,
                snapshot_id=run.snapshot_id,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
        )
        self._session.flush()
        return run

    def get(self, run_id: str) -> ResearchRun | None:
        row = self._session.scalars(
            select(ResearchRunORM).where(ResearchRunORM.run_id == run_id)
        ).first()
        if row is None:
            return None
        return ResearchRun(
            run_id=row.run_id,
            instrument_id=row.instrument_id,
            as_of=_ensure_utc(row.as_of),
            run_type=row.run_type,  # type: ignore[arg-type]
            status=row.status,  # type: ignore[arg-type]
            snapshot_id=row.snapshot_id,
            started_at=_ensure_utc(row.started_at),
            finished_at=_ensure_utc(row.finished_at),
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    """SQLite loses tzinfo on round-trip; stored values are UTC by convention."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _snapshot_row_to_domain(row: SnapshotORM) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        instrument_id=row.instrument_id,
        as_of=_ensure_utc(row.as_of),
        items=tuple(SnapshotItem(**item) for item in (row.items_json or [])),
        created_at=_ensure_utc(row.created_at),
    )
