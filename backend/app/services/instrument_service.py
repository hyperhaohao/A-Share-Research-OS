"""Unified InstrumentService (PW0) — one identity path for every entry point.

Search / Watchlist / Task / Pipeline / Workspace / Report / Prediction all
resolve instruments through this service:

    resolve(query)
    → Instrument Registry (DB, persistent)
    → miss + valid A-share code
      → remote quote source (name verification) → upsert
    → miss + name/pinyin text
      → remote keyword search (validated candidates) → upsert
    → InstrumentProfile

Dynamic profiles persist in the ``instrument_registry`` table, so a resolved
identity (e.g. ``000831`` → 中国稀土) survives service restarts. When remote
sources are unreachable, a valid code still resolves to a ``code_only``
profile (name shown as the code until a real source enriches it) — the
workspace keeps working and nothing is fabricated.
"""

from __future__ import annotations

import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.catalog import default_catalog
from app.domain.code_norm import InvalidInstrumentCode, normalize_code
from app.domain.instrument import (
    Board,
    Exchange,
    InstrumentProfile,
    InstrumentResolution,
    instrument_id_for,
)
from app.sources.base import SourceRequest, utc_now
from app.sources.instrument_search import search_cn_instruments
from app.sources.runtime import get_runtime
from app.storage.instrument_repo import InstrumentRegistryORM, InstrumentRegistryRepository

_IDENTITY_AVAILABILITY = ("identity", "static_profile")
_CODE_ONLY_AVAILABILITY = ("identity", "code_only")

_seed_lock = threading.Lock()


def _canonical_id(raw: str) -> str | None:
    """Return the canonical instrument_id when ``raw`` already is one."""
    upper = raw.strip().upper()
    if ":" not in upper:
        return None
    exchange_str, code = upper.split(":", 1)
    try:
        exchange = Exchange(exchange_str)
        normalize_code(code)
    except (ValueError, InvalidInstrumentCode):
        return None
    return instrument_id_for(exchange, code)


def _profile_from_code(code: str, exchange: Exchange, board: Board, *, name: str | None) -> InstrumentProfile:
    return InstrumentProfile(
        instrument_id=instrument_id_for(exchange, code),
        code=code,
        exchange=exchange,
        board=board,
        name=name or code,  # code_only placeholder until a real source names it
        aliases=(),
        data_availability=(_IDENTITY_AVAILABILITY if name else _CODE_ONLY_AVAILABILITY),
    )


