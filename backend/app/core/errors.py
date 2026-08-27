"""Stable error semantics.

Every error surfaced by the API carries a stable ``error_code`` so the
frontend can localize it; free-text detail is diagnostic only (task书 §9,
AGENTS.md §15). ``error_code`` values follow ``<domain>.<reason>`` kebab
dotted style, e.g. ``common.not_found``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Business error carrying a stable error code and HTTP status."""

    def __init__(self, error_code: str, status_code: int = 400, *, detail: str | None = None):
        super().__init__(detail or error_code)
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail


def error_body(error_code: str, *, detail: str | None = None) -> dict:
    """Build the canonical error envelope."""
    body: dict = {"status": "error", "error_code": error_code}
    if detail:
        body["detail"] = detail
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.error_code, detail=exc.detail),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "common.not_found", 405: "common.method_not_allowed"}.get(
            exc.status_code, "common.http_error"
        )
        return JSONResponse(status_code=exc.status_code, content=error_body(code))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body("common.validation_error", detail=str(exc.errors()[:3])),
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Never leak internals to clients; log server-side in later milestones.
        return JSONResponse(status_code=500, content=error_body("common.internal_error"))
