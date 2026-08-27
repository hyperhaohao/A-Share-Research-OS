"""Stable error envelope tests (TASK: no free-text as protocol)."""

from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import create_app


def test_unknown_route_returns_error_code_envelope():
    client = TestClient(create_app())
    resp = client.get("/api/v1/definitely-not-a-route")
    assert resp.status_code == 404
    body = resp.json()
    assert body["status"] == "error"
    assert body["error_code"] == "common.not_found"


def test_validation_error_returns_error_code_envelope():
    client = TestClient(create_app())
    resp = client.post("/api/v1/health")  # wrong method triggers 405 envelope
    assert resp.status_code == 405
    body = resp.json()
    assert body["status"] == "error"
    assert body["error_code"] == "common.method_not_allowed"


def test_app_error_carries_custom_code():
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise AppError("sample.custom_error", status_code=418)

    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 418
    assert resp.json()["error_code"] == "sample.custom_error"


def test_unhandled_exception_is_masked():
    app = create_app()

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret internals")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "common.internal_error"
    assert "secret" not in resp.text
