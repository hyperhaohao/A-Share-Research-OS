"""Instrument API contract tests."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_search_by_code():
    client = TestClient(create_app())
    resp = client.get("/api/v1/instruments", params={"query": "600519"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    instrument = body["results"][0]["instrument"]
    assert instrument["code"] == "600519"
    assert instrument["name"] == "贵州茅台"
    assert instrument["exchange"] == "SSE"
    assert instrument["market"] == "CN"
    assert body["results"][0]["matched_by"] == "code"


def test_search_by_name():
    client = TestClient(create_app())
    resp = client.get("/api/v1/instruments", params={"query": "宁德时代"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert any(r["instrument"]["code"] == "300750" for r in body["results"])


def test_search_empty_query():
    client = TestClient(create_app())
    resp = client.get("/api/v1/instruments", params={"query": ""})
    assert resp.status_code == 200
    assert resp.json() == {"query": "", "count": 0, "results": []}


def test_get_instrument_by_id_and_404_envelope():
    client = TestClient(create_app())
    ok = client.get("/api/v1/instruments/SSE:600519")
    assert ok.status_code == 200
    assert ok.json()["instrument"]["code"] == "600519"

    missing = client.get("/api/v1/instruments/SSE:999999")
    assert missing.status_code == 404
    body = missing.json()
    assert body["status"] == "error"
    assert body["error_code"] == "instrument.not_found"


def test_missing_market_data_is_null_not_guessed():
    client = TestClient(create_app())
    resp = client.get("/api/v1/instruments", params={"query": "688981"})
    instrument = resp.json()["results"][0]["instrument"]
    assert instrument["market_cap"] is None
    assert instrument["industry"] is not None
