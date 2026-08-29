"""Strategy monitor service (V2 Phase G, 总纲 §24/§25/§48/§49).

一次盯盘运行 = 观察采集（真实数据）→ 规则信号（强类型）→ 研究决策（§25
仅 Paper/Research）。观察与信号与决策分别落库、互相引用，绝不把技术
指标直接冒充 AI Decision（§24）。

观察源（全部真实数据）：
    quote_change    最近两次可见行情证据的价格变化（证据层，PIT 可见）
    corporate_event 自上次观察以来的新公司事件（corporate_events 表）

信号规则（强类型、可解释）：
    quote_move      |变化%| ≥ 阈值 → 行情显著变化信号
    new_event       出现新事件 → 新公司事件信号

决策策略（确定性、可解释，§49 全字段落库）：
    任一信号 → research_review（复核研究）；无信号 → research_continue
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.strategy_monitor import (
    DecisionKind,
    DecisionRecordORM,
    ObservationORM,
    SignalORM,
    StrategyMonitorRepository,
    _short_hex,
)
from app.domain.evidence import EvidenceType
from app.storage.orm import EvidenceORM
from app.storage.research_orm import CorporateEventORM

QUOTE_MOVE_THRESHOLD_PCT = 2.0
DEFAULT_INTERVAL_SECONDS = 3600


class StrategyMonitorRefusal(ValueError):
    """Explicit refusal (gate/shape violations are visible, never silent)."""


class StrategyMonitorService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = StrategyMonitorRepository(session)

    # -- definition（§48） ------------------------------------------------------------

    def create_monitor(self, version_id: str, *, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> dict:
        from app.application.strategy import StrategyRepository, StrategyStatus

        version = StrategyRepository(self._session).get_version(version_id)
        if version is None:
            raise KeyError(version_id)
        # §47 输出衔接：只有标记 EXPERIMENTAL 的版本可进入盯盘
        if version["status"] != StrategyStatus.EXPERIMENTAL:
            raise StrategyMonitorRefusal(
                "monitor requires an EXPERIMENTAL strategy version (§47: 未通过验证不可进入正式盯盘)"
            )
        now = datetime.now(timezone.utc)
        row = type(self)._orm(
            version_id=version_id,
            name=f"{version['name']} 盯盘",
            universe=version["universe"],
            interval_seconds=interval_seconds,
            now=now,
        )
        monitor = self._repo.add_monitor(row)
        return monitor

    @staticmethod
    def _orm(*, version_id: str, name: str, universe: list, interval_seconds: int, now: datetime):
        from app.application.strategy_monitor import StrategyMonitorORM

        return StrategyMonitorORM(
            monitor_id=f"mon_{_short_hex()}",
            version_id=version_id,
            name=name,
            universe_json=universe,
            rules_json={
                "quote_move_threshold_pct": QUOTE_MOVE_THRESHOLD_PCT,
                "interval_seconds": interval_seconds,
            },
            enabled=True,
            next_run_at=now,
            created_at=now,
            updated_at=now,
        )

    def list_monitors(self, *, limit: int = 50) -> list[dict]:
        return self._repo.list_monitors(limit=limit)

    def get_monitor(self, monitor_id: str) -> dict | None:
        return self._repo.get_monitor(monitor_id)

    def list_observations(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        return self._repo.list_observations(monitor_id, limit=limit)

    def list_signals(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        return self._repo.list_signals(monitor_id, limit=limit)

    def list_decisions(self, monitor_id: str, *, limit: int = 50) -> list[dict]:
        return self._repo.list_decisions(monitor_id, limit=limit)

    # -- run（观察 → 信号 → 决策） -------------------------------------------------------

    def run_monitor(self, monitor_id: str) -> dict:
        monitor = self._repo.get_monitor(monitor_id)
        if monitor is None:
            raise KeyError(monitor_id)
        if not monitor["enabled"]:
            raise StrategyMonitorRefusal("monitor is paused")

        now = datetime.now(timezone.utc)
        all_observations: list[dict] = []
        all_signals: list[dict] = []
        all_evidence_ids: list[str] = []

        threshold = float(
            (monitor["rules"] or {}).get("quote_move_threshold_pct", QUOTE_MOVE_THRESHOLD_PCT)
        )
        for member in monitor["universe"]:
            instrument_id = member["instrument_id"]
            observations = self._observe(instrument_id, monitor["monitor_id"], now)
            all_observations.extend(observations)
            for obs in observations:
                all_evidence_ids.extend(obs["evidence_ids"])
            signals = self._signalize(observations, monitor["monitor_id"], instrument_id, threshold)
            all_signals.extend(signals)

        decision = self._decide(
            monitor, all_observations, all_signals, all_evidence_ids, now
        )

        row = self._repo.get_monitor_row(monitor_id)
        interval = int((monitor["rules"] or {}).get("interval_seconds", DEFAULT_INTERVAL_SECONDS))
        row.last_run_at = now
        row.next_run_at = now + timedelta(seconds=interval)
        row.updated_at = now
        self._repo.save_monitor(row)
        return {
            "monitor": self._repo.get_monitor(monitor_id),
            "observations": len(all_observations),
            "signals": len(all_signals),
            "decision": decision,
        }

    # -- Observation（§24：系统观察到什么，只来自真实数据） ---------------------------------

    def _observe(self, instrument_id: str, monitor_id: str, now: datetime) -> list[dict]:
        observations: list[dict] = []

        # quote_change: the two newest quote evidences that carry a price
        # (kline evidence is also market_quote-typed but has no price key,
        # so fetch a bounded window and filter in Python)
        quotes = list(
            self._session.scalars(
                select(EvidenceORM)
                .where(
                    EvidenceORM.instrument_id == instrument_id,
                    EvidenceORM.evidence_type == "market_quote",
                )
                .order_by(EvidenceORM.available_time.desc())
                .limit(10)
            ).all()
        )
        prices = [
            (float(e.metadata_json["price"]), e.available_time, e.evidence_id)
            for e in quotes
            if isinstance((e.metadata_json or {}).get("price"), (int, float))
        ][:2]
        if len(prices) == 2:
            (new_price, new_at, new_id), (old_price, _old_at, old_id) = prices
            if old_price > 0:
                change_pct = round((new_price / old_price - 1) * 100, 2)
                observations.append(
                    self._repo.add_observation(
                        ObservationORM(
                            observation_id=f"obs_{_short_hex()}",
                            monitor_id=monitor_id,
                            instrument_id=instrument_id,
                            kind="quote_change",
                            text=f"行情变化：{old_price} → {new_price}（{change_pct:+.2f}%）",
                            payload_json={
                                "old_price": old_price,
                                "new_price": new_price,
                                "change_pct": change_pct,
                            },
                            evidence_ids_json=[new_id, old_id],
                            observed_at=now,
                        )
                    )
                )

        # corporate_event: events announced since the last observation of this kind
        since = self._repo.latest_observation_at(monitor_id, instrument_id, "corporate_event")
        stmt = (
            select(CorporateEventORM)
            .where(CorporateEventORM.instrument_id == instrument_id)
            .order_by(CorporateEventORM.announced_at.desc())
            .limit(10)
        )
        for event in self._session.scalars(stmt).all():
            if since is not None and event.announced_at <= since:
                continue
            observations.append(
                self._append_event_observation(monitor_id, instrument_id, event, now)
            )
        return observations

    def _append_event_observation(self, monitor_id: str, instrument_id: str, event, now: datetime) -> dict:
        return self._repo.add_observation(
            ObservationORM(
                observation_id=f"obs_{_short_hex()}",
                monitor_id=monitor_id,
                instrument_id=instrument_id,
                kind="corporate_event",
                text=f"公司事件：{event.title}",
                payload_json={"event_id": event.event_id, "event_type": event.event_type},
                evidence_ids_json=list(event.evidence_refs_json or []),
                observed_at=now,
            )
        )

    # -- Signal（§24：策略规则产生什么，强类型可解释） --------------------------------------

    def _signalize(self, observations: list[dict], monitor_id: str, instrument_id: str, threshold: float) -> list[dict]:
        signals: list[dict] = []
        for obs in observations:
            if obs["kind"] == "quote_change":
                change = abs(float(obs["payload"].get("change_pct", 0.0)))
                if change >= threshold:
                    signals.append(
                        self._repo.add_signal(
                            SignalORM(
                                signal_id=f"sig_{_short_hex()}",
                                monitor_id=monitor_id,
                                instrument_id=instrument_id,
                                rule_kind="quote_move",
                                strength=round(change, 2),
                                text=f"行情显著变化（|{change:.2f}%| ≥ 阈值 {threshold}%）",
                                observation_ids_json=[obs["observation_id"]],
                                created_at=datetime.now(timezone.utc),
                            )
                        )
                    )
            elif obs["kind"] == "corporate_event":
                signals.append(
                    self._repo.add_signal(
                        SignalORM(
                            signal_id=f"sig_{_short_hex()}",
                            monitor_id=monitor_id,
                            instrument_id=instrument_id,
                            rule_kind="new_event",
                            strength=1.0,
                            text=f"新公司事件信号：{obs['text']}",
                            observation_ids_json=[obs["observation_id"]],
                            created_at=datetime.now(timezone.utc),
                        )
                    )
                )
        return signals

    # -- Decision（§24/§25/§49：最终研究决策，全字段落库） ----------------------------------

    def _decide(
        self, monitor: dict, observations: list[dict], signals: list[dict], evidence_ids: list[str], now: datetime
    ) -> dict:
        if signals:
            decision = DecisionKind.RESEARCH_REVIEW
            confidence = min(0.9, 0.5 + 0.1 * len(signals))
            rationale = (
                f"产生 {len(signals)} 条信号（来源 {len(observations)} 条观察）——"
                "按策略规则需要复核研究状态。决策级别：Research Decision（§25，不涉及真实下单）。"
            )
        else:
            decision = DecisionKind.RESEARCH_CONTINUE
            confidence = 0.6
            rationale = (
                f"无显著信号（{len(observations)} 条观察均未触发规则）——继续观察。"
                "决策级别：Research Decision（§25）。"
            )
        return self._repo.add_decision(
            DecisionRecordORM(
                decision_id=f"dec_{_short_hex()}",
                monitor_id=monitor["monitor_id"],
                version_id=monitor["version_id"],
                decision=decision,
                confidence=confidence,
                rationale=rationale,
                observation_ids_json=[o["observation_id"] for o in observations],
                signal_ids_json=[s["signal_id"] for s in signals],
                evidence_ids_json=list(dict.fromkeys(evidence_ids))[:100],
                as_of=now,
                created_at=now,
            )
        )
