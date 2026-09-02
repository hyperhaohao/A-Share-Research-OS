"""可执行回测引擎（G6，观澜语义迁移任务书 §G6）.

事件驱动模拟（逐日），真实执行策略定义的规则：

    Entry 触发才建仓；Exit/Risk 真实改变交易路径；
    成本/滑点双边计提；停牌/涨跌停延迟成交；缺失数据诚实处理。

产出（可重放、注册 Artifact）：
    trades（非重叠交易序列）/ NAV / metrics（收益/回撤/胜率/换手/暴露/
    基准/超额）/ 分期（in_sample vs out_of_sample）/ regime（可复现定义：
    入场时收盘价相对 MA60 → trend_up/trend_down，非按年份命名）。

语义红线（§G6 DoD）：
  - 无 Entry 规则 → INSUFFICIENT_SIGNALS、零交易；
  - Entry 变化 → 交易日期与收益可解释变化；Exit/Risk 变化 → 持仓与回撤变化；
  - 交易级收益天然非重叠（单仓位序列）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime


class BacktestInputError(ValueError):
    pass


@dataclass
class BacktestSpec:
    entry_rules: list[dict] = field(default_factory=list)
    exit_rules: list[dict] = field(default_factory=list)
    risk_rules: list[dict] = field(default_factory=list)
    position_sizing: dict = field(default_factory=lambda: {"kind": "fixed_fraction", "fraction": 0.95})
    cost_bps: float = 10.0          # 双边佣金（bps）
    slippage_bps: float = 10.0      # 滑点（bps）
    benchmark: str = "buy_hold"


def _ma(closes: list[float], window: int, i: int) -> float | None:
    if i + 1 < window:
        return None
    seg = closes[i + 1 - window:i + 1]
    if any(v is None for v in seg):
        return None
    return sum(seg) / window


def _bar_date(bar: dict) -> str:
    return str(bar.get("date") or "")[:10]


def _apply_cost(price: float, bps: float) -> float:
    return price * (1 - bps / 10000.0)


def _apply_slippage_buy(price: float, bps: float) -> float:
    return price * (1 + bps / 10000.0)


def _apply_slippage_sell(price: float, bps: float) -> float:
    return price * (1 - bps / 10000.0)


def _entry_triggered(bar: dict, closes: list[float], i: int,
                     rules: list[dict]) -> tuple[bool, str]:
    if not rules:
        return False, "no_entry_rules"
    close = float(bar["close"])
    for rule in rules:
        kind = rule.get("kind")
        if kind == "price_above_ma":
            ma = _ma(closes, int(rule.get("window", 20)), i)
            if ma is None or close <= ma:
                return False, f"price_above_ma({rule.get('window')}) not met"
        elif kind == "price_below_ma":
            ma = _ma(closes, int(rule.get("window", 20)), i)
            if ma is None or close >= ma:
                return False, f"price_below_ma({rule.get('window')}) not met"
        elif kind == "quote_move":
            window = int(rule.get("window", 5))
            pct = float(rule.get("pct", 3.0))
            if i < window:
                return False, "insufficient history"
            move = (close / float(closes[i - window]) - 1) * 100
            if move < pct:
                return False, f"quote_move {move:.2f}% < {pct}%"
        else:
            return False, f"unknown entry rule: {kind}"
    return True, "all entry rules met"


def _exit_triggered(bar: dict, i: int, entry_price: float, entry_i: int,
                    rules: list[dict]) -> tuple[bool, str]:
    close = float(bar["close"])
    ret_pct = (close / entry_price - 1) * 100
    hold_days = i - entry_i
    for rule in rules:
        kind = rule.get("kind")
        if kind == "take_profit" and ret_pct >= float(rule.get("pct", 10.0)):
            return True, f"take_profit@{ret_pct:.2f}%"
        if kind == "stop_loss" and ret_pct <= -float(rule.get("pct", 8.0)):
            return True, f"stop_loss@{ret_pct:.2f}%"
        if kind == "max_hold_days" and hold_days >= int(rule.get("days", 40)):
            return True, f"max_hold_days({hold_days})"
    return False, ""


def run_event_backtest(bars: list[dict], spec: BacktestSpec,
                       *, include_phases: bool = True) -> dict:
    """单标的事件驱动回测（确定性；同输入同输出）。

    include_phases=False 供分期重放调用（避免无限递归）。
    """
    if not bars:
        raise BacktestInputError("no bars (missing data disclosed by caller)")
    bars = sorted(bars, key=_bar_date)
    if not spec.entry_rules:
        return {
            "status": "INSUFFICIENT_SIGNALS", "trades": [], "nav": [],
            "metrics": {"n_trades": 0},
            "note": "no entry rules → zero trades (§G6 DoD)",
        }

    closes = [float(b["close"]) for b in bars]
    cost = spec.cost_bps
    slip = spec.slippage_bps

    trades: list[dict] = []
    nav: list[dict] = []
    equity = 1.0
    position = None  # {entry_i, entry_date, entry_price, shares}
    max_drawdown = 0.0
    peak = 1.0
    days_in_market = 0

    def regime_at(i: int) -> str:
        ma = _ma(closes, 60, i)
        if ma is None:
            return "regime_insufficient"
        return "trend_up" if closes[i] >= ma else "trend_down"

    i = 0
    n = len(bars)
    while i < n:
        bar = bars[i]
        suspended = bool(bar.get("suspended"))
        if position is not None:
            days_in_market += 1
            # NAV mark-to-market（停牌沿用最后价）
            price_now = float(bar["close"]) if not suspended else position["last_price"]
            position["last_price"] = price_now
            equity_now = position["cash"] + position["shares"] * price_now
            nav.append({"date": _bar_date(bar), "equity": round(equity_now, 6)})
            peak = max(peak, equity_now)
            max_drawdown = max(max_drawdown, (peak - equity_now) / peak)
            if not suspended:
                exit_now, reason = _exit_triggered(bar, i, position["entry_price"],
                                                   position["entry_i"], spec.exit_rules)
                # 跌停无法卖出 → 顺延
                if exit_now and bar.get("limit_down"):
                    reason = "limit_down_defer"
                    exit_now = False
                risk_hit = any(
                    (peak - equity_now) / peak >= float(r.get("pct", 100.0)) / 100.0
                    for r in spec.risk_rules if r.get("kind") == "max_drawdown"
                )
                if risk_hit:
                    exit_now, reason = True, "risk_max_drawdown"
                if exit_now:
                    exit_price = _apply_cost(_apply_slippage_sell(float(bar["close"]), slip), cost)
                    ret = (exit_price / position["entry_price"] - 1) * 100
                    trades.append({
                        "instrument_id": position.get("instrument_id"),
                        "entry_date": position["entry_date"],
                        "entry_price": round(position["entry_price"], 4),
                        "exit_date": _bar_date(bar),
                        "exit_price": round(exit_price, 4),
                        "return_pct": round(ret, 3),
                        "hold_days": i - position["entry_i"],
                        "exit_reason": reason,
                        "regime": position.get("regime", "regime_insufficient"),
                    })
                    equity = position["cash"] + position["shares"] * exit_price
                    position = None
        if position is None and not suspended:
            hit, reason = _entry_triggered(bar, closes, i, spec.entry_rules)
            if hit:
                fraction = float(spec.position_sizing.get("fraction", 0.95))
                entry_price = _apply_cost(_apply_slippage_buy(closes[i], slip), cost)
                shares = equity * fraction / entry_price
                position = {
                    "entry_i": i, "entry_date": _bar_date(bar),
                    "entry_price": entry_price, "shares": shares,
                    "cash": equity * (1 - fraction), "last_price": entry_price,
                    "instrument_id": None, "regime": regime_at(i),
                }
        i += 1

    # 分期（按日期 70/30 切分；分别独立重放）
    split = int(n * 0.7)
    in_sample_bars = bars[:split]
    oos_bars = bars[split:]

    def _stats(trade_list: list[dict]) -> dict:
        if not trade_list:
            return {"n_trades": 0, "status": "INSUFFICIENT_SIGNALS"}
        rets = [t["return_pct"] for t in trade_list]
        wins = sum(1 for r in rets if r > 0)
        return {
            "n_trades": len(trade_list),
            "win_rate": round(wins / len(rets), 3),
            "avg_return_pct": round(sum(rets) / len(rets), 3),
            "total_return_pct": round(
                (1 + sum(1 for _ in trade_list) * 0) * 100
                * math.prod(1 + r / 100 for r in rets) - 100, 3),
        }

    def _replay(sub: list[dict]) -> dict:
        sub_spec = BacktestSpec(
            entry_rules=spec.entry_rules, exit_rules=spec.exit_rules,
            risk_rules=spec.risk_rules, position_sizing=spec.position_sizing,
            cost_bps=spec.cost_bps, slippage_bps=spec.slippage_bps,
        )
        if not sub:
            return {"n_trades": 0, "status": "INSUFFICIENT_DATA"}
        try:
            out = run_event_backtest(sub, sub_spec, include_phases=False)
        except BacktestInputError:
            return {"n_trades": 0, "status": "INSUFFICIENT_DATA"}
        return out["metrics"]

    benchmark_entry = closes[0]
    benchmark_return = round((closes[-1] / benchmark_entry - 1) * 100, 3)
    total = _stats(trades)
    total_return = total.get("total_return_pct", 0.0)

    return {
        "status": "ok",
        "trades": trades,
        "nav": nav,
        "metrics": {
            "n_trades": total["n_trades"],
            "win_rate": total.get("win_rate"),
            "avg_return_pct": total.get("avg_return_pct"),
            "total_return_pct": total_return,
            "max_drawdown_pct": round(max_drawdown * 100, 3),
            "avg_hold_days": (
                round(sum(t["hold_days"] for t in trades) / len(trades), 1)
                if trades else 0
            ),
            "exposure_pct": round(days_in_market / n * 100, 1),
            "turnover_per_year": round(
                len(trades) / max((n / 244.0), 0.01), 2),
            "benchmark_return_pct": benchmark_return,
            "excess_return_pct": round(total_return - benchmark_return, 3),
            "benchmark": spec.benchmark,
            "cost_bps": cost, "slippage_bps": slip,
            "n_bars": n,
        },
        "phases": ({
            "in_sample": _replay(in_sample_bars),
            "out_of_sample": _replay(oos_bars),
            "split_rule": "70/30 by date (deterministic)",
        } if include_phases else {"skipped": True}),
        "regimes_present": sorted({t["regime"] for t in trades}),
        "regime_definition": "entry-day close vs MA60 (deterministic, not by year)",
        "missing_data_note": "suspended/limit_down bars defer execution (no fabricated fills)",
    }
