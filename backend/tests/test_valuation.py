"""Deterministic valuation math: fixed-number unit tests (任务书 §36)."""

import pytest

from app.domain.valuation import (
    dcf_valuation,
    ddm_valuation,
    ev_ebitda_valuation,
    historical_percentile,
    pe_valuation,
    pb_valuation,
    peer_comps_valuation,
    ps_valuation,
)


class TestMultiples:
    def test_pe(self):
        result = pe_valuation(price=100.0, eps_ttm=4.0, target_pe=25)
        assert result.computable
        assert result.value == pytest.approx(100.0)
        assert result.detail["upside_pct"] == pytest.approx(0.0)

    def test_pe_upside(self):
        result = pe_valuation(price=80.0, eps_ttm=4.0, target_pe=25)
        assert result.value == pytest.approx(100.0)
        assert result.detail["upside_pct"] == pytest.approx(25.0)

    def test_pe_missing_eps_is_explicit(self):
        result = pe_valuation(price=100.0, eps_ttm=None, target_pe=25)
        assert not result.computable
        assert result.missing[0]["name"] == "eps_ttm"

    def test_pe_negative_eps_is_explicit(self):
        result = pe_valuation(price=100.0, eps_ttm=-0.5, target_pe=25)
        assert not result.computable

    def test_pb(self):
        result = pb_valuation(price=50.0, bvps=10.0, target_pb=4.0)
        assert result.value == pytest.approx(40.0)

    def test_ps(self):
        result = ps_valuation(price=30.0, revenue_per_share=12.0, target_ps=3.0)
        assert result.value == pytest.approx(36.0)

    def test_ev_ebitda(self):
        # EV = 8 × 500 = 4000; equity = 4000 − 1000 = 3000; per share = 30
        result = ev_ebitda_valuation(
            price=25.0, shares_outstanding=100.0, net_debt=1000.0,
            ebitda=500.0, target_multiple=8.0,
        )
        assert result.value == pytest.approx(30.0)
        assert result.detail["upside_pct"] == pytest.approx(20.0)


class TestDCF:
    def test_explicit_and_terminal(self):
        """Hand-computed: FCF 100/110/121 for 3y, wacc 10%, g 3%."""
        result = dcf_valuation(
            price=10.0, shares_outstanding=100.0,
            fcf_projections=[100.0, 110.0, 121.0],
            wacc=0.10, terminal_growth=0.03, net_debt=0.0,
        )
        pv1 = 100 / 1.1
        pv2 = 110 / 1.1**2
        pv3 = 121 / 1.1**3
        tv = 121 * 1.03 / 0.07
        pv_tv = tv / 1.1**3
        expected_equity = pv1 + pv2 + pv3 + pv_tv
        assert result.value == pytest.approx(expected_equity / 100.0, rel=1e-9)
        assert result.detail["pv_terminal"] == pytest.approx(pv_tv, rel=1e-9)

    def test_wacc_must_exceed_growth(self):
        result = dcf_valuation(
            price=10.0, shares_outstanding=100.0,
            fcf_projections=[100.0], wacc=0.03, terminal_growth=0.05,
        )
        assert not result.computable
        assert result.missing[0]["name"] == "wacc"

    def test_missing_projections(self):
        result = dcf_valuation(
            price=10.0, shares_outstanding=100.0,
            fcf_projections=None, wacc=0.10, terminal_growth=0.03,
        )
        assert not result.computable
        assert result.missing[0]["name"] == "fcf_projections"


class TestDDM:
    def test_gordon_growth(self):
        # D0=5, g=2%, r=7% → D1=5.1 → 5.1/0.05 = 102
        result = ddm_valuation(
            price=90.0, dividend_per_share=5.0,
            dividend_growth=0.02, discount_rate=0.07,
        )
        assert result.value == pytest.approx(102.0)

    def test_zero_dividend_is_explicit(self):
        result = ddm_valuation(
            price=90.0, dividend_per_share=0.0,
            dividend_growth=0.02, discount_rate=0.07,
        )
        assert not result.computable


class TestRelative:
    def test_historical_percentile_ranking(self):
        history = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        result = historical_percentile(
            price=100.0, current_multiple=16.0, historical_multiples=history
        )
        # 3 of 10 observations strictly below 16 → 30th percentile
        assert result.detail["percentile"] == pytest.approx(30.0)
        median = 19.0
        assert result.value == pytest.approx(100.0 * (median / 16.0))

    def test_percentile_needs_history(self):
        result = historical_percentile(
            price=100.0, current_multiple=16.0, historical_multiples=[16.0]
        )
        assert not result.computable

    def test_peer_comps_median(self):
        result = peer_comps_valuation(
            price=50.0, current_metric=2.0,
            peer_multiples=[15.0, 18.0, 20.0, 40.0],  # median = (18+20)/2 = 19
        )
        assert result.detail["median_multiple"] == pytest.approx(19.0)
        assert result.value == pytest.approx(38.0)

    def test_peer_comps_missing_metric(self):
        result = peer_comps_valuation(
            price=50.0, current_metric=None, peer_multiples=[15.0, 18.0]
        )
        assert not result.computable
        assert result.missing[0]["name"] == "current_metric"
