"""R1 provider tests: canned responses, fallback chains, live (marked)."""

import httpx
import pytest

from app.domain.evidence import AuthorityLevel, EvidenceType, FactStatus
from app.sources.base import SourceRequest, SourceStatus, utc_now
from app.sources.providers.announcements import (
    EastmoneyAnnouncementsProvider,
)
from app.sources.providers.capital_industry import (
    EastmoneyCapitalFlowProvider,
    EastmoneyIndustryProvider,
)
from app.sources.providers.eastmoney_financials import EastmoneyFinancialsProvider
from app.sources.providers.eastmoney_quote import EastmoneyQuoteProvider
from app.sources.providers.news import EastmoneyNewsProvider
from app.sources.registry import SourceRegistry


def _req(capability: str, instrument_id: str = "SSE:600519") -> SourceRequest:
    return SourceRequest(capability=capability, instrument_id=instrument_id)


def _patch(monkeypatch, responses: dict):
    """Patch app.sources.http transport with canned responses keyed by URL substring."""
    import app.sources.http as http_mod

    def fake_get(url, params=None, data=None, headers=None, timeout=10.0, jsonp=False, encoding=None):
        for key, value in responses.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                if isinstance(value, httpx.Response):
                    return value
                return httpx.Response(200, content=value.encode("utf-8"))
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(http_mod.httpx, "get", fake_get)

    def fake_post(url, data=None, headers=None, timeout=12.0):
        for key, value in responses.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return httpx.Response(200, content=value.encode("utf-8"))
        raise AssertionError(f"unexpected post url: {url}")

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)


class TestEastmoneyQuote:
    def test_quote_payload_scaled(self, monkeypatch):
        body = (
            '{"rc":0,"data":{"f43":129220,"f44":129497,"f45":128800,"f46":128900,'
            '"f47":6610,"f48":853668021,"f57":"600519","f58":"贵州茅台","f60":129230,'
            '"f116":1624000000000,"f117":1624000000000,"f162":2055,"f168":50,"f170":-1}}'
        )
        _patch(monkeypatch, {"stock/get": body})
        result = EastmoneyQuoteProvider().fetch(_req("market_data"))
        assert result.status is SourceStatus.SUCCESS
        payload = result.records[0].payload
        assert payload["price"] == pytest.approx(1292.20)
        assert payload["change_pct"] == pytest.approx(-0.01)
        assert payload["name"] == "贵州茅台"

    def test_transport_error_is_network_failure(self, monkeypatch):
        _patch(monkeypatch, {"stock/get": httpx.ConnectTimeout("down")})
        result = EastmoneyQuoteProvider().fetch(_req("market_data"))
        assert result.status is SourceStatus.NETWORK_ERROR
        assert result.retryable


class TestAnnouncementFallback:
    def test_cninfo_failure_falls_back_to_eastmoney(self, monkeypatch):
        """R1 core scenario: CNINFO 504 → registry falls through → Eastmoney."""
        registry = SourceRegistry()
        from app.sources.providers.announcements import CninfoAnnouncementsProvider

        registry.register(CninfoAnnouncementsProvider())
        registry.register(EastmoneyAnnouncementsProvider())

        import app.sources.http as http_mod

        em_body = (
            '{"data":{"list":[{"art_code":"AN1","title":"关于回购股份的公告",'
            '"notice_date":"2026-08-15 00:00:00",'
            '"columns":[{"column_name":"公告"}]}]}}'
        )

        def fake_get(url, params=None, data=None, headers=None, timeout=10.0, jsonp=False, encoding=None):
            if "np-anotice" in url:
                return httpx.Response(200, content=em_body.encode("utf-8"))
            raise AssertionError(f"unexpected url: {url}")

        def fake_post(url, data=None, headers=None, timeout=12.0):
            # CNINFO orgId lookup succeeds but the query endpoint 504s
            if "topSearch" in url:
                return httpx.Response(
                    200,
                    content=b'[{"code":"600519","orgId":"gssh0600519"}]',
                )
            if "hisAnnouncement" in url:
                return httpx.Response(504)
            raise AssertionError(f"unexpected post url: {url}")

        monkeypatch.setattr(http_mod.httpx, "get", fake_get)
        monkeypatch.setattr(http_mod.httpx, "post", fake_post)

        result = registry.resolve(_req("announcements"))
        assert result.is_success()
        assert result.source == "eastmoney_announcements"
        assert result.metadata["fallback_chain"] == [
            "cninfo_announcements",
            "eastmoney_announcements",
        ]


