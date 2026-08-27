"""Capability registry with ordered fallback (任务书 §10, §20).

``resolve`` walks the provider chain for a capability:

  - SUCCESS  → stop, return it;
  - PARTIAL  → stop (data present but incomplete);
  - NO_DATA / failure → record health, try the next provider;
  - exhausted → return a synthetic ``SOURCE_UNAVAILABLE`` result so callers
    always receive an explicit outcome (never a bare empty list).
"""

from __future__ import annotations

from app.sources.base import (
    SourceProvider,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.health import SourceHealthTracker


class SourceRegistry:
    def __init__(self) -> None:
        self._providers: list[SourceProvider] = []
        self.health = SourceHealthTracker()

    def register(self, provider: SourceProvider, *, priority: int | None = None) -> None:
        if priority is None:
            self._providers.append(provider)
            return
        self._providers.insert(min(priority, len(self._providers)), provider)

    def providers_for(self, capability: str) -> list[SourceProvider]:
        return [p for p in self._providers if capability in p.capabilities]

    def resolve(self, request: SourceRequest) -> SourceResult:
        """Try every provider supporting the capability, in order."""
        attempted: list[SourceResult] = []
        for provider in self.providers_for(request.capability):
            try:
                result = provider.fetch(request)
            except Exception as exc:  # noqa: BLE001 — a provider crash is a
                # source failure, never a registry crash (任务书 §21 explicit
                # failure semantics).
                result = SourceResult(
                    source=provider.provider_id,
                    capability=request.capability,
                    status=SourceStatus.SOURCE_UNAVAILABLE,
                    as_of=request.as_of,
                    attempted_at=utc_now(),
                    error_type=f"provider_exception:{type(exc).__name__}",
                )
            self.health.record(result)
            attempted.append(result)
            if result.is_success():
                if len(attempted) > 1:
                    # annotate which chain led here
                    result = SourceResult(
                        source=result.source,
                        capability=result.capability,
                        status=result.status,
                        as_of=result.as_of,
                        attempted_at=result.attempted_at,
                        records=result.records,
                        metadata={
                            **result.metadata,
                            "fallback_chain": [a.source for a in attempted],
                        },
                    )
                return result
        # No provider succeeded: synthesize an explicit unavailable result.
        last = attempted[-1] if attempted else None
        return SourceResult(
            source="registry",
            capability=request.capability,
            status=SourceStatus.SOURCE_UNAVAILABLE,
            as_of=request.as_of,
            attempted_at=utc_now(),
            error_type="no_provider_succeeded"
            if attempted
            else "no_provider_for_capability",
            metadata={
                "attempts": [
                    {
                        "source": a.source,
                        "status": a.status.value,
                        "error_type": a.error_type,
                        "no_data_reason": a.no_data_reason,
                    }
                    for a in attempted
                ],
                "last_attempted_at": last.attempted_at.isoformat() if last else None,
            },
        )
