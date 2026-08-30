"""Quality gates (任务书 §31).

Gates are real business rules over the research state — never cosmetics.
A FAIL blocks publication downstream (M11+): ``FinalReportQualityGate``
failures prevent a formal report from being issued.

Three gates:

  EvidenceQualityGate   the evidence set feeding research (PIT, authority,
                        freshness, coverage, conflicts, source failures)
  AnalysisQualityGate   the claims layer (evidence-backed, fact/prediction
                        boundary, conflicts explained, missing data disclosed)
  FinalReportQualityGate  the report artifact (citations valid, claims
                        supported, valuation assumptions, risks, disclaimer)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.evidence import AuthorityLevel, FactStatus, utc_now
from app.domain.source_trust import TrustEscalationError, check_fact_support, trust_for_evidence
from app.domain.snapshot import EvidenceSnapshot


class GateName(str, Enum):
    EVIDENCE = "evidence_quality"
    ANALYSIS = "analysis_quality"
    FINAL_REPORT = "final_report_quality"


class GateSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"


class GateStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class GateFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str  # stable machine code, e.g. "evidence.stale"
    message: str
    severity: GateSeverity


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: GateName
    status: GateStatus
    findings: tuple[GateFinding, ...] = ()
    evaluated_at: datetime

    @property
    def blocked(self) -> bool:
        return self.status is GateStatus.FAIL


# Default freshness windows per evidence type (days): quotes must be very
# fresh; filings and events age slowly.
_FRESHNESS_DAYS: dict[str, int] = {
    "market_quote": 3,
    "announcement": 180,
    "financial_report": 120,
    "news": 30,
    "research_report": 90,
    "corporate_action": 180,
    "macro_indicator": 90,
    "capital_flow": 7,
    "industry_data": 180,
}


class EvidenceQualityGate:
    """Gate over the evidence pinned by a snapshot."""

    gate = GateName.EVIDENCE

    def __init__(self, *, min_authority: AuthorityLevel = AuthorityLevel.C2,
                 max_stale_days: int | None = None) -> None:
        self._min_authority = min_authority
        self._max_stale_days = max_stale_days

    def evaluate(self, snapshot: EvidenceSnapshot, evidence: list, *, manifests: list | None = None) -> GateResult:
        findings: list[GateFinding] = []

        if not evidence:
            findings.append(
                GateFinding(
                    code="evidence.empty",
                    message="snapshot pins no evidence; research cannot start",
                    severity=GateSeverity.FAIL,
                )
            )

        # PIT: re-verify visibility at as_of (by construction true; guard
        # against upstream corruption).
        for record in evidence:
            if not record.visible_at(snapshot.as_of):
                findings.append(
                    GateFinding(
                        code="evidence.pit_violation",
                        message=f"{record.evidence_id} available after as_of",
                        severity=GateSeverity.FAIL,
                    )
                )

        # Authority: flag weak-only sourcing.
        authority_rank = {a.value: i for i, a in enumerate(AuthorityLevel)}
        threshold = authority_rank[self._min_authority.value]
        if evidence and all(authority_rank[r.authority_level.value] > threshold for r in evidence):
            findings.append(
                GateFinding(
                    code="evidence.low_authority",
                    message=f"no evidence at or above authority {self._min_authority.value}",
                    severity=GateSeverity.WARN,
                )
            )

        # Freshness per evidence type.
        limit = self._max_stale_days
        for record in evidence:
            window = _FRESHNESS_DAYS.get(record.evidence_type.value, 90)
            effective = limit if limit is not None else window
            stale_after = snapshot.as_of - timedelta(days=effective)
            if record.available_time < stale_after:
                findings.append(
                    GateFinding(
                        code="evidence.stale",
                        message=(
                            f"{record.evidence_id} ({record.evidence_type.value}) "
                            f"older than {effective}d at as_of"
                        ),
                        severity=GateSeverity.WARN if record.evidence_type.value != "market_quote" else GateSeverity.FAIL,
                    )
                )

        # Source failures visible for this instrument/capability.
        for manifest in manifests or []:
            if manifest.final_status not in ("success", "partial") and not manifest.from_cache:
                findings.append(
                    GateFinding(
                        code="evidence.source_failure",
                        message=(
                            f"{manifest.capability} collection ended '{manifest.final_status}'"
                            + (f" via {manifest.final_source}" if manifest.final_source else "")
                        ),
                        severity=GateSeverity.WARN,
                    )
                )

        status = GateStatus.FAIL if any(f.severity is GateSeverity.FAIL for f in findings) else (
            GateStatus.WARN if findings else GateStatus.PASS
        )
        return GateResult(gate=self.gate, status=status, findings=tuple(findings), evaluated_at=snapshot.as_of)


class AnalysisQualityGate:
    """Gate over claims in a research state."""

    gate = GateName.ANALYSIS

    # Prediction-flavoured words that must not appear in confirmed-fact claims.
    _PREDICTION_MARKERS = ("预计", "预期", "将增长", "将下降", "预计达到", "likely", "expected to")

    def evaluate(self, claims: list, evidence_lookup: dict[str, object]) -> GateResult:
        findings: list[GateFinding] = []

        if not claims:
            findings.append(
                GateFinding(
                    code="analysis.no_claims",
                    message="no claims produced for this research state",
                    severity=GateSeverity.WARN,
                )
            )

        evidence_lookup = evidence_lookup or {}
        for claim in claims:
            refs = claim.supporting_evidence_refs + claim.opposing_evidence_refs
            # 1) evidence must exist
            missing = [r for r in refs if r not in evidence_lookup]
            if missing:
                findings.append(
                    GateFinding(
                        code="analysis.dangling_reference",
                        message=f"claim {claim.claim_id} cites missing evidence {missing}",
                        severity=GateSeverity.FAIL,
                    )
                )
            # 2) fact/prediction boundary
            lowered = claim.statement.lower()
            if claim.fact_status is FactStatus.CONFIRMED_FACT and any(
                marker in lowered for marker in self._PREDICTION_MARKERS
            ):
                findings.append(
                    GateFinding(
                        code="analysis.fact_prediction_mix",
                        message=f"claim {claim.claim_id} mixes prediction language into a fact",
                        severity=GateSeverity.FAIL,
                    )
                )
            # 3) conflicts should be explained (a note in metadata)
            if claim.opposing_evidence_refs and not claim.metadata.get("conflict_note"):
                findings.append(
                    GateFinding(
                        code="analysis.conflict_unexplained",
                        message=f"claim {claim.claim_id} cites opposing evidence without explanation",
                        severity=GateSeverity.WARN,
                    )
                )
            # 4) thin support
            if len(claim.supporting_evidence_refs) <= 1 and claim.confidence >= 0.8:
                findings.append(
                    GateFinding(
                        code="analysis.thin_support_high_confidence",
                        message=f"claim {claim.claim_id} confidence {claim.confidence} on thin support",
                        severity=GateSeverity.WARN,
                    )
                )
            # 5) R2 source-trust escalation（方案 §8.3）：confirmed_fact 的证据基
            #    必须 ≥1 条 T0/T1 或 ≥2 条独立 T2/T3；T4-only 一票 FAIL
            if claim.fact_status is FactStatus.CONFIRMED_FACT:
                supporting = [
                    evidence_lookup[r]
                    for r in claim.supporting_evidence_refs
                    if r in evidence_lookup
                ]
                authorities = [
                    trust_for_evidence(
                        getattr(e, "authority_level", None),
                        getattr(e, "evidence_type", None),
                    )
                    for e in supporting
                ]
                try:
                    check_fact_support(authorities)
                except TrustEscalationError:
                    findings.append(
                        GateFinding(
                            code="analysis.source_trust_escalation",
                            message=(
                                f"claim {claim.claim_id} is confirmed_fact but its "
                                f"evidence base {authorities} does not meet the "
                                f"source-trust bar (>=1 T0/T1 or >=2 independent T2/T3)"
                            ),
                            severity=GateSeverity.FAIL,
                        )
                    )

        status = GateStatus.FAIL if any(f.severity is GateSeverity.FAIL for f in findings) else (
            GateStatus.WARN if findings else GateStatus.PASS
        )
        return GateResult(gate=self.gate, status=status, findings=tuple(findings), evaluated_at=utc_now())


class ReportGateInput(BaseModel):
    """Structured report-draft contract the final gate audits (§38 preview).

    M11's real ResearchReport renders into this shape for publication gating.
    """

    model_config = ConfigDict(extra="forbid")

    known_evidence_ids: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    claim_support: dict[str, tuple[str, ...]] = {}  # claim_id -> cited evidence ids
    has_valuation: bool = False
    valuation_assumptions: tuple[str, ...] = ()
    risk_section: bool = False
    data_quality_section: bool = False
    disclaimer: bool = False
    # Real disclosure audit (added in remediation R0.6): every capability
    # detected missing must appear in the report's data-quality disclosure.
    missing_capabilities: tuple[str, ...] = ()
    disclosed_missing: tuple[str, ...] = ()


class FinalReportQualityGate:
    """Gate over a report draft; FAIL blocks publication (任务书 §31)."""

    gate = GateName.FINAL_REPORT

    def evaluate(self, report: ReportGateInput) -> GateResult:
        findings: list[GateFinding] = []

        known = set(report.known_evidence_ids)
        # 1) every citation must resolve to known evidence ids
        for citation in report.citations:
            if citation not in known:
                findings.append(
                    GateFinding(
                        code="report.invalid_citation",
                        message=f"citation {citation} does not resolve to evidence",
                        severity=GateSeverity.FAIL,
                    )
                )

        # 2) every claim referenced must be supported by at least one valid citation
        for claim_id, cited in report.claim_support.items():
            if not cited or not (set(cited) & known):
                findings.append(
                    GateFinding(
                        code="report.unsupported_claim",
                        message=f"claim {claim_id} not supported by cited evidence",
                        severity=GateSeverity.FAIL,
                    )
                )

        # 2b) missing-data disclosure must be complete (remediation R0.6 —
        # the previous `or True` bypass is replaced by a real business rule)
        undisclosed = sorted(set(report.missing_capabilities) - set(report.disclosed_missing))
        if undisclosed:
            findings.append(
                GateFinding(
                    code="report.missing_data_undisclosed",
                    message=f"missing capabilities not disclosed: {undisclosed}",
                    severity=GateSeverity.FAIL,
                )
            )

        # 3) valuation section must carry assumptions
        if report.has_valuation and not report.valuation_assumptions:
            findings.append(
                GateFinding(
                    code="report.valuation_without_assumptions",
                    message="valuation present without assumptions",
                    severity=GateSeverity.FAIL,
                )
            )

        # 4) risks and data-quality must be disclosed
        if not report.risk_section:
            findings.append(
                GateFinding(
                    code="report.risks_missing",
                    message="no risk section",
                    severity=GateSeverity.FAIL,
                )
            )
        if not report.data_quality_section:
            findings.append(
                GateFinding(
                    code="report.data_quality_missing",
                    message="data quality not disclosed",
                    severity=GateSeverity.WARN,
                )
            )

        # 5) disclaimer required
        if not report.disclaimer:
            findings.append(
                GateFinding(
                    code="report.disclaimer_missing",
                    message="disclaimer missing",
                    severity=GateSeverity.FAIL,
                )
            )

        status = GateStatus.FAIL if any(f.severity is GateSeverity.FAIL for f in findings) else (
            GateStatus.WARN if findings else GateStatus.PASS
        )
        return GateResult(gate=self.gate, status=status, findings=tuple(findings), evaluated_at=utc_now())
