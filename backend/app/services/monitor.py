"""Monitor + MaterialityJudge (任务书 §45).

Monitor is the cheap loop: fresh quote collection, a new snapshot, and a
delta against the previous snapshot. The MaterialityJudge then decides —
with deterministic thresholds — whether nothing changed (NO_MATERIAL_CHANGE),
a delta research suffices (DELTA_RESEARCH), or a full research run is
required (FULL_RESEARCH). The judge never runs research itself.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.evidence import EvidenceType, utc_now
from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
from app.services.evidence_collector import collect_capability_evidence
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base, SnapshotORM
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


class MaterialityDecision(str, Enum):
    NO_MATERIAL_CHANGE = "no_material_change"
    DELTA_RESEARCH = "delta_research"
    FULL_RESEARCH = "full_research"


class MaterialityDecisionORM(Base):
    __tablename__ = "materiality_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)

    old_snapshot_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_snapshot_id: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(24), index=True)
    added_count: Mapped[int] = mapped_column(Integer, default=0)
    removed_count: Mapped[int] = mapped_column(Integer, default=0)
    price_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MaterialityDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    instrument_id: str
    old_snapshot_id: str | None
    new_snapshot_id: str
    decision: MaterialityDecision
    added_evidence_ids: tuple[str, ...]
    removed_evidence_ids: tuple[str, ...]
    price_change_pct: float | None
    reasons: tuple[str, ...]
    created_at: datetime


class MaterialityJudge:
    """Deterministic thresholds (§45). Rates are percentages."""

    def __init__(
        self,
        *,
        price_move_full_pct: float = 5.0,
        added_delta_threshold: int = 1,
        removed_any_is_full: bool = False,
    ) -> None:
        self._price_move_full_pct = price_move_full_pct
        self._added_delta_threshold = added_delta_threshold
        self._removed_any_is_full = removed_any_is_full

    def decide(
        self,
        *,
        old_snapshot: EvidenceSnapshot | None,
        new_snapshot: EvidenceSnapshot,
        added: list[str],
        removed: list[str],
        price_change_pct: float | None,
        added_kinds: list[str] | None = None,
    ) -> tuple[MaterialityDecision, list[str]]:
        reasons: list[str] = []
        added_kinds = added_kinds or []

        if old_snapshot is None:
            reasons.append("no previous snapshot: first monitoring pass")
            return MaterialityDecision.FULL_RESEARCH, reasons

        if not added and not removed and price_change_pct is None:
            reasons.append("no evidence delta and no price change observed")
            return MaterialityDecision.NO_MATERIAL_CHANGE, reasons

        if price_change_pct is not None and abs(price_change_pct) >= self._price_move_full_pct:
            reasons.append(
                f"price moved {price_change_pct:.2f}% (>= ±{self._price_move_full_pct}%)"
            )
            return MaterialityDecision.FULL_RESEARCH, reasons

        if removed:
            if self._removed_any_is_full:
                reasons.append(f"{len(removed)} evidence items no longer visible")
                return MaterialityDecision.FULL_RESEARCH, reasons
            reasons.append(f"{len(removed)} evidence items no longer visible")

        # New *non-quote* evidence (announcements, filings, news) is material.
        non_quote_additions = [k for k in added_kinds if k != "market_quote"]
        if len(non_quote_additions) >= self._added_delta_threshold:
            reasons.append(f"{len(non_quote_additions)} new non-quote evidence item(s)")
            return MaterialityDecision.DELTA_RESEARCH, reasons

        # Quote-only re-observations: any actual price change (below the FULL
        # threshold) warrants a delta pass; an unchanged price is noise.
        if price_change_pct not in (None, 0.0):
            reasons.append(
                f"price moved {price_change_pct:.2f}% (below ±{self._price_move_full_pct}% full threshold)"
            )
            return MaterialityDecision.DELTA_RESEARCH, reasons

        if added:
            reasons.append(
                f"{len(added)} quote re-observation(s) with unchanged price"
            )
        reasons.append("changes below materiality thresholds")
        return MaterialityDecision.NO_MATERIAL_CHANGE, reasons


class MaterialityRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(self, decision: MaterialityDecisionModel) -> str:
        row = MaterialityDecisionORM(
            decision_id=decision.decision_id,
            instrument_id=decision.instrument_id,
            old_snapshot_id=decision.old_snapshot_id,
            new_snapshot_id=decision.new_snapshot_id,
            decision=decision.decision.value,
            added_count=len(decision.added_evidence_ids),
            removed_count=len(decision.removed_evidence_ids),
            price_change_pct=decision.price_change_pct,
            reasons_json=list(decision.reasons),
            created_at=decision.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.decision_id

    def list_for(self, instrument_id: str, *, limit: int = 20) -> list[MaterialityDecisionModel]:
        rows = self._session.scalars(
            select(MaterialityDecisionORM)
            .where(MaterialityDecisionORM.instrument_id == instrument_id)
            .order_by(MaterialityDecisionORM.created_at.desc())
            .limit(limit)
        ).all()
        return [
            MaterialityDecisionModel(
                decision_id=r.decision_id,
                instrument_id=r.instrument_id,
                old_snapshot_id=r.old_snapshot_id,
                new_snapshot_id=r.new_snapshot_id,
                decision=r.decision,  # type: ignore[arg-type]
                added_evidence_ids=(),
                removed_evidence_ids=(),
                price_change_pct=r.price_change_pct,
                reasons=tuple(r.reasons_json or ()),
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]


class MonitorService:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session
        self._snapshots = SnapshotRepository(session)
        self._evidence = EvidenceRepository(session)
        self._repo = MaterialityRepository(session)

    def run_monitor(self, instrument_id: str, *, judge: MaterialityJudge | None = None,
                    act: bool = True) -> MaterialityDecisionModel:
        # 1) fresh collection + new snapshot at now
        collect_capability_evidence(
            instrument_id, "market_data", repo=self._evidence, fresh=True
        )
        new_snapshot = self._snapshots.build(
            instrument_id, utc_now(), evidence_repo=self._evidence
        )

        # 2) previous snapshot for the instrument (latest created before this one)
        old_snapshot = self._previous_snapshot(instrument_id, new_snapshot)

        # 3) delta
        old_ids = set(old_snapshot.evidence_ids) if old_snapshot else set()
        new_ids = set(new_snapshot.evidence_ids)
        added = sorted(new_ids - old_ids)
        removed = sorted(old_ids - new_ids)
        price_change_pct = self._price_change(old_snapshot, new_snapshot)

        # kinds of the added evidence (quote-only polls are judged differently)
        all_evidence = self._evidence.list_for_instrument(instrument_id)
        by_id = {e.evidence_id: e for e in all_evidence}
        added_kinds = [
            by_id[eid].evidence_type.value for eid in added if eid in by_id
        ]

        # 4) judge + persist
        judge = judge or MaterialityJudge()
        decision, reasons = judge.decide(
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            added=added,
            removed=removed,
            price_change_pct=price_change_pct,
            added_kinds=added_kinds,
        )
        model = MaterialityDecisionModel(
            decision_id=f"dec_{uuid4().hex[:16]}",
            instrument_id=instrument_id,
            old_snapshot_id=old_snapshot.snapshot_id if old_snapshot else None,
            new_snapshot_id=new_snapshot.snapshot_id,
            decision=decision,
            added_evidence_ids=tuple(added),
            removed_evidence_ids=tuple(removed),
            price_change_pct=price_change_pct,
            reasons=tuple(reasons),
            created_at=datetime.now(timezone.utc),
        )
        self._repo.save(model)

        if act:
            self._act_on_decision(model)
        return model

    def _act_on_decision(self, decision: MaterialityDecisionModel) -> None:
        """Dispatch the research action for the decision (整改二轮 F0.1):
        NO_MATERIAL_CHANGE → nothing; DELTA → new ReportVersion on the
        latest chain; FULL → the full ResearchPipeline (single implementation)."""
        if decision.decision is MaterialityDecision.NO_MATERIAL_CHANGE:
            return

        if decision.decision is MaterialityDecision.FULL_RESEARCH:
            from app.services.pipeline import ResearchPipeline

            ResearchPipeline(self._session).run(decision.instrument_id)
            return

        # delta_research: recompile on the new snapshot, extend the chain
        from app.domain.manifest import ReportVersion
        from app.storage.report_repo import ReportRepository
        from app.storage.manifest_repo import ReportVersionRepository
        from app.services.report_compiler import ReportCompiler

        compiler = ReportCompiler(self._session)
        structured = compiler.compile(decision.new_snapshot_id)
        rendered = compiler.render_and_gate(structured, language="zh-CN")
        reports = ReportRepository(self._session).list_for(decision.instrument_id)
        if not reports:
            return
        latest = reports[0]
        chain = ReportVersionRepository(self._session).list_chain(latest["report_id"])
        previous = chain[-1] if chain else None
        ReportVersionRepository(self._session).save(
            ReportVersion(
                report_id=latest["report_id"],
                version_no=(previous.version_no + 1) if previous else 1,
                parent_version_id=previous.version_id if previous else None,
                change_reason=(
                    f"delta research: {decision.decision.value} "
                    f"({len(decision.added_evidence_ids)} new evidence, "
                    f"price {decision.price_change_pct}%)"
                ),
                changed_sections=("market_and_capital",),
                language="zh-CN",
                markdown=rendered["markdown"],
                html=rendered["html"],
                content_json={"citations": sorted(set(structured.citations))},
            )
        )

    def _previous_snapshot(self, instrument_id: str, current: EvidenceSnapshot) -> EvidenceSnapshot | None:
        """The most recent stored snapshot for the instrument strictly before
        the current one (by as_of)."""
        rows = self._session.scalars(
            select(SnapshotORM)
            .where(SnapshotORM.instrument_id == instrument_id)
            .order_by(SnapshotORM.as_of.desc())
        ).all()
        for row in rows:
            if row.snapshot_id != current.snapshot_id and _ensure_utc(row.as_of) < current.as_of:
                return EvidenceSnapshot(
                    instrument_id=row.instrument_id,
                    as_of=_ensure_utc(row.as_of),
                    items=tuple(SnapshotItem(**item) for item in (row.items_json or [])),
                    created_at=_ensure_utc(row.created_at),
                )
        return None

    def _price_change(self, old: EvidenceSnapshot | None, new: EvidenceSnapshot) -> float | None:
        if old is None:
            return None
        evidence = self._evidence.list_for_instrument(new.instrument_id)
        by_id = {e.evidence_id: e for e in evidence}

        def _price(snapshot: EvidenceSnapshot) -> float | None:
            prices = []
            for item in snapshot.items:
                ev = by_id.get(item.evidence_id)
                if ev is not None and ev.evidence_type is EvidenceType.MARKET_QUOTE:
                    p = (ev.metadata or {}).get("price")
                    if p is not None:
                        prices.append(float(p))
            return prices[0] if prices else None

        old_price, new_price = _price(old), _price(new)
        if old_price in (None, 0) or new_price is None:
            return None
        return (new_price / old_price - 1) * 100
