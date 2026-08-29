"""UI Read Model API（UX Foundation, 评审 §12-§16）.

面向页面的聚合视图：一次请求返回一个页面所需的 L1/L2/L3 数据。
只读投影 —— 不建第二套 Domain，不写业务状态。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
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
