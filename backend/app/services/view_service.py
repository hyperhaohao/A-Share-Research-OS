"""UI Read Models / Query Service（UX Foundation, 总纲评审 §12-§16）.

专门为 UI 聚合已有数据的只读投影（Read Model / Projection）——不建第二套
Domain，不写业务状态。页面消费一个 View 一次拿到 L1（结论）/L2（依据）/
L3（技术详情入口）分层所需的一切，前端不再串多个 API 自行拼装。

    GET /views/watchlist                    → WatchlistCardView[]
    GET /views/instruments/{id}/overview    → InstrumentOverviewView
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.evidence import EvidenceType
from app.application.strategy_monitor import StrategyMonitorORM
from app.storage.instrument_repo import InstrumentRegistryORM
from app.storage.orm import WatchlistORM
from app.storage.prediction_repo import PredictionORM, ValidationRepository
from app.storage.report_repo import ReportORM
from app.storage.repository import EvidenceRepository
from app.storage.research_orm import ThesisORM
from app.storage.valuation_repo import ValuationORM


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc).isoformat()


def _newest(rows: list, key):
    return max(rows, key=key) if rows else None


class ViewService:
    """Read-model assembler: repo reads only, no writes (红线 2/1)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- 共享小节 ----------------------------------------------------------------

    def _identity(self, instrument_id: str) -> dict | None:
        row = self._session.scalars(
            select(InstrumentRegistryORM).where(
                InstrumentRegistryORM.instrument_id == instrument_id
            )
        ).first()
        if row is None:
            return None
        return {
            "instrument_id": row.instrument_id,
            "name": row.name if row.name != row.code else None,
            "code": row.code,
            "exchange": row.exchange,
            "board": row.board,
        }

    def _latest_quote(self, instrument_id: str) -> dict | None:
        evidence = EvidenceRepository(self._session).list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )
        priced = [
            e
            for e in evidence
            if e.evidence_type is EvidenceType.MARKET_QUOTE
            and isinstance((e.metadata or {}).get("price"), (int, float))
        ]
        if not priced:
            return None
        latest = max(priced, key=lambda e: e.available_time)
        md = latest.metadata
        return {
            "price": float(md["price"]),
            "change_pct": md.get("change_pct"),
            "quote_time": _iso(latest.available_time),
        }

    def _research(self, instrument_id: str) -> dict:
        theses = self._session.scalars(
            select(ThesisORM)
            .where(ThesisORM.instrument_id == instrument_id)
            .order_by(ThesisORM.created_at.desc(), ThesisORM.id.desc())
            .limit(1)
        ).all()
        judgment = None
        confidence = None
        title = None
        if theses:
            t = theses[0]
            s, o = len(t.supporting_claims_json or []), len(t.opposing_claims_json or [])
            if s > o:
                judgment = "up"
            elif o > s:
                judgment = "down"
            else:
                judgment = "neutral"
            confidence = t.confidence
            title = t.title
        return {"judgment": judgment, "confidence": confidence, "thesis_title": title}

    def _latest_report(self, instrument_id: str) -> dict | None:
        rows = self._session.scalars(
            select(ReportORM)
            .where(ReportORM.instrument_id == instrument_id)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
            .limit(1)
        ).all()
        if not rows:
            return None
        r = rows[0]
        return {
            "report_id": r.report_id,
            "created_at": _iso(r.created_at),
        }

    def _latest_prediction(self, instrument_id: str) -> dict | None:
        rows = self._session.scalars(
            select(PredictionORM)
            .where(PredictionORM.instrument_id == instrument_id)
            .order_by(PredictionORM.created_at.desc(), PredictionORM.id.desc())
            .limit(1)
        ).all()
        if not rows:
            return None
        r = rows[0]
        validation = ValidationRepository(self._session).get_for_prediction(r.prediction_id)
        return {
            "prediction_id": r.prediction_id,
            "horizon": r.horizon,
            "expected_direction": r.expected_direction,
            "expected_return_range": [r.expected_return_min, r.expected_return_max],
            "validated": validation is not None,
            "due_at": _iso(r.due_at),
        }

    def _monitor(self, instrument_id: str) -> dict | None:
        rows = self._session.scalars(
            select(StrategyMonitorORM)
            .where(StrategyMonitorORM.enabled.is_(True))
            .order_by(StrategyMonitorORM.created_at.desc())
            .limit(20)
        ).all()
        for m in rows:
            universe_ids = [
                u.get("instrument_id") for u in (m.universe_json or []) if isinstance(u, dict)
            ]
            if instrument_id in universe_ids:
                return {
                    "monitor_id": m.monitor_id,
                    "enabled": m.enabled,
                    "next_run_at": _iso(m.next_run_at),
                }
        return None

    # -- 关注池卡片视图 ---------------------------------------------------------------

    def watchlist_cards(self) -> list[dict]:
        rows = self._session.scalars(
            select(WatchlistORM).order_by(WatchlistORM.added_at.desc())
        ).all()
        cards: list[dict] = []
        for row in rows:
            instrument_id = row.instrument_id
            cards.append(
                {
                    "instrument_id": instrument_id,
                    "instrument": self._identity(instrument_id),
                    "quote": self._latest_quote(instrument_id),
                    "research": self._research(instrument_id),
                    "report": self._latest_report(instrument_id),
                    "prediction": self._latest_prediction(instrument_id),
                    "monitor": self._monitor(instrument_id),
                    "added_at": _iso(row.added_at),
                }
            )
        return cards

    # -- 工作台总览视图（§15） ------------------------------------------------------------

    def instrument_overview(self, instrument_id: str) -> dict:
        evidence = EvidenceRepository(self._session).list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )
        quality_items = len(evidence)
        source_kinds = len({e.evidence_type.value for e in evidence})

        thesis = self._research(instrument_id)
        theses = self._session.scalars(
            select(ThesisORM)
            .where(ThesisORM.instrument_id == instrument_id)
            .order_by(ThesisORM.created_at.desc(), ThesisORM.id.desc())
            .limit(1)
        ).all()
        catalysts: list[str] = []
        risks: list[str] = []
        if theses:
            catalysts = [str(c) for c in (theses[0].catalysts_json or [])][:5]
            risks = [str(r) for r in (theses[0].risks_json or [])][:5]

        return {
            "instrument": self._identity(instrument_id),
            "quote": self._latest_quote(instrument_id),
            "research": thesis,
            "catalysts": catalysts,
            "risks": risks,
            "report": self._latest_report(instrument_id),
            "prediction": self._latest_prediction(instrument_id),
            "monitor": self._monitor(instrument_id),
            "data_quality": {
                "evidence_count": quality_items,
                "source_kinds": source_kinds,
            },
        }
