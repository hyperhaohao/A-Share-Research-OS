"""Deterministic market analyst (M8).

Facts come only from the snapshot's evidence. Anything the analyst needs but
the snapshot does not contain becomes ``missing_data`` → a persisted
``ResearchRequest`` → the collector runs for that capability. The current
run still discloses the gap (PIT: data collected now belongs to the next
run's as_of).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.agents import (
    AnalystBrief,
    AnalystType,
    MissingData,
    ResearchRequest,
    ResearchRequestStatus,
)
from app.domain.evidence import EvidenceType
from app.domain.research import (
    Claim,
    ClaimStatus,
    ClaimType,
    FactStatus as ClaimFactStatus,
)
from app.domain.evidence import AuthorityLevel
from app.storage.agent_repo import AgentRepository
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


@dataclass
class AnalystRunOutcome:
    brief: AnalystBrief
    created_claim_ids: tuple[str, ...]
    open_requests: tuple[str, ...]


class MarketAnalyst:
    """Deterministic analyst over market-quote evidence."""

    analyst_type = AnalystType.MARKET

    def analyze(
        self,
        snapshot_id: str,
        *,
        session,  # noqa: ANN001
        run_id: str | None = None,
        collect_missing: bool = True,
    ) -> AnalystRunOutcome:
        snapshots = SnapshotRepository(session)
        snapshot = snapshots.get(snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)

        evidence_repo = EvidenceRepository(session)
        all_evidence = evidence_repo.list_for_instrument(
            snapshot.instrument_id, visible_at=snapshot.as_of
        )
        pinned_ids = set(snapshot.evidence_ids)
        # Integrity: cite only what the snapshot pins.
        quotes = [
            e
            for e in all_evidence
            if e.evidence_id in pinned_ids and e.evidence_type is EvidenceType.MARKET_QUOTE
        ]

        agents = AgentRepository(session)
        research = ResearchRepository(session)

        conclusions: list[dict] = []
        missing: list[MissingData] = []
        evidence_refs: list[str] = []
        created_claims: list[str] = []
        confidence = 0.5

        if quotes:
            latest = max(quotes, key=lambda e: e.available_time)
            payload = latest.metadata
            price = payload.get("price")
            change_pct = payload.get("change_pct")
            mcap = payload.get("total_market_cap_yuan")
            evidence_refs.append(latest.evidence_id)

            if price is not None:
                conclusions.append(
                    {
                        "metric": "price",
                        "value": price,
                        "text_zh": f"最新价格 {price}",
                        "text_en": f"Latest price {price}",
                        "evidence_id": latest.evidence_id,
                        "event_time": latest.event_time.isoformat()
                        if latest.event_time
                        else None,
                    }
                )
            if change_pct is not None:
                conclusions.append(
                    {
                        "metric": "change_pct",
                        "value": change_pct,
                        "text_zh": f"较前收盘变动 {change_pct}%",
                        "text_en": f"Changed {change_pct}% versus last close",
                        "evidence_id": latest.evidence_id,
                    }
                )
            if mcap is not None:
                conclusions.append(
                    {
                        "metric": "total_market_cap_yuan",
                        "value": mcap,
                        "text_zh": f"总市值约 {mcap / 1e8:.0f} 亿元",
                        "text_en": f"Total market cap ≈ ¥{mcap / 1e8:.0f}e8",
                        "evidence_id": latest.evidence_id,
                    }
                )

            # A mechanical, fully-cited fact claim (no prediction language).
            if price is not None and change_pct is not None:
                claim = Claim(
                    instrument_id=snapshot.instrument_id,
                    snapshot_id=snapshot.snapshot_id,
                    statement=f"截至{latest.available_time:%Y-%m-%d %H:%M}，最新价为 {price}（{change_pct}%）",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    supporting_evidence_refs=(latest.evidence_id,),
                    fact_status=ClaimFactStatus.CONFIRMED_FACT,
                    confidence=0.99,
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
                        if c.statement == claim.statement
                    ]
                    if existing:
                        created_claims.append(existing[0].claim_id)
                evidence_refs.append(latest.evidence_id)
                confidence = 0.85

        # Missing data disclosure: financials / announcements always needed for
        # a full market brief; only disclosed if snapshot lacks them.
        pinned_types = {
            e.evidence_type for e in all_evidence if e.evidence_id in pinned_ids
        }
        if EvidenceType.FINANCIAL_REPORT not in pinned_types:
            missing.append(
                MissingData(
                    capability="financials",
                    reason="no financial statements in snapshot; needed for fundamentals",
                    evidence_type="financial_report",
                )
            )
        if EvidenceType.ANNOUNCEMENT not in pinned_types:
            missing.append(
                MissingData(
                    capability="announcements",
                    reason="no announcements in snapshot; needed for event context",
                    evidence_type="announcement",
                )
            )
        if not quotes:
            missing.insert(
                0,
                MissingData(
                    capability="market_data",
                    reason="no quote evidence pinned by snapshot",
                    evidence_type="market_quote",
                ),
            )
            confidence = 0.2

        brief = AnalystBrief(
            analyst_type=self.analyst_type,
            instrument_id=snapshot.instrument_id,
            snapshot_id=snapshot.snapshot_id,
            run_id=run_id,
            conclusions=tuple(conclusions),
            claim_refs=tuple(created_claims),
            evidence_refs=tuple(evidence_refs),
            missing_data=tuple(missing),
            confidence=confidence,
            key_questions=(
                "估值水平在行业中的位置如何？",
                "近期是否有公司公告改变基本面预期？",
            ),
            risks=("行情数据时点偏差",),
        )

        brief_id = agents.save_brief(brief)
        _ = brief_id

        # Close the loop: missing data → persisted ResearchRequests → collect.
        open_requests: list[str] = []
        for gap in missing:
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

            for gap in missing:
                collect_capability_evidence(
                    snapshot.instrument_id, gap.capability, repo=evidence_repo
                )

        return AnalystRunOutcome(
            brief=brief,
            created_claim_ids=tuple(created_claims),
            open_requests=tuple(open_requests),
        )
