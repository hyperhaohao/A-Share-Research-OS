"""Shared HTTP helper for providers — explicit failure semantics (R1).

Every provider fetch goes through here so failures map to the SourceResult
taxonomy deterministically:

    transport error / timeout  → NETWORK_ERROR
    401 / 403                  → AUTH_ERROR
    other >=400                → SOURCE_UNAVAILABLE
    unparseable body           → PARSE_ERROR

Providers never turn an exception into an empty result (任务书整改 §6.10).
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.sources.base import SourceStatus

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-os/0.1",
}

_JSONP = re.compile(r"^[\w.$]+\((.*)\)\s*;?\s*$", re.S)


def http_json(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
    jsonp: bool = False,
    encoding: str | None = None,
) -> tuple[Any, None] | tuple[None, tuple[SourceStatus, str]]:
    """Fetch and parse a JSON (or JSONP) body.

    Returns ``(data, None)`` on success or ``(None, (status, error_type))``
    on a classified failure.
    """
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        resp = httpx.get(url, params=params, headers=merged, timeout=timeout)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return None, (SourceStatus.NETWORK_ERROR, type(exc).__name__)

    if resp.status_code in (401, 403):
        return None, (SourceStatus.AUTH_ERROR, f"http_{resp.status_code}")
    if resp.status_code >= 400:
        return None, (SourceStatus.SOURCE_UNAVAILABLE, f"http_{resp.status_code}")

    text = resp.content.decode(encoding or resp.encoding or "utf-8", errors="replace")
    if jsonp:
        m = _JSONP.match(text.strip())
        if not m:
            return None, (SourceStatus.PARSE_ERROR, "unparseable_jsonp")
        text = m.group(1)
    try:
        return json.loads(text), None
    except ValueError:
        return None, (SourceStatus.PARSE_ERROR, "unparseable_json")


def http_post_json(
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    timeout: float = 12.0,
) -> tuple[Any, None] | tuple[None, tuple[SourceStatus, str]]:
    merged = {**DEFAULT_HEADERS, **(headers or {}), "Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = httpx.post(url, data=data, headers=merged, timeout=timeout)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return None, (SourceStatus.NETWORK_ERROR, type(exc).__name__)
    if resp.status_code in (401, 403):
        return None, (SourceStatus.AUTH_ERROR, f"http_{resp.status_code}")
    if resp.status_code >= 400:
        return None, (SourceStatus.SOURCE_UNAVAILABLE, f"http_{resp.status_code}")
    try:
        return json.loads(resp.content.decode("utf-8", errors="replace")), None
    except ValueError:
        return None, (SourceStatus.PARSE_ERROR, "unparseable_json")


def eastmoney_secid(instrument_id: str) -> str | None:
    """SSE:600519 → 1.600519; SZSE:000001 → 0.000001; BSE:430047 → 0.430047."""
    if ":" not in instrument_id:
        return None
    exchange, code = instrument_id.split(":", 1)
    if exchange == "SSE":
        return f"1.{code}"
    if exchange in ("SZSE", "BSE"):
        return f"0.{code}"
    return None
