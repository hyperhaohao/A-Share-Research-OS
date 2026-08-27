"""Market-data + source-health API tests (mocked transport; live covered separately)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sources.runtime import reset_runtime


@pytest.fixture(autouse=True)
def fresh_runtime():
    reset_runtime()
    yield
    reset_runtime()


RAW_OK = (
    'v_sz000001="51~平安银行~000001~11.59~11.73~11.70~97570~631~2137~'
    "11.59~631~11.58~2137~11.57~880~11.56~899~11.55~521~"
    "11.60~343~11.61~100~11.62~512~11.63~44~11.64~10~"
    "11.59/5~20260828150123~-0.14~-1.19~11.72~11.51~"
    "11.59/997515/1155100000~997515~115510~1.98~4.66~~11.72~11.51~"
    '5.44~2231.20~2251.20~0.554~12.90~10.56~0.98"\n'
)


def test_quote_endpoint_real_provider(monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client = TestClient(create_app())

    first = client.get("/api/v1/market-data/quote", params={"instrument": "000001"})
    assert first.status_code == 200
    body = first.json()
    assert body["instrument_id"] == "SZSE:000001"
    assert body["quote"]["name"] == "平安银行"
    assert body["from_cache"] is False

    # second call is served from TTL cache
    second = client.get("/api/v1/market-data/quote", params={"instrument": "000001"})
    assert second.status_code == 200
    assert second.json()["from_cache"] is True


def test_quote_endpoint_accepts_prefixed_forms(monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client = TestClient(create_app())
    resp_api = client.get("/api/v1/market-data/quote", params={"instrument": "sz000001"})
    assert resp_api.status_code == 200
    assert resp_api.json()["instrument_id"] == "SZSE:000001"


def test_quote_resolves_name_via_catalog(monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client = TestClient(create_app())
    resp_api = client.get("/api/v1/market-data/quote", params={"instrument": "平安银行"})
    assert resp_api.status_code == 200
    assert resp_api.json()["instrument_id"] == "SZSE:000001"


def test_quote_network_failure_maps_to_503(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "get", boom)
    client = TestClient(create_app())
    resp = client.get("/api/v1/market-data/quote", params={"instrument": "600519"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error_code"] == "source.unavailable"


def test_unknown_instrument_is_404_envelope():
    client = TestClient(create_app())
    resp = client.get("/api/v1/market-data/quote", params={"instrument": "NOPE9999"})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "instrument.not_found"


def test_source_health_reflects_attempts(monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client = TestClient(create_app())
    client.get("/api/v1/market-data/quote", params={"instrument": "000001"})
    health = client.get("/api/v1/source-health").json()
    assert health["count"] >= 1
    provider = next(p for p in health["providers"] if p["provider_id"] == "tencent_quote")
    assert provider["last_status"] == "success"
    assert provider["available"] is True
