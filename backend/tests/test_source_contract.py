"""SourceResult contract invariants (任务书 §21)."""

from datetime import datetime, timezone

import pytest

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)


def _record() -> SourceRecord:
    return SourceRecord(
        subject="SSE:600519",
        kind="quote",
        payload={"price": 1.0},
        available_time=utc_now(),
    )


def _request() -> SourceRequest:
    return SourceRequest(capability="market_data", instrument_id="SSE:600519")


def test_success_requires_records():
    with pytest.raises(ValueError):
        SourceResult(
            source="p", capability="market_data", status=SourceStatus.SUCCESS,
            as_of=utc_now(), attempted_at=utc_now(),
        )


def test_success_cannot_carry_no_data_reason():
    with pytest.raises(ValueError):
        SourceResult(
            source="p", capability="market_data", status=SourceStatus.SUCCESS,
            as_of=utc_now(), attempted_at=utc_now(), records=(_record(),),
            no_data_reason="oops",
        )


def test_no_data_requires_reason_and_forbids_records():
    with pytest.raises(ValueError):
        SourceResult(
            source="p", capability="market_data", status=SourceStatus.NO_DATA,
            as_of=utc_now(), attempted_at=utc_now(),
        )
    with pytest.raises(ValueError):
        SourceResult(
            source="p", capability="market_data", status=SourceStatus.NO_DATA,
            as_of=utc_now(), attempted_at=utc_now(), no_data_reason="r",
            records=(_record(),),
        )


@pytest.mark.parametrize(
    "status",
    [
        SourceStatus.NETWORK_ERROR,
        SourceStatus.RATE_LIMIT,
        SourceStatus.PARSE_ERROR,
        SourceStatus.AUTH_ERROR,
        SourceStatus.SOURCE_UNAVAILABLE,
    ],
)
def test_failure_requires_error_type_and_forbids_records(status):
    with pytest.raises(ValueError):
        SourceResult(
            source="p", capability="market_data", status=status,
            as_of=utc_now(), attempted_at=utc_now(),
        )
    result = SourceResult(
        source="p", capability="market_data", status=status,
        as_of=utc_now(), attempted_at=utc_now(), error_type="x",
    )
    assert result.is_failure()
    assert result.records == ()


def test_retryable_flags_follow_taxonomy():
    assert SourceResult(
        source="p", capability="c", status=SourceStatus.NETWORK_ERROR,
        as_of=utc_now(), attempted_at=utc_now(), error_type="t",
        retryable=False,
    ).retryable  # normalized to True for network_error
    assert not SourceResult(
        source="p", capability="c", status=SourceStatus.PARSE_ERROR,
        as_of=utc_now(), attempted_at=utc_now(), error_type="t",
        retryable=True,
    ).retryable  # normalized to False for parse_error
