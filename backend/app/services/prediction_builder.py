"""PredictionBuilder (PW2) — derive a Prediction from one report's research state.

Every input is read from the persisted research state (thesis claim counts,
snapshot price, valuation implied prices). When a required input is missing
the builder raises :class:`PredictionNotDerivable` with an explicit reason —
ranges are never invented.

Derivation (deterministic, evidence-anchored):
    direction  supporting vs opposing claim counts of the latest thesis
    range      [min, max] of computable valuation implied prices relative
               to the snapshot's newest visible quote (percent)
    confidence the thesis' own confidence
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.prediction import Direction, Horizon, PredictionRecord
from app.storage.prediction_repo import PredictionRepository
from app.storage.report_repo import ReportRepository
from app.storage.repository import EvidenceRepository
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.storage.valuation_repo import ValuationRepository


class PredictionNotDerivable(ValueError):
    """The report's research state lacks a required input (explicit, honest
    refusal — a range is never invented)."""


class PredictionBuilder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def build_and_save(self, report_id: str, horizon: Horizon) -> PredictionRecord:
        report = ReportRepository(self._session).get(report_id)
        if report is None:
            raise KeyError(report_id)

        instrument_id = report["instrument_id"]
        snapshot_id = report["snapshot_id"]
        snapshot = SnapshotRepository(self._session).get(snapshot_id)
        if snapshot is None:
            raise PredictionNotDerivable("report has no snapshot research state")

        theses = ResearchRepository(self._session).list_theses(
            instrument_id, snapshot_id=snapshot_id
        )
        if not theses:
            raise PredictionNotDerivable("no thesis in the report's research state")
        thesis = max(theses, key=lambda t: t.created_at)

        supporting = len(thesis.supporting_claims)
        opposing = len(thesis.opposing_claims)
        if supporting > opposing:
            direction = Direction.UP
        elif opposing > supporting:
            direction = Direction.DOWN
        else:
            direction = Direction.NEUTRAL

        price = self._snapshot_price(instrument_id, snapshot)
        if price is None or price <= 0:
            raise PredictionNotDerivable("no visible quote in the report's research state")

        implied = [
            v["value"]
            for v in ValuationRepository(self._session).list_for(
                instrument_id, snapshot_id=snapshot_id
            )
            if v["computable"] and v["value"] is not None
        ]
        if not implied:
            raise PredictionNotDerivable("no computable valuation in the research state")

        lo = round((min(implied) / price - 1) * 100, 2)
        hi = round((max(implied) / price - 1) * 100, 2)
        if lo > hi:
            lo, hi = hi, lo

        prediction = PredictionRecord(
            instrument_id=instrument_id,
            research_run_id=None,
            as_of=snapshot.as_of,
            horizon=horizon,
            expected_direction=direction,
            expected_return_range=(lo, hi),
            confidence=thesis.confidence,
            supporting_thesis_id=thesis.thesis_id,
            trigger_conditions=tuple(thesis.trigger_conditions),
            invalidate_conditions=tuple(thesis.invalidate_conditions),
        )
        PredictionRepository(self._session).save(prediction)
        saved = PredictionRepository(self._session).get(prediction.prediction_id)
        assert saved is not None
        return saved

    def _snapshot_price(self, instrument_id: str, snapshot) -> float | None:
        """Newest quote price among the snapshot's pinned evidence (PIT-safe)."""
        evidence_repo = EvidenceRepository(self._session)
        pinned = set(snapshot.evidence_ids)
        quotes = [
            e
            for e in evidence_repo.list_for_instrument(
                instrument_id, visible_at=snapshot.as_of
            )
            if e.evidence_id in pinned and e.evidence_type.value == "market_quote"
        ]
        for record in sorted(quotes, key=lambda e: e.available_time, reverse=True):
            price = (record.metadata or {}).get("price")
            if isinstance(price, (int, float)) and price > 0:
                return float(price)
        return None
