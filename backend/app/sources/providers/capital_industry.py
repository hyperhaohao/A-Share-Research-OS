"""Capital flow (R1.5) and industry (R1.6) providers.

Capital flow v1: turnover / volume / amount come from the quote feed (stable
fields). The dedicated main-capital-flow endpoint was unresponsive during the
R1 survey, so ``main_capital_flow`` is reported as explicitly unavailable —
never fabricated (整改 §6.7).

Industry v1: the Eastmoney F10 company survey gives the EM industry chain
(industry / sub-industry / segment) and the main business description. Peers,
upstream and downstream are structured lists that stay empty with an explicit
note until a relationship source is wired (整改 §6.8 allows this for v1).
"""

from __future__ import annotations

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.http import eastmoney_secid, http_json
from app.sources.provider import BaseProvider

_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
_SURVEY_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
_HEADERS = {"Referer": "https://emweb.securities.eastmoney.com/"}


class EastmoneyCapitalFlowProvider(BaseProvider):
    provider_id = "eastmoney_capital_flow"
    capabilities = frozenset({"capital_flow"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        secid = eastmoney_secid(instrument_id)
        attempted_at = utc_now()

        data, failure = http_json(
            _QUOTE_URL,
            params={
                "secid": secid,
                "fields": "f47,f48,f168,f116,f117",
            },
            headers=_HEADERS,
            timeout=self._timeout_s,
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)
        raw = (data or {}).get("data")
        if not raw:
            return self._no_data(
                request, f"no capital flow data for {instrument_id}",
                attempted_at=attempted_at,
            )

        def scaled(field):
            v = raw.get(field)
            return round(v / 100, 4) if isinstance(v, (int, float)) else None

        payload = {
            "volume_hand": raw.get("f47"),
            "amount_yuan": raw.get("f48"),
            "turnover_rate": scaled("f168"),
            "total_market_cap_yuan": raw.get("f116"),
            "float_market_cap_yuan": raw.get("f117"),
            # explicit unavailability — never fabricated (整改 §6.7)
            "main_capital_flow": None,
            "main_capital_flow_status": "unavailable_from_source",
            "margin_financing": None,
            "margin_financing_status": "unavailable_from_source",
            "capital_flow_provider": self.provider_id,
        }
        record = SourceRecord(
            subject=instrument_id,
            kind="capital_flow",
            payload=payload,
            event_time=None,
            available_time=utc_now(),
            source_uri=_QUOTE_URL,
        )
        return self._success([record], request, attempted_at=attempted_at)

    def __init__(self, *, timeout: float = 8.0) -> None:
        self._timeout_s = timeout


class EastmoneyIndustryProvider(BaseProvider):
    provider_id = "eastmoney_industry"
    capabilities = frozenset({"industry"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange, code = instrument_id.split(":", 1)
        em_code = ("SH" if exchange == "SSE" else "SZ") + code
        attempted_at = utc_now()

        data, failure = http_json(_SURVEY_URL, params={"code": em_code}, headers=_HEADERS)
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)
        survey = ((data or {}).get("jbzl") or [{}])[0]
        industry_chain = (survey.get("EM2016") or "").split("-")
        if not industry_chain or not industry_chain[0]:
            return self._no_data(
                request, f"no industry classification for {instrument_id}",
                attempted_at=attempted_at,
            )
        payload = {
            "industry": industry_chain[0] if len(industry_chain) > 0 else None,
            "sub_industry": industry_chain[1] if len(industry_chain) > 1 else None,
            "segment": industry_chain[2] if len(industry_chain) > 2 else None,
            "industry_chain": industry_chain,
            "main_business": (survey.get("MAINBUSINESS") or None),
            "peers": [],
            "upstream": [],
            "downstream": [],
            "peers_status": "pending_relationship_source",
            "industry_provider": self.provider_id,
        }
        record = SourceRecord(
            subject=instrument_id,
            kind="industry_profile",
            payload=payload,
            event_time=None,
            available_time=utc_now(),
            source_uri=_SURVEY_URL,
        )
        return self._success([record], request, attempted_at=attempted_at)
