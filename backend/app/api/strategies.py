"""Strategy Lab API (V2 Phase F, 总纲 §46/§47)."""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.strategy import StrategyRepository
from app.core.errors import AppError
from app.db import get_session, session_scope
from app.services.strategy_service import StrategyRefusal, StrategyService

router = APIRouter(prefix="/strategies", tags=["strategy"])


class StrategyFromScreeningIn(BaseModel):
    screening_run_id: str = Field(min_length=6, max_length=32)
    name: str | None = Field(default=None, max_length=128)


def _execute_backtest_in_background(engine, backtest_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        backtest = StrategyRepository(worker_session).get_backtest(backtest_id)
        if backtest is None:
            return
        try:
            StrategyService(worker_session).run_backtest_from_backtest(backtest)
        except Exception:  # noqa: BLE001 — never kill the process on a backtest
            worker_session.rollback()
            StrategyRepository(worker_session).update_backtest(
                backtest_id, lambda p: {**p, "status": "failed", "error": "backtest crashed"}
            )


@router.post("/from-screening", status_code=201)
def create_from_screening(payload: StrategyFromScreeningIn, session: Session = Depends(get_session)) -> dict:
    try:
        version = StrategyService(session).create_from_screening(
            payload.screening_run_id, payload.name
        )
    except KeyError:
        raise AppError("screening.not_found", status_code=404) from None
    except StrategyRefusal as exc:
        raise AppError("strategy.unassemblable", status_code=422, detail=str(exc)) from None
    session.commit()
    return {"strategy": version}


@router.get("")
def list_strategies(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict:
    results = StrategyService(session).list_versions(limit=limit)
    return {"count": len(results), "results": results}


@router.get("/{version_id}")
def get_strategy(version_id: str, session: Session = Depends(get_session)) -> dict:
    detail = StrategyService(session).get_version_detail(version_id)
    if detail is None:
        raise AppError("strategy.not_found", status_code=404)
    return {"strategy": detail}


@router.post("/{version_id}/backtest", status_code=202)
def launch_backtest(version_id: str, session: Session = Depends(get_session)) -> dict:
    service = StrategyService(session)
    if service.get_version_detail(version_id) is None:
        raise AppError("strategy.not_found", status_code=404)
    backtest = service.start_backtest(version_id)
    session.commit()
    thread = threading.Thread(
        target=_execute_backtest_in_background,
        args=(session.get_bind(), backtest["backtest_id"]),
        daemon=True,
    )
    thread.start()
    return {"backtest": backtest}


@router.get("/backtests/{backtest_id}")
def get_backtest(backtest_id: str, session: Session = Depends(get_session)) -> dict:
    backtest = StrategyRepository(session).get_backtest(backtest_id)
    if backtest is None:
        raise AppError("strategy.not_found", status_code=404)
    return {"backtest": backtest}


@router.post("/{version_id}/validate")
def validate_strategy(version_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        version = StrategyService(session).validate_version(version_id)
    except KeyError:
        raise AppError("strategy.not_found", status_code=404) from None
    except StrategyRefusal as exc:
        raise AppError("strategy.validation_blocked", status_code=422, detail=str(exc)) from None
    return {"strategy": version}
