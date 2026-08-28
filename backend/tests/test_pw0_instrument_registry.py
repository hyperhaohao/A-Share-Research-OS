"""PW0 — persistent Instrument Registry + unified InstrumentService.

Covers the product-closure remediation (产品闭环二次审查 §2):
  - dynamic resolutions persist across service restarts (same DB, new session)
  - watchlist add of a raw code guarantees a usable InstrumentProfile
  - offline adds degrade to code_only profiles and self-heal when online
  - Chinese-name search resolves through a real remote source (smartbox)
    and re-derives exchange/board from local code-prefix rules
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session, session_scope
from app.main import create_app
from app.services.instrument_service import InstrumentService
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.instrument_repo import InstrumentRegistryRepository


def _quote_body(code: str, name: str, price: str, prefix: str) -> str:
    """A real-shaped tencent quote line (same field layout as RAW_OK)."""
    return (
        f'v_{prefix}{code}="1~{name}~{code}~{price}~1651.00~1655.00~32924~85755~24354~'
        f"{price}~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
        f"{price}~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
        f"{price}/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
        f"{price}/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
        f'4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
    )


def _smartbox_body(query: str) -> str:
    """Real-shaped smartbox response: ^-separated candidates, ~-split fields."""
    return (
        f'v_hint="{query}~2~000831~中国稀土~zgxt~11^'
        f'{query}~1~600111~北方稀土~bfxt~11^'
        f'{query}~4~01928.HK~非A股条目~HK~1"\n'
    )


SZSE_OK = _quote_body("000831", "中国稀土", "24.83", "sz")


@pytest.fixture()
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state._test_factory = factory  # restart simulation reads this
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _route_http(monkeypatch, *, quote_response: str, smartbox_response: str | None = None):
    """Split fake routing: quote host → quote body, smartbox host → hints."""
    def fake_get(url, timeout=None, **_kwargs):
        if "smartbox" in url:
            if smartbox_response is None:
                raise httpx.ConnectTimeout("offline")
            return httpx.Response(200, content=smartbox_response.encode("gbk"))
        return httpx.Response(200, content=quote_response.encode("gbk"))
    monkeypatch.setattr(httpx, "get", fake_get)


def test_unknown_code_search_persists_across_restart(client, monkeypatch):
    _route_http(monkeypatch, quote_response=SZSE_OK)
    resp = client.get("/api/v1/instruments", params={"query": "000831"})
    assert resp.status_code == 200
    instrument = resp.json()["results"][0]["instrument"]
    assert instrument["code"] == "000831"
    assert instrument["name"] == "中国稀土"
    assert instrument["exchange"] == "SZSE"

    # "restart": a brand-new service/session on the same DB still resolves it
    with session_scope(client.app.state._test_factory) as session:
        profile = InstrumentService(session).get_profile("SZSE:000831", allow_remote=False)
        assert profile is not None
        assert profile.name == "中国稀土"
        row = InstrumentRegistryRepository(session).get("SZSE:000831")
        assert row is not None and row.origin == "resolved"


def test_watchlist_add_raw_code_guarantees_profile(client, monkeypatch):
    _route_http(monkeypatch, quote_response=SZSE_OK)
    added = client.post("/api/v1/watchlist", json={"instrument": "000831", "note": ""})
    assert added.status_code == 201
    # the profile exists without any prior search — workspace can open
    got = client.get("/api/v1/instruments/SZSE:000831")
    assert got.status_code == 200
    assert got.json()["instrument"]["name"] == "中国稀土"


def test_offline_code_add_degrades_to_code_only_then_heals(client, monkeypatch):
    # fully offline: quote + smartbox fail
    def offline(url, timeout=None):
        raise httpx.ConnectTimeout("offline")
    monkeypatch.setattr(httpx, "get", offline)

    added = client.post("/api/v1/watchlist", json={"instrument": "000831", "note": ""})
    assert added.status_code == 201
    got = client.get("/api/v1/instruments/SZSE:000831")
    assert got.status_code == 200  # workspace opens even offline
    assert got.json()["instrument"]["name"] == "000831"  # honest placeholder

    # network returns: an explicit search enriches the code_only row
    _route_http(monkeypatch, quote_response=SZSE_OK)
    healed = client.get("/api/v1/instruments", params={"query": "000831"})
    assert healed.json()["results"][0]["instrument"]["name"] == "中国稀土"


def test_chinese_name_search_resolves_remote(client, monkeypatch):
    _route_http(
        monkeypatch,
        quote_response=SZSE_OK,
        smartbox_response=_smartbox_body("中国稀土"),
    )
    resp = client.get("/api/v1/instruments", params={"query": "中国稀土"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert any(
        r["instrument"]["code"] == "000831" and r["instrument"]["name"] == "中国稀土"
        for r in results
    )
    # candidates stay validated: the non-A-share smartbox entry never lands
    with session_scope(client.app.state._test_factory) as session:
        repo = InstrumentRegistryRepository(session)
        assert repo.get("SSE:600111") is not None  # valid A-share candidate kept
        assert repo.get_by_code("01928") is None  # HK-shaped entry dropped


def test_invalid_instrument_never_resolves(client):
    assert client.get("/api/v1/instruments", params={"query": "999999"}).json()["count"] == 0
    assert client.get("/api/v1/instruments/NOPE:123456").status_code == 404
