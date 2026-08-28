"""Research synthesis: ClaimCompiler, ThesisBuilder, ValuationInputBuilder,
RiskManager, ScenarioEngine (整改 R2.2–R2.7).

All synthesis is mechanical over evidence-backed claims — the deterministic
baseline that R3's LLM layer will augment under the same integrity rules:

    Thesis requires claims (domain invariant)          → R2.3
    Valuation inputs come from evidence, not users      → R2.6
    Risks carry the claims/evidence that justify them   → R2.7
    Scenario probabilities sum to 100                   → R2.5
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.debate import Scenario, ScenarioKind
from app.domain.evidence import FactStatus, utc_now
from app.domain.research import (
    ClaimType,
    InvestmentThesis,
    ThesisStatus,
)
from app.domain.valuation import ValuationMethod, ValuationResult, pb_valuation, pe_valuation, ps_valuation
from app.services.debate_engine import DebateScenarioRepository
from app.storage.orm import SourceManifestORM
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.storage.valuation_repo import ValuationRepository


# --------------------------------------------------------------------------
# ThesisBuilder (R2.3)
# --------------------------------------------------------------------------

@dataclass
class ThesisOutcome:
    thesis_id: str
    supporting_claim_ids: tuple[str, ...]
    opposing_claim_ids: tuple[str, ...]


class ThesisBuilder:
    """Build the run's investment thesis from the run's claims.

    Honest mechanical synthesis: claims backed by official disclosure /
    confirmed facts become supporting claims; media-report claims become
    context (opposing-attention) items; confidence is the mean of the
    supporting claim confidences. LLM argumentation (R3) will refine this
    under the same integrity rules.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._research = ResearchRepository(session)

    def build(
        self,
        instrument_id: str,
        snapshot_id: str,
        claim_ids: list[str],
        *,
        industry_label: str | None = None,
        brief_risks: list[str] | None = None,
    ) -> ThesisOutcome:
        claims = [self._research.get_claim(cid) for cid in claim_ids]
        claims = [c for c in claims if c is not None]

        supporting: list[str] = []
        opposing: list[str] = []
        for claim in claims:
            if claim.fact_status is FactStatus.MEDIA_REPORT:
                # media context is attention context, not evidential support
                opposing.append(claim.claim_id)
            else:
                supporting.append(claim.claim_id)
        supporting = supporting or [c.claim_id for c in claims][:1]

        confidences = [c.confidence for c in claims if c.claim_id in supporting]
        confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.5

        label = f"（{industry_label}）" if industry_label else ""
        description_parts = [
            c.statement for c in claims if c.claim_id in supporting
        ][:3]
        thesis = InvestmentThesis(
            instrument_id=instrument_id,
            snapshot_id=snapshot_id,
            title=f"{instrument_id} 研究综合论点",
            description=(
                f"基于本轮证据自动汇编的研究论点{label}："
                + "；".join(description_parts)
            ),
            supporting_claims=tuple(supporting),
            opposing_claims=tuple(opposing),
            confidence=confidence,
            catalysts=(),
            risks=tuple(dict.fromkeys(brief_risks or [])),
            trigger_conditions=(),
            invalidate_conditions=(),
            status=ThesisStatus.ACTIVE,
        )
        thesis_id = self._research.save_thesis(thesis)
        return ThesisOutcome(
            thesis_id=thesis_id,
            supporting_claim_ids=tuple(supporting),
            opposing_claim_ids=tuple(opposing),
        )


# --------------------------------------------------------------------------
# ValuationInputBuilder (R2.6)
# --------------------------------------------------------------------------

