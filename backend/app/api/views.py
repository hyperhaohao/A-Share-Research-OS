"""UI Read Model API（UX Foundation, 评审 §12-§16）.

面向页面的聚合视图：一次请求返回一个页面所需的 L1/L2/L3 数据。
只读投影 —— 不建第二套 Domain，不写业务状态。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.market_data import resolve_instrument_id
from app.core.errors import AppError
from app.db import get_session
from app.services.view_service import ViewService

router = APIRouter(prefix="/views", tags=["views"])


@router.get("/watchlist")
def watchlist_view(session: Session = Depends(get_session)) -> dict:
    cards = ViewService(session).watchlist_cards()
    return {"count": len(cards), "results": cards}


@router.get("/instruments/{instrument_id}/overview")
def instrument_overview_view(instrument_id: str, session: Session = Depends(get_session)) -> dict:
    resolved = resolve_instrument_id(instrument_id, session, allow_remote=False)
    if resolved is None:
        raise AppError("instrument.not_found", status_code=404)
    return {"overview": ViewService(session).instrument_overview(resolved)}


@router.get("/command-center")
def command_center_view(session: Session = Depends(get_session)) -> dict:
    from datetime import datetime, timezone

    view = ViewService(session).command_center_view()
    view["generated_at"] = datetime.now(timezone.utc).isoformat()
    view["data_status"] = "ok"
    return {"view": view}


@router.get("/report-library")
def report_library_view(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    rows = ViewService(session).report_library_rows(limit=limit)
    return {"count": len(rows), "results": rows}


@router.get("/experience-cards")
def experience_cards_view(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    rows = ViewService(session).experience_rows(limit=limit)
    return {"count": len(rows), "results": rows}


@router.get("/continuous-research")
def continuous_research_view(session: Session = Depends(get_session)) -> dict:
    rows = ViewService(session).continuous_research_rows()
    names = ViewService(session)._names_for([t["instrument_id"] for t in rows])  # noqa: SLF001
    for t in rows:
        t["instrument"] = names.get(t["instrument_id"])
    return {"count": len(rows), "results": rows}


@router.get("/prediction-review")
def prediction_review_view(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    from datetime import datetime, timezone

    service = ViewService(session)
    rows = service.prediction_review_rows(limit=limit)
    names = service._names_for([p["instrument_id"] for p in rows])  # noqa: SLF001
    for p in rows:
        p["instrument"] = names.get(p["instrument_id"])
    validated = [p for p in rows if p["validated"]]
    direction_correct = sum(
        1 for p in validated if p["validation"] and p["validation"]["direction_correct"]
    )
    range_hit = sum(1 for p in validated if p["validation"] and p["validation"]["range_hit"])
    excess = [
        p["validation"]["instrument_return_pct"]
        for p in validated
        if p["validation"] and p["validation"]["instrument_return_pct"] is not None
    ]
    return {
        "count": len(rows),
        "results": rows,
        "kpi": {
            "total": len(rows),
            "validated": len(validated),
            "direction_accuracy": round(direction_correct / len(validated) * 100, 1)
            if validated
            else None,
            "range_hit_rate": round(range_hit / len(validated) * 100, 1) if validated else None,
            "avg_return_pct": round(sum(excess) / len(excess), 3) if excess else None,
            "conflicts": sum(1 for p in rows if p["consistency"] == "conflict"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
