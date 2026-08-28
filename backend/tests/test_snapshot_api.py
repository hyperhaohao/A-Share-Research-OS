"""Snapshot + research-run API tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()



RAW_OK = (
    'v_sh600519="1~贵州茅台~600519~1648.00~1651.00~1655.00~32924~85755~24354~'
    "1648.00~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "1648.10~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "1648.00/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    "1648.00/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
    '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
)


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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def test_collect_then_snapshot_then_run(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)

    # collect real evidence
    collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
    assert collected["created"] >= 1

    # build a snapshot pinned to an explicit as_of (default = per-request now)
    as_of = _pit_as_of()
    snap = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": as_of},
    ).json()["snapshot"]
    assert snap["evidence_count"] == 1
    assert snap["snapshot_id"].startswith("snap_")

    # same as_of → identical immutable snapshot (idempotent)
    snap2 = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": as_of},
    ).json()["snapshot"]
    assert snap2["snapshot_id"] == snap["snapshot_id"]

    # research run pinned to the same as_of binds to the same snapshot
    run_body = client.post(
        "/api/v1/research-runs",
        params={"instrument": "600519", "as_of": as_of},
    ).json()
    assert run_body["run"]["snapshot_id"] == snap["snapshot_id"]
    assert run_body["run"]["status"] == "running"


def test_pit_api_future_snapshot_excludes_future_evidence(client, monkeypatch):
    """Collect now, request a snapshot as_of BEFORE the quote existed."""
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    client.post("/api/v1/evidence/collect", params={"instrument": "600519"})

    past = client.post(
        "/api/v1/snapshots",
        params={"instrument": "600519", "as_of": "2020-01-01T00:00:00+00:00"},
    ).json()["snapshot"]
    assert past["evidence_count"] == 0  # quote didn't exist then — invisible


def test_get_snapshot_unknown_is_404(client):
    resp = client.get("/api/v1/snapshots/snap_doesnotexist")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "snapshot.not_found"


def test_bad_as_of_is_validation_error(client):
    resp = client.post("/api/v1/snapshots", params={"instrument": "600519", "as_of": "not-a-date"})
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "common.validation_error"
