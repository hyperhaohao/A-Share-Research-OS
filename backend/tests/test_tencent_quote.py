"""Tencent quote provider: parsing + failure mapping (network mocked; live marked)."""

import httpx
import pytest

from app.sources.base import SourceRequest, SourceStatus
from app.sources.providers.tencent_quote import TencentQuoteProvider

# Realistic qt.gtimg.cn body layout (indexes 9-28 are five bid + five ask
# price/volume pairs; 30 = quote time; 39 = PE; 44/45 = float/total mcap 亿).
RAW_OK = (
    'v_sh600519="1~贵州茅台~600519~1648.00~1651.00~1655.00~32924~85755~24354~'
    "1648.00~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "1648.10~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "1648.00/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    "1648.00/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
    '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
)


def _req() -> SourceRequest:
    return SourceRequest(capability="market_data", instrument_id="SSE:600519")


def test_parse_ok(monkeypatch):
    provider = TencentQuoteProvider()
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    result = provider.fetch(_req())
    assert result.status is SourceStatus.SUCCESS
    payload = result.records[0].payload
    assert payload["name"] == "贵州茅台"
    assert payload["price"] == 1648.00
    assert payload["change_pct"] == -0.18
    assert payload["pe_ttm"] == 20.86
    assert payload["pb"] == 8.50
    assert payload["total_market_cap_yuan"] == pytest.approx(20771.00 * 1e8)
    assert payload["has_market_cap_fields"] is True
    assert result.records[0].subject == "SSE:600519"
    assert result.records[0].event_time is not None
    assert result.records[0].event_time.year == 2026


def test_network_error_is_retryable_failure(monkeypatch):
    provider = TencentQuoteProvider()

    def boom(url, timeout):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "get", boom)
    result = provider.fetch(_req())
    assert result.status is SourceStatus.NETWORK_ERROR
    assert result.retryable is True


def test_auth_error_on_403(monkeypatch):
    provider = TencentQuoteProvider()
    resp = httpx.Response(403)
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    result = provider.fetch(_req())
    assert result.status is SourceStatus.AUTH_ERROR


def test_source_unavailable_on_5xx(monkeypatch):
    provider = TencentQuoteProvider()
    resp = httpx.Response(503)
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    result = provider.fetch(_req())
    assert result.status is SourceStatus.SOURCE_UNAVAILABLE


def test_parse_error_on_garbage(monkeypatch):
    provider = TencentQuoteProvider()
    resp = httpx.Response(200, content=b"pv_none=1;")
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    result = provider.fetch(_req())
    assert result.status is SourceStatus.PARSE_ERROR


def test_malformed_instrument_id_raises_caller_error():
    """A malformed request is a caller contract violation, not source state."""
    provider = TencentQuoteProvider()
    with pytest.raises(ValueError):
        provider.fetch(SourceRequest(capability="market_data", instrument_id=None))
    with pytest.raises(ValueError):
        provider.fetch(SourceRequest(capability="market_data", instrument_id="NASDAQ:AAPL"))


def test_live_quote_real_network():
    """Live source verification (task书 §18: Source Milestone 必须真实验证).

    Requires outbound network; skipped when unreachable so CI stays green
    while the live check still runs in the M3 verification environment.
    """
    provider = TencentQuoteProvider(timeout=6.0)
    result = provider.fetch(_req())
    if result.status in (SourceStatus.NETWORK_ERROR, SourceStatus.SOURCE_UNAVAILABLE):
        pytest.skip("network unreachable for live quote verification")
    assert result.status is SourceStatus.SUCCESS
    payload = result.records[0].payload
    assert payload["name"]
    assert payload["price"] and payload["price"] > 0
