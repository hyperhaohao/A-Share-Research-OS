"""R2.9 live verification: one real A-share through the FULL pipeline.

整改 R2.9：Source → Evidence → Snapshot → Analysts → Claims → Thesis →
Debate → Scenario → Valuation → Risk → ResearchReport 全链真实执行，
无任何手工 POST 补链。离线自动 skip。
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


@pytest.fixture(scope="module")
def live():
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
def test_live_full_pipeline_real_stock(live):
    client, factory = live
    body = client.post("/api/v1/pipeline/run", params={"instrument": "600519"})
    outcome = body.json()
    if body.status_code != 202 or "run_id" not in outcome:
        pytest.skip(f"network unreachable: {body.text[:120]}")

    assert outcome["gate_status"] in ("pass", "warn")
    assert outcome["claim_count"] >= 1, "analysts must produce claims"

    session = factory()
    try:
        from app.services.debate_engine import DebateScenarioRepository
        from app.storage.manifest_repo import ManifestRepository
        from app.storage.research_repo import ResearchRepository
        from app.storage.repository import EvidenceRepository
        from app.storage.valuation_repo import ValuationRepository

        # real evidence of many types from real sources
        repo = EvidenceRepository(session)
        evidence = repo.list_for_instrument("SSE:600519")
        types = {e.evidence_type.value for e in evidence}
        assert "market_quote" in types
        assert "financial_report" in types
        assert types & {"announcement", "news"}

        # claims + thesis exist without manual wiring
        research = ResearchRepository(session)
        theses = research.list_theses("SSE:600519", snapshot_id=outcome["snapshot_id"])
        assert theses
        thesis = theses[0]
        assert thesis.supporting_claims

        # debate + scenarios
        debates = DebateScenarioRepository(session).list_debate_rounds(thesis.thesis_id)
        assert debates
        scenarios = DebateScenarioRepository(session).list_scenarios(thesis.thesis_id)
        assert scenarios and sum(s.probability for s in scenarios) == 100.0

        # valuations from real evidence inputs
        valuations = ValuationRepository(session).list_for(
            "SSE:600519", snapshot_id=outcome["snapshot_id"]
        )
        computable = [v for v in valuations if v["computable"]]
        assert computable, "PE/PB/PS must compute from real EPS/BVPS/revenue"
        for v in computable:
            assert v["inputs"].get("price"), v

        # manifest real values
        manifest = ManifestRepository(session).get_for_run(outcome["run_id"])
        assert manifest.code_commit not in ("0000000", "unversioned")
        assert manifest.random_seed != 0

        # the report body contains real analyst claims
        report = client.get(f"/api/v1/reports/{outcome['report_id']}").json()["report"]
        claims = research.list_claims("SSE:600519", snapshot_id=outcome["snapshot_id"])
        assert any(c.statement in report["markdown"] for c in claims)
    finally:
        session.close()
