"""Instrument domain models (task书 §19).

An instrument is the universal research subject. Identity fields
(code/exchange/market/name) are static reference facts; analytical fields
(industry/sector/concept_tags/market_cap) are populated from sources and
tracked with data availability so missing data is displayed as missing
(never guessed).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Exchange(str, Enum):
    SSE = "SSE"  # 上海证券交易所
    SZSE = "SZSE"  # 深圳证券交易所
    BSE = "BSE"  # 北京证券交易所


class Board(str, Enum):
    MAIN = "main_board"  # 沪/深主板
    CHINEXT = "chinext"  # 创业板
    STAR = "star_market"  # 科创板
    BSE = "bse"  # 北交所


class ListedStatus(str, Enum):
    LISTED = "listed"
    SUSPENDED = "suspended"
    DELISTED = "delisted"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InstrumentProfile(BaseModel):
    """Universal instrument identity + analytical metadata."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    instrument_id: str = Field(min_length=3, max_length=32)  # e.g. "SSE:600519"
    market: Literal["CN"] = "CN"
    code: str = Field(pattern=r"^\d{6}$")
    exchange: Exchange
    board: Board
    name: str = Field(min_length=1, max_length=64)
    aliases: tuple[str, ...] = ()

    currency: Literal["CNY"] = "CNY"
    industry: str | None = None
    sector: str | None = None
    concept_tags: tuple[str, ...] = ()

    listed_status: ListedStatus = ListedStatus.LISTED
    market_cap: float | None = Field(default=None, gt=0)
    data_availability: tuple[str, ...] = ()

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("name", "industry", "sector")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    def matches_text(self, query: str) -> bool:
        """Case/width-insensitive text match over name and aliases."""
        q = query.strip().upper()
        if not q:
            return False
        candidates = [self.name, *self.aliases, self.code]
        return any(q in c.upper() for c in candidates)


class InstrumentResolution(BaseModel):
    """One resolution attempt result for the search API."""

    model_config = ConfigDict(extra="forbid")

    instrument: InstrumentProfile
    matched_by: Literal["code", "name", "alias"]


def instrument_id_for(exchange: Exchange, code: str) -> str:
    return f"{exchange.value}:{code}"
