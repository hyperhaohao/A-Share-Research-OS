"""Debate + scenario tests (任务书 §35/§37)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.debate import Scenario, ScenarioKind
from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
)
from app.domain.research import (
    Claim,
    ClaimStatus,
    ClaimType,
    InvestmentThesis,
    ThesisStatus,
)
from app.services.debate_engine import DebateEngine, DebateScenarioRepository
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.storage.research_repo import ReferenceNotFoundError, ResearchRepository

AS_OF = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)
SNAPSHOT_ID = "snap_test000000000000"


@pytest.fixture()
def dbsession():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def thesis_id(dbsession):
    """Seed evidence -> claim -> thesis and return the thesis id."""
    repo = EvidenceRepository(dbsession)
    available = AS_OF - timedelta(days=1)
    ev_id, _ = repo.save(
        EvidenceRecord(
            instrument_id="SSE:600519",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title="quote",
            summary="market quote: price=1648.0",
            source="tencent_quote",
            source_type="market_data_redistributor",
            authority_level=AuthorityLevel.B2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=available - timedelta(minutes=1),
            available_time=available,
            ingested_time=available + timedelta(minutes=1),
            revision_time=available + timedelta(minutes=1),
            metadata={"price": 1648.0},
        )
    )
    research = ResearchRepository(dbsession)
    claim_id = research.save_claim(
        Claim(
            instrument_id="SSE:600519",
            snapshot_id=SNAPSHOT_ID,
            statement="贵州茅台当前估值处于近五年低位",
            claim_type=ClaimType.VALUATION_ASSESSMENT,
            supporting_evidence_refs=(ev_id,),
            fact_status=FactStatus.CONFIRMED_FACT,
            confidence=0.8,
            status=ClaimStatus.PROPOSED,
        )
    )
    thesis_id = research.save_thesis(
        InvestmentThesis(
            instrument_id="SSE:600519",
            snapshot_id=SNAPSHOT_ID,
            title="估值修复论点",
            description="低估值 + 稳定基本面",
            supporting_claims=(claim_id,),
            confidence=0.75,
            risks=("消费疲软", "政策限制"),
            status=ThesisStatus.ACTIVE,
        )
    )
    return thesis_id


class TestScenarioSet:
    def test_probabilities_must_sum_to_100(self, dbsession):
        repo = DebateScenarioRepository(dbsession)
        scenarios = [
            Scenario(
                thesis_id="ths_test000000000001",
                snapshot_id=SNAPSHOT_ID,
                instrument_id="SSE:600519",
                kind=ScenarioKind.BEAR,
                probability=30,
            ),
            Scenario(
                thesis_id="ths_test000000000001",
                snapshot_id=SNAPSHOT_ID,
                instrument_id="SSE:600519",
                kind=ScenarioKind.BASE,
                probability=40,
            ),
            Scenario(
                thesis_id="ths_test000000000001",
                snapshot_id=SNAPSHOT_ID,
                instrument_id="SSE:600519",
                kind=ScenarioKind.BULL,
                probability=20,
            ),
        ]
        with pytest.raises(ValueError):
            repo.save_scenario_set(scenarios)

    def test_valid_set_persists(self, dbsession):
        repo = DebateScenarioRepository(dbsession)
        scenarios = [
            Scenario(
                thesis_id="ths_test000000000001",
                snapshot_id=SNAPSHOT_ID,
                instrument_id="SSE:600519",
                kind=kind,
                probability=p,
            )
            for kind, p in (
                (ScenarioKind.BEAR, 25),
                (ScenarioKind.BASE, 50),
                (ScenarioKind.BULL, 25),
            )
        ]
        ids = repo.save_scenario_set(scenarios)
        assert len(ids) == 3
        loaded = repo.list_scenarios("ths_test000000000001")
        assert sum(s.probability for s in loaded) == 100.0
        assert {s.kind for s in loaded} == {ScenarioKind.BEAR, ScenarioKind.BASE, ScenarioKind.BULL}


thesis_id_stub = "ths_test000000000001"


class TestDebate:
    def test_debate_creates_cited_bull_bear_claims(self, dbsession, thesis_id):
        engine = DebateEngine(dbsession)
        debate = engine.run_round(thesis_id)
        assert debate.round_no == 1

        research = ResearchRepository(dbsession)
        bull = research.get_claim(debate.bull_claim_id)
        bear = research.get_claim(debate.bear_claim_id)
        assert bull is not None and bear is not None
        assert "看多论点" in bull.statement
        assert "看空论点" in bear.statement
        # debate claims are analyst inference citing existing evidence
        assert bull.fact_status.value == "analyst_inference"
        assert bull.supporting_evidence_refs  # cites the seeded quote evidence

    def test_multiple_rounds_and_exhaustion(self, dbsession, thesis_id):
        engine = DebateEngine(dbsession)
        engine.run_round(thesis_id)
        engine.run_round(thesis_id)
        engine.run_round(thesis_id)
        with pytest.raises(ValueError):
            engine.run_round(thesis_id)
        rounds = DebateScenarioRepository(dbsession).list_debate_rounds(thesis_id)
        assert [r.round_no for r in rounds] == [1, 2, 3]

    def test_thesis_without_claims_cannot_exist(self, dbsession):
        """§35 precondition: a debate needs a thesis, a thesis needs claims,
        and claims need evidence — so a debate can never lack an evidence base."""
        research = ResearchRepository(dbsession)
        with pytest.raises(ValueError):
            research.save_thesis(
                InvestmentThesis(
                    instrument_id="SSE:600519",
                    snapshot_id=SNAPSHOT_ID,
                    title="无主张论点",
                    description="应拒绝",
                    supporting_claims=(),
                    confidence=0.5,
                )
            )
