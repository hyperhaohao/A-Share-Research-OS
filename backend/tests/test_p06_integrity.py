"""P0-06: cross-instrument / cross-snapshot integrity negative tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.domain.evidence import (
    AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus, utc_now,
)
from app.domain.research import Claim, ClaimType, FactStatus as CF
from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.storage.orm import Base
from app.sources.runtime import reset_runtime


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
    yield TestClient(app), factory
    reset_runtime()


def _ev(session, instrument_id: str, price: float) -> str:
    t = utc_now()
    eid, _ = EvidenceRepository(session).save(
        EvidenceRecord(
            instrument_id=instrument_id,
            evidence_type=EvidenceType.MARKET_QUOTE,
            title=f"{instrument_id} quote",
            summary=f"price={price}",
            source="tencent_quote",
            source_type="market_data_redistributor",
            authority_level=AuthorityLevel.B2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=t,
            available_time=t,
            ingested_time=t,
            revision_time=t,
            metadata={"price": price},
        )
    )
    return eid


def _snapshot(session, instrument_id: str, evidence_ids: list) -> str:
    snap = EvidenceSnapshot(
        instrument_id=instrument_id,
        as_of=utc_now(),
        items=tuple(SnapshotItem(evidence_id=e, content_hash="a" * 64) for e in evidence_ids),
        created_at=utc_now(),
    )
    from app.storage.orm import SnapshotORM
    session.add(
        SnapshotORM(
            snapshot_id=snap.snapshot_id,
            content_hash=snap.content_hash,
            instrument_id=snap.instrument_id,
            as_of=snap.as_of,
            items_json=[i.model_dump(mode="json") for i in snap.items],
            created_at=snap.created_at,
        )
    )
    session.flush()
    return snap.snapshot_id


def test_cross_instrument_evidence_rejected(client):
    """Claim for A citing evidence from B → refused."""
    client, factory = client
    session = factory()
    try:
        ev_a = _ev(session, "SSE:600519", 100.0)
        ev_b = _ev(session, "SZSE:000001", 11.0)
        snap_a = _snapshot(session, "SSE:600519", [ev_a])
        session.flush()

        from app.storage.research_repo import ResearchRepository
        from app.domain.research import Claim, ClaimType
        research = ResearchRepository(session)
        with pytest.raises(Exception):
            research.save_claim(
                Claim(
                    instrument_id="SSE:600519",
                    snapshot_id=snap_a,
                    statement="cross-instrument",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    supporting_evidence_refs=(ev_b,),
                    fact_status=FactStatus.CONFIRMED_FACT,
                    confidence=0.9,
                )
            )
    finally:
        session.close()


def test_cross_snapshot_evidence_rejected(client):
    """Claim for snapshot A citing evidence NOT pinned by A → refused."""
    client, factory = client
    session = factory()
    try:
        ev_a = _ev(session, "SSE:600519", 100.0)
        ev_b = _ev(session, "SSE:600519", 200.0)
        snap_a = _snapshot(session, "SSE:600519", [ev_a])
        session.flush()

        from app.storage.research_repo import ResearchRepository
        from app.domain.research import Claim, ClaimType
        research = ResearchRepository(session)
        with pytest.raises(Exception):
            research.save_claim(
                Claim(
                    instrument_id="SSE:600519",
                    snapshot_id=snap_a,
                    statement="cross-snapshot",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    supporting_evidence_refs=(ev_b,),  # not pinned by snap_a
                    fact_status=FactStatus.CONFIRMED_FACT,
                    confidence=0.9,
                )
            )
    finally:
        session.close()
