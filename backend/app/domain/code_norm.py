"""A-share instrument code normalization and board classification.

Accepts common raw forms and returns a canonical (code, exchange, board):

    600519  600519.SH  SH600519  sh 600519   → SSE main   (60xxxx)
    688981  688981.SH  SH688981              → SSE star   (688/689)
    000001  000001.SZ  SZ000001              → SZSE main  (000/001/002/003)
    300750  300750.SZ  SZ300750              → SZSE chinext (300/301/302)
    430047  831799     BJ430047              → BSE        (43/83/87/92)

Unknown shapes raise :class:`InvalidInstrumentCode`, which the API maps to a
stable error code (never a fabricated match).
"""

from __future__ import annotations

import re

from app.domain.instrument import Board, Exchange

_SH_PREFIX = re.compile(r"^(sh|ss|沪)")
_SZ_PREFIX = re.compile(r"^(sz|深)")
_BJ_PREFIX = re.compile(r"^(bj|北)")
_SUFFIX = re.compile(r"\.(sh|ss|sz|bj)$", re.IGNORECASE)


class InvalidInstrumentCode(ValueError):
    """Raised when a raw string cannot be interpreted as an A-share code."""


def _clean(raw: str) -> str:
    text = raw.strip().lower().replace("．", ".").replace("。", ".")
    return re.sub(r"[\s_-]+", "", text)


def normalize_code(raw: str) -> tuple[str, Exchange, Board]:
    """Normalize a raw instrument string to (code, exchange, board)."""
    if not isinstance(raw, str) or not _clean(raw):
        raise InvalidInstrumentCode("empty instrument code")

    text = _clean(raw)

    # Peel explicit exchange markers first.
    exchange_hint: Exchange | None = None
    if _SUFFIX.search(text):
        m = _SUFFIX.search(text)
        text = text[: m.start()]
        exchange_hint = {"sh": Exchange.SSE, "ss": Exchange.SSE, "sz": Exchange.SZSE, "bj": Exchange.BSE}[
            m.group(1).lower()
        ]
    else:
        if _SH_PREFIX.match(text):
            exchange_hint = Exchange.SSE
            text = re.sub(r"^(sh|ss|沪)", "", text)
        elif _SZ_PREFIX.match(text):
            exchange_hint = Exchange.SZSE
            text = re.sub(r"^(sz|深)", "", text)
        elif _BJ_PREFIX.match(text):
            exchange_hint = Exchange.BSE
            text = re.sub(r"^(bj|北)", "", text)

    if not re.fullmatch(r"\d{6}", text):
        raise InvalidInstrumentCode(f"not a 6-digit A-share code: {raw!r}")

    code = text
    exchange, board = _classify(code)

    # A hint can only confirm, never contradict the code itself (e.g. 300750
    # belongs to SZSE regardless of a bogus .SH suffix).
    if exchange_hint is not None and exchange_hint != exchange:
        raise InvalidInstrumentCode(
            f"exchange hint {exchange_hint.value} contradicts code {code} ({exchange.value})"
        )
    return code, exchange, board


def _classify(code: str) -> tuple[Exchange, Board]:
    prefix3 = code[:3]
    if code.startswith(("688", "689")):
        return Exchange.SSE, Board.STAR
    if code.startswith("60"):
        return Exchange.SSE, Board.MAIN
    if prefix3 in ("300", "301", "302"):
        return Exchange.SZSE, Board.CHINEXT
    if prefix3 in ("000", "001", "002", "003"):
        return Exchange.SZSE, Board.MAIN
    if code.startswith(("43", "83", "87", "92")):
        return Exchange.BSE, Board.BSE
    raise InvalidInstrumentCode(f"unrecognized A-share code prefix: {code!r}")
