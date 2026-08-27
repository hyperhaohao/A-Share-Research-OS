"""Tencent realtime quote provider — a real, key-free A-share market source.

Live-verified during M0 audit via the upstream TideTrading loader matrix;
this implementation speaks the same public endpoint directly
(``http://qt.gtimg.cn/q=sh600519``), GBK-encoded ``~``-separated fields.

Failure mapping (任务书 §21):
  - connection/timeout      → NETWORK_ERROR   (retryable)
  - unexpected body shape   → PARSE_ERROR     (not retryable)
  - unknown/empty symbol    → NO_DATA with reason (explicit, not a fake success)
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, ClassVar

import httpx

from app.domain.instrument import Exchange, instrument_id_for
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.provider import BaseProvider

_RESPONSE_LINE = re.compile(r'v_(?P<market>sh|sz|bj)(?P<code>\d{6})="(?P<body>[^"]*)"')
_FIELDS_WITH_MCAP = 50


class TencentQuoteProvider(BaseProvider):
    """``market_data`` capability: realtime A-share quotes."""

    provider_id = "tencent_quote"
    capabilities = frozenset({"market_data"})

    DEFAULT_URL: ClassVar[str] = "http://qt.gtimg.cn/q="

    def __init__(self, *, base_url: str | None = None, timeout: float = 5.0) -> None:
        self._base_url = base_url or self.DEFAULT_URL
        self._timeout = timeout

    # -- market code mapping -------------------------------------------------
    @staticmethod
    def _market_prefix(exchange: Exchange) -> str:
        return {Exchange.SSE: "sh", Exchange.SZSE: "sz", Exchange.BSE: "bj"}[exchange]

    @staticmethod
    def _exchange_from_prefix(prefix: str) -> Exchange:
        return {"sh": Exchange.SSE, "sz": Exchange.SZSE, "bj": Exchange.BSE}[prefix]

    # -- fetching ------------------------------------------------------------
    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            # caller contract violation — raised, not reported as source state
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange_str, code = instrument_id.split(":", 1)
        try:
            exchange = Exchange(exchange_str)
        except ValueError:
            raise ValueError(
                f"unsupported exchange in instrument_id: {instrument_id}"
            ) from None

        url = f"{self._base_url}{self._market_prefix(exchange)}{code}"
        attempted_at = utc_now()
        try:
            resp = httpx.get(url, timeout=self._timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return self._failure(
                request, SourceStatus.NETWORK_ERROR, type(exc).__name__,
                attempted_at=attempted_at,
            )
        if resp.status_code in (401, 403):
            return self._failure(
                request, SourceStatus.AUTH_ERROR, f"http_{resp.status_code}",
                attempted_at=attempted_at,
            )
        if resp.status_code >= 400:
            return self._failure(
                request, SourceStatus.SOURCE_UNAVAILABLE, f"http_{resp.status_code}",
                attempted_at=attempted_at,
            )

        parsed = self._parse(resp.content.decode("gbk", errors="replace"), code)
        if parsed is None:
            return self._failure(
                request, SourceStatus.PARSE_ERROR, "unparseable_quote_body",
                attempted_at=attempted_at,
            )
        if not parsed.payload:
            return self._no_data(
                request,
                f"no quote payload for {instrument_id}",
                attempted_at=attempted_at,
            )
        return self._success([parsed], request, attempted_at=attempted_at)

    # -- parsing -------------------------------------------------------------
    def _parse(self, text: str, code: str) -> SourceRecord | None:
        match = _RESPONSE_LINE.search(text)
        if match is None:
            return None
        fields = match.group("body").split("~")
        if len(fields) < 40 or not fields[1]:
            return None

        def num(idx: int) -> float | None:
            raw = fields[idx]
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        quote_time_raw = fields[30] if len(fields) > 30 else ""
        try:
            quote_dt = datetime.strptime(quote_time_raw, "%Y%m%d%H%M%S") if quote_time_raw else None
        except ValueError:
            quote_dt = None

        amount_yuan = num(37) * 10_000 if num(37) is not None else None
        total_mcap = num(45) * 100_000_000 if num(45) is not None else None
        payload: dict[str, Any] = {
            "code": code,
            "name": fields[1] or None,
            "price": num(3),
            "last_close": num(4),
            "open": num(5),
            "high": num(33),
            "low": num(34),
            "change": num(31),
            "change_pct": num(32),
            "volume_hand": num(36),
            "amount_yuan": amount_yuan,
            "turnover_rate": num(38),
            "pe_ttm": num(39),
            "pb": num(46) if len(fields) > 46 else None,
            "total_market_cap_yuan": total_mcap,
            "quote_provider": self.provider_id,
            # fields below are only marked available when the body carried them
            "field_count": len(fields),
            "has_market_cap_fields": len(fields) >= _FIELDS_WITH_MCAP,
        }
        return SourceRecord(
            subject=instrument_id_for(self._exchange_from_prefix(match.group("market")), code),
            kind="quote",
            payload=payload,
            event_time=quote_dt,
            available_time=utc_now(),
            source_uri=self._base_url,
        )
