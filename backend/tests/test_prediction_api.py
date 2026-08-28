"""Prediction API + one-shot validation + scheduler integration."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
)
from app.domain.evidence import utc_now
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


STATE: dict = {}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    STATE["factory"] = factory

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


def _seed_quote(client, price: float, available_at: datetime) -> str:
    """Insert a quote evidence atom with an explicit available_time."""
    from app.storage.repository import EvidenceRepository

    session = STATE["factory"]()
    try:
        record = EvidenceRecord(
            instrument_id="SSE:600519",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title=f"SSE:600519 market_quote {price}",
            summary=f"market quote: price={price}",
            source="tencent_quote",
            source_type="market_data_redistributor",
            authority_level=AuthorityLevel.B2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=available_at - timedelta(minutes=1),
            available_time=available_at,
            ingested_time=available_at,
            revision_time=available_at,
            metadata={"price": price},
        )
        evidence_id, _ = EvidenceRepository(session).save(record)
        session.commit()
        return evidence_id
    finally:
        session.close()


def test_create_prediction_and_due_listing(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    created = client.post(
        "/api/v1/predictions",
        json={
            "instrument": "600519",
            "as_of": "2026-07-01T15:00:00+00:00",
            "horizon": "5D",
            "expected_direction": "up",
            "expected_return_min": 0.0,
            "expected_return_max": 5.0,
            "confidence": 0.7,
        },
    )
    assert created.status_code == 201
    prediction = created.json()["prediction"]
    assert prediction["prediction_id"].startswith("prd_")
    assert prediction["due_at"] == "2026-07-08T15:00:00+00:00"  # 5 trading days

    due = client.get("/api/v1/predictions/due").json()
    assert due["count"] == 1  # due date long passed


def test_validation_flow_with_price_series(client, monkeypatch):
    """Start price at as_of, end price at due → deterministic outcome (§80)."""
    as_of = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    due = datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)
    _seed_quote(client, 1648.0, as_of)
    _seed_quote(client, 1730.4, due)  # exactly +5.0%

    created = client.post(
        "/api/v1/predictions",
        json={
            "instrument": "600519",
            "as_of": as_of.isoformat(),
            "horizon": "5D",
            "expected_direction": "up",
            "expected_return_min": 0.0,
            "expected_return_max": 10.0,
            "confidence": 0.7,
        },
    ).json()["prediction"]

    validated = client.post(
        f"/api/v1/predictions/{created['prediction_id']}/validate"
    ).json()["prediction"]
    validation = validated["validation"]
    assert validation["instrument_return_pct"] == pytest.approx(5.0)
    assert validation["direction_correct"] is True
    assert validation["range_hit"] is True

    # one-shot: second validate returns the same record
    again = client.post(
        f"/api/v1/predictions/{created['prediction_id']}/validate"
    ).json()["prediction"]["validation"]
    assert again["validation_id"] == validation["validation_id"]


def test_premature_validation_is_422(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    created = client.post(
        "/api/v1/predictions",
        json={
            "instrument": "600519",
            "as_of": "2099-01-01T00:00:00+00:00",  # start price not yet visible
            "horizon": "5D",
            "expected_direction": "up",
            "expected_return_min": 0.0,
            "expected_return_max": 5.0,
            "confidence": 0.7,
        },
    ).json()["prediction"]
    resp = client.post(f"/api/v1/predictions/{created['prediction_id']}/validate")
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "prediction.not_matured"


def test_validation_task_via_scheduler(client, monkeypatch):
    """§48: prediction_validation task type validates due predictions."""
    as_of = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    due = datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)
    _seed_quote(client, 1648.0, as_of)
    _seed_quote(client, 1600.0, due)  # -2.9%

    created = client.post(
        "/api/v1/predictions",
        json={
            "instrument": "600519",
            "as_of": as_of.isoformat(),
            "horizon": "5D",
            "expected_direction": "down",
            "expected_return_min": -10.0,
            "expected_return_max": 0.0,
            "confidence": 0.6,
        },
    ).json()["prediction"]

    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    task = client.post(
        "/api/v1/tasks",
        json={"instrument": "600519", "task_type": "prediction_validation", "schedule": "interval:0"},
    ).json()["task"]
    tick = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] in tick["claimed"]
    assert task["task_id"] in tick["succeeded"]

    listed = client.get("/api/v1/predictions", params={"instrument_id": "SSE:600519"}).json()
    validated = [r for r in listed["results"] if "validation" in r]
    assert len(validated) == 1
    assert validated[0]["validation"]["instrument_return_pct"] == pytest.approx(-2.9126, abs=1e-3)
    assert validated[0]["validation"]["direction_correct"] is True  # expected down, price down

    _ = created, utc_now()
