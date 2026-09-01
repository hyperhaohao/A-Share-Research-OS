"""QuantBrief service: run the quant loop into the research state (R3.5).

    collect historical_data → run deterministic backtest → factors →
    QuantBrief (AnalystBrief, analyst_type=quant) → Research State

The brief cites the kline evidence it derived from; metrics are pure
engine output, never hand-authored.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.agents import (
    AnalystBrief,
    AnalystType,
    MissingData,
    ResearchRequest,
    ResearchRequestStatus,
)
from app.domain.evidence import EvidenceType
from app.domain.research import Claim, ClaimStatus, ClaimType, FactStatus
from app.quant.engine import factor_snapshot, run_backtest
from app.services.evidence_collector import collect_capability_evidence
from app.storage.agent_repo import AgentRepository
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


class QuantBriefService:
    def analyze(
        self,
        snapshot_id: str,
        *,
        session: Session,  # noqa: ANN001
        run_id: str | None = None,
        collect_missing: bool = False,
    ):
        snapshots = SnapshotRepository(session)
        snapshot = snapshots.get(snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)

        evidence_repo = EvidenceRepository(session)
        agents = AgentRepository(session)
        pinned = set(snapshot.evidence_ids)
        all_evidence = evidence_repo.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        kline = [
            e
            for e in all_evidence
            if e.evidence_id in pinned and e.evidence_type is EvidenceType.MARKET_QUOTE
            and (e.metadata or {}).get("bar_count") is not None
        ]

        if not kline:
            # try collecting; the collector stores a market_quote-typed record
            # with bar_count set by the kline provider
            if collect_missing:
                collect_capability_evidence(
                    snapshot.instrument_id, "historical_data", repo=evidence_repo
                )
                all_evidence = evidence_repo.list_for_instrument(
                    snapshot.instrument_id, visible_at=snapshot.as_of
                )
                pinned = set(snapshot.evidence_ids)
                kline = [
                    e for e in all_evidence
                    if e.evidence_id in pinned
                    and (e.metadata or {}).get("bar_count") is not None
                ]
            if not kline:
                missing = MissingData(
                    capability="historical_data",
                    reason="no historical bars in snapshot; quant loop skipped",
                    evidence_type="market_quote",
                )
                request = ResearchRequest(
                    instrument_id=snapshot.instrument_id,
                    capability=missing.capability,
                    reason=missing.reason,
                    requested_by="quant",
                    snapshot_id=snapshot.snapshot_id,
                    status=ResearchRequestStatus.OPEN,
                )
                agents.save_request(request)
                brief = AnalystBrief(
                    analyst_type=AnalystType.QUANT,
                    instrument_id=snapshot.instrument_id,
                    snapshot_id=snapshot.snapshot_id,
                    run_id=run_id,
                    missing_data=(missing,),
                    confidence=0.2,
                )
                agents.save_brief(brief)
                return brief, {}

            # kline evidence arrived after collection; rebuild not possible
            # (snapshot immutable) — the next run will pin it. Disclose.
            missing = MissingData(
                capability="historical_data",
                reason="kline evidence exists but is not pinned by this snapshot (PIT)",
                evidence_type="market_quote",
            )
            brief = AnalystBrief(
                analyst_type=AnalystType.QUANT,
                instrument_id=snapshot.instrument_id,
                snapshot_id=snapshot.snapshot_id,
                run_id=run_id,
                missing_data=(missing,),
                confidence=0.3,
            )
            agents.save_brief(brief)
            return brief, {}

        latest = max(kline, key=lambda e: e.available_time)
        bars_raw = latest.metadata.get("bars") or []
        from app.quant.engine import Bar

        bars = [
            Bar(
                date=b["date"], open=b["open"], close=b["close"],
                high=b["high"], low=b["low"], volume=b["volume"],
                turnover=b.get("turnover"),
            )
            for b in bars_raw
        ]
        metrics = run_backtest(bars)
        factors = factor_snapshot(bars)

        conclusions = [
            {
                "metric": "strategy_total_return_pct",
                "value": metrics["strategy_total_return_pct"],
                "text_zh": f"动量策略区间收益 {metrics['strategy_total_return_pct']}%",
                "text_en": f"Momentum strategy return {metrics['strategy_total_return_pct']}%",
                "evidence_id": latest.evidence_id,
            },
            {
                "metric": "sharpe",
                "value": metrics["sharpe"],
                "text_zh": f"年化 Sharpe {metrics['sharpe']}",
                "text_en": f"Annualized Sharpe {metrics['sharpe']}",
                "evidence_id": latest.evidence_id,
            },
            {
                "metric": "max_drawdown_pct",
                "value": metrics["max_drawdown_pct"],
                "text_zh": f"最大回撤 {metrics['max_drawdown_pct']}%",
                "text_en": f"Max drawdown {metrics['max_drawdown_pct']}%",
                "evidence_id": latest.evidence_id,
            },
            {
                "metric": "momentum_5d",
                "value": factors.get("momentum_5d"),
                "text_zh": f"5 日动量 {factors.get('momentum_5d')}",
                "text_en": f"5d momentum {factors.get('momentum_5d')}",
                "evidence_id": latest.evidence_id,
            },
        ]
        # F1.4: quant claims — analyst_inference (never confirmed_fact),
        # citing the kline evidence they were computed from
        research = ResearchRepository(session)
        claim_refs: list[str] = []
        quant_specs = [
            (
                f"过去 {metrics['n_days']} 个交易日 5 日动量策略回测收益 "
                f"{metrics['strategy_total_return_pct']}%（Sharpe {metrics['sharpe']}）",
                "quant_backtest",
            ),
            (
                f"5 日动量信号 {factors.get('momentum_5d')}",
                "quant_momentum",
            ),
            (
                f"20 日波动率 {factors.get('volatility_20d')}",
                "quant_volatility",
            ),
        ]
        for statement, tag in quant_specs:
            # F4（任务书 §7.1）：可解释置信度替代固定 0.65/0.5 ——
            # 样本充足性进 basis（n_days < 10 → directness=inference 降级）
            from app.domain.confidence import compute_claim_confidence
            from app.domain.source_trust import trust_for_evidence

            outcome = compute_claim_confidence(
                supporting_trusts=[
                    trust_for_evidence(latest.authority_level, latest.evidence_type).value
                ],
                directness="derived" if metrics["n_days"] >= 10 else "inference",
                semantic_consistency="passed",
            )
            claim = Claim(
                instrument_id=snapshot.instrument_id,
                snapshot_id=snapshot.snapshot_id,
                statement=statement,
                claim_type=ClaimType.INDUSTRY_TREND,  # quant signal ≈ trend claim
                supporting_evidence_refs=(latest.evidence_id,),
                fact_status=FactStatus.ANALYST_INFERENCE,
                confidence=outcome.value,
                confidence_level=outcome.level,
                confidence_basis={**outcome.basis, "sample_days": metrics["n_days"]},
                status=ClaimStatus.PROPOSED,
                metadata={"analyst": "quant", "signal_type": tag},
            )
            try:
                claim_refs.append(research.save_claim(claim))
            except Exception:
                existing = [
                    c for c in research.list_claims(
                        snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
                    ) if c.statement == statement
                ]
                if existing:
                    claim_refs.append(existing[0].claim_id)

        brief = AnalystBrief(
            analyst_type=AnalystType.QUANT,
            instrument_id=snapshot.instrument_id,
            snapshot_id=snapshot.snapshot_id,
            run_id=run_id,
            conclusions=tuple(conclusions),
            claim_refs=tuple(claim_refs),
            evidence_refs=(latest.evidence_id,),
            confidence=0.75,
            key_questions=("信号在更长窗口/同业上是否稳定？",),
            risks=("回测为历史模拟，不构成未来收益承诺",),
        )
        agents.save_brief(brief)
        return brief, {"metrics": metrics, "factors": factors}
