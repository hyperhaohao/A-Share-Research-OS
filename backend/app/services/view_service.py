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
        """P0-09: Research Stance 来自 Thesis 的结构化方向（description 含看多/看空语义），
        claim 数量仅作为 support_balance 报出，不再直接决定方向。"""
        theses = self._session.scalars(
            select(ThesisORM)
            .where(ThesisORM.instrument_id == instrument_id)
            .order_by(ThesisORM.created_at.desc(), ThesisORM.id.desc())
            .limit(1)
        ).all()
        judgment = None
        confidence = None
        title = None
        support_balance = None
        if theses:
            t = theses[0]
            s, o = len(t.supporting_claims_json or []), len(t.opposing_claims_json or [])
            support_balance = f"{s}:{o}"
            confidence = t.confidence
            title = t.title
            # Thesis.description 是研究管线的结构化综合结论（含行业/财务/事件/宏观）
            # 方向从 Thesis 的 catalysts + trigger_conditions（看多催化剂存在）
            # 与 risks + invalidate_conditions（看空信号存在）的相对权重推导，
            # 但当前不做自然语言 NLP —— 只报 support_balance，judgment 留给前端展示原始 Thesis。
            judgment = None  # 让 UI 显示 Thesis 标题而非方向标签
        return {
            "judgment": judgment,
            "confidence": confidence,
            "thesis_title": title,
            "support_balance": support_balance,
        }

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
        """P1-01: batch projection — constant SQL count regardless of N."""
        from app.storage.prediction_repo import PredictionORM
        from app.storage.report_repo import ReportORM
        from app.storage.research_orm import ThesisORM
        from app.storage.orm import EvidenceORM
        from app.application.strategy_monitor import StrategyMonitorORM

        watch_rows = self._session.scalars(
            select(WatchlistORM).order_by(WatchlistORM.added_at.desc())
        ).all()
        ids = [w.instrument_id for w in watch_rows]
        if not ids:
            return []

        # batch: identities
        inst_rows = self._session.scalars(
            select(InstrumentRegistryORM).where(InstrumentRegistryORM.instrument_id.in_(ids))
        ).all()
        identities = {
            r.instrument_id: {
                "instrument_id": r.instrument_id,
                "name": r.name if r.name != r.code else None,
                "code": r.code,
                "exchange": r.exchange,
                "board": r.board,
            }
            for r in inst_rows
        }

        # batch: latest priced quote per instrument
        quote_rows = self._session.scalars(
            select(EvidenceORM).where(
                EvidenceORM.instrument_id.in_(ids),
                EvidenceORM.evidence_type == "market_quote",
            )
        ).all()
        latest_quote: dict[str, dict] = {}
        for e in quote_rows:
            md = e.metadata_json or {}
            price = md.get("price")
            if not isinstance(price, (int, float)) or price <= 0:
                continue
            iid = e.instrument_id
            prev = latest_quote.get(iid)
            if prev is None or e.available_time > prev["available_time_dt"]:
                latest_quote[iid] = {
                    "price": float(price),
                    "change_pct": md.get("change_pct"),
                    "available_time_dt": e.available_time,
                }

        # batch: latest thesis per instrument
        thesis_rows = self._session.scalars(
            select(ThesisORM).where(ThesisORM.instrument_id.in_(ids))
        ).all()
        latest_thesis: dict[str, ThesisORM] = {}
        for t in thesis_rows:
            prev = latest_thesis.get(t.instrument_id)
            if prev is None or (t.created_at and prev.created_at and t.created_at > prev.created_at):
                latest_thesis[t.instrument_id] = t

        # batch: latest report per instrument
        report_rows = self._session.scalars(
            select(ReportORM).where(ReportORM.instrument_id.in_(ids))
        ).all()
        latest_report: dict[str, ReportORM] = {}
        for r in report_rows:
            prev = latest_report.get(r.instrument_id)
            if prev is None or (r.created_at and prev.created_at and r.created_at > prev.created_at):
                latest_report[r.instrument_id] = r

        # batch: latest prediction per instrument
        pred_rows = self._session.scalars(
            select(PredictionORM).where(PredictionORM.instrument_id.in_(ids))
        ).all()
        latest_pred: dict[str, PredictionORM] = {}
        for p_row in pred_rows:
            prev = latest_pred.get(p_row.instrument_id)
            if prev is None or (p_row.created_at and prev.created_at and p_row.created_at > prev.created_at):
                latest_pred[p_row.instrument_id] = p_row

        # batch: monitors covering any of the ids
        monitors = self._session.scalars(
            select(StrategyMonitorORM).where(StrategyMonitorORM.enabled.is_(True))
        ).all()
        monitor_by_id: dict[str, dict] = {}
        for m in monitors:
            for u in (m.universe_json or []):
                if isinstance(u, dict) and u.get("instrument_id") in ids:
                    mid = u["instrument_id"]
                    if mid not in monitor_by_id:
                        monitor_by_id[mid] = {
                            "monitor_id": m.monitor_id,
                            "enabled": m.enabled,
                            "next_run_at": _iso(m.next_run_at),
                        }

        # memory join
        cards = []
        for w in watch_rows:
            iid = w.instrument_id
            inst = identities.get(iid)
            quote = latest_quote.get(iid)
            t = latest_thesis.get(iid)
            rep = latest_report.get(iid)
            pred = latest_pred.get(iid)
            cards.append({
                "instrument_id": iid,
                "instrument": inst,
                "quote": (
                    {
                        "price": quote["price"],
                        "change_pct": quote.get("change_pct"),
                        "quote_time": _iso(quote["available_time_dt"]),
                    }
                    if quote
                    else None
                ),
                "research": {
                    "judgment": None,
                    "confidence": t.confidence if t else None,
                    "thesis_title": t.title if t else None,
                    "support_balance": (
                        f"{len(t.supporting_claims_json or [])}:{len(t.opposing_claims_json or [])}"
                        if t
                        else None
                    ),
                },
                "report": (
                    {"report_id": rep.report_id, "created_at": _iso(rep.created_at)}
                    if rep
                    else None
                ),
                "prediction": (
                    {
                        "prediction_id": pred.prediction_id,
                        "horizon": pred.horizon,
                        "expected_direction": pred.expected_direction,
                        "expected_return_range": [pred.expected_return_min, pred.expected_return_max],
                        "validated": False,
                        "due_at": _iso(pred.due_at),
                    }
                    if pred
                    else None
                ),
                "monitor": monitor_by_id.get(iid),
                "added_at": _iso(w.added_at),
            })
        return cards


    # -- 工作台总览视图（§15） ------------------------------------------------------------

    def instrument_overview(self, instrument_id: str) -> dict:
        """P1-05/06/07: enriched overview with real valuation, specific latest
        changes, and per-capability data quality."""
        evidence = EvidenceRepository(self._session).list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )

        # P1-07: per-capability data quality
        by_type: dict[str, int] = {}
        for e in evidence:
            by_type[e.evidence_type.value] = by_type.get(e.evidence_type.value, 0) + 1
        expected_caps = {"market_quote", "financial_report", "announcements", "news", "industry_data", "capital_flow", "macro_indicator"}
        available_caps = set(by_type.keys()) & expected_caps
        quality_score = f"{len(available_caps)}/{len(expected_caps)}"

        # P1-06: latest changes — the 5 newest evidence items with type
        latest_changes = sorted(evidence, key=lambda e: e.available_time, reverse=True)[:5]
        changes = [
            {
                "evidence_type": e.evidence_type.value,
                "title": e.title[:80],
                "available_time": _iso(e.available_time),
            }
            for e in latest_changes
        ]

        # P1-05: real valuation from the latest snapshot's valuations
        valuation_summary = None
        from app.storage.valuation_repo import ValuationORM
        from app.storage.orm import SnapshotORM
        latest_snap = self._session.scalars(
            select(SnapshotORM)
            .where(SnapshotORM.instrument_id == instrument_id)
            .order_by(SnapshotORM.as_of.desc(), SnapshotORM.id.desc())
            .limit(1)
        ).first()
        if latest_snap:
            val_rows = self._session.scalars(
                select(ValuationORM).where(
                    ValuationORM.snapshot_id == latest_snap.snapshot_id,
                    ValuationORM.computable.is_(True),
                )
            ).all()
            if val_rows:
                quote = self._latest_quote(instrument_id)
                price = quote["price"] if quote else None
                implied = []
                for v in val_rows:
                    implied.append({
                        "method": v.method.value if hasattr(v.method, "value") else str(v.method),
                        "implied_price": v.value,
                        "upside_pct": round((v.value / price - 1) * 100, 2) if price and price > 0 else None,
                    })
                valuation_summary = {
                    "current_price": price,
                    "as_of": _iso(latest_snap.as_of),
                    "methods": implied,
                }

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
            "valuation": valuation_summary,
            "latest_changes": changes,
            "data_quality": {
                "evidence_count": len(evidence),
                "source_kinds": len({e.evidence_type.value for e in evidence}),
                "quality_score": quality_score,
                "capability_breakdown": by_type,
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
                # Direction may be a str (ORM row) — _consistency expects the enum
                class expected_direction:
                    value = r.expected_direction
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
                            "benchmark_return_pct": validation.benchmark_return_pct,
                            "excess_return_pct": validation.excess_return_pct,
                            "direction_correct": validation.direction_correct,
                            "range_hit": validation.range_hit,
                        }
                        if validation
                        else None
                    ),
                }
            )
        return out

    def experience_rows(self, *, limit: int = 50) -> list[dict]:
        """经验卡 Library 行（§25）：状态/置信度/验证数/来源/更新时间。"""
        from app.application.experience import ExperienceCardORM, ExperienceValidationORM

        rows = self._session.scalars(
            select(ExperienceCardORM)
            .order_by(ExperienceCardORM.created_at.desc(), ExperienceCardORM.id.desc())
            .limit(limit)
        ).all()
        validations = self._session.scalars(select(ExperienceValidationORM)).all()
        count_by_card: dict[str, int] = {}
        for v in validations:
            count_by_card[v.card_id] = count_by_card.get(v.card_id, 0) + 1
        out = []
        for r in rows:
            out.append(
                {
                    "card_id": r.card_id,
                    "title": r.title,
                    "instrument_id": r.instrument_id,
                    "status": r.status,
                    "confidence": r.confidence,
                    "current_version": r.current_version,
                    "validation_count": count_by_card.get(r.card_id, 0),
                    "source_report_id": r.source_report_id,
                    "created_at": _iso(r.created_at),
                    "updated_at": _iso(r.updated_at),
                }
            )
        return out

    def report_library_rows(self, *, limit: int = 50) -> list[dict]:
        reports = self._session.scalars(
            select(ReportORM)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
            .limit(limit)
        ).all()
        # P0-08: PIT — 每份报告用其 snapshot_id 匹配同时点的 Thesis，
        # 不使用当前最新 Thesis（消除历史时点污染）
        snapshot_ids = {r.snapshot_id for r in reports}
        theses = self._session.scalars(
            select(ThesisORM).where(ThesisORM.snapshot_id.in_(snapshot_ids))
        ).all() if snapshot_ids else []
        thesis_by_snapshot: dict[str, ThesisORM] = {}
        for t in theses:
            # 同一 snapshot 多条 thesis 时取最新
            keep = thesis_by_snapshot.get(t.snapshot_id)
            if keep is None or (t.created_at and keep.created_at and t.created_at > keep.created_at):
                thesis_by_snapshot[t.snapshot_id] = t
        names = self._names_for([r.instrument_id for r in reports])
        out = []
        for r in reports:
            t = thesis_by_snapshot.get(r.snapshot_id)
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
