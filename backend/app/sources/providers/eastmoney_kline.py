"""Eastmoney daily-kline provider — historical_data capability (R3.5)."""

from __future__ import annotations

from datetime import timedelta, timezone

from app.domain.instrument import Exchange
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    utc_now,
)
from app.sources.http import eastmoney_secid, http_json
from app.sources.provider import BaseProvider
from app.quant.engine import Bar

_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
_HEADERS = {"Referer": "https://quote.eastmoney.com/"}
_CN_TZ = timezone(timedelta(hours=8))


class EastmoneyKlineProvider(BaseProvider):
    """Daily bars for factors/backtests. kind=historical_bars."""

    provider_id = "eastmoney_kline"
    capabilities = frozenset({"historical_data"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange_str, code = instrument_id.split(":", 1)
        Exchange(exchange_str)
        secid = eastmoney_secid(instrument_id)
        attempted_at = utc_now()

        limit = int(request.params.get("bars", 120))
        data, failure = http_json(
            _KLINE_URL,
            params={
                "secid": secid,
                "klt": 101,  # daily
                "fqt": 1,  # forward-adjusted
                "lmt": limit,
                "end": "20500101",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            },
            headers=_HEADERS,
            timeout=self._timeout_s,
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        klines = ((data or {}).get("data") or {}).get("klines") or []
        if not klines:
            return self._no_data(
                request, f"no kline data for {instrument_id}", attempted_at=attempted_at
            )

        bars = []
        for line in klines[:limit]:
            parts = line.split(",")
            # date, open, close, high, low, volume, amount, amplitude, change_pct, change, turnover
            if len(parts) < 11:
                continue
            bars.append(
                Bar(
                    date=parts[0],
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=float(parts[5]),
                    turnover=float(parts[10]) if parts[10] not in ("", "-") else None,
                )
            )
        if not bars:
            return self._no_data(request, "no usable bars", attempted_at=attempted_at)

        payload = {
            "instrument_id": instrument_id,
            "bars": [
                {
                    "date": b.date, "open": b.open, "close": b.close,
                    "high": b.high, "low": b.low, "volume": b.volume,
                    "turnover": b.turnover,
                }
                for b in bars
            ],
            "bar_count": len(bars),
            "kline_provider": self.provider_id,
        }
        record = SourceRecord(
            subject=instrument_id,
            kind="historical_bars",
            payload=payload,
            event_time=None,
            available_time=utc_now(),
            source_uri=_KLINE_URL,
        )
        return self._success([record], request, attempted_at=attempted_at)

    def __init__(self, *, timeout: float = 12.0) -> None:
        self._timeout_s = timeout
