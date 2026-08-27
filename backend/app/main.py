"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.instruments import router as instruments_router
from app.api.market_data import router as market_data_router
from app.api.source_health import router as source_health_router
from app.api.evidence import router as evidence_router
from app.api.snapshots import router as snapshots_router
from app.api.research import router as research_router
from app.api.quality import router as quality_router
from app.config import get_settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(instruments_router, prefix="/api/v1")
    app.include_router(market_data_router, prefix="/api/v1")
    app.include_router(source_health_router, prefix="/api/v1")
    app.include_router(evidence_router, prefix="/api/v1")
    app.include_router(snapshots_router, prefix="/api/v1")
    app.include_router(research_router, prefix="/api/v1")
    app.include_router(quality_router, prefix="/api/v1")
    return app


app = create_app()
