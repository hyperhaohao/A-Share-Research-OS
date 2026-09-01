"""Full analyst set over the R1 evidence capabilities (整改 R2.1).

Every analyst follows the same discipline as MarketAnalyst (M8):

    facts only from snapshot-pinned evidence;
    missing data disclosed → ResearchRequest → collector;
    claims created with mandatory evidence references;
    briefs persisted with structured, bilingual conclusions.

The per-analyst logic lives in ``extract()`` — a pure function over the
pinned evidence list returning (conclusions, claim specs, missing).
Claims are mechanical facts derived from evidence payloads; no invented
numbers anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.agents import (
    AnalystBrief,
    AnalystType,
    MissingData,
    ResearchRequest,
    ResearchRequestStatus,
)
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
from app.domain.research import Claim, ClaimStatus, ClaimType
from app.storage.agent_repo import AgentRepository
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository

def _ensure_utc(value):
    from datetime import timezone as _tz
    return value if (value is None or value.tzinfo is not None) else value.replace(tzinfo=_tz.utc)


@dataclass
class ClaimSpec:
    """A claim to create, derived mechanically from evidence payloads.

    F4（任务书 §7.1）：置信度不再由分析师硬编码 —— 落库时由
    ``compute_claim_confidence`` 按支撑证据信任层/独立性/直接性/新鲜度计算
    （directness 由 fact_status 推导），basis 随 Claim 落库可审计。
    """

    statement: str
    claim_type: ClaimType
    fact_status: FactStatus
    evidence_refs: tuple[str, ...]


@dataclass
class Extracted:
    conclusions: list[dict] = field(default_factory=list)
    claim_specs: list[ClaimSpec] = field(default_factory=list)
    missing: list[MissingData] = field(default_factory=list)
    confidence: float = 0.5
    key_questions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()


class AnalystRunError(Exception):
    pass


class BaseSnapshotAnalyst:
    """Template method: pin evidence → extract → claims + brief + requests."""

    analyst_type: AnalystType
    capability: str
    evidence_type: EvidenceType

    def analyze(
        self,
        snapshot_id: str,
        *,
        session,  # noqa: ANN001
        run_id: str | None = None,
        collect_missing: bool = True,
    ) -> "AnalystOutcome":
        snapshots = SnapshotRepository(session)
        snapshot = snapshots.get(snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)

        evidence_repo = EvidenceRepository(session)
        all_evidence = evidence_repo.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        pinned_ids = set(snapshot.evidence_ids)
        mine = [
            e
            for e in all_evidence
            if e.evidence_id in pinned_ids and e.evidence_type is self.evidence_type
        ]

        extracted = self.extract(mine, snapshot=snapshot, pinned_ids=pinned_ids)

        agents = AgentRepository(session)
        research = ResearchRepository(session)
        created_claims: list[str] = []
        for spec in extracted.claim_specs:
            # F4（任务书 §7.1）：可解释置信度 —— 由支撑证据的信任层/独立性/
            # 直接性/新鲜度计算，替代分析师硬编码（0.95/0.9/0.55 已废除）
            outcome = self._compute_confidence(session, spec)
            claim = Claim(
                instrument_id=snapshot.instrument_id,
                snapshot_id=snapshot.snapshot_id,
                statement=spec.statement,
                claim_type=spec.claim_type,
                supporting_evidence_refs=spec.evidence_refs,
                fact_status=spec.fact_status,
                confidence=outcome.value,
                confidence_level=outcome.level,
                confidence_basis=outcome.basis,
                status=ClaimStatus.PROPOSED,
                metadata={"analyst": self.analyst_type.value},
            )
            try:
                created_claims.append(research.save_claim(claim))
            except Exception:
                # duplicate (snapshot, statement): reuse the existing claim
                existing = [
                    c
                    for c in research.list_claims(
                        snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
                    )
                    if c.statement == spec.statement
                ]
                if existing:
                    created_claims.append(existing[0].claim_id)

        brief = AnalystBrief(
            analyst_type=self.analyst_type,
            instrument_id=snapshot.instrument_id,
            snapshot_id=snapshot.snapshot_id,
            run_id=run_id,
            conclusions=tuple(extracted.conclusions),
            claim_refs=tuple(created_claims),
            evidence_refs=tuple(e.evidence_id for e in mine),
            missing_data=tuple(extracted.missing),
            confidence=extracted.confidence,
            key_questions=extracted.key_questions,
            risks=extracted.risks,
        )
        agents.save_brief(brief)

        open_requests: list[str] = []
        for gap in extracted.missing:
            request = ResearchRequest(
                instrument_id=snapshot.instrument_id,
                capability=gap.capability,
                reason=gap.reason,
                requested_by=self.analyst_type.value,
                snapshot_id=snapshot.snapshot_id,
                status=ResearchRequestStatus.OPEN,
            )
            open_requests.append(agents.save_request(request))

        if collect_missing:
            from app.services.evidence_collector import collect_capability_evidence

            for gap in extracted.missing:
                collect_capability_evidence(
                    snapshot.instrument_id, gap.capability, repo=evidence_repo
                )

        return AnalystOutcome(
            brief=brief,
            created_claim_ids=tuple(created_claims),
            open_requests=tuple(open_requests),
        )


    # ── F4（任务书 §7.1）：可解释置信度 ──────────────────────────────────────
    _DIRECTNESS_BY_FACT_STATUS = {
        FactStatus.OFFICIAL_DISCLOSURE.value: "direct_quote",
        FactStatus.CONFIRMED_FACT.value: "direct_quote",
        FactStatus.REGULATORY_DOCUMENT.value: "direct_quote",
        FactStatus.MANAGEMENT_STATEMENT.value: "derived",
        FactStatus.MEDIA_REPORT.value: "derived",
        FactStatus.MARKET_EXPECTATION.value: "derived",
        FactStatus.ANALYST_INFERENCE.value: "inference",
        FactStatus.RUMOR.value: "inference",
    }

    def _compute_confidence(self, session, spec: ClaimSpec):
        """由支撑证据信任层/独立来源组/直接性/新鲜度计算置信度（非固定值）。"""
        from datetime import datetime, timezone

        from sqlalchemy import select as _select

        from app.domain.confidence import compute_claim_confidence
        from app.domain.source_trust import trust_for_evidence
        from app.services.source_independence import independent_group_count
        from app.storage.orm import EvidenceORM

        rows = session.scalars(
            _select(EvidenceORM).where(EvidenceORM.evidence_id.in_(spec.evidence_refs))
        ).all()
        if not rows:
            outcome = compute_claim_confidence(supporting_trusts=[])
        else:
            trusts = [trust_for_evidence(r.authority_level, r.evidence_type).value for r in rows]
            now = datetime.now(timezone.utc)
            ages = [
                max((now - _ensure_utc(r.available_time)).total_seconds() / 86400.0, 0.0)
                for r in rows
                if r.available_time is not None
            ]
            outcome = compute_claim_confidence(
                supporting_trusts=trusts,
                corroboration_groups=independent_group_count(rows),
                directness=self._DIRECTNESS_BY_FACT_STATUS.get(
                    spec.fact_status.value if hasattr(spec.fact_status, "value") else str(spec.fact_status),
                    "derived",
                ),
                evidence_age_days=min(ages) if ages else None,
            )
        return outcome

    def extract(self, evidence: list[EvidenceRecord], *, snapshot, pinned_ids: set) -> Extracted:
        raise NotImplementedError


@dataclass
class AnalystOutcome:
    brief: AnalystBrief
    created_claim_ids: tuple[str, ...]
    open_requests: tuple[str, ...] = ()


def _latest(evidence: list[EvidenceRecord]) -> EvidenceRecord | None:
    return max(evidence, key=lambda e: e.available_time) if evidence else None


class FinancialAnalyst(BaseSnapshotAnalyst):
    """财务分析师 — 机械事实：最新报告期关键指标（含同比）。"""

    analyst_type = AnalystType.FUNDAMENTAL
    capability = "financials"
    evidence_type = EvidenceType.FINANCIAL_REPORT

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="financials",
                    reason="no financial statements in snapshot",
                    evidence_type="financial_report",
                )
            )
            out.confidence = 0.2
            return out

        latest = _latest(evidence)
        payload = latest.metadata
        report_date = payload.get("report_date")
        refs: tuple[str, ...] = (latest.evidence_id,)

        metrics = [
            ("eps", "EPS", "元", float),
            ("bvps", "每股净资产", "元", float),
            ("roe_pct", "ROE", "%", float),
            ("gross_margin_pct", "毛利率", "%", float),
            ("revenue_yoy_pct", "营收同比", "%", float),
            ("net_profit_yoy_pct", "归母净利同比", "%", float),
        ]
        conclusions: list[dict] = []
        for key, label, unit, _cast in metrics:
            value = payload.get(key)
            if value is None:
                continue
            conclusions.append(
                {
                    "metric": key,
                    "value": value,
                    "text_zh": f"{report_date} {label} {value}{unit}",
                    "text_en": f"{report_date} {label}: {value}{unit}",
                    "evidence_id": latest.evidence_id,
                }
            )
        out.conclusions = conclusions

        revenue = payload.get("revenue_yuan")
        profit = payload.get("net_profit_yuan")
        if report_date:
            out.claim_specs.append(
                ClaimSpec(
                    statement=(
                        f"公司 {report_date} 报告期披露：营业收入 {revenue and round(revenue / 1e8, 2)} 亿元，"
                        f"归母净利润 {profit and round(profit / 1e8, 2)} 亿元"
                    ),
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                    evidence_refs=refs,
                )
            )
        rev_yoy = payload.get("revenue_yoy_pct")
        if rev_yoy is not None:
            out.claim_specs.append(
                ClaimSpec(
                    statement=f"公司 {report_date} 报告期营业收入同比增长 {rev_yoy}%",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                    evidence_refs=refs,
                )
            )
        out.confidence = 0.85
        out.key_questions = ("盈利增长的可持续性如何？", "资产负债结构是否支持扩张？")
        return out


class EventAnalyst(BaseSnapshotAnalyst):
    """公告/公司事件分析师 — 机械事实：近期公告清单。"""

    analyst_type = AnalystType.NEWS  # reuses the news slot in the enum for events
    capability = "announcements"
    evidence_type = EvidenceType.ANNOUNCEMENT

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="announcements",
                    reason="no announcements in snapshot",
                    evidence_type="announcement",
                )
            )
            out.confidence = 0.3
            return out

        for ev in sorted(evidence, key=lambda e: e.available_time, reverse=True)[:5]:
            title = (ev.metadata or {}).get("title") or ev.title
            out.conclusions.append(
                {
                    "metric": "announcement",
                    "value": title,
                    "text_zh": f"{ev.available_time:%Y-%m-%d} 公告：《{title}》",
                    "text_en": f"{ev.available_time:%Y-%m-%d} announcement: {title}",
                    "evidence_id": ev.evidence_id,
                }
            )
            out.claim_specs.append(
                ClaimSpec(
                    statement=f"公司于 {ev.available_time:%Y-%m-%d} 发布公告《{title}》",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                    evidence_refs=(ev.evidence_id,),
                )
            )
        out.confidence = 0.85
        out.key_questions = ("公告事项对基本面与估值的影响方向？",)
        return out


class NewsAnalyst(BaseSnapshotAnalyst):
    """新闻分析师 — media_report 级别（不得高于公告权威度）。"""

    analyst_type = AnalystType.NEWS
    capability = "news"
    evidence_type = EvidenceType.NEWS

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="news",
                    reason="no news in snapshot",
                    evidence_type="news",
                )
            )
            out.confidence = 0.3
            return out

        for ev in sorted(evidence, key=lambda e: e.available_time, reverse=True)[:5]:
            title = (ev.metadata or {}).get("title") or ev.title
            out.conclusions.append(
                {
                    "metric": "news",
                    "value": title,
                    "text_zh": f"媒体报道：《{title}》",
                    "text_en": f"Media report: {title}",
                    "text_language": None,
                    "evidence_id": ev.evidence_id,
                }
            )
        # one aggregated media-report claim citing all listed news
        if out.conclusions:
            refs = tuple(c["evidence_id"] for c in out.conclusions)
            out.claim_specs.append(
                ClaimSpec(
                    statement=(
                        f"近期存在 {len(refs)} 条与公司相关的媒体报道（明细见引用），"
                        "内容以媒体报道口径为准"
                    ),
                    claim_type=ClaimType.INDUSTRY_TREND,
                    fact_status=FactStatus.MEDIA_REPORT,
                    evidence_refs=refs,
                )
            )
        out.confidence = 0.55
        out.risks = ("媒体报道可能与事实存在偏差",)
        return out


class IndustryAnalyst(BaseSnapshotAnalyst):
    """行业分析师 — 行业链与主营业务事实。"""

    analyst_type = AnalystType.FUNDAMENTAL
    capability = "industry"
    evidence_type = EvidenceType.INDUSTRY_DATA

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="industry",
                    reason="no industry classification in snapshot",
                    evidence_type="industry_data",
                )
            )
            out.confidence = 0.3
            return out

        payload = _latest(evidence).metadata
        chain = payload.get("industry_chain") or []
        main_business = payload.get("main_business")
        if chain:
            label = " - ".join(chain)
            out.conclusions.append(
                {
                    "metric": "industry_chain",
                    "value": chain,
                    "text_zh": f"行业分类：{label}",
                    "text_en": f"Industry chain: {label}",
                    "evidence_id": _latest(evidence).evidence_id,
                }
            )
            out.claim_specs.append(
                ClaimSpec(
                    statement=f"公司行业分类为：{label}",
                    claim_type=ClaimType.COMPETITIVE_POSITION,
                    fact_status=FactStatus.CONFIRMED_FACT,
                    evidence_refs=(_latest(evidence).evidence_id,),
                )
            )
        if main_business:
            out.claim_specs.append(
                ClaimSpec(
                    statement=f"公司主营业务：{str(main_business)[:200]}",
                    claim_type=ClaimType.COMPETITIVE_POSITION,
                    fact_status=FactStatus.CONFIRMED_FACT,
                    evidence_refs=(_latest(evidence).evidence_id,),
                )
            )
        out.confidence = 0.8
        out.key_questions = ("同业竞争格局与公司在链中的位置？", "上下游价格传导如何影响毛利？")
        return out


class CapitalFlowAnalyst(BaseSnapshotAnalyst):
    """资金面分析师 — 量/额/换手事实；缺失项显式披露。"""

    analyst_type = AnalystType.CAPITAL_FLOW
    capability = "capital_flow"
    evidence_type = EvidenceType.CAPITAL_FLOW

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="capital_flow",
                    reason="no capital flow data in snapshot",
                    evidence_type="capital_flow",
                )
            )
            out.confidence = 0.3
            return out

        payload = _latest(evidence).metadata
        turnover = payload.get("turnover_rate")
        amount = payload.get("amount_yuan")
        refs = (_latest(evidence).evidence_id,)
        if turnover is not None:
            out.conclusions.append(
                {
                    "metric": "turnover_rate",
                    "value": turnover,
                    "text_zh": f"换手率 {turnover}%",
                    "text_en": f"Turnover rate {turnover}%",
                    "evidence_id": refs[0],
                }
            )
        if amount is not None:
            out.conclusions.append(
                {
                    "metric": "amount_yuan",
                    "value": amount,
                    "text_zh": f"成交额约 {round(amount / 1e8, 2)} 亿元",
                    "text_en": f"Turnover ≈ ¥{round(amount / 1e8, 2)}e8",
                    "evidence_id": refs[0],
                }
            )
        out.claim_specs.append(
            ClaimSpec(
                statement=f"最新换手率 {turnover}%，成交额 {amount and round(amount / 1e8, 2)} 亿元",
                claim_type=ClaimType.FUNDAMENTAL_FACT,
                fact_status=FactStatus.CONFIRMED_FACT,
                evidence_refs=refs,
            )
        )
        if payload.get("main_capital_flow_status") == "unavailable_from_source":
            out.risks = ("主力资金数据当前来源不可用，资金面判断存在盲区",)
        out.confidence = 0.7
        return out


class MacroPolicyAnalyst(BaseSnapshotAnalyst):
    """宏观/政策分析师 — 按行业关键词检索政策报道。"""

    analyst_type = AnalystType.NEWS
    capability = "macro_policy"
    evidence_type = EvidenceType.MACRO_INDICATOR

    def extract(self, evidence, *, snapshot, pinned_ids) -> Extracted:
        out = Extracted()
        if not evidence:
            out.missing.append(
                MissingData(
                    capability="macro_policy",
                    reason="no policy news in snapshot",
                    evidence_type="macro_indicator",
                )
            )
            out.confidence = 0.3
            return out

        for ev in sorted(evidence, key=lambda e: e.available_time, reverse=True)[:4]:
            payload = ev.metadata or {}
            title = payload.get("title") or ev.title
            bodies = payload.get("official_bodies") or []
            note = f"（涉及：{'、'.join(bodies)}）" if bodies else ""
            out.conclusions.append(
                {
                    "metric": "policy_news",
                    "value": title,
                    "text_zh": f"政策报道：《{title}》{note}",
                    "text_en": f"Policy report: {title}{note}",
                    "text_language": None,
                    "evidence_id": ev.evidence_id,
                }
            )
        if out.conclusions:
            refs = tuple(c["evidence_id"] for c in out.conclusions)
            out.claim_specs.append(
                ClaimSpec(
                    statement=f"近期存在 {len(refs)} 条相关宏观/政策报道（明细见引用）",
                    claim_type=ClaimType.INDUSTRY_TREND,
                    fact_status=FactStatus.MEDIA_REPORT,
                    evidence_refs=refs,
                )
            )
        out.confidence = 0.55
        return out


# Orchestrator order: industry first (feeds macro keyword), then fundamentals.
ORCHESTRATION: list[BaseSnapshotAnalyst] = [
    IndustryAnalyst(),
    FinancialAnalyst(),
    EventAnalyst(),
    NewsAnalyst(),
    CapitalFlowAnalyst(),
]


def evidence_payload(evidence: EvidenceRecord) -> dict[str, Any]:
    return evidence.metadata or {}
