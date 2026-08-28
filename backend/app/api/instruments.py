"""Instrument search / lookup API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import AppError
from app.domain.catalog import default_catalog
from app.domain.code_norm import InvalidInstrumentCode, normalize_code
from app.domain.instrument import utc_now

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _profile_payload(profile) -> dict:
    data = profile.model_dump(mode="json")
    # Explicit missing-data contract: absent analytical fields are surfaced
    # as null so clients can render "missing" instead of guessing (task书 §8).
    for optional in ("industry", "sector", "market_cap"):
        data[optional] = data.get(optional)
    return data


@router.get("")
def search_instruments(
    query: str = Query(default="", max_length=64, description="code, name, or alias"),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    # Dynamic resolution: if the query looks like a valid A-share code not in
    # the catalog, create a profile from the code structure (UX0)
    normalized = None
    try:
        code, exchange, board = normalize_code(query)
        normalized = f"{exchange.value}:{code}"
    except (InvalidInstrumentCode, ValueError):
        pass
    if normalized and normalized not in {p.instrument_id for p in default_catalog().all()}:
        from app.sources.runtime import get_runtime
        from app.sources.base import SourceRequest, utc_now
        result = get_runtime().registry.resolve(
            SourceRequest(capability="market_data", instrument_id=normalized, as_of=utc_now())
        )
        if result.is_success() and result.records:
            name = result.records[0].payload.get("name") or code
            profile = default_catalog().resolve_or_create(query, name=name)
            if profile:
                default_catalog().upsert(profile)

    resolutions = default_catalog().resolve(query, limit=limit)
    return {
        "query": query,
        "count": len(resolutions),
        "results": [
            {"matched_by": r.matched_by, "instrument": _profile_payload(r.instrument)}
            for r in resolutions
        ],
    }


@router.get("/{instrument_id}")
def get_instrument(instrument_id: str) -> dict:
    profile = default_catalog().get(instrument_id.upper())
    if profile is None:
        raise AppError("instrument.not_found", status_code=404)
    return {"instrument": _profile_payload(profile)}