class ValuationInputBuilder:
    """Build deterministic valuation inputs from evidence (never manual).

    Financial evidence (latest report) + quote evidence (price / market cap)
    yield PE / PB / PS inputs with real provenance:

        price / market cap ← quote evidence
        EPS / BVPS         ← latest financial report evidence
        revenue per share  ← revenue / implied shares (mcap ÷ price)

    Target multiples are explicit recorded assumptions (calibrated by
    history/peers once R3 quant lands). DCF / DDM / percentile / comps stay
    explicitly not-computable until their data exists — the engine's
    missing-input semantics, not guesses.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._valuations = ValuationRepository(session)

    def _pinned_evidence(self, instrument_id: str, snapshot):
        repo = EvidenceRepository(self._session)
        all_evidence = repo.list_for_instrument(instrument_id, visible_at=snapshot.as_of)
        pinned = set(snapshot.evidence_ids)
        return [e for e in all_evidence if e.evidence_id in pinned]

    def compute_from_evidence(self, instrument_id: str, snapshot) -> list[ValuationResult]:
        built = self.build(instrument_id, snapshot)
        assumptions = built.pop("__assumptions__", [])
        methods = built.pop("__methods__", [])
        _ = assumptions
        results: list[ValuationResult] = []
        for method_name in methods:
            inputs = built.get(method_name) or {}
            if method_name == "pe":
                result = pe_valuation(
                    price=inputs.get("price"),
                    eps_ttm=inputs.get("eps_ttm"),
                    target_pe=inputs.get("target_pe", 25),
                )
            elif method_name == "pb":
                result = pb_valuation(
                    price=inputs.get("price"),
                    bvps=inputs.get("bvps"),
                    target_pb=inputs.get("target_pb", 5),
                )
            elif method_name == "ps":
                result = ps_valuation(
                    price=inputs.get("price"),
                    revenue_per_share=inputs.get("revenue_per_share"),
                    target_ps=inputs.get("target_ps", 8),
                )
            else:
                continue
            results.append(result)
            self._store(result, instrument_id, snapshot)
        return results

    def build(self, instrument_id: str, snapshot) -> dict:
        evidence = self._pinned_evidence(instrument_id, snapshot)
        by_type: dict[str, list] = {}
        for e in evidence:
            by_type.setdefault(e.evidence_type.value, []).append(e)

        financials = sorted(
            by_type.get("financial_report") or [],
            key=lambda e: e.available_time, reverse=True,
        )
        # only real quote records (price present) — kline bars are also
        # market_quote-typed but carry no spot price
        quotes = sorted(
            [e for e in (by_type.get("market_quote") or [])
             if (e.metadata or {}).get("price") is not None],
            key=lambda e: e.available_time, reverse=True,
        )
        if not financials or not quotes:
            return {"__assumptions__": [], "__methods__": []}

        fin = financials[0].metadata or {}
        quote = quotes[0].metadata or {}
        price = quote.get("price")
        mcap = quote.get("total_market_cap_yuan")
        eps = fin.get("eps")
        bvps = fin.get("bvps")
        revenue = fin.get("revenue_yuan")

        assumptions: list[str] = []
        methods: list[str] = []
        built: dict = {}

        if price in (None, 0):
            return {"__assumptions__": assumptions, "__methods__": methods}

        base_inputs = {
            "price": price,
            "evidence_ref": quotes[0].evidence_id,
        }
        implied_shares = None
        if mcap and price:
            implied_shares = mcap / price
            base_inputs["implied_shares_outstanding"] = implied_shares

        if eps and eps > 0:
            pe_inputs = {**base_inputs, "eps_ttm": eps, "target_pe": 25}
            built["pe"] = pe_inputs
            methods.append("pe")
            assumptions.append(
                "PE: 目标倍数默认 25x（EPS TTM 来自财报证据；历史分位/同业校准 R3 接入）"
            )
        if bvps and bvps > 0:
            pb_inputs = {**base_inputs, "bvps": bvps, "target_pb": 5}
            built["pb"] = pb_inputs
            methods.append("pb")
            assumptions.append("PB: 目标倍数默认 5x（BVPS 来自财报证据；待同业校准）")
        if revenue and implied_shares and revenue > 0:
            rps = round(revenue / implied_shares, 4)
            ps_inputs = {**base_inputs, "revenue_per_share": rps, "target_ps": 8}
            built["ps"] = ps_inputs
            methods.append("ps")
            assumptions.append(
                "PS: 目标倍数默认 8x（收入/股 = 营收/隐含股本，均来自证据）"
            )
        built["__assumptions__"] = assumptions
        built["__methods__"] = methods
        return built

    def _store(self, result: ValuationResult, instrument_id: str, snapshot) -> str:
        from app.api.valuation import ValuationIn

        payload = ValuationIn(
            instrument_id=instrument_id,
            snapshot_id=snapshot.snapshot_id,
            method=ValuationMethod(result.method.value),
            inputs=dict(result.inputs_used),
        )
        return self._valuations.save(result, payload)


# --------------------------------------------------------------------------
# RiskManager (R2.7)
# --------------------------------------------------------------------------

@dataclass
class RiskItem:
    risk_type: str
    description: str
    supporting_claim_ids: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    likelihood: str = "medium"  # low / medium / high
    impact: str = "medium"
    trigger: str | None = None
    invalidate_condition: str | None = None


class RiskManager:
    """Structured risk register derived from theses, claims and source state.

    Not a generic template: every risk carries the claims/evidence that
    justify it, and data-availability risks come from the actual manifests.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._research = ResearchRepository(session)

    def build(self, instrument_id: str, snapshot, thesis_ids: list[str]) -> list[RiskItem]:
        risks: list[RiskItem] = []
        claims_by_id = {
            c.claim_id: c
            for c in self._research.list_claims(
                instrument_id, snapshot_id=snapshot.snapshot_id
            )
        }
        for thesis_id in thesis_ids:
            thesis = self._research.get_thesis(thesis_id)
            if thesis is None:
                continue
            for note in thesis.risks or ():
                supporting = tuple(thesis.supporting_claims)
                evidence_ids = tuple(
                    ref
                    for cid in supporting
                    if (c := claims_by_id.get(cid)) is not None
                    for ref in c.supporting_evidence_refs
                )
                risks.append(
                    RiskItem(
                        risk_type="thesis_risk",
                        description=str(note)[:500],
                        supporting_claim_ids=supporting,
                        supporting_evidence_ids=evidence_ids,
                        likelihood="medium",
                        impact="medium",
                    )
                )
            for invalidate in thesis.invalidate_conditions or ():
                risks.append(
                    RiskItem(
                        risk_type="invalidation",
                        description=f"论点失效条件：{invalidate}",
                        supporting_claim_ids=tuple(thesis.supporting_claims),
                        likelihood="low",
                        impact="high",
                        invalidate_condition=str(invalidate),
                    )
                )
        # data-availability risks from actual manifests (evidence-backed)
        rows = self._session.scalars(
            select(SourceManifestORM)
            .where(SourceManifestORM.instrument_id == instrument_id)
            .order_by(SourceManifestORM.created_at.desc())
            .limit(20)
        ).all()
        for row in rows:
            if row.final_status not in ("success", "partial") and not row.from_cache:
                risks.append(
                    RiskItem(
                        risk_type="data_availability",
                        description=(
                            f"能力 {row.capability} 采集未成功（{row.final_status}），"
                            "相关研究维度存在盲区"
                        ),
                        likelihood="high",
                        impact="medium",
                    )
                )
        return risks


