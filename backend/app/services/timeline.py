"""Unified timeline (任务书 §46).

A derived read model — no duplicate storage. Events are aggregated from the
existing research objects (evidence, claims, theses, corporate events,
research runs, report versions, materiality decisions) and answer
「何时发生了什么」 for one instrument.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.manifest_repo import _ensure_utc, ReportVersionORM
from app.storage.orm import (
    EvidenceORM,
    ResearchRunORM,
    SnapshotORM,
)
from app.storage.research_orm import ClaimORM, CorporateEventORM, ThesisORM
from app.storage.report_repo import ReportORM


@dataclass
class TimelineEvent:
    occurred_at: datetime
    kind: str  # evidence_added / claim_changed / thesis_changed /
    # corporate_event / research_run / report_version / snapshot_built
    title: str
    ref_id: str
    detail: dict[str, Any]

    def as_dict(self) -> dict:
        return {
            "occurred_at": self.occurred_at.isoformat(),
            "kind": self.kind,
            "title": self.title,
            "ref_id": self.ref_id,
            "detail": self.detail,
        }


class TimelineService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def build(
        self,
        instrument_id: str,
        *,
        kinds: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TimelineEvent]:
        wanted = set(kinds) if kinds else None

        def wanted_kind(kind: str) -> bool:
            return wanted is None or kind in wanted

        events: list[TimelineEvent] = []

        # evidence (quotes → market events; others → evidence_added)
        for row in self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.instrument_id == instrument_id)
        ):
            kind = (
                "market_event"
                if row.evidence_type == "market_quote"
                else "evidence_added"
            )
            if wanted_kind(kind):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.available_time) or utc_fallback(),
                        kind=kind,
                        title=row.title,
                        ref_id=row.evidence_id,
                        detail={"evidence_type": row.evidence_type, "source": row.source},
                    )
                )

        # claims
        if wanted_kind("claim_changed"):
            for row in self._session.scalars(
                select(ClaimORM).where(ClaimORM.instrument_id == instrument_id)
            ):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.created_at) or utc_fallback(),
                        kind="claim_changed",
                        title=row.statement[:120],
                        ref_id=row.claim_id,
                        detail={"claim_type": row.claim_type, "status": row.status},
                    )
                )

        # theses
        if wanted_kind("thesis_changed"):
            for row in self._session.scalars(
                select(ThesisORM).where(ThesisORM.instrument_id == instrument_id)
            ):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.created_at) or utc_fallback(),
                        kind="thesis_changed",
                        title=row.title,
                        ref_id=row.thesis_id,
                        detail={"status": row.status, "confidence": row.confidence},
                    )
                )

        # corporate events
        if wanted_kind("corporate_event"):
            for row in self._session.scalars(
                select(CorporateEventORM).where(
                    CorporateEventORM.instrument_id == instrument_id
                )
            ):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.occurred_at) or utc_fallback(),
                        kind="corporate_event",
                        title=row.title,
                        ref_id=row.event_id,
                        detail={"event_type": row.event_type},
                    )
                )

        # research runs
        if wanted_kind("research_run"):
            for row in self._session.scalars(
                select(ResearchRunORM).where(ResearchRunORM.instrument_id == instrument_id)
            ):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.as_of) or utc_fallback(),
                        kind="research_run",
                        title=f"research run ({row.run_type})",
                        ref_id=row.run_id,
                        detail={"status": row.status, "snapshot_id": row.snapshot_id},
                    )
                )

        # report versions (reports themselves carry the instrument)
        if wanted_kind("report_version"):
            report_rows = self._session.scalars(
                select(ReportVersionORM)
            ).all()
            # reports table holds instrument mapping; join in python (small scale)
            report_map = {
                r.report_id: r.instrument_id
                for r in self._session.scalars(
                    select(ReportORM).where(ReportORM.instrument_id == instrument_id)
                )
            }
            for row in report_rows:
                if row.report_id in report_map:
                    events.append(
                        TimelineEvent(
                            occurred_at=_ensure_utc(row.created_at) or utc_fallback(),
                            kind="report_version",
                            title=f"report v{row.version_no} ({row.language})",
                            ref_id=row.version_id,
                            detail={"report_id": row.report_id, "version_no": row.version_no},
                        )
                    )

        # snapshots
        if wanted_kind("snapshot_built"):
            for row in self._session.scalars(
                select(SnapshotORM).where(SnapshotORM.instrument_id == instrument_id)
            ):
                events.append(
                    TimelineEvent(
                        occurred_at=_ensure_utc(row.as_of) or utc_fallback(),
                        kind="snapshot_built",
                        title=f"evidence snapshot ({len(row.items_json or [])} items)",
                        ref_id=row.snapshot_id,
                        detail={"content_hash": row.content_hash[:16]},
                    )
                )

        events.sort(key=lambda e: e.occurred_at, reverse=True)
        if wanted is not None:
            events = [e for e in events if e.kind in wanted]
        return events[offset : offset + limit]


def utc_fallback() -> datetime:
    from app.domain.evidence import utc_now

    return utc_now()
