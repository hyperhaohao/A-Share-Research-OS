"""Persistent Instrument Registry (PW0).

The in-memory seed catalog (``domain/catalog.py``) remains the curated
baseline of identity facts; this registry is the *durable* store every entry
point (Search / Watchlist / Task / Pipeline / Workspace / Report / Prediction)
reads and writes through :class:`app.services.instrument_service.InstrumentService`.

Dynamic resolutions — e.g. ``000831`` → 中国稀土, resolved live from a real
quote source — are upserted here so they survive service restarts. Identity
facts (code/name/exchange/board) are publicly verifiable reference data from
real sources; analytical fields (industry/sector) stay ``None`` until a real
source provides them (missing is displayed, never guessed).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, func, select
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.domain.instrument import Board, Exchange, InstrumentProfile, ListedStatus
from app.storage.orm import Base


class InstrumentRegistryORM(Base):
    __tablename__ = "instrument_registry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str] = mapped_column(String(8))
    board: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(64))
    aliases_json: Mapped[list] = mapped_column(JSON, default=list)
    listed_status: Mapped[str] = mapped_column(String(16), default="listed")

    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Provenance: seed (curated catalog) / resolved (live source) / code_only
    # (structure derived, name pending enrichment).
    origin: Mapped[str] = mapped_column(String(16), default="resolved")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class InstrumentRegistryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, instrument_id: str) -> InstrumentRegistryORM | None:
        return self._session.scalars(
            select(InstrumentRegistryORM).where(
                InstrumentRegistryORM.instrument_id == instrument_id
            )
        ).first()

    def get_by_code(self, code: str) -> InstrumentRegistryORM | None:
        return self._session.scalars(
            select(InstrumentRegistryORM).where(InstrumentRegistryORM.code == code)
        ).first()

    def search_text(self, query: str, *, limit: int = 10) -> list[InstrumentRegistryORM]:
        """Case-insensitive substring match over name; code/alias matching
        lives in the service layer (codes are structured, aliases in JSON)."""
        pattern = f"%{query.strip().upper()}%"
        rows = self._session.scalars(
            select(InstrumentRegistryORM)
            .where(func.upper(InstrumentRegistryORM.name).like(pattern))
            .order_by(InstrumentRegistryORM.code)
            .limit(limit)
        ).all()
        return list(rows)

    def all_ids(self) -> set[str]:
        return set(
            self._session.scalars(select(InstrumentRegistryORM.instrument_id)).all()
        )

    def upsert_profile(self, profile: InstrumentProfile, *, origin: str) -> InstrumentProfile:
        """Insert-or-update from a domain profile. First-write-wins for
        created_at; a ``code_only`` row is upgraded in place when a real
        name arrives (origin → ``resolved``)."""
        row = self.get(profile.instrument_id)
        now = _utc()
        if row is None:
            row = InstrumentRegistryORM(
                instrument_id=profile.instrument_id,
                code=profile.code,
                exchange=profile.exchange.value,
                board=profile.board.value,
                name=profile.name,
                aliases_json=list(profile.aliases),
                listed_status=profile.listed_status.value,
                sector=profile.sector,
                industry=profile.industry,
                origin=origin,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
            self._session.flush()
            return profile
        # update-in-place (names/enrichment may arrive later than the code);
        # a code-placeholder name never overwrites a real resolved name
        if profile.name and profile.name != profile.code:
            row.name = profile.name
        if profile.aliases:
            merged = list(dict.fromkeys([*row.aliases_json, *profile.aliases]))
            row.aliases_json = merged
        if profile.industry:
            row.industry = profile.industry
        if profile.sector:
            row.sector = profile.sector
        if origin != "code_only":
            row.origin = origin
        row.updated_at = now
        self._session.flush()
        return self.row_to_profile(row)

    def delete(self, instrument_id: str) -> bool:
        row = self.get(instrument_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    @staticmethod
    def row_to_profile(row: InstrumentRegistryORM) -> InstrumentProfile:
        return InstrumentProfile(
            instrument_id=row.instrument_id,
            code=row.code,
            exchange=Exchange(row.exchange),
            board=Board(row.board),
            name=row.name,
            aliases=tuple(row.aliases_json or ()),
            listed_status=ListedStatus(row.listed_status),
            sector=row.sector,
            industry=row.industry,
        )