class TestFinancials:
    def test_financial_records_with_pit_anchor(self, monkeypatch):
        zyzb = (
            '{"data":[{"REPORT_DATE":"2026-06-30 00:00:00","REPORT_TYPE":"中报",'
            '"NOTICE_DATE":"2026-08-15 00:00:00","CURRENCY":"CNY",'
            '"EPSJB":35.57,"BPS":200.99,"ROEJQ":16.75,'
            '"TOTALOPERATEREVE":92278072083.21,"PARENTNETPROFIT":44516880421.86,'
            '"XSMLL":89.55,"XSJLL":50.75}]}'
        )
        zcfzb = '{"data":[{"TOTAL_ASSETS":3.1e11,"TOTAL_LIABILITIES":4.5e10}]}'
        _patch(monkeypatch, {"ZYZBAjaxNew": zyzb, "zcfzbAjaxNew": zcfzb})
        result = EastmoneyFinancialsProvider().fetch(_req("financials"))
        assert result.status is SourceStatus.SUCCESS
        first = result.records[0]
        assert first.kind == "financial_report"
        # PIT anchor: available_time = NOTICE_DATE
        assert first.available_time.year == 2026
        assert first.available_time.month == 8
        assert first.payload["eps"] == pytest.approx(35.57)
        assert first.payload["roe_pct"] == pytest.approx(16.75)
        assert first.payload["total_assets_yuan"] == pytest.approx(3.1e11)


class TestNews:
    def test_news_records_c2(self, monkeypatch):
        body = (
            'cb({"result":{"cmsArticleWebOld":[{"date":"2026-08-28 08:18:00",'
            '"code":"202608273856986968","title":"贵州茅台发布半年报",'
            '"content":"营收同比增长"}]}})'
        )
        _patch(monkeypatch, {"search-api-web": body})
        result = EastmoneyNewsProvider().fetch(_req("news"))
        assert result.status is SourceStatus.SUCCESS
        record = result.records[0]
        assert "半年报" in record.payload["title"]

    def test_macro_policy_marks_official_bodies(self, monkeypatch):
        body = (
            'cb({"result":{"cmsArticleWebOld":[{"date":"2026-08-28 08:18:00",'
            '"code":"p1","title":"央行宣布下调存款准备金率","content":"国务院常务会议部署"}]}})'
        )
        from app.sources.providers.news import EastmoneyMacroPolicyProvider

        _patch(monkeypatch, {"search-api-web": body})
        result = EastmoneyMacroPolicyProvider().fetch(
            SourceRequest(capability="macro_policy", params={"keyword": "货币政策"})
        )
        record = result.records[0]
        assert record.payload["mentions_official_body"] is True
        assert "央行" in record.payload["official_bodies"]


class TestCapitalFlowAndIndustry:
    def test_capital_flow_explicit_unavailable_fields(self, monkeypatch):
        body = '{"rc":0,"data":{"f47":6610,"f48":853668021,"f168":50,"f116":1624e10,"f117":1624e10}}'
        _patch(monkeypatch, {"stock/get": body})
        result = EastmoneyCapitalFlowProvider().fetch(_req("capital_flow"))
        payload = result.records[0].payload
        assert payload["turnover_rate"] == pytest.approx(0.5)
        assert payload["main_capital_flow"] is None
        assert payload["main_capital_flow_status"] == "unavailable_from_source"

    def test_industry_chain(self, monkeypatch):
        body = (
            '{"jbzl":[{"SECURITY_NAME_ABBR":"贵州茅台",'
            '"EM2016":"食品饮料-饮料-白酒","MAINBUSINESS":"茅台酒及系列酒"}]}'
        )
        _patch(monkeypatch, {"CompanySurvey": body})
        result = EastmoneyIndustryProvider().fetch(_req("industry"))
        payload = result.records[0].payload
        assert payload["industry"] == "食品饮料"
        assert payload["sub_industry"] == "饮料"
        assert payload["segment"] == "白酒"
        assert payload["peers"] == []


class TestEvidenceMapping:
    def test_authority_follows_source(self):
        """整改 §6.4-6.6: authority follows the source, not just capability."""
        from app.services.evidence_collector import evidence_type_for

        cn = evidence_type_for("announcements", "cninfo_announcements")
        em = evidence_type_for("announcements", "eastmoney_announcements")
        assert cn[2] is AuthorityLevel.A2
        assert em[2] is AuthorityLevel.B2
        news = evidence_type_for("news", "eastmoney_news")
        assert news[1] is FactStatus.MEDIA_REPORT
        assert news[2] is AuthorityLevel.C2


@pytest.mark.live
class TestLiveProviders:
    """Real-network verification (整改 R1.8): skipped automatically offline."""

    def _skip_if_offline(self, result):
        if result.status in (SourceStatus.NETWORK_ERROR, SourceStatus.SOURCE_UNAVAILABLE):
            pytest.skip("network unreachable for live verification")

    def test_live_market_fallback_chain(self):
        from app.sources.runtime import get_runtime

        result = get_runtime().registry.resolve(_req("market_data"))
        self._skip_if_offline(result)
        assert result.is_success()

    def test_live_announcements(self):
        from app.sources.runtime import get_runtime

        result = get_runtime().registry.resolve(_req("announcements"))
        self._skip_if_offline(result)
        assert result.is_success()
        assert result.records

    def test_live_financials(self):
        from app.sources.runtime import get_runtime

        result = get_runtime().registry.resolve(_req("financials"))
        self._skip_if_offline(result)
        assert result.is_success()
        assert result.records[0].payload.get("eps") is not None

    def test_live_news(self):
        from app.sources.runtime import get_runtime

        result = get_runtime().registry.resolve(_req("news"))
        self._skip_if_offline(result)
        assert result.is_success()
