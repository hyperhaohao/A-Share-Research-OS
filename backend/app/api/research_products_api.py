"""Research Product Compiler API（R8-C7，方案 §11.4-§11.6）."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.research_products_compiler import MarketProductCompiler

router = APIRouter(prefix="/research-products", tags=["research-products"])


@router.get("/mainline-radar")
def mainline_radar(session: Session = Depends(get_session)) -> dict:
    return {"product": MarketProductCompiler(session).compile_mainline_radar()}


@router.get("/overseas-mapping")
def overseas_mapping(session: Session = Depends(get_session)) -> dict:
    return {"product": MarketProductCompiler(session).compile_overseas_mapping()}


@router.get("/daily-brief")
def daily_brief(session: Session = Depends(get_session)) -> dict:
    return {"product": MarketProductCompiler(session).compile_daily_brief()}
