"""PIT gate + immutable snapshot tests (任务书 §23/§24/§74)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
)
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import (
    ResearchRunRepository,
    SnapshotRepository,
)

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


def _record(available: datetime, price: float) -> EvidenceRecord:
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


class TestPITGate:
    def test_future_evidence_never_enters_snapshot(self, dbsession, evidence_repo):
        """§74: available_time > as_of must be invisible to the snapshot."""
        past = evidence_repo.save(_record(AS_OF - timedelta(days=1), 1500.0))[0]
        evidence_repo.save(_record(AS_OF + timedelta(days=1), 9999.0))

        snapshot = SnapshotRepository(dbsession).build(
            "SSE:600519", AS_OF, evidence_repo=evidence_repo
        )
        assert snapshot.evidence_ids == (past,)

    def test_boundary_equality_is_visible(self, dbsession, evidence_repo):
        """available_time == as_of is visible (<= rule)."""
        boundary_id, _ = evidence_repo.save(_record(AS_OF, 1600.0))
        snapshot = SnapshotRepository(dbsession).build(
            "SSE:600519", AS_OF, evidence_repo=evidence_repo
        )
        assert snapshot.evidence_ids == (boundary_id,)

    def test_naive_as_of_rejected(self, dbsession, evidence_repo):
        with pytest.raises(ValueError):
            SnapshotRepository(dbsession).build(
                "SSE:600519",
                datetime(2026, 8, 28, 10, 0),  # naive
                evidence_repo=evidence_repo,
            )


class TestSnapshotImmutability:
    def test_rebuild_same_asof_returns_stored_snapshot(self, dbsession, evidence_repo):
        evidence_repo.save(_record(AS_OF - timedelta(days=1), 1500.0))
        repo = SnapshotRepository(dbsession)

        first = repo.build("SSE:600519", AS_OF, evidence_repo=evidence_repo)

        # Later, a NEW fact arrives (available at a later time).
        evidence_repo.save(_record(AS_OF + timedelta(days=2), 1700.0))

        # Rebuild for the same as_of: identical immutable snapshot.
        second = repo.build("SSE:600519", AS_OF, evidence_repo=evidence_repo)
        assert second.snapshot_id == first.snapshot_id
        assert second.content_hash == first.content_hash
        assert second.evidence_ids == first.evidence_ids

    def test_later_asof_picks_up_new_evidence(self, dbsession, evidence_repo):
        evidence_repo.save(_record(AS_OF - timedelta(days=1), 1500.0))
        repo = SnapshotRepository(dbsession)
        first = repo.build("SSE:600519", AS_OF, evidence_repo=evidence_repo)

        evidence_repo.save(_record(AS_OF + timedelta(days=2), 1700.0))
        later = repo.build(
            "SSE:600519",
            AS_OF + timedelta(days=3),
            evidence_repo=evidence_repo,
        )
        assert len(later.evidence_ids) == 2
        assert later.snapshot_id != first.snapshot_id

    def test_snapshot_content_addressed_identity(self, dbsession, evidence_repo):
        evidence_repo.save(_record(AS_OF - timedelta(days=1), 1500.0))
        repo = SnapshotRepository(dbsession)
        snapshot = repo.build("SSE:600519", AS_OF, evidence_repo=evidence_repo)
        assert snapshot.snapshot_id.startswith("snap_")
        assert len(snapshot.content_hash) == 64
        # identity covers content: a different as_of yields a different id
        other = repo.build(
            "SSE:600519", AS_OF + timedelta(days=1), evidence_repo=evidence_repo
        )
        assert other.snapshot_id != snapshot.snapshot_id


class TestResearchRun:
    def test_run_binds_snapshot(self, dbsession, evidence_repo):
        evidence_repo.save(_record(AS_OF - timedelta(days=1), 1500.0))
        snapshots = SnapshotRepository(dbsession)
        runs = ResearchRunRepository(dbsession)

        snapshot = snapshots.build("SSE:600519", AS_OF, evidence_repo=evidence_repo)
        run = runs.create("run_abc123", "SSE:600519", AS_OF, snapshot_id=snapshot.snapshot_id)

        assert run.status.value == "running"
        loaded = runs.get("run_abc123")
        assert loaded is not None
        assert loaded.snapshot_id == snapshot.snapshot_id

    def test_finished_cannot_precede_started(self, dbsession):
        runs = ResearchRunRepository(dbsession)
        from app.domain.snapshot import ResearchRun

        with pytest.raises(ValueError):
            ResearchRun(
                run_id="run_bad",
                instrument_id="SSE:600519",
                as_of=AS_OF,
                started_at=AS_OF,
                finished_at=AS_OF - timedelta(hours=1),
            )
        _ = runs  # repo usable; domain guard fires first
