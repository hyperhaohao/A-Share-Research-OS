"""Report compiler service: research state → structured report → artifacts.

Compile is read-only over the research state (snapshot, evidence, claims,
theses, debates, scenarios, valuations) plus the quality gate. Publication
requires FinalReportQualityGate not to FAIL (任务书 §31).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.quality import FinalReportQualityGate, GateStatus, ReportGateInput
from app.domain.report import ReportRenderer, StructuredReport
from app.domain.evidence import EvidenceType
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.storage.valuation_repo import ValuationRepository
from app.services.debate_engine import DebateScenarioRepository


class ReportCompiler:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._snapshots = SnapshotRepository(session)
        self._evidence = EvidenceRepository(session)
        self._research = ResearchRepository(session)
        self._valuations = ValuationRepository(session)
        self._debates = DebateScenarioRepository(session)

    def compile(
        self,
        snapshot_id: str,
        *,
        language: str = "zh-CN",
    ) -> dict:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)

        pinned = set(snapshot.evidence_ids)
        all_evidence = self._evidence.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        evidence = {e.evidence_id: e for e in all_evidence if e.evidence_id in pinned}
        claims = self._research.list_claims(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )
        theses = self._research.list_theses(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )
        valuations = self._valuations.list_for(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )

        report = StructuredReport(
            instrument_id=snapshot.instrument_id,
            snapshot_id=snapshot.snapshot_id,
            as_of=snapshot.as_of,
            generated_at=datetime.now(timezone.utc),
        )

        # -- market & capital (quotes) -------------------------------------
        market = report.section("market_and_capital")
        for ev in evidence.values():
            if ev.evidence_type is not EvidenceType.MARKET_QUOTE:
                continue
            payload = ev.metadata
            market.items.append(
                {
                    "text_zh": (
                        f"最新价格 {payload.get('price')}（{payload.get('change_pct')}%）"
                    ),
                    "text_en": (
                        f"Latest price {payload.get('price')} ({payload.get('change_pct')}%)"
                    ),
                    "text_language": None,  # generated symmetric text
                    "evidence_ids": [ev.evidence_id],
                    "numbers": {"price": payload.get("price"), "change_pct": payload.get("change_pct")},
                }
            )
            report.citations.append(ev.evidence_id)

        # -- key theses -----------------------------------------------------
        theses_section = report.section("key_theses")
        for thesis in theses:
            # aggregate the thesis's own claims' evidence for citation + gating
            thesis_evidence: list[str] = []
            for cid in tuple(thesis.supporting_claims) + tuple(thesis.opposing_claims):
                c = self._research.get_claim(cid)
                if c is not None:
                    thesis_evidence.extend(c.supporting_evidence_refs)
                    thesis_evidence.extend(c.opposing_evidence_refs)
            theses_section.items.append(
                {
                    "text_zh": f"{thesis.title}：{thesis.description}",
                    "text_en": None,  # en filled by narrative layer (or fallback marker)
                    "text_language": "zh-CN",
                    "evidence_ids": list(dict.fromkeys(thesis_evidence)),
                    "claim_ids": list(thesis.supporting_claims),
                }
            )
            report.citations.extend(dict.fromkeys(thesis_evidence))
        # claims → citations
        claims_section_items: list[dict] = []
        for claim in claims:
            claims_section_items.append(
                {
                    "text_zh": claim.statement,
                    "text_en": None,
                    "text_language": "zh-CN",
                    "evidence_ids": list(claim.supporting_evidence_refs),
                }
            )
            report.citations.extend(claim.supporting_evidence_refs)
            report.citations.extend(claim.opposing_evidence_refs)
        if claims_section_items:
            market_exec = report.section("executive_summary")
            market_exec.items = claims_section_items

        # -- valuation -------------------------------------------------------
        valuation_section = report.section("valuation")
        for v in valuations:
            if not v["computable"]:
                valuation_section.items.append(
                    {
                        "text_zh": f"{v['method']}：不可计算（{', '.join(m['name'] for m in v['missing'])} 缺失）",
                        "text_en": f"{v['method']}: not computable (missing {', '.join(m['name'] for m in v['missing'])})",
                        "text_language": None,
                        "evidence_ids": [],
                        "numbers": {"value": None},
                    }
                )
                continue
            detail = v["detail"]
            upside = detail.get("upside_pct")
            valuation_section.items.append(
                {
                    "text_zh": f"{v['method']}：隐含价格 {v['value']}，空间 {upside}%",
                    "text_en": f"{v['method']}: implied price {v['value']}, upside {upside}%",
                    "text_language": None,
                    "evidence_ids": [],
                    "numbers": {"value": v["value"], "upside_pct": upside},
                }
            )
            # real assumption provenance: the actual inputs used by the engine
            report.valuation_summaries.append(
                {
                    "method": v["method"],
                    "inputs": sorted((v.get("inputs") or {}).keys()),
                    "value": v["value"],
                }
            )

        # -- scenarios / debates ---------------------------------------------
        for thesis in theses:
            scenarios = self._debates.list_scenarios(thesis.thesis_id)
            if scenarios:
                scenario_section = report.section("scenarios")
                for s in scenarios:
                    total = {"text_zh": f"{s.kind.value}: {s.probability}%", "text_en": f"{s.kind.value}: {s.probability}%"}
                    total.update({"text_language": None, "evidence_ids": [], "probability": s.probability})
                    scenario_section.items.append(total)
            debates = self._debates.list_debate_rounds(thesis.thesis_id)
            if debates:
                bull_bear = report.section("bull_bear")
                for d in debates:
                    bull = self._research.get_claim(d.bull_claim_id)
                    bear = self._research.get_claim(d.bear_claim_id)
                    if bull is not None:
                        bull_bear.items.append(
                            {"text_zh": bull.statement, "text_en": None,
                             "text_language": "zh-CN", "evidence_ids": list(bull.supporting_evidence_refs)}
                        )
                    if bear is not None:
                        bull_bear.items.append(
                            {"text_zh": bear.statement, "text_en": None,
                             "text_language": "zh-CN", "evidence_ids": list(bear.supporting_evidence_refs)}
                        )

        # -- risks from theses -------------------------------------------------
        risks_section = report.section("risks")
        for thesis in theses:
            for risk in thesis.risks:
                risks_section.items.append(
                    {"text_zh": risk, "text_en": None, "text_language": "zh-CN", "evidence_ids": []}
                )
            for invalidate in thesis.invalidate_conditions:
                risks_section.items.append(
                    {"text_zh": f"失效条件：{invalidate}", "text_en": f"Invalidate: {invalidate}",
                     "text_language": None, "evidence_ids": []}
                )

        # -- data quality --------------------------------------------------------
        quality = report.section("data_quality")
        missing_capabilities = self._missing_capabilities(evidence, pinned)
        report.missing_capabilities = list(missing_capabilities)
        for gap in missing_capabilities:
            report.data_quality_notes.append(gap)
            quality.items.append(
                {
                    "text_zh": f"缺失：{gap}",
                    "text_en": f"Missing: {gap}",
                    "text_language": None,
                    "evidence_ids": [],
                }
            )

        # -- source manifest -------------------------------------------------------
        manifest_section = report.section("source_manifest")
        seen_sources = {e.source for e in evidence.values()}
        for source in sorted(seen_sources):
            manifest_section.items.append(
                {"text_zh": source, "text_en": source, "text_language": None, "evidence_ids": []}
            )

        # -- disclaimer ---------------------------------------------------------
        disclaimer = report.section("disclaimer")
        disclaimer.items.append(
            {
                "text_zh": None,
                "text_en": None,
                "text_language": None,
                "evidence_ids": [],
                "is_disclaimer": True,
            }
        )

        return report

    def render_and_gate(
        self,
        report: StructuredReport,
        *,
        language: str = "zh-CN",
    ) -> dict:
        """Render artifacts and run the publication gate; FAIL blocks publish."""
        renderer = ReportRenderer(language)
        markdown = renderer.render_markdown(report)
        html = renderer.render_html(report)

        computable_valuations = [
            v for v in report.valuation_summaries if v.get("value") is not None
        ]
        # F0.3: the citation universe is the SNAPSHOT's pinned evidence —
        # not the report's own citations (which made the check self-referential
        # and unable to catch out-of-snapshot citations).
        pinned_universe = self._snapshot_evidence_ids(report.snapshot_id)
        gate_input = ReportGateInput(
            known_evidence_ids=tuple(pinned_universe),
            citations=tuple(set(report.citations)),
            claim_support=self._claim_support(report),
            has_valuation=bool(computable_valuations),
            # real assumptions = the actual engine input names per computable method
            valuation_assumptions=tuple(
                f"{v['method']}: inputs={','.join(v['inputs'])}"
                for v in computable_valuations
            ),
            risk_section=bool(report.sections.get("risks") and report.sections["risks"].items),
            data_quality_section=bool(
                report.sections.get("data_quality") and report.sections["data_quality"].items
            ),
            disclaimer=True,
            missing_capabilities=tuple(report.missing_capabilities),
            disclosed_missing=tuple(report.data_quality_notes),
        )
        gate = FinalReportQualityGate().evaluate(gate_input)
        report.gate_status = gate.status.value

        return {
            "language": language,
            "markdown": markdown,
            "html": html,
            "gate": {
                "status": gate.status.value,
                "blocked": gate.blocked,
                "findings": [f.model_dump(mode="json") for f in gate.findings],
            },
        }

    def _snapshot_evidence_ids(self, snapshot_id: str) -> set[str]:
        snapshot = self._snapshots.get(snapshot_id)
        return set(snapshot.evidence_ids) if snapshot else set()

    def _claim_support(self, report: StructuredReport) -> dict[str, tuple[str, ...]]:
        support: dict[str, tuple[str, ...]] = {}
        for section in report.sections.values():
            for item in section.items:
                claim_ids = item.get("claim_ids") or []
                evidence = tuple(item.get("evidence_ids") or ())
                for claim_id in claim_ids:
                    support.setdefault(claim_id, evidence)
        return support

    def _missing_capabilities(self, evidence: dict, pinned: set[str]) -> list[str]:
        pinned_types = {
            e.evidence_type for eid, e in evidence.items() if eid in pinned
        }
        missing = []
        if EvidenceType.MARKET_QUOTE not in pinned_types:
            missing.append("market_data")
        if EvidenceType.FINANCIAL_REPORT not in pinned_types:
            missing.append("financials")
        if EvidenceType.ANNOUNCEMENT not in pinned_types:
            missing.append("announcements")
        return missing
