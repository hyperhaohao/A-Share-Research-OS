"""Research Product Compiler API（R8-C7，方案 §11.4-§11.6）."""

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import AppError
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


class CompileRegisterIn(BaseModel):
    confirm: bool = Field(default=False)


@router.post("/{kind}/compile", status_code=201)
def compile_and_register_product(kind: str, payload: CompileRegisterIn,
                                 session: Session = Depends(get_session)) -> dict:
    """编译 + 版本落库 + Artifact 注册（§G9：产品=Artifact/Version/PIT）。

    显式 Command（confirm=true）；未确认 → 422。
    """
    if not payload.confirm:
        raise AppError(
            "research_products.compile_needs_confirm", status_code=422,
            detail="POST {\"confirm\": true} — compile+register is an explicit command",
        ) from None
    if kind not in ("mainline-radar", "overseas-mapping", "daily-brief"):
        raise AppError("research_products.unknown_kind", status_code=404) from None
    kind_map = {"mainline-radar": "mainline_radar",
                "overseas-mapping": "overseas_mapping",
                "daily-brief": "daily_brief"}
    from app.services.research_products_compiler import MarketProductCompiler

    out = MarketProductCompiler(session).compile_and_register(kind_map[kind])
    session.commit()
    return out


@router.get("/compiles")
def list_compiles(product_type: str | None = Query(default=None, max_length=40),
                  limit: int = Query(default=20, ge=1, le=100),
                  session: Session = Depends(get_session)) -> dict:
    from app.services.research_products_compiler import MarketProductCompiler

    results = MarketProductCompiler(session).list_compiles(
        product_type=product_type, limit=limit)
    return {"count": len(results), "results": results}


@router.get("/compiles/diff")
def compile_diff(product_type: str = Query(max_length=40),
                 v1: int = Query(ge=1), v2: int = Query(ge=1),
                 session: Session = Depends(get_session)) -> dict:
    from app.core.errors import AppError
    from app.services.research_products_compiler import MarketProductCompiler

    try:
        out = MarketProductCompiler(session).compile_diff(product_type, v1, v2)
    except ValueError as exc:
        raise AppError("research_products.version_not_found", status_code=404,
                       detail=str(exc)) from None
    return out
