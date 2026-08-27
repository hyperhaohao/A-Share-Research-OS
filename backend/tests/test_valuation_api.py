"""Valuation API tests: deterministic compute + explicit missing semantics."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


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


def test_pe_computation_persisted(client):
    body = client.post(
        "/api/v1/valuations/compute",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": "snap_test000000000000",
            "method": "pe",
            "inputs": {"price": 80.0, "eps_ttm": 4.0, "target_pe": 25},
        },
    ).json()["valuation"]
    assert body["computable"] is True
    assert body["value"] == pytest.approx(100.0)
    assert body["detail"]["upside_pct"] == pytest.approx(25.0)


def test_missing_inputs_persisted_as_gap(client):
    body = client.post(
        "/api/v1/valuations/compute",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": "snap_test000000000000",
            "method": "pe",
            "inputs": {"price": 80.0, "target_pe": 25},
        },
    ).json()["valuation"]
    assert body["computable"] is False
    assert body["value"] is None
    assert body["missing"][0]["name"] == "eps_ttm"


def test_list_valuations_filters_by_snapshot(client):
    for snapshot in ("snap_a000000000000000", "snap_b000000000000000"):
        client.post(
            "/api/v1/valuations/compute",
            json={
                "instrument_id": "SSE:600519",
                "snapshot_id": snapshot,
                "method": "pb",
                "inputs": {"price": 50.0, "bvps": 10.0, "target_pb": 4.0},
            },
        )
    all_rows = client.get("/api/v1/valuations", params={"instrument_id": "SSE:600519"}).json()
    assert all_rows["count"] == 2
    filtered = client.get(
        "/api/v1/valuations",
        params={"instrument_id": "SSE:600519", "snapshot_id": "snap_a000000000000000"},
    ).json()
    assert filtered["count"] == 1
    assert filtered["results"][0]["snapshot_id"] == "snap_a000000000000000"


def test_scenario_bound_valuation(client):
    """A valuation can be attached to a scenario (thesis binding from M9)."""
    body = client.post(
        "/api/v1/valuations/compute",
        json={
            "instrument_id": "SSE:600519",
            "snapshot_id": "snap_test000000000000",
            "thesis_id": "ths_test000000000001",
            "scenario_id": "scn_test000000000001",
            "method": "ddm",
            "inputs": {
                "price": 90.0,
                "dividend_per_share": 5.0,
                "dividend_growth": 0.02,
                "discount_rate": 0.07,
            },
        },
    ).json()["valuation"]
    assert body["scenario_id"] == "scn_test000000000001"
    assert body["computable"] is True
    assert body["value"] == pytest.approx(102.0)
