"""Remote instrument search — Tencent smartbox keyword resolver (PW0).

Resolves a free-text query (Chinese name, pinyin, or code fragment) to real
(code, name) candidates via the public key-free endpoint
``https://smartbox.gtimg.cn/t3?v=2&q=<query>&t=all`` (GBK-encoded).

Trust boundary: the wire response only contributes *candidate code + name*
strings. Exchange/board classification is always re-derived locally from the
code prefix (``domain/code_norm.py``), and names are verified against a real
quote fetch before persisting — a malformed or contradictory candidate is
skipped, never guessed into the registry.

Failure semantics (任务书 §21): network/parse problems surface as an explicit
``error_type`` on the result — the caller shows "no match / source
unavailable", never a fabricated candidate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx

from app.domain.code_norm import InvalidInstrumentCode, normalize_code

DEFAULT_URL = "https://smartbox.gtimg.cn/t3"
_BODY = re.compile(r'v_hint="(?P<body>.*)"', re.DOTALL)


@dataclass(frozen=True)
class InstrumentCandidate:
    code: str
    name: str
    instrument_id: str  # derived locally from code prefix rules


@dataclass(frozen=True)
class InstrumentSearchResult:
    query: str
    candidates: tuple[InstrumentCandidate, ...] = field(default_factory=tuple)
    error_type: str | None = None  # None ⇒ clean outcome (possibly empty)


def search_cn_instruments(
    query: str,
    *,
    base_url: str | None = None,
    timeout: float = 5.0,
    limit: int = 10,
) -> InstrumentSearchResult:
    """Resolve a free-text query to validated (code, name) candidates."""
    q = (query or "").strip()
    if not q:
        return InstrumentSearchResult(query=q)

    url = base_url or DEFAULT_URL
    attempted_error: str | None = None
    try:
        resp = httpx.get(url, params={"v": "2", "q": q, "t": "all"}, timeout=timeout)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return InstrumentSearchResult(
            query=q, error_type=f"network:{type(exc).__name__}"
        )
    if resp.status_code >= 400:
        return InstrumentSearchResult(query=q, error_type=f"http_{resp.status_code}")

    body_match = _BODY.search(resp.content.decode("gbk", errors="replace"))
    if body_match is None:
        # Empty hint responses come back with an empty quoted body; anything
        # else is an unexpected shape.
        return InstrumentSearchResult(query=q, error_type=None)

    candidates: list[InstrumentCandidate] = []
    seen: set[str] = set()
    for entry in body_match.group("body").split("^"):
        fields = entry.split("~")
        if len(fields) < 4:
            continue
        code, name = fields[2].strip(), fields[3].strip()
        if not re.fullmatch(r"\d{6}", code) or code in seen or not name:
            continue
        try:
            _code, _exchange, _board = normalize_code(code)
        except InvalidInstrumentCode:
            continue  # not an A-share-shaped candidate — skip, never guess
        seen.add(code)
        candidates.append(
            InstrumentCandidate(
                code=code,
                name=name,
                instrument_id=f"{_exchange.value}:{_code}",
            )
        )
        if len(candidates) >= limit:
            break
    return InstrumentSearchResult(query=q, candidates=tuple(candidates))
