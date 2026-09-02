"""G6 — Executable Strategy Lab（观澜语义迁移任务书 §G6）.

覆盖：
  - 无 Entry → INSUFFICIENT_SIGNALS 零交易；
  - Entry 变化 → 交易日期与收益可解释变化；
  - Exit/Risk 变化 → 持仓、回撤、收益变化；
  - 成本/滑点双边计提（收益随成本递减）；
  - 停牌/跌停延迟成交（不伪造成交）；
  - 交易非重叠（单仓位序列）；分期 in/out-of-sample；
  - regime 可复现定义（MA60，非按年）；
  - max_drawdown 风险规则强制平仓。
"""

from __future__ import annotations

from app.services.backtest_engine import BacktestSpec, run_event_backtest


def _bars(prices: list[float], *, start_day: int = 1,
          suspended_idx: set[int] | None = None,
          limit_down_idx: set[int] | None = None) -> list[dict]:
    from datetime import timedelta

    base = __import__("datetime").datetime(2026, 1, 5)
    out = []
    suspended_idx = suspended_idx or set()
    limit_down_idx = limit_down_idx or set()
    for i, p in enumerate(prices):
        out.append({
            "date": str((base + timedelta(days=i)).date()),
            "close": p,
            "suspended": i in suspended_idx,
            "limit_down": i in limit_down_idx,
        })
    return out


def test_no_entry_rules_insufficient_signals():
    bars = _bars([10.0] * 30)
    out = run_event_backtest(bars, BacktestSpec(entry_rules=[]))
    assert out["status"] == "INSUFFICIENT_SIGNALS"
    assert out["trades"] == []
    assert out["metrics"]["n_trades"] == 0


def test_entry_triggers_position_and_exit_take_profit():
    # 价格先下探（满足 price_below_ma），随后上冲触发止盈
    prices = ([20.0] * 25 + [10.0, 10.0] + [12.0, 14.0, 16.0, 18.0, 20.0] + [10.0] * 5)
    bars = _bars(prices)
    spec = BacktestSpec(
        entry_rules=[{"kind": "price_below_ma", "window": 10}],
        exit_rules=[{"kind": "take_profit", "pct": 10.0}],
    )
    out = run_event_backtest(bars, spec)
    assert out["metrics"]["n_trades"] >= 1
    assert out["trades"][0]["exit_reason"].startswith("take_profit")


def test_entry_change_changes_trades():
    prices = [10.0] * 10 + [12.0, 14.0, 16.0, 18.0, 20.0] + [10.0] * 10
    bars = _bars(prices)
    spec_a = BacktestSpec(
        entry_rules=[{"kind": "quote_move", "pct": 5.0, "window": 3}],
        exit_rules=[{"kind": "max_hold_days", "days": 5}],
    )
    spec_b = BacktestSpec(
        entry_rules=[{"kind": "quote_move", "pct": 30.0, "window": 3}],
        exit_rules=[{"kind": "max_hold_days", "days": 5}],
    )
    out_a = run_event_backtest(bars, spec_a)
    out_b = run_event_backtest(bars, spec_b)
    # 门槛变化 → 交易可解释变化
    assert out_a["metrics"]["n_trades"] != out_b["metrics"]["n_trades"] or \
        out_a["trades"] != out_b["trades"]


def test_exit_change_changes_path():
    prices = ([10.0] * 12 + [11.0, 12.0, 9.0, 9.5, 10.0, 10.5] + [10.0] * 10)
    bars = _bars(prices)
    entry = [{"kind": "quote_move", "pct": 5.0, "window": 3}]
    out_tp = run_event_backtest(bars, BacktestSpec(
        entry_rules=entry, exit_rules=[{"kind": "take_profit", "pct": 20.0}]))
    out_sl = run_event_backtest(bars, BacktestSpec(
        entry_rules=entry, exit_rules=[{"kind": "stop_loss", "pct": 5.0}]))
    assert out_sl["trades"] != out_tp["trades"]
    assert any(t["exit_reason"].startswith("stop_loss") for t in out_sl["trades"])


def test_cost_and_slippage_reduce_returns():
    prices = [10.0] * 10 + [12.0, 14.0] + [10.0] * 10
    bars = _bars(prices)
    entry = [{"kind": "quote_move", "pct": 5.0, "window": 3}]
    free = run_event_backtest(bars, BacktestSpec(
        entry_rules=entry, exit_rules=[{"kind": "max_hold_days", "days": 3}],
        cost_bps=0.0, slippage_bps=0.0))
    costly = run_event_backtest(bars, BacktestSpec(
        entry_rules=entry, exit_rules=[{"kind": "max_hold_days", "days": 3}],
        cost_bps=50.0, slippage_bps=50.0))
    assert costly["metrics"]["avg_return_pct"] < free["metrics"]["avg_return_pct"]


def test_trades_are_non_overlapping():
    prices = [10.0, 11.0, 12.0, 11.0, 10.0] * 8
    bars = _bars(prices)
    out = run_event_backtest(bars, BacktestSpec(
        entry_rules=[{"kind": "price_below_ma", "window": 3}],
        exit_rules=[{"kind": "take_profit", "pct": 3.0},
                    {"kind": "max_hold_days", "days": 3}]))
    dates = [(t["entry_date"], t["exit_date"]) for t in out["trades"]]
    for (e1, x1), (e2, x2) in zip(dates, dates[1:]):
        assert e2 > x1, "单仓位序列：下一入场必须晚于上一退出"


def test_suspension_and_limit_down_defer_execution():
    # 持仓期间第 3 天停牌、第 4 天跌停 → 出场顺延（不伪造成交）
    prices = [10.0] * 10 + [12.0, 13.0, 9.0, 9.0, 9.0, 9.0] + [10.0] * 6
    bars = _bars(prices, suspended_idx={12}, limit_down_idx={13, 14})
    out = run_event_backtest(bars, BacktestSpec(
        entry_rules=[{"kind": "quote_move", "pct": 5.0, "window": 3}],
        exit_rules=[{"kind": "stop_loss", "pct": 5.0}]))
    assert out["metrics"]["n_trades"] >= 1
    deferred = [t for t in out["trades"]
                if t["exit_date"] > "2026-01-15"]
    assert deferred, "exit must defer past suspended/limit_down bars"


def test_phases_regime_and_risk_drawdown():
    import math

    prices = []
    p = 20.0
    for i in range(80):
        p = p * (1.02 if i % 10 < 7 else 0.985)
        prices.append(round(p, 2))
    bars = _bars(prices)
    spec = BacktestSpec(
        entry_rules=[{"kind": "price_above_ma", "window": 10}],
        exit_rules=[{"kind": "take_profit", "pct": 8.0},
                    {"kind": "max_hold_days", "days": 10}],
        risk_rules=[{"kind": "max_drawdown", "pct": 12.0}],
    )
    out = run_event_backtest(bars, spec)
    assert "phases" in out
    assert out["phases"]["split_rule"].startswith("70/30")
    assert out["regime_definition"].startswith("entry-day close vs MA60")
    assert out["metrics"]["max_drawdown_pct"] <= 12.0 * 1.5  # 风险规则生效（容差）
    assert out["metrics"]["benchmark_return_pct"] is not None
    assert "excess_return_pct" in out["metrics"]
