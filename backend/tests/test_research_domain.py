"""Research domain: traceability + referential integrity (任务书 §28/§29/§75 前置)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.evidence import (
    AuthorityLevel, utc_now,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
)
from app.domain.research import (
    Claim,
    ClaimStatus,
    ClaimType,
    CorporateEvent,
    EventType,
    InvestmentThesis,
    ThesisStatus,
)
from app.storage.orm import Base
from app.storage.research_repo import ReferenceNotFoundError, ResearchRepository
from app.storage.repository import EvidenceRepository

AS_OF = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


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
def evidence_repo(dbsession):
    return EvidenceRepository(dbsession)


@pytest.fixture()
def research_repo(dbsession):
    return ResearchRepository(dbsession)


def _quote_evidence(price: float) -> EvidenceRecord:
    available = AS_OF - timedelta(days=1)
    return EvidenceRecord(
        instrument_id="SSE:600519",
        evidence_type=EvidenceType.MARKET_QUOTE,
        title=f"SSE:600519 market_quote {price}",
        summary=f"market quote: price={price}",
        source="tencent_quote",
        source_type="market_data_redistributor",
        authority_level=AuthorityLevel.B2,
        fact_status=FactStatus.CONFIRMED_FACT,
        event_time=available - timedelta(minutes=1),
        available_time=available,
        ingested_time=available + timedelta(minutes=1),
        revision_time=available + timedelta(minutes=1),
        metadata={"price": price},
    )


def _claim(evidence_ids: tuple[str, ...], snapshot_id: str = "snap_test000000000000") -> Claim:
    return Claim(
        instrument_id="SSE:600519",
        snapshot_id=snapshot_id,
        statement="贵州茅台当前估值处于近五年低位",
        claim_type=ClaimType.VALUATION_ASSESSMENT,
        supporting_evidence_refs=evidence_ids,
        fact_status=FactStatus.CONFIRMED_FACT,
        confidence=0.8,
        status=ClaimStatus.PROPOSED,
    )


def _thesis(claim_ids: tuple[str, ...], snapshot_id: str = "snap_test000000000000") -> InvestmentThesis:
    return InvestmentThesis(
        instrument_id="SSE:600519",
        snapshot_id=snapshot_id,
        title="估值修复论点",
        description="基于估值处于低位与基本面稳定的论点",
        supporting_claims=claim_ids,
        confidence=0.75,
        catalysts=("白酒需求回暖", "分红提升"),
        risks=("消费疲软", "政策限制"),
        trigger_conditions=("批价回升",),
        invalidate_conditions=("批价连续两季下行",),
        status=ThesisStatus.ACTIVE,
    )


def test_claim_requires_existing_evidence(dbsession, research_repo):
    with pytest.raises(ReferenceNotFoundError):
        research_repo.save_claim(_claim(("ev_doesnotexist",)))


def test_claim_without_any_evidence_is_rejected_by_domain():
    with pytest.raises(ValueError):
        _claim(())


def test_thesis_requires_existing_claims(dbsession, research_repo):
    with pytest.raises(ReferenceNotFoundError):
        research_repo.save_thesis(_thesis(("clm_doesnotexist",)))


def test_full_traceability_chain_thesis_claim_evidence(dbsession, evidence_repo, research_repo):
    """§75 前置：Thesis → Claim → Evidence 每一跳真实存在。"""
    from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
    from app.storage.orm import SnapshotORM

    ev_id, _ = evidence_repo.save(_quote_evidence(1648.0))

    snap = EvidenceSnapshot(
        instrument_id="SSE:600519", as_of=utc_now(), items=(),
        created_at=utc_now(),
    )
    # pin the evidence
    snap = EvidenceSnapshot(
        instrument_id="SSE:600519", as_of=utc_now(),
        items=(SnapshotItem(evidence_id=ev_id, content_hash=snap.content_hash),),
        created_at=utc_now(),
    )
    dbsession.add(
        SnapshotORM(
            snapshot_id=snap.snapshot_id, content_hash=snap.content_hash,
            instrument_id=snap.instrument_id, as_of=snap.as_of,
            items_json=[i.model_dump(mode="json") for i in snap.items],
            created_at=snap.created_at,
        )
    )
    dbsession.flush()

    claim = _claim((ev_id,), snapshot_id=snap.snapshot_id)
    claim_id = research_repo.save_claim(claim)

    thesis = _thesis((claim_id,), snapshot_id=snap.snapshot_id)
    thesis_id = research_repo.save_thesis(thesis)

    # walk the chain backwards through the repositories
    saved_thesis = next(
        t for t in research_repo.list_theses("SSE:600519") if t.thesis_id == thesis_id
    )
    assert saved_thesis.supporting_claims == (claim_id,)

    saved_claim = research_repo.get_claim(claim_id)
    assert saved_claim is not None
    assert ev_id in saved_claim.supporting_evidence_refs

    saved_evidence = evidence_repo.list_for_instrument("SSE:600519")
    assert any(e.evidence_id == ev_id for e in saved_evidence)
    # evidence carries its source provenance (M3 chain)
    assert all(e.source for e in saved_evidence)


def test_opposing_evidence_also_validated(dbsession, evidence_repo, research_repo):
    ev_id, _ = evidence_repo.save(_quote_evidence(1648.0))
    claim = Claim(
        instrument_id="SSE:600519",
        snapshot_id="snap_test000000000000",
        statement="多空对照断言",
        claim_type=ClaimType.GROWTH_OUTLOOK,
        supporting_evidence_refs=(ev_id,),
        opposing_evidence_refs=("ev_missing",),
        fact_status=FactStatus.ANALYST_INFERENCE,
        confidence=0.5,
    )
    with pytest.raises(ReferenceNotFoundError):
        research_repo.save_claim(claim)


def test_corporate_event_lifecycle(dbsession, evidence_repo, research_repo):
    ev_id, _ = evidence_repo.save(_quote_evidence(1648.0))
    occurred = AS_OF - timedelta(days=7)
    event = CorporateEvent(
        instrument_id="SSE:600519",
        event_type=EventType.EARNINGS,
        title="发布2026年中报",
        description="半年报披露：营收与净利同比变化",
        occurred_at=occurred,
        announced_at=occurred + timedelta(hours=2),
        evidence_refs=(ev_id,),
    )
    event_id = research_repo.save_event(event)
    events = research_repo.list_events("SSE:600519")
    assert len(events) == 1
    assert events[0].event_id == event_id
    assert events[0].event_type is EventType.EARNINGS

    with pytest.raises(ValueError):
        CorporateEvent(
            instrument_id="SSE:600519",
            event_type=EventType.EARNINGS,
            title="时间倒置",
            description="公告早于发生",
            occurred_at=AS_OF,
            announced_at=occurred,
        )
