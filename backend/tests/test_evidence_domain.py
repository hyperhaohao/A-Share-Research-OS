"""Evidence domain invariants (任务书 §22-26)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
    SourceManifest,
)


def _clocks(offset: timedelta = timedelta(0)):
    base = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc) + offset
    return dict(
        event_time=base - timedelta(days=1),
        available_time=base,
        ingested_time=base + timedelta(hours=1),
        revision_time=base + timedelta(hours=1),
    )


def _record(**overrides) -> EvidenceRecord:
    params = dict(
        instrument_id="SSE:600519",
        evidence_type=EvidenceType.MARKET_QUOTE,
        title="SSE:600519 market_quote",
        summary="market quote: price=1648.0",
        source="tencent_quote",
        source_type="market_data_redistributor",
        authority_level=AuthorityLevel.B2,
        fact_status=FactStatus.CONFIRMED_FACT,
        confidence=1.0,
        metadata={"price": 1648.0},
    )
    params.update(_clocks())
    params.update(overrides)
    return EvidenceRecord(**params)


def test_content_addressed_identity_is_stable():
    a = _record()
    b = _record()
    assert a.content_hash == b.content_hash
    assert a.evidence_id == b.evidence_id
    assert a.evidence_id.startswith("ev_")


def test_content_hash_changes_with_payload():
    a = _record(metadata={"price": 1648.0})
    b = _record(metadata={"price": 1649.0})
    assert a.content_hash != b.content_hash


def test_naive_datetimes_rejected():
    with pytest.raises(ValueError):
        _record(event_time=datetime(2026, 8, 27, 10, 0))  # naive


def test_ingested_cannot_precede_available():
    clocks = _clocks()
    clocks["ingested_time"] = clocks["available_time"] - timedelta(hours=2)
    with pytest.raises(ValueError):
        _record(**clocks)


def test_revision_cannot_precede_available():
    clocks = _clocks()
    clocks["revision_time"] = clocks["available_time"] - timedelta(hours=2)
    with pytest.raises(ValueError):
        _record(**clocks)


def test_pit_visibility_rule():
    record = _record()
    after = record.available_time + timedelta(minutes=1)
    before = record.available_time - timedelta(minutes=1)
    assert record.visible_at(after) is True
    assert record.visible_at(before) is False
    with pytest.raises(ValueError):
        record.visible_at(record.available_time.replace(tzinfo=None))


def test_source_manifest_defaults():
    manifest = SourceManifest(
        instrument_id="SSE:600519",
        capability="market_data",
        requested_as_of=datetime.now(timezone.utc),
    )
    assert manifest.manifest_id
    assert manifest.final_status == "pending"
    assert manifest.evidence_ids == ()
