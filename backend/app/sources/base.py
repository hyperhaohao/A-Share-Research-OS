"""Source layer contracts.

SourceResult semantics follow the OpenAlpha CN provider contract
(src/openalpha_cn/providers/base.py, MIT License, Copyright (c) 2026 ss8875),
adapted for this project's capability model and SourceStatus set
(A-Share-Research-OS 任务书 §20-21).

Core invariants (任务书 §21):
  - a failure must never masquerade as an empty success;
  - ``success`` requires at least one record; ``no_data`` requires a reason;
  - every result carries provider id, capability, attempt time and as_of.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


class SourceStatus(str, Enum):
    SUCCESS = "success"
    NO_DATA = "no_data"
    PARTIAL = "partial"
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    PARSE_ERROR = "parse_error"
    AUTH_ERROR = "auth_error"
    SOURCE_UNAVAILABLE = "source_unavailable"


FAILURE_STATUSES = frozenset(
    {
        SourceStatus.NETWORK_ERROR,
        SourceStatus.RATE_LIMIT,
        SourceStatus.PARSE_ERROR,
        SourceStatus.AUTH_ERROR,
        SourceStatus.SOURCE_UNAVAILABLE,
    }
)

RETRYABLE_STATUSES = frozenset(
    {
        SourceStatus.NETWORK_ERROR,
        SourceStatus.RATE_LIMIT,
        SourceStatus.SOURCE_UNAVAILABLE,
    }
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class SourceRequest:
    """A deterministic point-in-time source request."""

    capability: str  # market_data / announcements / financials / news / ...
    instrument_id: str | None = None
    as_of: datetime = field(default_factory=utc_now)
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class SourceRecord:
    """One normalized record returned by a provider.

    ``available_time`` is when the information became (or becomes) available
    to the market — the PIT gate in M5 will enforce
    ``available_time <= as_of`` before anything enters an EvidenceSnapshot.
    """

    subject: str  # instrument_id or another subject key
    kind: str  # quote / profile / announcement / ...
    payload: Mapping[str, Any]
    available_time: datetime
    event_time: datetime | None = None
    source_uri: str | None = None


@dataclass(frozen=True, kw_only=True)
class SourceResult:
    """Explicit success-or-failure result of one provider call."""

    source: str
    capability: str
    status: SourceStatus
    as_of: datetime
    attempted_at: datetime
    records: tuple[SourceRecord, ...] = ()
    error_type: str | None = None
    retryable: bool = False
    no_data_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status is SourceStatus.SUCCESS and not self.records:
            raise ValueError("success requires at least one record")
        if self.status is SourceStatus.SUCCESS and self.no_data_reason is not None:
            raise ValueError("success cannot carry a no_data_reason")
        if self.status is SourceStatus.NO_DATA:
            if self.records:
                raise ValueError("no_data cannot carry records")
            if not self.no_data_reason:
                raise ValueError("no_data requires a reason")
        if self.status in FAILURE_STATUSES:
            if self.records:
                raise ValueError("failure cannot carry records")
            if not self.error_type:
                raise ValueError(f"{self.status.value} requires error_type")
        expected_retryable = self.status in RETRYABLE_STATUSES
        if self.status in FAILURE_STATUSES and self.retryable != expected_retryable:
            # keep the declared retryable consistent with the status taxonomy
            object.__setattr__(self, "retryable", expected_retryable)

    def is_success(self) -> bool:
        return self.status in (SourceStatus.SUCCESS, SourceStatus.PARTIAL)

    def is_failure(self) -> bool:
        return self.status in FAILURE_STATUSES


@runtime_checkable
class SourceProvider(Protocol):
    """Capability-scoped provider interface."""

    provider_id: str
    capabilities: frozenset[str]

    def fetch(self, request: SourceRequest) -> SourceResult:
        """Return an explicit SourceResult; providers must never raise for
        expected data conditions — failures are returned, not thrown."""
