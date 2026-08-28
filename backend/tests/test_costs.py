"""Cost accounting endpoint tests (任务书 §70)."""


from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()



def test_costs_shape_and_pipeline_accounting(client=None):
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
    client = TestClient(app)

    # a research run exists (created via the research-runs API)
    client.post(
        "/api/v1/research-runs",
        params={"instrument": "600519", "as_of": _pit_as_of()},
    )
    client.post(
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
    costs = client.get("/api/v1/costs").json()
    assert "totals" in costs
    assert costs["totals"]["runs"] >= 1
    assert costs["totals"]["llm_calls"] == 0  # deterministic pipeline: no LLM calls
    for run in costs["runs"]:
        # running runs have no duration yet (finished_at unset) — honest shape
        assert run["duration_ms"] is None or run["duration_ms"] >= 0
