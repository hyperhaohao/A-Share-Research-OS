"""Source result cache with per-capability TTL semantics (任务书 §69).

Cache serves freshness, never truth: cached values are returned as
``from_cache`` metadata on an explicit SourceResult, and PIT-sensitive
callers re-resolve as_of through the provider when needed (M5 will enforce
the PIT gate downstream of the cache).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping

# Default TTLs per capability (seconds). Quote-level data is very short;
# identity/profile data is long (任务书 §69 examples).
DEFAULT_TTLS: Mapping[str, int] = {
    "market_data": 5,
    "news": 60,
    "announcements": 300,
    "financials": 6 * 3600,
    "instrument": 24 * 3600,
    "capital_flow": 60,
    "macro": 12 * 3600,
    "industry": 12 * 3600,
    "corporate_actions": 6 * 3600,
    "research": 24 * 3600,
}

_UNSET = object()


@dataclass
class _Entry:
    value: Any
    expires_at: datetime


class TTLCache:
    """Monotonic-capability TTL cache. Not PIT-unsafe: callers include as_of
    in cache keys when historical resolution matters."""

    def __init__(self, ttls: Mapping[str, int] | None = None) -> None:
        self._ttls = dict(DEFAULT_TTLS)
        if ttls:
            self._ttls.update(ttls)
        self._store: dict[str, _Entry] = {}

    def ttl_for(self, capability: str) -> int:
        return self._ttls.get(capability, 60)

    def make_key(self, capability: str, instrument_id: str | None, params: Mapping[str, Any]) -> str:
        params_part = "&".join(f"{k}={params[k]!r}" for k in sorted(params))
        return f"{capability}|{instrument_id or ''}|{params_part}"

    def get(self, key: str, now: datetime) -> Any | None:
        entry = self._store.get(key, _UNSET)
        if entry is _UNSET:
            return None
        if now >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def put(self, key: str, value: Any, now: datetime, *, capability: str | None = None) -> None:
        ttl = self.ttl_for(capability or "")
        self._store[key] = _Entry(value=value, expires_at=now + timedelta(seconds=ttl))

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
