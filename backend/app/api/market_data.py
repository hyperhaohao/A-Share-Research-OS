"""Market data API — real quotes through the source registry (M3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.instrument_service import InstrumentService
from app.sources.base import SourceRequest, utc_now
from app.sources.runtime import get_runtime

router = APIRouter(tags=["market-data"])


def resolve_instrument_id(raw: str, session: Session, *, allow_remote: bool = True) -> str | None:
    """Resolve any accepted form (code/prefix/name) to a canonical id.

    PW0: goes through the unified InstrumentService — persistent registry
    first, real-source resolution second. ``allow_remote=False`` keeps read
    paths off the network (registry + code structure only)."""
    return InstrumentService(session).resolve_id(raw, allow_remote=allow_remote)


@router.get("/market-data/quote")
def quote(
    instrument: str = Query(min_length=4, max_length=32, description="code or instrument_id"),
    session: Session = Depends(get_session),
) -> dict:
    """Realtime quote resolved through the source layer (fallback + cache)."""
    instrument_id = resolve_instrument_id(instrument, session, allow_remote=False)
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

@router.get("/market-data/daily-bars")
def daily_bars(
    instrument: str = Query(default="", max_length=32),
    limit: int = Query(default=60, ge=10, le=500),
    session: Session = Depends(get_session),
) -> dict:
    """Evidence-backed daily bars (PIT-visible kline evidence, G7 K线区数据源).

    Honest contract: no kline evidence collected yet -> empty bars + has_data
    false (前端显形「暂无K线数据」，不回退假图，方案 §25)."""
    from app.services.workflow_service import load_daily_bars

    resolved = resolve_instrument_id(instrument, session, allow_remote=False)
    if resolved is None:
        raise AppError("instrument.not_found", status_code=404)
    bars = load_daily_bars(session, resolved)
    shown = bars[-limit:] if limit and len(bars) > limit else bars
    return {
        "instrument_id": resolved,
        "count": len(shown),
        "total_collected": len(bars),
        "has_data": len(shown) > 0,
        "bars": shown,
    }
