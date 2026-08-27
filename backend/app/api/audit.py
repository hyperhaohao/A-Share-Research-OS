"""Audit + revision API (M14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.audit import AuditFinding, AuditLevel, AuditResult, RevisionStatus, audit_claim
from app.storage.manifest_repo import ReportVersionRepository
from app.storage.report_repo import ReportRepository
from app.storage.repository import EvidenceRepository
from app.storage.research_repo import ResearchRepository, ReferenceNotFoundError
from app.storage.revision_repo import RevisionRepository

router = APIRouter(prefix="/reports", tags=["audit"])
revisions_router = APIRouter(prefix="/revisions", tags=["audit"])


class AuditIn(BaseModel):
    level: AuditLevel
    target_id: str | None = Field(default=None, max_length=24)


class RevisionIn(BaseModel):
    base_version_id: str = Field(min_length=8, max_length=24)
    target_section: str = Field(min_length=1, max_length=64)
    target_claim_id: str | None = Field(default=None, max_length=24)
    original_text: str = Field(min_length=1, max_length=8000)
    proposed_text: str = Field(min_length=1, max_length=8000)
    reason: str = Field(min_length=1, max_length=2000)
    added_evidence_refs: list[str] = Field(default_factory=list)
    invalidated_evidence_refs: list[str] = Field(default_factory=list)
    affected_claims: list[str] = Field(default_factory=list)
    confidence_change: float = 0.0


def _finding_payload(f: AuditFinding) -> dict:
    return {"code": f.code, "severity": f.severity, "message": f.message}


def _proposal_payload(p) -> dict:
    return {
        "proposal_id": p.proposal_id,
        "report_id": p.report_id,
        "base_version_id": p.base_version_id,
        "target_section": p.target_section,
        "target_claim_id": p.target_claim_id,
        "original_text": p.original_text,
        "proposed_text": p.proposed_text,
        "reason": p.reason,
        "added_evidence_refs": list(p.added_evidence_refs),
        "invalidated_evidence_refs": list(p.invalidated_evidence_refs),
        "affected_claims": list(p.affected_claims),
        "confidence_change": p.confidence_change,
        "status": p.status.value,
        "created_at": p.created_at.isoformat(),
    }


@router.post("/{report_id}/audits")
def run_audit(
    report_id: str,
    payload: AuditIn,
    session: Session = Depends(get_session),
) -> dict:
    """Deterministic audit over the report's research state (§43)."""
    report = ReportRepository(session).get(report_id)
    if report is None:
        raise AppError("report.not_found", status_code=404)

    from app.storage.snapshot_repo import SnapshotRepository

    snapshot = SnapshotRepository(session).get(report["snapshot_id"])
    if snapshot is None:
        raise AppError("snapshot.not_found", status_code=404)

    evidence_repo = EvidenceRepository(session)
    pinned = set(snapshot.evidence_ids)
    evidence = {
        e.evidence_id: e
        for e in evidence_repo.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        if e.evidence_id in pinned
    }
    research = ResearchRepository(session)
    claims = research.list_claims(
        snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
    )

    if payload.level in (AuditLevel.CLAIM, AuditLevel.SENTENCE):
        target = next(
            (c for c in claims if c.claim_id == payload.target_id), None
        ) if payload.target_id else (claims[0] if claims else None)
        if target is None:
            raise AppError("audit.no_target", status_code=422)
        result = audit_claim(target, evidence, as_of=snapshot.as_of)
        results = [result]
    elif payload.level is AuditLevel.THESIS:
        theses = research.list_theses(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )
        results = []
        for thesis in theses:
            if payload.target_id and thesis.thesis_id != payload.target_id:
                continue
            for cid in tuple(thesis.supporting_claims) + tuple(thesis.opposing_claims):
                claim = research.get_claim(cid)
                if claim is not None:
                    results.append(audit_claim(claim, evidence, as_of=snapshot.as_of))
    else:
        results = [audit_claim(c, evidence, as_of=snapshot.as_of) for c in claims]

    all_findings = [_finding_payload(f) for r in results for f in r.findings]
    blocked = any(f["severity"] == "fail" for f in all_findings)
    return {
        "report_id": report_id,
        "level": payload.level.value,
        "findings": all_findings,
        "has_fail": blocked,
    }


@router.post("/{report_id}/revisions", status_code=201)
def create_revision(
    report_id: str,
    payload: RevisionIn,
    session: Session = Depends(get_session),
) -> dict:
    from app.domain.audit import RevisionProposal

    repo = RevisionRepository(session)
    proposal = RevisionProposal(
        report_id=report_id,
        base_version_id=payload.base_version_id,
        target_section=payload.target_section,
        target_claim_id=payload.target_claim_id,
        original_text=payload.original_text,
        proposed_text=payload.proposed_text,
        reason=payload.reason,
        added_evidence_refs=tuple(payload.added_evidence_refs),
        invalidated_evidence_refs=tuple(payload.invalidated_evidence_refs),
        affected_claims=tuple(payload.affected_claims),
        confidence_change=payload.confidence_change,
        status=RevisionStatus.PROPOSED,
    )
    try:
        proposal_id = repo.save(proposal)
    except ReferenceNotFoundError as exc:
        raise AppError("revision.evidence_not_found", status_code=422, detail=str(exc)) from None
    saved = repo.get(proposal_id)
    assert saved is not None
    return {"proposal": _proposal_payload(saved)}


@revisions_router.post("/{proposal_id}/accept")
def accept_revision(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    repo = RevisionRepository(session)
    try:
        version = repo.accept(proposal_id)
    except KeyError:
        raise AppError("revision.not_found", status_code=404) from None
    except ValueError as exc:
        raise AppError("revision.invalid_state", status_code=422, detail=str(exc)) from None
    except ReferenceNotFoundError as exc:
        raise AppError("report.version_chain_missing", status_code=422, detail=str(exc)) from None
    saved = ReportVersionRepository(session).get(version.version_id)
    assert saved is not None
    return {
        "version": {
            "version_id": saved.version_id,
            "report_id": saved.report_id,
            "version_no": saved.version_no,
            "parent_version_id": saved.parent_version_id,
            "changed_sections": list(saved.changed_sections),
            "change_reason": saved.change_reason,
        }
    }


@revisions_router.post("/{proposal_id}/reject")
def reject_revision(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    repo = RevisionRepository(session)
    try:
        repo.reject(proposal_id)
    except KeyError:
        raise AppError("revision.not_found", status_code=404) from None
    except ValueError as exc:
        raise AppError("revision.invalid_state", status_code=422, detail=str(exc)) from None
    proposal = repo.get(proposal_id)
    assert proposal is not None
    return {"proposal": _proposal_payload(proposal)}


@router.get("/{report_id}/revisions")
def list_revisions(
    report_id: str,
    session: Session = Depends(get_session),
) -> dict:
    proposals = RevisionRepository(session).list_for_report(report_id)
    return {"count": len(proposals), "results": [_proposal_payload(p) for p in proposals]}
