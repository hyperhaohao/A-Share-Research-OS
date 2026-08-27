"""Quality gate service: evaluate and persist gate results for a snapshot."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.quality import (
    AnalysisQualityGate,
    EvidenceQualityGate,
    FinalReportQualityGate,
    GateName,
    GateResult,
    ReportGateInput,
)
from app.storage.quality_orm import QualityGateResultORM, _ensure_utc
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


class QualityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._snapshots = SnapshotRepository(session)
        self._evidence = EvidenceRepository(session)
        self._research = ResearchRepository(session)

    # -- persistence ---------------------------------------------------------
    def _persist(self, snapshot, result: GateResult) -> str:
        row = QualityGateResultORM(
            result_id=f"gate_{uuid4().hex[:16]}",
            snapshot_id=snapshot.snapshot_id,
            instrument_id=snapshot.instrument_id,
            gate=result.gate.value,
            status=result.status.value,
            findings_json=[f.model_dump(mode="json") for f in result.findings],
            evaluated_at=result.evaluated_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.result_id

    def history(self, snapshot_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(QualityGateResultORM)
            .where(QualityGateResultORM.snapshot_id == snapshot_id)
            .order_by(QualityGateResultORM.evaluated_at.desc())
        ).all()
        return [
            {
                "result_id": r.result_id,
                "snapshot_id": r.snapshot_id,
                "instrument_id": r.instrument_id,
                "gate": r.gate,
                "status": r.status,
                "findings": r.findings_json or [],
                "evaluated_at": _ensure_utc(r.evaluated_at).isoformat()
                if r.evaluated_at
                else None,
            }
            for r in rows
        ]

    # -- evaluation ----------------------------------------------------------
    def run_evidence_and_analysis_gates(self, snapshot_id: str) -> list[GateResult]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)

        evidence = self._evidence.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        evidence_by_id = {e.evidence_id: e for e in evidence}
        claims = self._research.list_claims(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )
        manifests = self._evidence_recent_manifests(snapshot.instrument_id)

        results: list[GateResult] = []

        evidence_gate = EvidenceQualityGate().evaluate(snapshot, evidence, manifests=manifests)
        results.append(evidence_gate)
        self._persist(snapshot, evidence_gate)

        analysis_gate = AnalysisQualityGate().evaluate(
            claims, evidence_lookup=evidence_by_id
        )
        results.append(analysis_gate)
        self._persist(snapshot, analysis_gate)

        return results

    def run_final_report_gate(self, report: ReportGateInput) -> GateResult:
        """Run the publication gate over a report draft (M11 wires the real report)."""
        return FinalReportQualityGate().evaluate(report)

    def _evidence_recent_manifests(self, instrument_id: str) -> list:
        """Manifests for this instrument; used for source-failure visibility."""
        from app.domain.evidence import SourceManifest
        from app.storage.orm import SourceManifestORM

        rows = self._session.scalars(
            select(SourceManifestORM)
            .where(SourceManifestORM.instrument_id == instrument_id)
            .order_by(SourceManifestORM.created_at.desc())
            .limit(20)
        ).all()
        return [
            SourceManifest(
                manifest_id=r.manifest_id,
                instrument_id=r.instrument_id,
                capability=r.capability,
                requested_as_of=_ensure_utc(r.requested_as_of),
                created_at=_ensure_utc(r.created_at),
                providers_attempted=tuple(r.providers_attempted or ()),
                final_status=r.final_status,
                final_source=r.final_source,
                evidence_ids=tuple(r.evidence_ids or ()),
                from_cache=r.from_cache,
            )
            for r in rows
        ]