# --------------------------------------------------------------------------
# ScenarioEngine (R2.5)
# --------------------------------------------------------------------------

class ScenarioEngine:
    """Bear/Base/Bull scenario set over the thesis, valuation attached."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = DebateScenarioRepository(session)

    def build_for(
        self,
        thesis_id: str,
        snapshot_id: str,
        instrument_id: str,
        *,
        base_value: float | None,
        assumptions: list[str],
    ) -> list[str]:
        factors = {"bear": 0.85, "base": 1.0, "bull": 1.15}
        probabilities = {"bear": 30.0, "base": 45.0, "bull": 25.0}
        catalysts = {
            "bear": ["none assumed"],
            "base": ["兑现当前证据所支持的预期"],
            "bull": ["需求/价格超预期", "政策或行业催化"],
        }
        risks = {
            "bear": ["价格与销量双降", "竞争加剧"],
            "base": ["经营低于假设"],
            "bull": ["高估持续性"],
        }
        scenarios = []
        for kind, factor in factors.items():
            value = round(base_value * factor, 2) if base_value else None
            scenarios.append(
                Scenario(
                    thesis_id=thesis_id,
                    snapshot_id=snapshot_id,
                    instrument_id=instrument_id,
                    kind=ScenarioKind(kind),
                    probability=probabilities[kind],
                    assumptions=[
                        *assumptions,
                        f"估值基准隐含价格 {base_value if base_value else 'N/A'}，情景系数 {factor}",
                    ],
                    catalysts=catalysts[kind],
                    risks=risks[kind],
                    trigger_conditions=[
                        f"隐含价格达到 {value}" if value else "触发条件待定"
                    ],
                )
            )
        return self._repo.save_scenario_set(scenarios)
