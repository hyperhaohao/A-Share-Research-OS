"""Market data API — real quotes through the source registry (M3)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import AppError
from app.domain.catalog import default_catalog
from app.domain.code_norm import InvalidInstrumentCode, normalize_code
from app.sources.base import SourceRequest, utc_now
from app.sources.runtime import get_runtime

router = APIRouter(tags=["market-data"])


def resolve_instrument_id(raw: str) -> str | None:
    """Resolve any accepted instrument form (code/prefix/name) to an id."""
    upper = raw.strip().upper()
    if upper.split(":")[0] in ("SSE", "SZSE", "BSE") and ":" in upper:
        return upper  # already a canonical instrument_id
    try:
        code, exchange, _board = normalize_code(raw)
    except InvalidInstrumentCode:
        results = default_catalog().resolve(raw, limit=1)
        if not results:
            return None
        return results[0].instrument.instrument_id
    return f"{exchange.value}:{code}"


@router.get("/market-data/quote")
def quote(
    instrument: str = Query(min_length=4, max_length=32, description="code or instrument_id"),
) -> dict:
    """Realtime quote resolved through the source layer (fallback + cache)."""
    instrument_id = resolve_instrument_id(instrument)
    if instrument_id is None:
        raise AppError("instrument.not_found", status_code=404)

    runtime = get_runtime()
    request = SourceRequest(capability="market_data", instrument_id=instrument_id, as_of=utc_now())
    result = runtime.resolve_cached(request)

    if not result.is_success():
        raise AppError(
            "source.unavailable",
            status_code=503,
            detail=result.error_type or result.no_data_reason or result.status.value,
        )
    record = result.records[0]
    return {
        "instrument_id": record.subject,
        "quote": record.payload,
        "event_time": record.event_time.isoformat() if record.event_time else None,
        "available_time": record.available_time.isoformat(),
        "source": result.source,
        "as_of": result.as_of.isoformat(),
        "from_cache": bool(result.metadata.get("from_cache", False)),
    }
