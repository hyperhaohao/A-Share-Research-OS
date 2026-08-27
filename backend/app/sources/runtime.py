"""Process-wide source runtime: registry, cache, default providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.sources.base import SourceRequest, SourceResult, SourceStatus, SourceRecord, utc_now
from app.sources.cache import TTLCache
from app.sources.providers.tencent_quote import TencentQuoteProvider
from app.sources.registry import SourceRegistry


@dataclass
class SourceRuntime:
    """Bundles registry + cache and exposes cache-aware resolution."""

    registry: SourceRegistry = field(default_factory=SourceRegistry)
    cache: TTLCache = field(default_factory=TTLCache)

    def __post_init__(self) -> None:
        if not self.registry.providers_for("market_data"):
            self.registry.register(TencentQuoteProvider())

    def resolve_cached(self, request: SourceRequest) -> SourceResult:
        """Resolve with a per-capability TTL cache in front of the registry."""
        now = utc_now()
        key = self.cache.make_key(request.capability, request.instrument_id, request.params)
        cached = self.cache.get(key, now)
        if cached is not None:
            # serve the cached result, annotated as cache hit
            return SourceResult(
                source=cached.source,
                capability=cached.capability,
                status=cached.status,
                as_of=cached.as_of,
                attempted_at=cached.attempted_at,
                records=cached.records,
                no_data_reason=cached.no_data_reason,
                error_type=cached.error_type,
                metadata={**cached.metadata, "from_cache": True},
            )
        result = self.registry.resolve(request)
        if result.is_success():
            self.cache.put(key, result, now, capability=request.capability)
        return result


_runtime: SourceRuntime | None = None


def get_runtime() -> SourceRuntime:
    global _runtime
    if _runtime is None:
        _runtime = SourceRuntime()
    return _runtime


def reset_runtime() -> None:
    """Test seam: rebuild the process runtime."""
    global _runtime
    _runtime = None