class InstrumentService:
    """Persistent, source-backed instrument identity (see module docstring)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = InstrumentRegistryRepository(session)

    # -- seed sync -------------------------------------------------------------

    def ensure_seed(self) -> None:
        """Idempotently persist the curated seed catalog into the registry.

        A sentinel-row check keeps the common path to one indexed SELECT; the
        lock makes concurrent first requests safe (get-then-insert races are
        impossible within the process). Existing rows are never overwritten —
        a live-resolved name always wins.
        """
        with _seed_lock:
            seeds = default_catalog().all()
            if self._repo.get(seeds[0].instrument_id) is not None:
                return
            for profile in seeds:
                if self._repo.get(profile.instrument_id) is None:
                    self._repo.upsert_profile(profile, origin="seed")
            self._session.flush()

    # -- search ------------------------------------------------------------------

    def search(
        self, query: str, *, limit: int = 10, allow_remote: bool = True
    ) -> list[InstrumentResolution]:
        query = (query or "").strip()
        if not query:
            return []
        self.ensure_seed()

        # 1) Canonical id form: "SSE:600519"
        canonical = _canonical_id(query)
        if canonical is not None:
            profile = self.ensure_profile(canonical, allow_remote=allow_remote)
            return [InstrumentResolution(instrument=profile, matched_by="code")] if profile else []

        # 2) Structured code form: "000831" / "000831.SZ" / "SZ000001"
        try:
            code, exchange, board = normalize_code(query)
        except InvalidInstrumentCode:
            code = None
        if code is not None:
            row = self._repo.get_by_code(code)
            if row is not None and row.origin != "code_only":
                return [
                    InstrumentResolution(
                        instrument=self._repo.row_to_profile(row), matched_by="code"
                    )
                ]
            # missing or code_only → ensure_profile (persists / enriches)
            profile = self.ensure_profile(
                instrument_id_for(exchange, code), allow_remote=allow_remote
            )
            return [InstrumentResolution(instrument=profile, matched_by="code")] if profile else []

        # 3) Local name / alias search over the persistent registry.
        results: list[InstrumentResolution] = []
        seen: set[str] = set()
        for row in self._repo.search_text(query, limit=limit):
            seen.add(row.instrument_id)
            results.append(
                InstrumentResolution(
                    instrument=self._repo.row_to_profile(row), matched_by="name"
                )
            )
        if len(results) < limit:
            q = query.upper()
            for profile in self._alias_scan():
                if profile.instrument_id in seen:
                    continue
                if any(q in alias.upper() for alias in profile.aliases):
                    seen.add(profile.instrument_id)
                    results.append(
                        InstrumentResolution(instrument=profile, matched_by="alias")
                    )
                    if len(results) >= limit:
                        break

        if results or not allow_remote:
            return results

        # 4) Remote keyword resolution (real sources; candidates validated
        #    against local code-prefix rules inside the resolver).
        return self._search_remote(query, limit=limit)

    def _search_remote(self, query: str, *, limit: int) -> list[InstrumentResolution]:
        outcome = search_cn_instruments(query, limit=limit)
        if outcome.error_type is not None or not outcome.candidates:
            return []
        resolutions: list[InstrumentResolution] = []
        for i, candidate in enumerate(outcome.candidates):
            # Verify the top candidate's name against a real quote fetch;
            # further candidates keep the search result's authoritative
            # listing name (both are real-source data, never invented).
            name = candidate.name
            if i == 0:
                verified = self._quote_name(candidate.instrument_id)
                if verified:
                    name = verified
            code, exchange, board = normalize_code(candidate.code)
            profile = _profile_from_code(code, exchange, board, name=name)
            self._repo.upsert_profile(profile, origin="resolved")
            resolutions.append(InstrumentResolution(instrument=profile, matched_by="name"))
        self._session.flush()
        return resolutions

    # -- id resolution ------------------------------------------------------------

    def resolve_id(self, raw: str, *, allow_remote: bool = True) -> str | None:
        """Resolve any accepted form to a canonical instrument_id (or None)."""
        raw = (raw or "").strip()
        if not raw:
            return None
        if ":" in raw:
            canonical = _canonical_id(raw)
            if canonical is not None:
                self.ensure_profile(canonical, allow_remote=allow_remote)
                return canonical
        resolutions = self.search(raw, limit=1, allow_remote=allow_remote)
        if resolutions:
            return resolutions[0].instrument.instrument_id
        return None

    def ensure_profile(
        self, instrument_id: str, *, allow_remote: bool = True
    ) -> InstrumentProfile | None:
        """Guarantee a persistent profile exists for a canonical id.

        Order: registry (real-name rows returned as-is) → code_only rows get
        one opportunistic enrichment attempt when remote is allowed → new
        ids resolve via remote quote verification → code_only structural
        profile as the offline fallback. ``None`` only for non-A-share ids.
        """
        row = self._repo.get(instrument_id)
        if row is not None and row.origin != "code_only":
            return self._repo.row_to_profile(row)

        # derive the bare code (a canonical id carries the exchange prefix)
        raw = row.code if row else instrument_id.split(":", 1)[1] if ":" in instrument_id else instrument_id
        try:
            code, exchange, board = normalize_code(raw)
        except InvalidInstrumentCode:
            return None
        if instrument_id_for(exchange, code) != instrument_id:
            return None

        if row is not None:
            # code_only row: enrich opportunistically (user-initiated paths
            # only — read paths pass allow_remote=False and stay cheap).
            if allow_remote:
                name = self._quote_name(instrument_id)
                if name:
                    profile = _profile_from_code(code, exchange, board, name=name)
                    self._repo.upsert_profile(profile, origin="resolved")
                    self._session.flush()
                    return profile
            return self._repo.row_to_profile(row)

        name = self._quote_name(instrument_id) if allow_remote else None
        profile = _profile_from_code(code, exchange, board, name=name)
        self._repo.upsert_profile(profile, origin="resolved" if name else "code_only")
        self._session.flush()
        return profile

    def get_profile(
        self, instrument_id: str, *, allow_remote: bool = True
    ) -> InstrumentProfile | None:
        self.ensure_seed()
        row = self._repo.get(instrument_id.strip().upper())
        if row is not None:
            return self._repo.row_to_profile(row)
        return self.ensure_profile(instrument_id, allow_remote=allow_remote)

    # -- helpers -------------------------------------------------------------

    def _alias_scan(self) -> list[InstrumentProfile]:
        """Alias matching over registry rows (registry is bounded by listed
        A-share count; a portable alias LIKE across engines is not worth it)."""
        rows = self._session.scalars(select(InstrumentRegistryORM)).all()
        return [self._repo.row_to_profile(row) for row in rows]

    def _quote_name(self, instrument_id: str) -> str | None:
        """Best-effort live name verification through the market-data source.

        Network failures degrade to ``None`` (caller keeps the structural
        profile) — resolution never fabricates a name.
        """
        try:
            result = get_runtime().registry.resolve(
                SourceRequest(
                    capability="market_data", instrument_id=instrument_id, as_of=utc_now()
                )
            )
        except Exception:  # noqa: BLE001 — unreachable source must not break identity
            return None
        if result.is_success() and result.records:
            name = result.records[0].payload.get("name")
            return name if isinstance(name, str) and name.strip() else None
        return None
