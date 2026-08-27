"""Evidence persistence: dedup idempotency + manifest + PIT listing."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
    SourceManifest,
)
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository


@pytest.fixture()
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = factory()
    yield EvidenceRepository(session)
    session.close()


def _record(offset_hours: float = 0) -> EvidenceRecord:
    base = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc) + timedelta(hours=offset_hours)
    return EvidenceRecord(
        instrument_id="SSE:600519",
        evidence_type=EvidenceType.MARKET_QUOTE,
        title="SSE:600519 market_quote",
        summary="market quote: price=1648.0",
        source="tencent_quote",
        source_type="market_data_redistributor",
        authority_level=AuthorityLevel.B2,
        fact_status=FactStatus.CONFIRMED_FACT,
        event_time=base - timedelta(days=1),
        available_time=base,
        ingested_time=base + timedelta(hours=1),
        revision_time=base + timedelta(hours=1),
        metadata={"price": 1648.0},
    )


def test_save_is_idempotent_by_source_and_content(repo):
    first_id, first_created = repo.save(_record())
    assert first_created is True
    second_id, second_created = repo.save(_record())
    assert second_created is False
    assert first_id == second_id
    assert repo.count() == 1


def test_different_content_is_new_evidence(repo):
    a, _ = repo.save(_record())
    other = _record()
    other.title = "different title"
    b_id, created = repo.save(other)
    assert created is True
    assert b_id != a
    assert repo.count() == 2


def test_pit_filter_hides_future_evidence(repo):
    now_evidence = _record(offset_hours=0)
    future_evidence = _record(offset_hours=48)  # available in 2 days
    repo.save(now_evidence)
    repo.save(future_evidence)

    as_of = datetime(2026, 8, 29, tzinfo=timezone.utc)
    visible = repo.list_for_instrument("SSE:600519", visible_at=as_of)
    assert len(visible) == 1
    assert visible[0].available_time <= as_of

    everything = repo.list_for_instrument("SSE:600519")
    assert len(everything) == 2


def test_manifest_roundtrip(repo):
    manifest = SourceManifest(
        instrument_id="SSE:600519",
        capability="market_data",
        requested_as_of=datetime.now(timezone.utc),
        providers_attempted=({"source": "tencent_quote", "status": "success"},),
        final_status="success",
        final_source="tencent_quote",
        evidence_ids=("ev_abc",),
    )
    manifest_id = repo.save_manifest(manifest)
    loaded = repo.get_manifest(manifest_id)
    assert loaded is not None
    assert loaded.final_status == "success"
    assert loaded.evidence_ids == ("ev_abc",)
    assert loaded.providers_attempted[0]["source"] == "tencent_quote"
