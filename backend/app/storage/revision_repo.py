"""RevisionProposal persistence + accept/reject flow (M14)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.audit import RevisionProposal, RevisionStatus
from app.domain.manifest import ReportVersion
from app.storage.agent_repo import _ensure_utc
from app.storage.manifest_repo import ReportVersionRepository
from app.storage.orm import Base
from app.storage.research_repo import ReferenceNotFoundError, ResearchRepository


class RevisionProposalORM(Base):
    __tablename__ = "revision_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    proposal_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    report_id: Mapped[str] = mapped_column(String(24), index=True)
    base_version_id: Mapped[str] = mapped_column(String(24), index=True)

    target_section: Mapped[str] = mapped_column(String(64))
    target_claim_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    original_text: Mapped[str] = mapped_column(default="")
    proposed_text: Mapped[str] = mapped_column(default="")
    reason: Mapped[str] = mapped_column(default="")
    added_evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    invalidated_evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    affected_claims_json: Mapped[list] = mapped_column(JSON, default=list)
    confidence_change: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RevisionRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session
        self._research = ResearchRepository(session)
        self._versions = ReportVersionRepository(session)

    def save(self, proposal: RevisionProposal, *, validate_evidence: bool = True) -> str:
        if validate_evidence:
            refs = tuple(proposal.added_evidence_refs) + tuple(proposal.invalidated_evidence_refs)
            if refs:
                self._research._require_evidence(refs)
        row = RevisionProposalORM(
            proposal_id=proposal.proposal_id,
            report_id=proposal.report_id,
            base_version_id=proposal.base_version_id,
            target_section=proposal.target_section,
            target_claim_id=proposal.target_claim_id,
            original_text=proposal.original_text,
            proposed_text=proposal.proposed_text,
            reason=proposal.reason,
            added_evidence_refs_json=list(proposal.added_evidence_refs),
            invalidated_evidence_refs_json=list(proposal.invalidated_evidence_refs),
            affected_claims_json=list(proposal.affected_claims),
            confidence_change=proposal.confidence_change,
            status=proposal.status.value,
            created_at=proposal.created_at,
            resolved_at=proposal.resolved_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.proposal_id

    def get(self, proposal_id: str) -> RevisionProposal | None:
        row = self._session.scalars(
            select(RevisionProposalORM).where(
                RevisionProposalORM.proposal_id == proposal_id
            )
        ).first()
        return None if row is None else self._row_to_domain(row)

    def list_for_report(self, report_id: str) -> list[RevisionProposal]:
        rows = self._session.scalars(
            select(RevisionProposalORM)
            .where(RevisionProposalORM.report_id == report_id)
            .order_by(RevisionProposalORM.created_at.desc())
        ).all()
        return [self._row_to_domain(r) for r in rows]

    def accept(self, proposal_id: str) -> ReportVersion:
        """Accept the proposal → structured patch → new immutable version.

        F0 (P0-01): works on the structured section items stored in
        content_json (not markdown string replacement). Both markdown and
        HTML are re-rendered from the modified structured state, and the
        quality gate is re-run before saving.
        """
        proposal = self.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.status is not RevisionStatus.PROPOSED:
            raise ValueError(f"proposal already {proposal.status.value}")

        chain = self._versions.list_chain(proposal.report_id)
        if not chain:
            raise ReferenceNotFoundError(
                f"report {proposal.report_id} has no version chain to extend"
            )

        # stale base_version check
        previous = chain[-1]
        if previous.version_id != proposal.base_version_id:
            raise ValueError(
                f"stale base_version: expected {previous.version_id}, "
                f"got {proposal.base_version_id}"
            )

        # restore section items from the previous version's content_json
        section_items = previous.content_json.get("section_items", {})
        import sys
        exec_items = section_items.get(proposal.target_section, [])
        print(f"DEBUG: target_section={proposal.target_section}, items={len(exec_items)}, original={proposal.original_text[:40]}", file=sys.stderr)
        for i, it in enumerate(exec_items):
            print(f"  item[{i}] text_zh={it.get('text_zh', '')[:50]}", file=sys.stderr)
        if not section_items:
            raise ValueError(
                "previous version has no section_items in content_json — "
                "cannot perform structured revision"
            )

        # find the matching item in the target section
        target_section = section_items.get(proposal.target_section)
        if target_section is None:
            raise ValueError(
                f"section {proposal.target_section} not found in version"
            )

            import sys
        print(f'DBG proposal.original_text={proposal.original_text!r}', file=sys.stderr)
        matched = False
        for item in target_section:
            if item.get("text_zh") == proposal.original_text:
                item["text_zh"] = proposal.proposed_text
                item["text_en"] = None
                item["text_language"] = "zh-CN"
                matched = True
            elif item.get("text_en") == proposal.original_text:
                item["text_en"] = proposal.proposed_text
                matched = True
        if not matched:
            raise ValueError(
                f"original_text not found in section {proposal.target_section}"
            )

        # rebuild the report from modified section items
        from app.domain.report import (
            ReportRenderer,
            ReportSection,
            StructuredReport,
        )
        from datetime import datetime as _dt, timezone as _tz

        report = StructuredReport(
            instrument_id=previous.content_json.get("instrument_id", ""),
            snapshot_id=previous.content_json.get("snapshot_id", ""),
            as_of=_dt.now(_tz.utc),
            generated_at=_dt.now(_tz.utc),
        )
        all_citations: list[str] = []
        for key, items in section_items.items():
            section = report.section(key)
            section.items = items
            for item in items:
                for ev in item.get("evidence_ids", []):
                    all_citations.append(ev)
        report.citations = list(dict.fromkeys(all_citations))

        # re-render both artifacts
        renderer = ReportRenderer(previous.language)
        revised_markdown = renderer.render_markdown(report)
        revised_html = renderer.render_html(report)

        # re-run the quality gate
        from app.domain.quality import (
            FinalReportQualityGate,
            ReportGateInput,
        )

        gate_input = ReportGateInput(
            known_evidence_ids=tuple(set(report.citations)),
            citations=tuple(set(report.citations)),
            claim_support=self._extract_claim_support(report),
            has_valuation=bool(report.sections.get("valuation") and report.sections["valuation"].items),
            valuation_assumptions=("revised via structured revision",),
            risk_section=bool(report.sections.get("risks") and report.sections["risks"].items),
            data_quality_section=True,
            disclaimer=True,
        )
        gate = FinalReportQualityGate().evaluate(gate_input)
        if gate.blocked:
            raise ValueError(
                f"revision gate FAILED: "
                + "; ".join(f.code for f in gate.findings if f.severity == "fail")
            )

        version = ReportVersion(
            report_id=proposal.report_id,
            version_no=previous.version_no + 1,
            parent_version_id=previous.version_id,
            change_reason=proposal.reason,
            changed_sections=(proposal.target_section,),
            language=previous.language,
            markdown=revised_markdown,
            html=revised_html,
            content_json={
                **previous.content_json,
                "section_items": section_items,
                "revision_proposal_id": proposal.proposal_id,
                "citations": sorted(set(report.citations)),
            },
        )
        version_id = self._versions.save(version)

        proposal.status = RevisionStatus.ACCEPTED
        proposal.resolved_at = datetime.now(timezone.utc)
        self._sync_status(proposal)
        return version

    @staticmethod
    def _extract_claim_support(report) -> dict:
        support: dict = {}
        for section in report.sections.values():
            for item in section.items:
                for cid in item.get("claim_ids", []):
                    support[cid] = tuple(item.get("evidence_ids", []))
        return support

    def reject(self, proposal_id: str) -> None:
        proposal = self.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.status is not RevisionStatus.PROPOSED:
            raise ValueError(f"proposal already {proposal.status.value}")
        proposal.status = RevisionStatus.REJECTED
        proposal.resolved_at = datetime.now(timezone.utc)
        self._sync_status(proposal)

    def _sync_status(self, proposal: RevisionProposal) -> None:
        from sqlalchemy import update as _update

        self._session.execute(
            _update(RevisionProposalORM)
            .where(RevisionProposalORM.proposal_id == proposal.proposal_id)
            .values(status=proposal.status.value, resolved_at=proposal.resolved_at)
        )
        self._session.flush()

    @staticmethod
    def _row_to_domain(r: RevisionProposalORM) -> RevisionProposal:
        return RevisionProposal(
            proposal_id=r.proposal_id,
            report_id=r.report_id,
            base_version_id=r.base_version_id,
            target_section=r.target_section,
            target_claim_id=r.target_claim_id,
            original_text=r.original_text,
            proposed_text=r.proposed_text,
            reason=r.reason,
            added_evidence_refs=tuple(r.added_evidence_refs_json or ()),
            invalidated_evidence_refs=tuple(r.invalidated_evidence_refs_json or ()),
            affected_claims=tuple(r.affected_claims_json or ()),
            confidence_change=r.confidence_change,
            status=r.status,  # type: ignore[arg-type]
            created_at=_ensure_utc(r.created_at),
            resolved_at=_ensure_utc(r.resolved_at),
        )

def _markdown_to_structured(markdown: str):
    """Minimal markdown→structured adapter for re-rendering HTML after a
    targeted revision. The full compiler remains the production path."""
    from app.domain.report import StructuredReport, ReportSection
    from datetime import datetime, timezone as _tz

    report = StructuredReport(
        instrument_id="", snapshot_id="",
        as_of=datetime.now(_tz.utc),
        generated_at=datetime.now(_tz.utc),
    )
    current_section = None
    for line in markdown.splitlines():
        if line.startswith("## "):
            key = line[3:].strip().lower().replace(" ", "_")
            current_section = ReportSection(key=key)
            report.sections[key] = current_section
        elif line.startswith("- ") and current_section is not None:
            current_section.items.append(
                {"text_zh": line[2:], "text_en": line[2:], "text_language": "zh-CN"}
            )
    return report
