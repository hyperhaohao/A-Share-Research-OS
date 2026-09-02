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
from app.storage.repository import EvidenceRepository
from app.storage.research_orm import CorporateEventORM

def _ensure_utc(v):
    from datetime import timezone as _tz

    return v if (v is None or v.tzinfo is not None) else v.replace(tzinfo=_tz.utc)


QUOTE_MOVE_THRESHOLD_PCT = 2.0
DEFAULT_INTERVAL_SECONDS = 3600

# 盯盘观察源扩展（深度扩展 e）：证据账本驱动的观察种类
# （种类名 → 证据类型值）；新证据（相对上次观察）即成为新观察。
EVIDENCE_OBS_KINDS: dict[str, str] = {
    "announcement": "announcement",
    "news": "news",
    "capital_flow": "capital_flow",
    "macro_change": "macro_indicator",
}
_MAX_PER_KIND = 10


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
        # §47 + §G7.4：EXPERIMENTAL/VALIDATED 均可监控（不再排除 Validated）
        if version["status"] not in (StrategyStatus.EXPERIMENTAL, StrategyStatus.VALIDATED):
            raise StrategyMonitorRefusal(
                "monitor requires EXPERIMENTAL or VALIDATED strategy version "
                "(§47/§G7.4: 未通过验证不可进入正式盯盘)"
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
        # G9（方案 §40）：盯盘注册 Artifact 并 generated_from 策略版本
        from app.application.artifacts import ArtifactService, RelationType

        service = ArtifactService(self._session)
        monitor_artifact = service.register(
            artifact_type="strategy_monitor",
            domain_type="StrategyMonitor",
            domain_id=monitor["monitor_id"],
            title=monitor["name"],
            summary=f"策略盯盘 · universe {len(monitor.get('universe') or [])} 标的",
            instrument_ids=(),
            created_by="strategy_monitor",
            route="/monitoring/" + monitor["monitor_id"],
        )
        strategy_artifact = service.by_domain("StrategyVersion", version_id)
        if strategy_artifact is not None:
            service.link(
                from_artifact_id=monitor_artifact,
                to_artifact_id=strategy_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
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
        """G7（§G7.2/§G7.6/§G7.7）：状态机门 + 执行所引用策略版本规则 +
        Cursor 幂等（同批输入重复运行不产生重复信号）+ 失败持久化。"""
        from app.application.run_events import record_run_event
        from app.application.strategy import StrategyRepository
        from app.services.backtest_engine import BacktestSpec, run_event_backtest
        from app.services.workflow_service import load_daily_bars

        monitor = self._repo.get_monitor(monitor_id)
        if monitor is None:
            raise KeyError(monitor_id)
        row = self._repo.get_monitor_row(monitor_id)
        # §G7.3 状态机：仅 ACTIVE 运行
        if (row.status or "ACTIVE") != "ACTIVE":
            raise StrategyMonitorRefusal(
                f"monitor status={row.status} — only ACTIVE monitors run"
            )

        now = datetime.now(timezone.utc)
        is_first_run = row.quote_cursor is None  # §G7.7：历史回填 vs 实时新信号
        record_run_event(
            self._session, monitor_id, "monitor_started",
            {"version_id": monitor["version_id"], "universe": len(monitor["universe"]),
             "first_run": is_first_run},
        )
        all_observations: list[dict] = []
        all_signals: list[dict] = []
        all_evidence_ids: list[str] = []

        threshold = float(
            (monitor["rules"] or {}).get("quote_move_threshold_pct", QUOTE_MOVE_THRESHOLD_PCT)
        )

        # §G7.2：执行所引用策略版本的真实规则（G6 引擎，per 标的）
        from app.application.strategy import StrategyRepository as _SR

        version = _SR(self._session).get_version(monitor["version_id"])
        strategy_signals: list[dict] = []
        if version is not None:
            entry_policy = dict(version["entry_policy"] or {})
            horizon = int(entry_policy.get("horizon_days") or 20)
            threshold_pct = float(entry_policy.get("threshold_pct") or 0.0)
            cursor = _ensure_utc(row.quote_cursor)
            for member in monitor["universe"]:
                instrument_id = member["instrument_id"]
                bars = load_daily_bars(self._session, instrument_id)
                bars = [b for b in bars if not cursor or b["date"] > cursor.date().isoformat()]
                spec = BacktestSpec(
                    entry_rules=[{"kind": "quote_move",
                                  "pct": threshold_pct, "window": min(horizon, 10)}],
                    exit_rules=[{"kind": "max_hold_days", "days": horizon}],
                )
                try:
                    out = run_event_backtest(bars, spec, include_phases=False)
                except Exception as exc:  # noqa: BLE001 — 无数据等 → 失败持久化
                    row.last_error = f"{type(exc).__name__}: {exc}"[:500]
                    self._repo.save_monitor(row)
                    continue
                if out.get("status") == "INSUFFICIENT_SIGNALS":
                    continue
                for trade in out["trades"]:
                    key = f"{monitor_id}:{instrument_id}:{trade['entry_date']}:{trade['exit_date']}"
                    dup = self._session.scalars(
                        select(SignalORM).where(
                            SignalORM.idempotency_key == key)
                    ).first()
                    if dup is not None:
                        continue  # 幂等：同批输入不重复
                    signal = self._repo.add_signal(SignalORM(
                        signal_id=f"sig_{_short_hex()}",
                        monitor_id=monitor_id,
                        instrument_id=instrument_id,
                        rule_kind="strategy_entry_exit",
                        strength=abs(float(trade["return_pct"])) / 100.0,
                        text=(f"策略规则执行：{trade['entry_date']} 入场 → "
                              f"{trade['exit_date']} 出场（{trade['exit_reason']}，"
                              f"{trade['return_pct']:+.2f}%）"),
                        observation_ids_json=[],
                        created_at=now,
                        direction="long",
                        idempotency_key=key,
                    ))
                    strategy_signals.append(signal)
        else:
            raise StrategyMonitorRefusal(
                f"strategy version missing: {monitor['version_id']}")

        for member in monitor["universe"]:
            instrument_id = member["instrument_id"]
            observations = self._observe(instrument_id, monitor["monitor_id"], now)
            all_observations.extend(observations)
            for obs in observations:
                all_evidence_ids.extend(obs["evidence_ids"])
            signals = self._signalize(observations, monitor["monitor_id"], instrument_id, threshold)
            all_signals.extend(signals)

        all_signals.extend(strategy_signals)

        decision = self._decide(
            monitor, all_observations, all_signals, all_evidence_ids, now
        )

        row = self._repo.get_monitor_row(monitor_id)
        interval = int((monitor["rules"] or {}).get("interval_seconds", DEFAULT_INTERVAL_SECONDS))
        row.last_run_at = now
        row.next_run_at = now + timedelta(seconds=interval)
        # §G7.6 Cursor：行情 Cursor = 本次运行时间（下次只看增量）
        row.quote_cursor = now
        row.evidence_cursor = now
        row.updated_at = now
        self._repo.save_monitor(row)
        record_run_event(
            self._session, monitor_id, "monitor_completed",
            {"observations": len(all_observations), "signals": len(all_signals),
             "strategy_signals": len(strategy_signals),
             "decision": decision["decision"], "first_run": is_first_run},
        )
        return {
            "monitor": self._repo.get_monitor(monitor_id),
            "observations": len(all_observations),
            "signals": len(all_signals),
            "strategy_signals": len(strategy_signals),
            "decision": decision,
        }

    # -- G7 状态机（§G7.3：ACTIVE↔PAUSED→RETIRED；FAILED 保留） ----------------

    def set_status(self, monitor_id: str, new_status: str) -> dict:
        from app.application.run_events import record_run_event

        row = self._repo.get_monitor_row(monitor_id)
        if row is None:
            raise KeyError(monitor_id)
        allowed = {
            "ACTIVE": {"PAUSED", "RETIRED"},
            "PAUSED": {"ACTIVE", "RETIRED"},
            "RETIRED": set(),
        }
        current = row.status or "ACTIVE"
        if new_status not in allowed.get(current, set()):
            raise StrategyMonitorRefusal(
                f"cannot transition {current} → {new_status} (§G7.3)"
            )
        row.status = new_status
        row.enabled = new_status == "ACTIVE"
        row.updated_at = datetime.now(timezone.utc)
        self._repo.save_monitor(row)
        record_run_event(
            self._session, monitor_id, "monitor_status_changed",
            {"from": current, "to": new_status},
        )
        return self._repo.get_monitor(monitor_id)

    # -- Observation（§24：系统观察到什么，只来自真实数据） ---------------------------------

    def _observe(self, instrument_id: str, monitor_id: str, now: datetime) -> list[dict]:
        observations: list[dict] = []
        all_evidence = EvidenceRepository(self._session).list_for_instrument(
            instrument_id, visible_at=now
        )

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

        # 证据账本驱动的观察（§48：新公告/新新闻/资金变化/宏观变化）
        for obs_kind, evidence_type_value in EVIDENCE_OBS_KINDS.items():
            since = self._repo.latest_observation_at(monitor_id, instrument_id, obs_kind)
            new_items = [
                e
                for e in all_evidence
                if e.evidence_type.value == evidence_type_value
                and (since is None or e.available_time > since)
            ]
            new_items.sort(key=lambda e: e.available_time, reverse=True)
            for item in new_items[:_MAX_PER_KIND]:
                observations.append(
                    self._repo.add_observation(
                        ObservationORM(
                            observation_id=f"obs_{_short_hex()}",
                            monitor_id=monitor_id,
                            instrument_id=instrument_id,
                            kind=obs_kind,
                            text=f"{item.title}",
                            payload_json={"evidence_type": evidence_type_value},
                            evidence_ids_json=[item.evidence_id],
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
            elif obs["kind"] in ("corporate_event", "announcement", "news", "capital_flow", "macro_change"):
                rule_kind = f"new_{obs['kind']}"
                label = {
                    "corporate_event": "新公司事件信号",
                    "announcement": "新公告信号",
                    "news": "新新闻信号",
                    "capital_flow": "资金变化信号",
                    "macro_change": "宏观变化信号",
                }.get(obs["kind"], "新观察信号")
                signals.append(
                    self._repo.add_signal(
                        SignalORM(
                            signal_id=f"sig_{_short_hex()}",
                            monitor_id=monitor_id,
                            instrument_id=instrument_id,
                            rule_kind=rule_kind,
                            strength=1.0,
                            text=f"{label}：{obs['text']}",
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
        # F4（任务书 §7.1）：决策置信度由可解释因素计算（信号数/观察数/
        # 证据信任层），替代固定公式 min(0.9, 0.5+0.1*signals) 与固定 0.6
        from app.domain.confidence import compute_claim_confidence
        from app.domain.source_trust import trust_for_evidence
        from app.storage.orm import EvidenceORM
        from sqlalchemy import select as _select

        ev_rows = (
            self._session.scalars(
                _select(EvidenceORM).where(EvidenceORM.evidence_id.in_(evidence_ids[:50]))
            ).all()
            if evidence_ids
            else []
        )
        trusts = [
            trust_for_evidence(r.authority_level, r.evidence_type).value for r in ev_rows
        ]

        if signals:
            decision = DecisionKind.RESEARCH_REVIEW
            outcome = compute_claim_confidence(
                supporting_trusts=trusts or ["T4_social_unverified"],
                corroboration_groups=len(signals),
                directness="derived",
            )
            confidence = min(0.9, outcome.value)
            basis_note = (
                f"置信度 basis: model={outcome.model_version} "
                f"trust={outcome.basis['source_trust']} "
                f"signals(独立组)={len(signals)} → {outcome.value}/{outcome.level}"
            )
            rationale = (
                f"产生 {len(signals)} 条信号（来源 {len(observations)} 条观察）——"
                "按策略规则需要复核研究状态。决策级别：Research Decision（§25，不涉及真实下单）。"
                f"{basis_note}"
            )
        else:
            decision = DecisionKind.RESEARCH_CONTINUE
            # 无信号 → 继续观察决策的置信度反映「观察证据对现状的支撑度」，
            # 由观察证据信任层计算（无证据时诚实给 insufficient 级）
            outcome = compute_claim_confidence(
                supporting_trusts=trusts,
                directness="derived",
            )
            confidence = outcome.value
            basis_note = (
                f"置信度 basis: model={outcome.model_version} "
                f"trust={outcome.basis.get('source_trust')} "
                f"observations={len(observations)} → {outcome.value}/{outcome.level}"
            )
            rationale = (
                f"无显著信号（{len(observations)} 条观察均未触发规则）——继续观察。"
                "决策级别：Research Decision（§25）。"
                f"{basis_note}"
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
