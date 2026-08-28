"""R1.8 live verification: 4 real A-shares × 4 capabilities → Evidence+Manifest.

整改 R1 DoD：至少 3–5 只不同类型真实 A 股，market/announcement/financial/news
均能形成真实 Evidence，且 Source → Evidence → SourceManifest 可追溯。

Skips automatically when the network is unreachable (offline CI stays green).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.domain.evidence import AuthorityLevel, EvidenceType, FactStatus
from app.sources.base import SourceStatus
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from tests.test_research_api import RAW_OK

# 4 boards × research styles (task书 §71): 消费 / 金融 / 新能源 / 半导体
INSTRUMENTS = [
    ("600519", "SSE:600519", "白酒/消费"),
    ("000001", "SZSE:000001", "银行/金融"),
    ("300750", "SZSE:300750", "动力电池/新能源"),
    ("688981", "SSE:688981", "半导体/科技"),
]

LIVE_CAPABILITIES = ["market_data", "announcements", "financials", "news"]


@pytest.fixture(scope="module")
def live_client():
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
    yield TestClientLike(app, factory)
    reset_runtime()


class TestClientLike:
    def __init__(self, app, factory):
        self.app = app
        self.factory = factory


def _offline(session) -> bool:
    """Probe with a real quote; True when the network is unreachable."""
    from app.services.evidence_collector import collect_capability_evidence

    outcome = collect_capability_evidence(
        "SSE:600519", "market_data", repo=EvidenceRepository(session), fresh=True
    )
    return outcome.manifest.final_status in ("network_error", "source_unavailable")


@pytest.mark.live
def test_r1_live_multicapability_evidence(live_client):
    """R1 DoD: 4 real instruments × 4 capabilities → traceable evidence."""
    from fastapi.testclient import TestClient

    client = TestClient(live_client.app)
    factory = live_client.factory

    session = factory()
    try:
        if _offline(session):
            pytest.skip("network unreachable for R1 live verification")

        repo = EvidenceRepository(session)
        for raw_code, instrument_id, style in INSTRUMENTS:
            collected = client.post(
                "/api/v1/evidence/collect",
                params={"instrument": raw_code, "capability": "market_data"},
            )
            assert collected.status_code == 200, collected.text

            for capability in LIVE_CAPABILITIES[1:]:
                outcome = client.post(
                    "/api/v1/evidence/collect",
                    params={"instrument": raw_code, "capability": capability},
                )
                assert outcome.status_code == 200, outcome.text
                manifest = outcome.json()["manifest"]
                # failed sources stay visible in the manifest, never faked
                assert manifest["final_status"] in (
                    "success", "partial", "no_data", "source_unavailable",
                )

            # traceability: per capability, evidence rows exist with manifest links
            evidence = repo.list_for_instrument(instrument_id)
            by_type = {e.evidence_type for e in evidence}
            assert EvidenceType.MARKET_QUOTE in by_type, instrument_id
            assert EvidenceType.ANNOUNCEMENT in by_type, instrument_id
            assert EvidenceType.FINANCIAL_REPORT in by_type, instrument_id
            assert EvidenceType.NEWS in by_type, instrument_id

            # announcements must never sit at media authority (整改 §6.6)
            for e in evidence:
                if e.evidence_type is EvidenceType.ANNOUNCEMENT:
                    assert e.fact_status.value == "official_disclosure"
                    assert e.authority_level in (AuthorityLevel.A2, AuthorityLevel.B2)
                if e.evidence_type is EvidenceType.NEWS:
                    assert e.authority_level is AuthorityLevel.C2

            # financials carry the PIT anchor (NOTICE_DATE)
            financials = [
                e for e in evidence
                if e.evidence_type is EvidenceType.FINANCIAL_REPORT
            ]
            assert financials, instrument_id
            for e in financials:
                assert e.available_time >= e.event_time  # notice >= period end
    finally:
        session.close()


@pytest.mark.live
def test_r1_live_financial_metrics_normalization(live_client):
    """Financial evidence carries the normalized metrics the valuation engine needs."""
    from fastapi.testclient import TestClient

    client = TestClient(live_client.app)
    factory = live_client.factory
    session = factory()
    try:
        from app.services.evidence_collector import collect_capability_evidence

        outcome = collect_capability_evidence(
            "SSE:600519", "financials", repo=EvidenceRepository(session), fresh=True
        )
        if outcome.manifest.final_status in ("network_error", "source_unavailable"):
            pytest.skip("network unreachable")
        assert outcome.manifest.final_status == "success"
        metrics = outcome.evidence[0].metadata
        for key in ("eps", "bvps", "roe_pct", "revenue_yuan", "net_profit_yuan"):
            assert metrics.get(key) is not None, key
        # normalized inputs usable by the deterministic valuation engine
        assert metrics["eps"] > 0
    finally:
        session.close()
