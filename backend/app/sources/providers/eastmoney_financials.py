"""Eastmoney financial statements provider (R1.3).

ZYZBAjaxNew (主要指标) covers the required normalized metrics with a real
PIT anchor: NOTICE_DATE is when the filing was announced (available_time),
REPORT_DATE is the period end (event_time). zcfzbAjaxNew (资产负债表) adds
balance-sheet totals. Authority B2 — major financial data platform relaying
official filings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    utc_now,
)
from app.sources.http import http_json
from app.sources.provider import BaseProvider

_ZYZB = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
_ZCFZB = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew"
_HEADERS = {"Referer": "https://emweb.securities.eastmoney.com/"}

_CN_TZ = timezone(timedelta(hours=8))


def _em_code(instrument_id: str) -> str | None:
    if ":" not in instrument_id:
        return None
    exchange, code = instrument_id.split(":", 1)
    if exchange == "SSE":
        return f"SH{code}"
    if exchange in ("SZSE", "BSE"):
        return f"SZ{code}"
    return None


def _cn_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.strip().replace(" ", "T")).replace(tzinfo=_CN_TZ)
    except ValueError:
        return None


def _num(rec: dict, key: str) -> float | None:
    v = rec.get(key)
    return float(v) if isinstance(v, (int, float)) else None


class EastmoneyFinancialsProvider(BaseProvider):
    provider_id = "eastmoney_financials"
    capabilities = frozenset({"financials"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        code = _em_code(instrument_id)
        if not code:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        attempted_at = utc_now()

        data, failure = http_json(_ZYZB, params={"type": 0, "code": code}, headers=_HEADERS)
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        records_raw = (data or {}).get("data") or []
        if not records_raw:
            return self._no_data(
                request, f"no financial indicators for {instrument_id}",
                attempted_at=attempted_at,
            )

        # fetch balance sheets for ALL periods (PIT fix: each period gets
        # its own balance data, never the latest merged into historical)
        periods_needed = int(request.params.get("periods", 4))
        all_periods = [(r.get("REPORT_DATE") or "")[:10] for r in records_raw[:periods_needed]]
        balance_by_period: dict[str, dict] = {}
        if all_periods:
            bs_data, bs_failure = http_json(
                _ZCFZB,
                params={"companyType": 4, "reportDateType": 0, "reportType": 1,
                        "dates": ",".join(all_periods), "code": code},
                headers=_HEADERS,
            )
            if bs_failure is None:
                for bs_row in (bs_data or {}).get("data") or []:
                    period_key = (bs_row.get("REPORT_DATE") or "")[:10]
                    balance_by_period[period_key] = {
                        "total_assets_yuan": _num(bs_row, "TOTAL_ASSETS"),
                        "total_liabilities_yuan": _num(bs_row, "TOTAL_LIABILITIES"),
                        "monetary_funds_yuan": _num(bs_row, "MONETARYFUNDS"),
                    }

        records: list[SourceRecord] = []
        for rec in records_raw[:periods_needed]:
            notice = _cn_date(rec.get("NOTICE_DATE"))
            report_date = _cn_date(rec.get("REPORT_DATE"))
            period_key = (rec.get("REPORT_DATE") or "")[:10]
            balance = balance_by_period.get(period_key, {})
            payload = {
                "report_date": (rec.get("REPORT_DATE") or "")[:10],
                "report_type": rec.get("REPORT_TYPE"),
                "notice_date": rec.get("NOTICE_DATE"),
                "currency": rec.get("CURRENCY", "CNY"),
                # normalized metrics (任务书整改 §6.5)
                "eps": _num(rec, "EPSJB"),
                "bvps": _num(rec, "BPS"),
                "roe_pct": _num(rec, "ROEJQ"),
                "revenue_yuan": _num(rec, "TOTALOPERATEREVE"),
                "net_profit_yuan": _num(rec, "PARENTNETPROFIT"),
                "operating_profit_yuan": _num(rec, "KCFJCXSYJLR"),
                "gross_margin_pct": _num(rec, "XSMLL"),
                "net_margin_pct": _num(rec, "XSJLL"),
                "ocf_per_share": _num(rec, "MGJYXJJE"),
                "revenue_yoy_pct": _num(rec, "TOTALOPERATEREVETZ"),
                "net_profit_yoy_pct": _num(rec, "PARENTNETPROFITTZ"),
                "roic_like_pct": _num(rec, "ZZCJLL"),
                "shares_factor_note": "per-share metrics as reported",
                "financials_provider": self.provider_id,
                **balance,
            }
            records.append(
                SourceRecord(
                    subject=instrument_id,
                    kind="financial_report",
                    payload=payload,
                    event_time=report_date,
                    available_time=notice or utc_now(),
                    source_uri=_ZYZB,
                )
            )
        if not records:
            return self._no_data(request, "no usable financial records",
                                 attempted_at=attempted_at)
        return self._success(records, request, attempted_at=attempted_at)
