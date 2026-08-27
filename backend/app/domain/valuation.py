"""Deterministic valuation engine (任务书 §36).

Every number is computed by testable code from explicitly provided inputs.
Missing inputs make a method explicitly not computable — the engine never
guesses. LLM layers (M11) may *explain* these outputs but never produce
unattributed target prices.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValuationMethod(str, Enum):
    PE = "pe"
    PB = "pb"
    PS = "ps"
    EV_EBITDA = "ev_ebitda"
    DCF = "dcf"
    DDM = "ddm"
    HISTORICAL_PERCENTILE = "historical_percentile"
    PEER_COMPS = "peer_comps"


class MissingInput(Exception):
    """A required input was not provided — the method cannot run honestly."""

    def __init__(self, name: str, reason: str = "missing input"):
        self.name = name
        self.reason = reason
        super().__init__(f"{name}: {reason}")


@dataclass
class ValuationResult:
    method: ValuationMethod
    value: float | None  # implied value per share, or None when blocked
    inputs_used: dict[str, Any] = field(default_factory=dict)
    missing: list[dict[str, str]] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def computable(self) -> bool:
        return self.value is not None


def _require(**named):
    """Return the first missing input name, collecting all of them."""
    missing = []
    values = {}
    for name, value in named.items():
        if value is None:
            missing.append(name)
        else:
            values[name] = value
    return values, missing


# -- multiples ---------------------------------------------------------------

def pe_valuation(price: float | None, eps_ttm: float | None, target_pe: float) -> ValuationResult:
    """Implied price = target_pe × eps_ttm."""
    detail: dict[str, Any] = {}
    try:
        if price is None:
            raise MissingInput("price")
        if eps_ttm is None or eps_ttm <= 0:
            raise MissingInput("eps_ttm", "missing or non-positive; PE undefined")
        implied = target_pe * eps_ttm
        detail = {
            "implied_price": implied,
            "upside_pct": (implied / price - 1) * 100,
            "target_pe": target_pe,
        }
        return ValuationResult(
            method=ValuationMethod.PE, value=implied,
            inputs_used={"price": price, "eps_ttm": eps_ttm, "target_pe": target_pe},
            detail=detail,
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.PE, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


def pb_valuation(price: float | None, bvps: float | None, target_pb: float) -> ValuationResult:
    try:
        if price is None:
            raise MissingInput("price")
        if bvps is None or bvps <= 0:
            raise MissingInput("bvps", "missing or non-positive; PB undefined")
        implied = target_pb * bvps
        return ValuationResult(
            method=ValuationMethod.PB, value=implied,
            inputs_used={"price": price, "bvps": bvps, "target_pb": target_pb},
            detail={"implied_price": implied, "upside_pct": (implied / price - 1) * 100},
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.PB, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


def ps_valuation(price: float | None, revenue_per_share: float | None, target_ps: float) -> ValuationResult:
    try:
        if price is None:
            raise MissingInput("price")
        if revenue_per_share is None or revenue_per_share <= 0:
            raise MissingInput("revenue_per_share")
        implied = target_ps * revenue_per_share
        return ValuationResult(
            method=ValuationMethod.PS, value=implied,
            inputs_used={"price": price, "revenue_per_share": revenue_per_share, "target_ps": target_ps},
            detail={"implied_price": implied, "upside_pct": (implied / price - 1) * 100},
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.PS, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


def ev_ebitda_valuation(
    price: float | None,
    shares_outstanding: float | None,
    net_debt: float | None,
    ebitda: float | None,
    target_multiple: float,
) -> ValuationResult:
    """Implied equity value = target_multiple × EBITDA − net debt; per share."""
    try:
        if price is None:
            raise MissingInput("price")
        if shares_outstanding is None or shares_outstanding <= 0:
            raise MissingInput("shares_outstanding")
        if ebitda is None or ebitda <= 0:
            raise MissingInput("ebitda")
        if net_debt is None:
            raise MissingInput("net_debt")
        implied_ev = target_multiple * ebitda
        implied_equity = implied_ev - net_debt
        implied = implied_equity / shares_outstanding
        return ValuationResult(
            method=ValuationMethod.EV_EBITDA, value=implied,
            inputs_used={
                "price": price, "shares_outstanding": shares_outstanding,
                "net_debt": net_debt, "ebitda": ebitda, "target_multiple": target_multiple,
            },
            detail={
                "implied_ev": implied_ev,
                "implied_equity": implied_equity,
                "implied_price": implied,
                "upside_pct": (implied / price - 1) * 100,
            },
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.EV_EBITDA, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


# -- cash-flow models ---------------------------------------------------------

def dcf_valuation(
    price: float | None,
    shares_outstanding: float | None,
    fcf_projections: list[float] | None,
    wacc: float,
    terminal_growth: float,
    net_debt: float | None = 0.0,
) -> ValuationResult:
    """Two-stage DCF: NPV of explicit FCFs + Gordon terminal value.

    ``fcf_projections`` covers the explicit horizon (per year, per share ×
    shares handled in aggregate). Returns implied equity value per share.
    """
    try:
        if price is None:
            raise MissingInput("price")
        if shares_outstanding is None or shares_outstanding <= 0:
            raise MissingInput("shares_outstanding")
        if not fcf_projections:
            raise MissingInput("fcf_projections", "at least one projection year required")
        if wacc <= terminal_growth:
            raise MissingInput("wacc", "wacc must exceed terminal growth")

        pv_explicit = sum(
            fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcf_projections)
        )
        last = fcf_projections[-1]
        terminal_value = last * (1 + terminal_growth) / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** len(fcf_projections))
        enterprise = pv_explicit + pv_terminal
        equity = enterprise - (net_debt or 0.0)
        implied = equity / shares_outstanding
        return ValuationResult(
            method=ValuationMethod.DCF, value=implied,
            inputs_used={
                "price": price, "shares_outstanding": shares_outstanding,
                "fcf_projections": fcf_projections, "wacc": wacc,
                "terminal_growth": terminal_growth, "net_debt": net_debt,
            },
            detail={
                "pv_explicit": pv_explicit,
                "pv_terminal": pv_terminal,
                "enterprise_value": enterprise,
                "equity_value": equity,
                "implied_price": implied,
                "upside_pct": (implied / price - 1) * 100,
            },
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.DCF, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


def ddm_valuation(
    price: float | None,
    dividend_per_share: float | None,
    dividend_growth: float,
    discount_rate: float,
) -> ValuationResult:
    """Gordon growth: value = D1 / (r − g)."""
    try:
        if price is None:
            raise MissingInput("price")
        if dividend_per_share is None or dividend_per_share <= 0:
            raise MissingInput("dividend_per_share")
        if discount_rate <= dividend_growth:
            raise MissingInput("discount_rate", "discount rate must exceed growth")
        implied = dividend_per_share * (1 + dividend_growth) / (discount_rate - dividend_growth)
        return ValuationResult(
            method=ValuationMethod.DDM, value=implied,
            inputs_used={
                "price": price, "dividend_per_share": dividend_per_share,
                "dividend_growth": dividend_growth, "discount_rate": discount_rate,
            },
            detail={"implied_price": implied, "upside_pct": (implied / price - 1) * 100},
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.DDM, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


# -- relative ------------------------------------------------------------------

def historical_percentile(
    price: float | None,
    current_multiple: float | None,
    historical_multiples: list[float] | None,
    multiple_name: str = "pe",
) -> ValuationResult:
    """Percentile rank of the current multiple within its own history."""
    try:
        if price is None:
            raise MissingInput("price")
        if current_multiple is None or current_multiple <= 0:
            raise MissingInput("current_multiple")
        if not historical_multiples or len(historical_multiples) < 2:
            raise MissingInput("historical_multiples", "need at least two observations")
        below = sum(1 for m in historical_multiples if m < current_multiple)
        percentile = below / len(historical_multiples) * 100
        median = statistics.median(historical_multiples)
        implied = price * (median / current_multiple)
        return ValuationResult(
            method=ValuationMethod.HISTORICAL_PERCENTILE, value=implied,
            inputs_used={
                "price": price, "current_multiple": current_multiple,
                "historical_multiples": historical_multiples, "multiple_name": multiple_name,
            },
            detail={
                "percentile": percentile,
                "median_multiple": median,
                "implied_price_at_median": implied,
                "upside_pct": (implied / price - 1) * 100,
            },
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.HISTORICAL_PERCENTILE, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )


def peer_comps_valuation(
    price: float | None,
    current_metric: float | None,
    peer_multiples: list[float] | None,
    metric_name: str = "pe",
) -> ValuationResult:
    """Apply the peer median multiple to the company's own metric."""
    try:
        if price is None:
            raise MissingInput("price")
        if current_metric is None or current_metric <= 0:
            raise MissingInput("current_metric")
        if not peer_multiples:
            raise MissingInput("peer_multiples")
        median = statistics.median(peer_multiples)
        implied = median * current_metric
        return ValuationResult(
            method=ValuationMethod.PEER_COMPS, value=implied,
            inputs_used={
                "price": price, "current_metric": current_metric,
                "peer_multiples": peer_multiples, "metric_name": metric_name,
            },
            detail={
                "median_multiple": median,
                "implied_price": implied,
                "upside_pct": (implied / price - 1) * 100,
            },
        )
    except MissingInput as exc:
        return ValuationResult(
            method=ValuationMethod.PEER_COMPS, value=None,
            missing=[{"name": exc.name, "reason": exc.reason}],
        )
