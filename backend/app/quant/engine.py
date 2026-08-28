"""Deterministic quant engine (整改 R3.5, 方案 A).

Real quant loop inside the formal system:

    Instrument → Historical bars (Eastmoney kline capability) →
    Factors (5d/20d momentum, 20d volatility) → Score/signal (momentum
    sign, evaluated on t-1 to avoid lookahead) → Backtest (long/flat) →
    Metrics (total return, annualized, sharpe, max drawdown, win rate,
    vs buy&hold) → QuantBrief → Research State

All math is pure and covered by fixed-number tests; the design follows the
TideTrading backtest layout adopted in ADR-001 (loaders → engines → metrics).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Bar:
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    turnover: float | None = None


@dataclass
class QuantMetrics:
    strategy_total_return_pct: float
    buyhold_total_return_pct: float
    annualized_return_pct: float
    sharpe: float
    max_drawdown_pct: float
    win_rate_pct: float
    invested_days: int
    n_days: int


def _daily_returns(closes: list[float]) -> list[float]:
    return [
        closes[i] / closes[i - 1] - 1
        for i in range(1, len(closes))
        if closes[i - 1] != 0
    ]


def momentum(closes: list[float], window: int) -> list[float | None]:
    """close_t / close_{t-window} − 1; None until the window fills."""
    out: list[float | None] = []
    for i in range(len(closes)):
        if i < window or closes[i - window] == 0:
            out.append(None)
        else:
            out.append(closes[i] / closes[i - window] - 1)
    return out


def volatility(daily_returns: list[float], window: int) -> list[float | None]:
    """Rolling std-dev of daily returns over the last ``window`` days."""
    out: list[float | None] = []
    for i in range(len(daily_returns)):
        if i + 1 < window:
            out.append(None)
            continue
        window_slice = daily_returns[i + 1 - window : i + 1]
        mean = sum(window_slice) / window
        var = sum((r - mean) ** 2 for r in window_slice) / window
        out.append(math.sqrt(var))
    return out


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 1.0
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1)
    return worst * 100


def run_backtest(bars: list[Bar], *, momentum_window: int = 5) -> dict:
    """Long/flat momentum backtest.

    Signal: position_t = 1 if momentum_5(t-1) > 0 else 0 (decided on the
    previous day's close — no lookahead). Strategy daily return =
    position_{t-1} × market return_t. When flat, cash earns 0.
    """
    n = len(bars)
    if n < momentum_window + 2:
        raise ValueError(f"need at least {momentum_window + 2} bars, got {n}")

    closes = [b.close for b in bars]
    mom = momentum(closes, momentum_window)
    returns = _daily_returns(closes)  # aligned with bars[1:]

    equity = 1.0
    curve: list[float] = [1.0]
    strategy_returns: list[float] = []
    buyhold_returns = returns
    invested_days = 0
    wins = 0

    for i in range(1, n):
        signal = mom[i - 1]
        position = 1 if (signal is not None and signal > 0) else 0
        r = returns[i - 1]
        strategy_r = position * r
        strategy_returns.append(strategy_r)
        equity *= 1 + strategy_r
        curve.append(equity)
        if position:
            invested_days += 1
            if strategy_r > 0:
                wins += 1

    total = (equity - 1) * 100
    buyhold_equity = closes[-1] / closes[0]
    buyhold_total = (buyhold_equity - 1) * 100

    days = len(strategy_returns)
    annualized = ((1 + total / 100) ** (252 / days) - 1) * 100 if days else 0.0
    mean_r = sum(strategy_returns) / days if days else 0.0
    var = (
        sum((r - mean_r) ** 2 for r in strategy_returns) / days
        if days
        else 0.0
    )
    std = math.sqrt(var)
    sharpe = (mean_r / std) * math.sqrt(252) if std > 0 else 0.0

    return {
        "strategy_total_return_pct": round(total, 4),
        "buyhold_total_return_pct": round(buyhold_total, 4),
        "annualized_return_pct": round(annualized, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown_pct": round(max_drawdown(curve), 4),
        "win_rate_pct": round(wins / invested_days * 100, 2) if invested_days else 0.0,
        "invested_days": invested_days,
        "n_days": days,
        "momentum_window": momentum_window,
        "start_date": bars[0].date,
        "end_date": bars[-1].date,
    }


def factor_snapshot(bars: list[Bar]) -> dict:
    """Latest factor values for the research state."""
    closes = [b.close for b in bars]
    mom5 = momentum(closes, 5)
    mom20 = momentum(closes, 20)
    rets = _daily_returns(closes)
    vol20 = volatility(rets, 20)
    return {
        "momentum_5d": mom5[-1],
        "momentum_20d": mom20[-1],
        "volatility_20d": vol20[-1],
        "as_of_date": bars[-1].date if bars else None,
    }
