"""Eastmoney realtime quote provider — market_data fallback (R1.1).

Chain: Tencent (primary) → Eastmoney (fallback). Both speak the same
SourceResult semantics; prices are scaled by 100 in the raw feed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ClassVar

from app.domain.instrument import Exchange, instrument_id_for
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.http import eastmoney_secid, http_json
from app.sources.provider import BaseProvider

_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f117,f162,f168,f170"


class EastmoneyQuoteProvider(BaseProvider):
    provider_id = "eastmoney_quote"
    capabilities = frozenset({"market_data"})

    BASE_URL: ClassVar[str] = "https://push2.eastmoney.com/api/qt/stock/get"

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange_str, code = instrument_id.split(":", 1)
        try:
            Exchange(exchange_str)
        except ValueError:
            raise ValueError(f"unsupported exchange in instrument_id: {instrument_id}") from None

        secid = eastmoney_secid(instrument_id)
        attempted_at = utc_now()
        data, failure = http_json(
            self.BASE_URL,
            params={"secid": secid, "fields": _FIELDS},
            headers={"Referer": "https://quote.eastmoney.com/"},
            timeout=self._timeout,
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        payload_raw = (data or {}).get("data")
        if not payload_raw or payload_raw.get("f43") in (None, "-"):
            return self._no_data(
                request, f"no quote payload for {instrument_id}", attempted_at=attempted_at
            )

        def scaled(field):
            v = payload_raw.get(field)
            return round(v / 100, 4) if isinstance(v, (int, float)) else None

        price = scaled("f43")
        record = SourceRecord(
            subject=instrument_id_for(Exchange(exchange_str), code),
            kind="quote",
            payload={
                "code": code,
                "name": payload_raw.get("f58"),
                "price": price,
                "open": scaled("f46"),
                "high": scaled("f44"),
                "low": scaled("f45"),
                "last_close": scaled("f60"),
                "change_pct": scaled("f170"),
                "turnover_rate": scaled("f168"),
                "pe_ttm": scaled("f162"),
                "volume_hand": payload_raw.get("f47"),
                "amount_yuan": payload_raw.get("f48"),
                "total_market_cap_yuan": payload_raw.get("f116"),
                "float_market_cap_yuan": payload_raw.get("f117"),
                "quote_provider": self.provider_id,
            },
            event_time=None,
            available_time=utc_now(),
            source_uri=self.BASE_URL,
        )
        if price is None:
            return self._no_data(
                request, f"no price for {instrument_id}", attempted_at=attempted_at
            )
        return self._success([record], request, attempted_at=attempted_at)

    @property
    def _timeout(self) -> float:
        return getattr(self, "_timeout_s", 8.0)

    def __init__(self, *, timeout: float = 8.0) -> None:
        self._timeout_s = timeout
