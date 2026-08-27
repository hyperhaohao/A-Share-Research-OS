"""Audit + RevisionProposal domain (任务书 §43/§44).

Audits are deterministic checks over the citation chain — no LLM required
for the honest detection path:

  unsupported           claim cites no resolvable evidence
  outdated              cited evidence is stale relative to as_of
  conflicting           opposing evidence cited without an explanation
  numeric_inconsistency numbers in the statement that appear in no cited
                        evidence payload

RevisionProposal (§44): a proposed change with full context — the LLM (or a
reviewer) proposes; acceptance creates a new immutable ReportVersion.
Original text is never overwritten in place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.evidence import utc_now


class AuditLevel(str, Enum):
    SENTENCE = "sentence"
    CLAIM = "claim"
    THESIS = "thesis"
    FULL_REPORT = "full_report"


class AuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str  # audit.unsupported / audit.outdated / audit.conflicting /
    # audit.numeric_inconsistency / audit.logic_leap
    severity: str  # "fail" | "warn" | "info"
    message: str


class AuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: AuditLevel
    target_id: str | None
    findings: tuple[AuditFinding, ...] = ()
    checked_at: datetime = Field(default_factory=utc_now)


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def audit_claim(claim, evidence_lookup: dict, *, as_of: datetime | None = None,
                stale_days: int = 180) -> AuditResult:
    """Deterministic audit of one claim against its cited evidence."""
    findings: list[AuditFinding] = []
    now = as_of or utc_now()

    refs = list(claim.supporting_evidence_refs) + list(claim.opposing_evidence_refs)
    missing = [r for r in refs if r not in evidence_lookup]
    if missing:
        findings.append(
            AuditFinding(
                code="audit.unsupported",
                severity="fail",
                message=f"cited evidence not resolvable: {missing}",
            )
        )

    for ref in refs:
        ev = evidence_lookup.get(ref)
        if ev is None:
            continue
        if now - ev.available_time > timedelta(days=stale_days):
            findings.append(
                AuditFinding(
                    code="audit.outdated",
                    severity="warn",
                    message=f"evidence {ref} available {ev.available_time:%Y-%m-%d} is >{stale_days}d old",
                )
            )

    if claim.opposing_evidence_refs and not (claim.metadata or {}).get("conflict_note"):
        findings.append(
            AuditFinding(
                code="audit.conflicting",
                severity="warn",
                message="opposing evidence cited without an explanation",
            )
        )

    # Numeric consistency: every number in the statement should trace to the
    # cited evidence payloads (or the statement carries no numbers at all).
    statement_numbers = set(_NUMBER.findall(claim.statement))
    if statement_numbers and refs:
        evidence_text = " ".join(
            str(v)
            for ref in refs
            if (ev := evidence_lookup.get(ref)) is not None
            for v in (ev.metadata or {}).values()
        )
        untraceable = [n for n in statement_numbers if n not in evidence_text]
        if untraceable:
            findings.append(
                AuditFinding(
                    code="audit.numeric_inconsistency",
                    severity="fail",
                    message=f"numbers {untraceable} in statement not traceable to cited evidence",
                )
            )

    return AuditResult(level=AuditLevel.CLAIM, target_id=claim.claim_id, findings=tuple(findings))


class RevisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RevisionProposal(BaseModel):
    """A proposed report change with full context (任务书 §44)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    proposal_id: str = Field(default_factory=lambda: f"rev_{uuid4().hex[:16]}")
    report_id: str = Field(min_length=8, max_length=24)
    base_version_id: str = Field(min_length=8, max_length=24)

    target_section: str = Field(min_length=1, max_length=64)
    target_claim_id: str | None = None
    original_text: str = Field(min_length=1, max_length=8000)
    proposed_text: str = Field(min_length=1, max_length=8000)
    reason: str = Field(min_length=1, max_length=2000)
    added_evidence_refs: tuple[str, ...] = ()
    invalidated_evidence_refs: tuple[str, ...] = ()
    affected_claims: tuple[str, ...] = ()
    confidence_change: float = 0.0

    status: RevisionStatus = RevisionStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def _validate(self) -> "RevisionProposal":
        for name in ("created_at", "resolved_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.original_text == self.proposed_text:
            raise ValueError("proposed text must differ from original")
        return self
