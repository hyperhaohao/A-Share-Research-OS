"""Provider base helper: explicit result constructors.

Providers subclass this and build results exclusively through ``_success``,
``_no_data`` and ``_failure`` so every outcome is explicit and typed
(任务书 §21 — 禁止失败伪装为空成功).
"""

from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Any, Mapping

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)


class BaseProvider(ABC):
    provider_id: str
    capabilities: frozenset[str]

    def _success(
        self,
        records: list[SourceRecord],
        request: SourceRequest,
        *,
        attempted_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SourceResult:
        return SourceResult(
            source=self.provider_id,
            capability=request.capability,
            status=SourceStatus.SUCCESS,
            as_of=request.as_of,
            attempted_at=attempted_at or utc_now(),
            records=tuple(records),
            metadata=metadata or {},
        )

    def _no_data(
        self,
        request: SourceRequest,
        reason: str,
        *,
        attempted_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SourceResult:
        return SourceResult(
            source=self.provider_id,
            capability=request.capability,
            status=SourceStatus.NO_DATA,
            as_of=request.as_of,
            attempted_at=attempted_at or utc_now(),
            no_data_reason=reason,
            metadata=metadata or {},
        )

    def _failure(
        self,
        request: SourceRequest,
        status: SourceStatus,
        error_type: str,
        *,
        attempted_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SourceResult:
        if status not in {
            SourceStatus.NETWORK_ERROR,
            SourceStatus.RATE_LIMIT,
            SourceStatus.PARSE_ERROR,
            SourceStatus.AUTH_ERROR,
            SourceStatus.SOURCE_UNAVAILABLE,
        }:
            raise ValueError(f"not a failure status: {status}")
        return SourceResult(
            source=self.provider_id,
            capability=request.capability,
            status=status,
            as_of=request.as_of,
            attempted_at=attempted_at or utc_now(),
            error_type=error_type,
            metadata=metadata or {},
        )
