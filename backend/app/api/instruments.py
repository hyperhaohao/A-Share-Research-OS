"""Instrument search / lookup API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import AppError
from app.domain.catalog import default_catalog

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
