"""In-process event bus for research execution SSE streams (任务书 §67).

Events are plain dicts with a stable ``event`` name and JSON payload. SSE
(§67 event names):
    run_started / source_progress / evidence_ready / quality_gate /
    analyst_progress / valuation_ready / report_ready / run_completed /
    run_failed
"""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_EVENT_NAMES = {
    "run_started",
    "source_progress",
    "evidence_ready",
    "snapshot_built",
    "quality_gate",
    "analyst_progress",
    "claims_compiled",
    "thesis_ready",
    "debate_ready",
    "valuation_ready",
    "scenario_ready",
    "risk_ready",
    "report_ready",
    "run_completed",
    "run_failed",
    # R4（方案 §10.3/§10.4/§10.5）：自主研究循环语义事件
    "profile_applied",
    "waiting_data",
    "reviewing",
    "missing_data_summary",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BusEvent:
    run_id: str
    event: str
    payload: dict[str, Any]
    at: str = field(default_factory=utc_now_iso)

    def sse_line(self) -> str:
        return (
            f"event: {self.event}\n"
            f"data: {json.dumps({'run_id': self.run_id, 'at': self.at, **self.payload}, ensure_ascii=False, default=str)}\n\n"
        )


class EventBus:
    """Thread-safe pub/sub keyed by run_id. Subscribers get their own queue."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[queue.Queue]] = {}

    def subscribe(self, run_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: queue.Queue) -> None:
        with self._lock:
            subs = self._subscribers.get(run_id)
            if subs and q in subs:
                subs.remove(q)
                if not subs:
                    self._subscribers.pop(run_id, None)

    def publish(self, run_id: str, event: str, payload: dict[str, Any]) -> None:
        if event not in _EVENT_NAMES:
            raise ValueError(f"unknown event name: {event}")
        bus_event = BusEvent(run_id=run_id, event=event, payload=payload)
        with self._lock:
            subs = list(self._subscribers.get(run_id, ()))
        for q in subs:
            q.put(bus_event)

    def subscriber_count(self, run_id: str) -> int:
        with self._lock:
            return len(self._subscribers.get(run_id, ()))


_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus


def reset_event_bus() -> None:
    global _bus
    with _bus_lock:
        _bus = None
