"""Monitor + MaterialityJudge tests (任务书 §45)."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.domain.snapshot import EvidenceSnapshot
from app.services.monitor import MaterialityJudge
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK

AS_OF = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client():
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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _quote_response(price: str) -> httpx.Response:
    body = RAW_OK.replace("1648.00~1651.00", f"{price}~1651.00", 1)
    return httpx.Response(200, content=body.encode("gbk"))


class TestMaterialityJudgeUnit:
    def _snap(self) -> EvidenceSnapshot:
        return EvidenceSnapshot(
            instrument_id="SSE:600519", as_of=AS_OF, items=(), created_at=AS_OF
        )

    def test_no_change_when_nothing_differs(self):
        judge = MaterialityJudge()
        snap = self._snap()
        decision, reasons = judge.decide(
            old_snapshot=snap, new_snapshot=snap, added=[], removed=[], price_change_pct=None
        )
        assert decision.value == "no_material_change"

    def test_big_price_move_is_full_research(self):
        snap = self._snap()
        decision, reasons = MaterialityJudge().decide(
            old_snapshot=snap, new_snapshot=snap, added=[], removed=[],
            price_change_pct=-6.2,
        )
        assert decision.value == "full_research"
        assert any("price moved" in r for r in reasons)

    def test_small_added_evidence_is_delta(self):
        snap = self._snap()
        decision, _ = MaterialityJudge().decide(
            old_snapshot=snap, new_snapshot=snap, added=["ev_1"], removed=[],
            price_change_pct=0.5, added_kinds=["announcement"],
        )
        assert decision.value == "delta_research"

    def test_quote_only_reobservation_is_noise(self):
        snap = self._snap()
        decision, _ = MaterialityJudge().decide(
            old_snapshot=snap, new_snapshot=snap, added=["ev_1"], removed=[],
            price_change_pct=0.0, added_kinds=["market_quote"],
        )
        assert decision.value == "no_material_change"

    def test_no_delta_below_threshold(self):
        snap = self._snap()
        strict = MaterialityJudge(added_delta_threshold=3)
        decision2, _ = strict.decide(
            old_snapshot=snap, new_snapshot=snap, added=["ev_1"], removed=[],
            price_change_pct=0.0, added_kinds=["announcement"],
        )
        assert decision2.value == "no_material_change"

    def test_first_pass_is_full_research(self):
        decision, reasons = MaterialityJudge().decide(
            old_snapshot=None, new_snapshot=self._snap(), added=[], removed=[],
            price_change_pct=None,
        )
        assert decision.value == "full_research"
        assert any("no previous snapshot" in r for r in reasons)


def test_monitor_first_pass_is_full_research(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote_response("1648.00"))
    body = client.post("/api/v1/monitor/run", params={"instrument": "600519"}).json()["decision"]
    assert body["decision"] == "full_research"
    assert "no previous snapshot" in body["reasons"][0]
    assert body["old_snapshot_id"] is None


def test_monitor_second_pass_no_change_then_delta(client, monkeypatch):
    """Same quote twice → no_material_change; changed price → delta."""
    # Patch BEFORE run 1: the first two passes see the identical 1648 quote.
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote_response("1648.00"))
    client.post("/api/v1/monitor/run", params={"instrument": "600519"})

    # identical content → dedup keeps the same evidence → no delta
    second = client.post("/api/v1/monitor/run", params={"instrument": "600519"}).json()["decision"]
    assert second["decision"] == "no_material_change"

    # a genuinely new price → new evidence → delta_research
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote_response("1680.00"))
    third = client.post("/api/v1/monitor/run", params={"instrument": "600519"}).json()["decision"]
    assert third["decision"] == "delta_research", f"third={third}"
    assert third["price_change_pct"] is not None

    # a big move → full_research
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote_response("1900.00"))
    fourth = client.post("/api/v1/monitor/run", params={"instrument": "600519"}).json()["decision"]
    assert fourth["decision"] == "full_research"


def test_decisions_listing(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote_response("1648.00"))
    client.post("/api/v1/monitor/run", params={"instrument": "600519"})
    listed = client.get("/api/v1/monitor/decisions", params={"instrument_id": "SSE:600519"}).json()
    assert listed["count"] >= 1
    assert listed["results"][0]["decision"] in ("full_research", "no_material_change", "delta_research")
