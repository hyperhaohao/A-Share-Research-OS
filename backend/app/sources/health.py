"""Source health tracking (任务书 §84: source health 在 UI 可见)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from app.sources.base import SourceResult, SourceStatus, utc_now

_FAILURES_FOR_OUTAGE = 3  # consecutive failures before a provider is "down"


@dataclass
class ProviderHealth:
    provider_id: str
    capability: str
    last_status: SourceStatus
    last_attempted_at: datetime
    last_error_type: str | None
    consecutive_failures: int
    available: bool

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "capability": self.capability,
            "last_status": self.last_status.value,
            "last_attempted_at": self.last_attempted_at.isoformat(),
            "last_error_type": self.last_error_type,
            "consecutive_failures": self.consecutive_failures,
            "available": self.available,
        }


class SourceHealthTracker:
    """Tracks the latest result per (provider, capability)."""

    def __init__(self, *, outage_threshold: int = _FAILURES_FOR_OUTAGE) -> None:
        self._outage_threshold = outage_threshold
        self._state: dict[tuple[str, str], dict] = {}

    def record(self, result: SourceResult) -> None:
        key = (result.source, result.capability)
        state = self._state.get(key)
        if state is None:
            state = {"consecutive_failures": 0}
            self._state[key] = state
        if result.is_failure():
            state["consecutive_failures"] += 1
        else:
            state["consecutive_failures"] = 0
        state.update(
            last_status=result.status,
            last_attempted_at=result.attempted_at,
            last_error_type=result.error_type,
        )

    def snapshot(self) -> list[ProviderHealth]:
        items: list[ProviderHealth] = []
        for (provider_id, capability), state in sorted(self._state.items()):
            failures = state["consecutive_failures"]
            items.append(
                ProviderHealth(
                    provider_id=provider_id,
                    capability=capability,
                    last_status=state["last_status"],
                    last_attempted_at=state["last_attempted_at"],
                    last_error_type=state["last_error_type"],
                    consecutive_failures=failures,
                    available=failures < self._outage_threshold,
                )
            )
        return items

    def is_available(self, provider_id: str, capability: str) -> bool:
        state = self._state.get((provider_id, capability))
        if state is None:
            return True  # never tried — assume usable until proven otherwise
        return state["consecutive_failures"] < self._outage_threshold


def health_mapping(tracker: SourceHealthTracker, now: datetime | None = None) -> list[dict]:
    _ = now or utc_now()
    return [h.as_dict() for h in tracker.snapshot()]
