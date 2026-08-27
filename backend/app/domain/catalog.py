"""Instrument catalog: resolution by code or name.

M2 scope: a static, real-identity seed catalog covering the four boards
(沪主板/深主板/创业板/科创板) with representative instruments across the
research styles required by 任务书 §71 (金融/消费/新能源/科技/周期).
Identity facts (code/name/exchange/board) are publicly verifiable static
reference data — not market data, not LLM output.

M3+ : the Source Layer will extend this catalog with live metadata
(industry/sector/market_cap/listed_status) and populate data_availability.
Missing data stays ``None`` / absent — displayed as missing, never guessed.
"""

from __future__ import annotations

from app.domain.code_norm import InvalidInstrumentCode, normalize_code
from app.domain.instrument import (
    Board,
    Exchange,
    InstrumentProfile,
    InstrumentResolution,
    instrument_id_for,
)

_IDENTITY = ("identity", "static_profile")

# (code, name, exchange, board, aliases, sector, industry)
_SEED: tuple[tuple[str, str, Exchange, Board, tuple[str, ...], str, str], ...] = (
    ("600519", "贵州茅台", Exchange.SSE, Board.MAIN, ("KWEICHOW MOUTAI", "茅台"), "consumer", "白酒"),
    ("601398", "工商银行", Exchange.SSE, Board.MAIN, ("ICBC",), "financial", "银行"),
    ("601899", "紫金矿业", Exchange.SSE, Board.MAIN, ("ZIJIN MINING",), "materials", "有色金属"),
    ("603288", "海天味业", Exchange.SSE, Board.MAIN, ("FOSHAN HAITIAN",), "consumer", "调味品"),
    ("000001", "平安银行", Exchange.SZSE, Board.MAIN, ("PING AN BANK",), "financial", "银行"),
    ("000858", "五粮液", Exchange.SZSE, Board.MAIN, ("WULIANGYE",), "consumer", "白酒"),
    ("002594", "比亚迪", Exchange.SZSE, Board.MAIN, ("BYD",), "industrial", "新能源车"),
    ("300750", "宁德时代", Exchange.SZSE, Board.CHINEXT, ("CATL",), "industrial", "动力电池"),
    ("300059", "东方财富", Exchange.SZSE, Board.CHINEXT, ("EAST MONEY",), "financial", "金融科技"),
    ("688981", "中芯国际", Exchange.SSE, Board.STAR, ("SMIC",), "technology", "半导体"),
    ("688111", "金山办公", Exchange.SSE, Board.STAR, ("KINGSOFT OFFICE", "WPS"), "technology", "软件"),
    ("688041", "海光信息", Exchange.SSE, Board.STAR, ("HIGOS",), "technology", "半导体"),
)


def _build_profile(code: str, name: str, exchange: Exchange, board: Board, aliases: tuple[str, ...], sector: str, industry: str) -> InstrumentProfile:
    return InstrumentProfile(
        instrument_id=instrument_id_for(exchange, code),
        code=code,
        exchange=exchange,
        board=board,
        name=name,
        aliases=aliases,
        sector=sector,
        industry=industry,
        data_availability=_IDENTITY,
    )


class InstrumentCatalog:
    """In-memory registry with code index and name/alias text search."""

    def __init__(self, profiles: tuple[InstrumentProfile, ...] = ()) -> None:
        self._by_id: dict[str, InstrumentProfile] = {}
        self._by_code: dict[str, InstrumentProfile] = {}
        for profile in profiles:
            self._put(profile)

    def _put(self, profile: InstrumentProfile) -> None:
        self._by_id[profile.instrument_id] = profile
        self._by_code[profile.code] = profile

    def resolve(self, query: str, *, limit: int = 10) -> list[InstrumentResolution]:
        """Resolve a raw query (code forms, name, or alias substring)."""
        query = (query or "").strip()
        if not query:
            return []

        # 1) Direct code interpretation.
        try:
            code, exchange, _board = normalize_code(query)
        except InvalidInstrumentCode:
            code_match = None
        else:
            code_match = self._by_code.get(code)
            if code_match is not None and code_match.exchange != exchange:
                # catalog inconsistency would be a data bug; treat as no match
                code_match = None
        if code_match is not None:
            return [InstrumentResolution(instrument=code_match, matched_by="code")]

        # 2) Name / alias substring search.
        seen: set[str] = set()
        results: list[InstrumentResolution] = []
        for profile in self._by_id.values():
            if len(results) >= limit:
                break
            if profile.instrument_id in seen:
                continue
            if profile.name.upper().find(query.upper()) >= 0:
                matched_by = "name"
            elif any(a.upper().find(query.upper()) >= 0 for a in profile.aliases):
                matched_by = "alias"
            else:
                continue
            seen.add(profile.instrument_id)
            results.append(
                InstrumentResolution(instrument=profile, matched_by=matched_by)
            )
        return results

    def get(self, instrument_id: str) -> InstrumentProfile | None:
        return self._by_id.get(instrument_id)

    def all(self) -> list[InstrumentProfile]:
        return list(self._by_id.values())


_default_catalog: InstrumentCatalog | None = None


def default_catalog() -> InstrumentCatalog:
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = InstrumentCatalog(
            tuple(
                _build_profile(code, name, exchange, board, aliases, sector, industry)
                for code, name, exchange, board, aliases, sector, industry in _SEED
            )
        )
    return _default_catalog
