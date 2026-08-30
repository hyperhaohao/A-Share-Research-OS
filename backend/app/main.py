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
from app.api.analysts import router as analysts_router
from app.api.debate import router as debate_router
from app.api.valuation import router as valuation_router
from app.api.reports import router as reports_router
from app.api.manifest import router as manifest_router
from app.api.report_qa import router as report_qa_router
from app.api.audit import router as audit_router, revisions_router
from app.api.timeline import router as timeline_router
from app.api.graph import router as graph_router
from app.api.tasks import router as tasks_router
from app.api.predictions import router as predictions_router
from app.api.stream import router as stream_router, watchlist_router
from app.api.regression import router as regression_router
from app.api.costs import router as costs_router
from app.api.monitor import router as monitor_router
from app.api.artifacts import router as artifacts_router
from app.api.command import router as command_router
from app.api.experience import router as experience_router
from app.api.workflows import router as workflows_router
from app.api.screening import router as screening_router
from app.api.strategies import router as strategies_router
from app.api.strategy_monitors import router as strategy_monitors_router
from app.api.research_map import router as research_map_router
from app.api.replay import router as replay_router
from app.api.views import router as views_router
from app.api.auth import router as auth_router
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

    from fastapi import Request as FastAPIRequest

    from app.auth import decode_token
    from app.config import get_settings as _gs

    _OPEN_PATHS = {"/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/register", "/api/openapi.json", "/api/docs"}

    @app.middleware("http")
    async def auth_gate(request: FastAPIRequest, call_next):
        """Multi-user auth gate — active only when ASRO_AUTH_ENABLED=true."""
        if not _gs().auth_enabled:
            return await call_next(request)
        path = request.url.path
        if path in _OPEN_PATHS or path.startswith("/api/v1/auth/"):
            return await call_next(request)
        if not path.startswith("/api/v1/"):
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
        if not token:
            token = request.query_params.get("token", "")
        if not token:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"status": "error", "error_code": "auth.token_required"})
        payload = decode_token(token)
        if payload is None:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"status": "error", "error_code": "auth.token_invalid"})
        request.state.user = {"username": payload["sub"], "role": payload.get("role", "viewer")}
        # role enforcement: viewer = GET only; analyst/admin = full access
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if payload.get("role") == "viewer":
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"status": "error", "error_code": "auth.forbidden"})
        return await call_next(request)

    from app.db import get_session as _get_session_dep

    @app.middleware("http")
    async def commit_db_session(request: FastAPIRequest, call_next):
        """Commit the request's DB session BEFORE the response is sent.

        FastAPI runs dependency teardown (get_session's commit) after the
        response is delivered, so without this a client that follows a write
        with an immediate read can observe pre-commit state.
        """
        response = await call_next(request)
        session = getattr(request.state, "db_session", None)
        if session is not None:
            session.commit()
        return response

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
    app.include_router(analysts_router, prefix="/api/v1")
    app.include_router(debate_router, prefix="/api/v1")
    app.include_router(valuation_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(manifest_router, prefix="/api/v1")
    app.include_router(report_qa_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(revisions_router, prefix="/api/v1")
    app.include_router(timeline_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(predictions_router, prefix="/api/v1")
    app.include_router(stream_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(regression_router, prefix="/api/v1")
    app.include_router(costs_router, prefix="/api/v1")
    app.include_router(monitor_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")
    app.include_router(command_router, prefix="/api/v1")
    app.include_router(experience_router, prefix="/api/v1")
    app.include_router(workflows_router, prefix="/api/v1")
    app.include_router(screening_router, prefix="/api/v1")
    app.include_router(strategies_router, prefix="/api/v1")
    app.include_router(strategy_monitors_router, prefix="/api/v1")
    app.include_router(research_map_router, prefix="/api/v1")
    app.include_router(replay_router, prefix="/api/v1")
    app.include_router(views_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    return app


app = create_app()
