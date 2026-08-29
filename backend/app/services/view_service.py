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
from app.storage.orm import ResearchRunORM, WatchlistORM
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

    # -- UI2 剩余 Read Model（评审 §10/§11：消除 N+1/2N） -------------------------

    def _names_for(self, instrument_ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for iid in set(instrument_ids):
            out[iid] = self._identity(iid) or {
                "instrument_id": iid,
                "name": None,
                "code": iid.split(":")[-1],
                "exchange": None,
                "board": None,
            }
        return out

    def command_center_view(self) -> dict:
        runs = self._session.scalars(
            select(ResearchRunORM)
            .order_by(ResearchRunORM.started_at.desc(), ResearchRunORM.id.desc())
            .limit(12)
        ).all()
        recent = [
            {
                "run_id": r.run_id,
                "instrument_id": r.instrument_id,
                "status": r.status,
                "started_at": _iso(r.started_at),
            }
            for r in runs
        ]
        running = [r for r in recent if r["status"] == "running"]

        plans = self.list_plans_internal()
        current_plan = next((p for p in plans if p["status"] == "running"), None)
        recent_plans = [p for p in plans if p is not current_plan][:6]

        tasks = self.continuous_research_rows()
        active_tasks = [t for t in tasks if t["status"] == "running"]

        pending = self.prediction_review_rows(limit=20)
        pending_predictions = [p for p in pending if not p["validated"]]
        # 排序（任务书 §15）：冲突优先 → 到期优先 → 置信度优先
        pending_predictions.sort(
            key=lambda p: (
                0 if p["consistency"] == "conflict" else 1,
                p["due_at"] or "9999",
                -p["confidence"],
            )
        )

        names = self._names_for(
            [r["instrument_id"] for r in recent]
            + [t["instrument_id"] for t in tasks]
            + [p["instrument_id"] for p in pending_predictions]
        )

        return {
            "running_runs": running,
            "recent_runs": recent[:6],
            "active_tasks": active_tasks,
            "current_plan": current_plan,
            "recent_plans": recent_plans,
            "pending_predictions": pending_predictions[:6],
            "names": names,
        }

    def list_plans_internal(self) -> list[dict]:
        from app.application.conversation import ConversationRepository

        return ConversationRepository(self._session).list_plans(limit=8)

    def continuous_research_rows(self) -> list[dict]:
        from app.scheduler.tasks import TaskRepository

        tasks = TaskRepository(self._session).list_all()
        report_rows = self._session.scalars(
            select(ReportORM)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
        ).all()
        latest_report: dict[str, ReportORM] = {}
        for r in report_rows:
            if r.instrument_id not in latest_report:
                latest_report[r.instrument_id] = r
        out = []
        for t in tasks:
            rep = latest_report.get(t.instrument_id)
            identity = self._identity(t.instrument_id)
            out.append(
                {
                    "task_id": t.task_id,
                    "instrument_id": t.instrument_id,
                    "task_type": t.task_type.value,
                    "schedule": t.schedule,
                    "status": t.status.value,
                    "enabled": t.enabled,
                    "last_run_at": _iso(t.last_run_at),
                    "next_run_at": _iso(t.next_run_at),
                    "instrument": identity,
                    "latest_report": (
                        {"report_id": rep.report_id, "created_at": _iso(rep.created_at)}
                        if rep
                        else None
                    ),
                }
            )
        return out

    def prediction_review_rows(self, *, limit: int = 50) -> list[dict]:
        from app.api.predictions import _consistency

        rows = self._session.scalars(
            select(PredictionORM)
            .order_by(PredictionORM.created_at.desc(), PredictionORM.id.desc())
            .limit(limit)
        ).all()
        validations = ValidationRepository(self._session)
        out = []
        for r in rows:
            validation = validations.get_for_prediction(r.prediction_id)
            lo, hi = r.expected_return_min, r.expected_return_max

            class _Shim:
                expected_direction = r.expected_direction
                expected_return_range = (lo, hi)

            consistency, note = _consistency(_Shim())
            out.append(
                {
                    "prediction_id": r.prediction_id,
                    "instrument_id": r.instrument_id,
                    "horizon": r.horizon,
                    "expected_direction": r.expected_direction,
                    "expected_return_range": [lo, hi],
                    "consistency": consistency,
                    "consistency_note": note,
                    "confidence": r.confidence,
                    "due_at": _iso(r.due_at),
                    "created_at": _iso(r.created_at),
                    "validated": validation is not None,
                    "validation": (
                        {
                            "instrument_return_pct": validation.instrument_return_pct,
                            "direction_correct": validation.direction_correct,
                            "range_hit": validation.range_hit,
                        }
                        if validation
                        else None
                    ),
                }
            )
        return out

    def report_library_rows(self, *, limit: int = 50) -> list[dict]:
        reports = self._session.scalars(
            select(ReportORM)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
            .limit(limit)
        ).all()
        theses = self._session.scalars(select(ThesisORM)).all()
        latest_thesis: dict[str, ThesisORM] = {}
        for t in theses:
            keep = latest_thesis.get(t.instrument_id)
            if keep is None or (t.created_at and keep.created_at and t.created_at > keep.created_at):
                latest_thesis[t.instrument_id] = t
        names = self._names_for([r.instrument_id for r in reports])
        out = []
        for r in reports:
            t = latest_thesis.get(r.instrument_id)
            s = len(t.supporting_claims_json or []) if t else 0
            o = len(t.opposing_claims_json or []) if t else 0
            judgment = "up" if s > o else "down" if o > s else ("neutral" if t else None)
            out.append(
                {
                    "report_id": r.report_id,
                    "instrument_id": r.instrument_id,
                    "name": names.get(r.instrument_id, {}).get("name"),
                    "code": names.get(r.instrument_id, {}).get("code"),
                    "judgment": judgment,
                    "confidence": t.confidence if t else None,
                    "created_at": _iso(r.created_at),
                    "gate_status": r.gate_status,
                }
            )
        return out
