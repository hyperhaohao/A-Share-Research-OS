"""Strategy Lab API (V2 Phase F, 总纲 §46/§47)."""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.strategy import StrategyRepository
from app.core.errors import AppError
from app.db import get_session, session_scope
from app.services.strategy_service import StrategyRefusal, StrategyService

router = APIRouter(prefix="/strategies", tags=["strategy"])


class StrategyFromScreeningIn(BaseModel):
    screening_run_id: str = Field(min_length=6, max_length=32)
    name: str | None = Field(default=None, max_length=128)


def _execute_backtest_in_background(engine, backtest_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        backtest = StrategyRepository(worker_session).get_backtest(backtest_id)
        if backtest is None:
            return
        try:
            StrategyService(worker_session).run_backtest_from_backtest(backtest)
        except Exception:  # noqa: BLE001 — never kill the process on a backtest
            worker_session.rollback()
            StrategyRepository(worker_session).update_backtest(
                backtest_id, lambda p: {**p, "status": "failed", "error": "backtest crashed"}
            )


@router.post("/from-screening", status_code=201)
def create_from_screening(payload: StrategyFromScreeningIn, session: Session = Depends(get_session)) -> dict:
    try:
        version = StrategyService(session).create_from_screening(
            payload.screening_run_id, payload.name
        )
    except KeyError:
        raise AppError("screening.not_found", status_code=404) from None
    except StrategyRefusal as exc:
        raise AppError("strategy.unassemblable", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"strategy": version}


@router.get("")
def list_strategies(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = StrategyService(session).list_versions(limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{version_id}")
def get_strategy(version_id: str, session: Session = Depends(get_session)) -> dict:
    detail = StrategyService(session).get_version_detail(version_id)
    if detail is None:
        raise AppError("strategy.not_found", status_code=404)
    return {"strategy": detail}


@router.post("/{version_id}/backtest", status_code=202)
def launch_backtest(version_id: str, session: Session = Depends(get_session)) -> dict:
    service = StrategyService(session)
    if service.get_version_detail(version_id) is None:
        raise AppError("strategy.not_found", status_code=404)
    backtest = service.start_backtest(version_id)
    session.commit()
    thread = threading.Thread(
        target=_execute_backtest_in_background,
        args=(session.get_bind(), backtest["backtest_id"]),
        daemon=True,
    )
    thread.start()
    return {"backtest": backtest}


@router.get("/backtests/{backtest_id}")
def get_backtest(backtest_id: str, session: Session = Depends(get_session)) -> dict:
    backtest = StrategyRepository(session).get_backtest(backtest_id)
    if backtest is None:
        raise AppError("strategy.not_found", status_code=404)
    return {"backtest": backtest}


@router.get("/backtests/{backtest_id}/events")
def backtest_events(backtest_id: str, session: Session = Depends(get_session)) -> dict:
    from app.application.run_events import list_run_events

    results = list_run_events(session, backtest_id)
    if not results:
        raise AppError("strategy.events_not_found", status_code=404)
    return {"backtest_id": backtest_id, "count": len(results), "results": results}


@router.post("/{version_id}/validate")
def validate_strategy(version_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        version = StrategyService(session).validate_version(version_id)
    except KeyError:
        raise AppError("strategy.not_found", status_code=404) from None
    except StrategyRefusal as exc:
        raise AppError("strategy.validation_blocked", status_code=422, detail=str(exc)) from None
    return {"strategy": version}


# ── G6：可执行回测 v2（事件驱动，真实 Entry/Exit/Risk 执行） ─────────────────


@router.post("/{version_id}/backtest-v2", status_code=202)
def run_backtest_v2(version_id: str, session: Session = Depends(get_session)) -> dict:
    """事件驱动回测：执行版本 Entry/Exit/Risk 规则（成本/滑点/停牌/涨跌停）。

    Entry 规则缺失 → INSUFFICIENT_SIGNALS 零交易（§G6 DoD，不冒充回测）。
    结果（trades/NAV/metrics/分期/regime）落 StrategyBacktestRun + Artifact。
    """
    from app.application.strategy import (
        BacktestStatus,
        StrategyBacktestRunORM,
        StrategyRepository,
    )
    from app.core.errors import AppError
    from datetime import datetime as _dt, timezone as _tz
    from uuid import uuid4 as _uuid4

    version = StrategyRepository(session).get_version(version_id)
    if version is None:
        raise AppError("strategy.version_not_found", status_code=404) from None

    entry_policy = dict(version["entry_policy"] or {})
    exit_policy = dict(version["exit_policy"] or {})
    risk_policy = dict(version["risk_policy"] or {})
    horizon = int(entry_policy.get("horizon_days") or 20)
    threshold = float(entry_policy.get("threshold_pct") or 0.0)
    # 现有 entry_policy 语义（forward_return 阈值）→ G6 入场规则转换（可解释）
    # entry_rules 显式空列表 = 无入场（INSUFFICIENT_SIGNALS）；缺省才转换默认
    if "entry_rules" in entry_policy:
        entry_rules = list(entry_policy["entry_rules"])
    else:
        entry_rules = [{"kind": "quote_move", "pct": threshold,
                        "window": min(horizon, 10)}]
    exit_rules = exit_policy.get("exit_rules") or [
        {"kind": "max_hold_days", "days": horizon}
    ]
    risk_rules = risk_policy.get("risk_rules") or [
        {"kind": "max_drawdown", "pct": float(risk_policy.get("max_drawdown_pct", 15.0))}
    ]

    from app.services.backtest_engine import BacktestSpec, BacktestInputError, run_event_backtest

    spec = BacktestSpec(
        entry_rules=entry_rules, exit_rules=exit_rules, risk_rules=risk_rules,
        cost_bps=float(risk_policy.get("cost_bps", 10.0)),
        slippage_bps=float(risk_policy.get("slippage_bps", 10.0)),
    )

    from app.services.workflow_service import load_daily_bars

    results = []
    aggregate_trades = 0
    aggregate_returns = []
    failure_cases = []
    for member in version["universe"]:
        instrument_id = member["instrument_id"] if isinstance(member, dict) else str(member)
        bars = load_daily_bars(session, instrument_id)
        try:
            out = run_event_backtest(bars, spec)
        except BacktestInputError as exc:
            failure_cases.append({"instrument_id": instrument_id,
                                  "reason": str(exc)})
            continue
        results.append({"instrument_id": instrument_id, **out})
        aggregate_trades += out["metrics"]["n_trades"]
        aggregate_returns.extend(t["return_pct"] for t in out["trades"])

    n_ok = len(results)
    aggregate = {
        "engine": "event_backtest_v1",
        "entry_rules": entry_rules, "exit_rules": exit_rules,
        "risk_rules": risk_rules,
        "n_instruments_ok": n_ok,
        "n_trades_total": aggregate_trades,
        "mean_trade_return_pct": (
            round(sum(aggregate_returns) / len(aggregate_returns), 3)
            if aggregate_returns else None
        ),
        "combined_phase_metrics": [
            {**r["metrics"], "instrument_id": r["instrument_id"]}
            for r in results
        ][:10],
    }

    row = StrategyBacktestRunORM(
        backtest_id=f"bt_{_uuid4().hex[:12]}",
        version_id=version_id,
        results_json=results,
        aggregate_json=aggregate,
        failure_cases_json=failure_cases,
        status=BacktestStatus.COMPLETED,
        created_at=_dt.now(_tz.utc),
        updated_at=_dt.now(_tz.utc),
    )
    session.add(row)
    session.flush()

    artifact_id = None
    try:
        from app.application.artifacts import ArtifactService

        artifact_id = ArtifactService(session).register(
            artifact_type="strategy_backtest",
            domain_type="StrategyBacktest",
            domain_id=row.backtest_id,
            title=f"可执行回测 {version['name']} v{version['version_no']}",
            instrument_ids=(),
            created_by="backtest_v2",
            route="/strategy",
            metadata={"n_trades_total": aggregate_trades,
                      "entry_rules": entry_rules},
        )
    except Exception as exc:  # noqa: BLE001 — 显形 INCOMPLETE_PROVENANCE
        aggregate["provenance_status"] = "INCOMPLETE_PROVENANCE"
        aggregate["provenance_error"] = f"{type(exc).__name__}: {exc}"[:200]
    row.aggregate_json = aggregate
    session.flush()

    if aggregate_trades == 0 and not entry_policy.get("entry_rules"):
        aggregate["status"] = "INSUFFICIENT_SIGNALS"
        row.aggregate_json = aggregate
        session.flush()

    return {
        "backtest_id": row.backtest_id,
        "aggregate": aggregate,
        "n_instruments": len(results),
        "failure_cases": failure_cases,
        "artifact_id": artifact_id,
    }
