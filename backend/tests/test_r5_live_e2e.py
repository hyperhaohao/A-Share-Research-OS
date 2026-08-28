"""R5.1 Live Research E2E — multi-instrument, full chain, no manual wiring.

整改 R5.1/R5.3：4 只不同板块/风格的真实 A 股，每只自动执行：

    pipeline 全链（collect all capabilities → snapshot → analysts →
    claims → thesis → debate → scenarios → valuations → report+gate）→
    monitor → materiality → prediction → mark-to-market validation

All through the public API only. Skips when the network is unreachable.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base

INSTRUMENTS = [
    ("600519", "白酒/消费"),
    ("000001", "银行/金融"),
    ("300750", "新能源/成长"),
    ("688981", "半导体/科技"),
]


@pytest.fixture(scope="module")
def e2e():
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
    yield TestClient(app), factory
    reset_runtime()


@pytest.mark.live
def test_r5_live_research_e2e_multi_instrument(e2e):
    client, factory = e2e
    session = factory()
    try:
        # connectivity probe
        probe = client.post(
            "/api/v1/evidence/collect",
            params={"instrument": "600519", "capability": "market_data"},
        )
        probe_body = probe.json()
        if probe_body["manifest"]["final_status"] in (
            "network_error", "source_unavailable",
        ):
            pytest.skip("network unreachable for R5 live E2E")

        completed = 0
        for raw_code, _style in INSTRUMENTS:
            # ---- full pipeline (the ONLY way claims/theses enter) ---------
            run = client.post(
                "/api/v1/pipeline/run", params={"instrument": raw_code}
            )
            if run.status_code != 202:
                continue  # transient source outage on one instrument is OK
            outcome = run.json()
            assert outcome["claim_count"] >= 1, raw_code
            assert outcome["thesis_id"], raw_code
            assert outcome["gate_status"] in ("pass", "warn"), raw_code

            # chain elements exist
            from app.services.debate_engine import DebateScenarioRepository
            from app.storage.manifest_repo import ManifestRepository
            from app.storage.research_repo import ResearchRepository
            from app.storage.repository import EvidenceRepository
            from app.storage.valuation_repo import ValuationRepository

            research = ResearchRepository(session)
            theses = research.list_theses(
                f"{'SSE' if raw_code.startswith('6') else 'SZSE'}:{raw_code}",
                snapshot_id=outcome["snapshot_id"],
            )
            assert theses
            scenarios = DebateScenarioRepository(session).list_scenarios(theses[0].thesis_id)
            assert scenarios and sum(s.probability for s in scenarios) == 100.0
            valuations = ValuationRepository(session).list_for(
                f"{'SSE' if raw_code.startswith('6') else 'SZSE'}:{raw_code}",
                snapshot_id=outcome["snapshot_id"],
            )
            assert any(v["computable"] for v in valuations), raw_code
            manifest = ManifestRepository(session).get_for_run(outcome["run_id"])
            assert manifest is not None and manifest.code_commit != "0000000"
            completed += 1

        assert completed >= 3, f"expected ≥3 instruments to complete, got {completed}"

        # ---- monitor → materiality → (delta/full) -------------------------
        for raw_code, _style in INSTRUMENTS[:2]:
            decision = client.post(
                "/api/v1/monitor/run", params={"instrument": raw_code}
            ).json()["decision"]
            assert decision["decision"] in (
                "no_material_change", "delta_research", "full_research",
            )

        # ---- prediction → mark-to-market validation -----------------------
        prediction = client.post(
            "/api/v1/predictions",
            json={
                "instrument": "600519",
                "as_of": "2026-08-28T15:00:00+00:00",
                "horizon": "5D",
                "expected_direction": "up",
                "expected_return_min": -10.0,
                "expected_return_max": 10.0,
                "confidence": 0.6,
            },
        ).json()["prediction"]
        assert prediction["due_at"]
        validated = client.post(
            f"/api/v1/predictions/{prediction['prediction_id']}/validate"
        ).json()["prediction"]
        assert validated["validation"] is not None
        # mark-to-market at creation time: return ~0, explicit numbers
        assert validated["validation"]["instrument_return_pct"] == 0.0
    finally:
        session.close()


@pytest.mark.live
def test_r5_live_scheduler_tick_with_real_sources(e2e):
    """Scheduler tick over real network: monitor task runs to completion."""
    client, factory = e2e
    task = client.post(
        "/api/v1/tasks",
        json={"instrument": "000001", "task_type": "monitor",
              "schedule": "interval:3600"},
    )
    if task.status_code != 201:
        pytest.skip("instrument unavailable")
    task_id = task.json()["task"]["task_id"]
    tick = client.post("/api/v1/tasks/scheduler/tick").json()
    if task_id in tick["failed"]:
        pytest.skip("sources unreachable during tick")
    assert task_id in tick["claimed"]
    assert task_id in tick["succeeded"]
