"""Registry fallback, health tracking, and cache semantics."""

from datetime import datetime, timedelta, timezone

import pytest

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.cache import TTLCache
from app.sources.health import SourceHealthTracker
from app.sources.provider import BaseProvider
from app.sources.registry import SourceRegistry


def _record(subject="SSE:600519") -> SourceRecord:
    return SourceRecord(
        subject=subject, kind="quote", payload={"price": 1.0}, available_time=utc_now()
    )


def _req(capability="market_data") -> SourceRequest:
    return SourceRequest(capability=capability, instrument_id="SSE:600519")


class _Provider(BaseProvider):
    def __init__(self, provider_id, status, *, capabilities=frozenset({"market_data"})):
        self.provider_id = provider_id
        self.capabilities = capabilities
        self.status = status
        self.calls = 0

    def fetch(self, request: SourceRequest) -> SourceResult:
        self.calls += 1
        base = dict(as_of=request.as_of, attempted_at=utc_now())
        if self.status is SourceStatus.SUCCESS:
            return SourceResult(
                source=self.provider_id, capability=request.capability,
                status=self.status, records=(_record(),), **base,
            )
        if self.status is SourceStatus.NO_DATA:
            return SourceResult(
                source=self.provider_id, capability=request.capability,
                status=self.status, no_data_reason="nothing", **base,
            )
        return SourceResult(
            source=self.provider_id, capability=request.capability,
            status=self.status, error_type="e", **base,
        )


class TestFallback:
    def test_first_success_short_circuits(self):
        first, second = _Provider("a", SourceStatus.SUCCESS), _Provider("b", SourceStatus.SUCCESS)
        registry = SourceRegistry()
        registry.register(first)
        registry.register(second)
        result = registry.resolve(_req())
        assert result.source == "a"
        assert second.calls == 0
        assert "fallback_chain" not in result.metadata

    def test_failure_then_success_returns_success_with_chain(self):
        failing, working = _Provider("a", SourceStatus.NETWORK_ERROR), _Provider("b", SourceStatus.SUCCESS)
        registry = SourceRegistry()
        registry.register(failing)
        registry.register(working)
        result = registry.resolve(_req())
        assert result.source == "b"
        assert result.is_success()
        assert result.metadata["fallback_chain"] == ["a", "b"]

    def test_no_data_falls_through(self):
        empty, working = _Provider("a", SourceStatus.NO_DATA), _Provider("b", SourceStatus.SUCCESS)
        registry = SourceRegistry()
        registry.register(empty)
        registry.register(working)
        result = registry.resolve(_req())
        assert result.source == "b"

    def test_exhausted_chain_is_explicit_unavailable(self):
        failing, empty = _Provider("a", SourceStatus.RATE_LIMIT), _Provider("b", SourceStatus.NO_DATA)
        registry = SourceRegistry()
        registry.register(failing)
        registry.register(empty)
        result = registry.resolve(_req())
        assert result.status is SourceStatus.SOURCE_UNAVAILABLE
        assert result.error_type == "no_provider_succeeded"
        assert [a["status"] for a in result.metadata["attempts"]] == ["rate_limit", "no_data"]

    def test_no_provider_for_capability(self):
        registry = SourceRegistry()
        result = registry.resolve(SourceRequest(capability="announcements"))
        assert result.status is SourceStatus.SOURCE_UNAVAILABLE
        assert result.error_type == "no_provider_for_capability"

    def test_capability_filtering(self):
        quote_provider = _Provider("q", SourceStatus.SUCCESS)
        news_provider = _Provider("n", SourceStatus.SUCCESS, capabilities=frozenset({"news"}))
        registry = SourceRegistry()
        registry.register(quote_provider)
        registry.register(news_provider)
        result = registry.resolve(SourceRequest(capability="news"))
        assert result.source == "n"
        assert quote_provider.calls == 0


class TestHealth:
    def test_failure_streak_marks_unavailable(self):
        tracker = SourceHealthTracker()
        failing = _Provider("a", SourceStatus.NETWORK_ERROR)
        for _ in range(3):
            tracker.record(failing.fetch(_req()))
        snapshot = tracker.snapshot()
        assert snapshot[0].consecutive_failures == 3
        assert snapshot[0].available is False

    def test_recovery_resets_streak(self):
        tracker = SourceHealthTracker()
        failing, working = _Provider("a", SourceStatus.NETWORK_ERROR), _Provider("a", SourceStatus.SUCCESS)
        for _ in range(3):
            tracker.record(failing.fetch(_req()))
        tracker.record(working.fetch(_req()))
        assert tracker.snapshot()[0].available is True

    def test_never_tried_is_available(self):
        tracker = SourceHealthTracker()
        assert tracker.is_available("ghost", "market_data") is True


class TestCache:
    def test_hit_within_ttl_miss_after(self):
        cache = TTLCache()
        now = datetime.now(timezone.utc)
        key = cache.make_key("market_data", "SSE:600519", {})
        cache.put(key, "value", now, capability="market_data")
        assert cache.get(key, now + timedelta(seconds=2)) == "value"
        assert cache.get(key, now + timedelta(seconds=6)) is None

    def test_capability_ttl_defaults(self):
        cache = TTLCache()
        assert cache.ttl_for("market_data") == 5
        assert cache.ttl_for("instrument") == 24 * 3600

    def test_param_ordering_stable_key(self):
        cache = TTLCache()
        k1 = cache.make_key("c", "SSE:1", {"a": 1, "b": 2})
        k2 = cache.make_key("c", "SSE:1", {"b": 2, "a": 1})
        assert k1 == k2
