"""部署准备：多用户认证（JWT + bcrypt + middleware gate）."""

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password
from app.config import get_settings
from app.db import get_session
from app.main import create_app
from app.storage.orm import Base


@pytest.fixture()
def client_auth_on():
    """Auth enabled — middleware gates /api/v1/*."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    original = get_settings().auth_enabled
    get_settings().auth_enabled = True
    app = create_app()
    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    get_settings().auth_enabled = original


@pytest.fixture()
def client_auth_off():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)


def test_auth_disabled_by_default(client_auth_off):
    """Default: auth off → all endpoints accessible without token."""
    resp = client_auth_off.get("/api/v1/health")
    assert resp.status_code == 200
    resp = client_auth_off.get("/api/v1/views/watchlist")
    assert resp.status_code == 200


def test_register_bootstrap_creates_admin(client_auth_on):
    """First register = admin bootstrap (no auth needed when table is empty)."""
    resp = client_auth_on.post(
        "/api/v1/auth/register", json={"username": "admin", "password": "secret123", "role": "admin"}
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "admin"


def test_register_second_user_requires_admin_token(client_auth_on):
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    # no token → 401
    r1 = client_auth_on.post("/api/v1/auth/register", json={"username": "bob", "password": "password1"})
    assert r1.status_code == 401
    # login as admin → token → register bob
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    r2 = client_auth_on.post(
        "/api/v1/auth/register",
        json={"username": "bob", "password": "password1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201
    assert r2.json()["user"]["role"] == "analyst"


def test_register_duplicate_username_409(client_auth_on):
    """409 only after auth (username enumeration is prevented by 401-first)."""
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    token = login.json()["access_token"]
    r = client_auth_on.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "other123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


def test_login_and_access_protected(client_auth_on):
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    token = login.json()["access_token"]
    # protected endpoint with token
    resp = client_auth_on.get("/api/v1/views/watchlist", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # without token → 401
    resp = client_auth_on.get("/api/v1/views/watchlist")
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "auth.token_required"


def test_login_invalid_credentials(client_auth_on):
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    resp = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "auth.invalid_credentials"


def test_me_endpoint(client_auth_on):
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    token = login.json()["access_token"]
    resp = client_auth_on.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["role"] == "admin"


def test_role_enforcement_viewer_write_403(client_auth_on):
    """Role gate: viewer can read but cannot write (403 on POST/DELETE)."""
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    admin_token = login.json()["access_token"]
    # create a viewer user
    client_auth_on.post(
        "/api/v1/auth/register",
        json={"username": "viewer1", "password": "viewpass1", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    viewer_login = client_auth_on.post("/api/v1/auth/login", json={"username": "viewer1", "password": "viewpass1"})
    viewer_token = viewer_login.json()["access_token"]
    # GET is allowed for viewer
    resp = client_auth_on.get("/api/v1/views/watchlist", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp.status_code == 200
    # POST is denied for viewer
    resp = client_auth_on.post(
        "/api/v1/watchlist", json={"instrument": "600519"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "auth.forbidden"


def test_role_enforcement_analyst_can_write(client_auth_on):
    """Analyst role can write (full access except admin operations)."""
    client_auth_on.post("/api/v1/auth/register", json={"username": "admin", "password": "secret123"})
    login = client_auth_on.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    admin_token = login.json()["access_token"]
    client_auth_on.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "analypass1", "role": "analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    analyst_login = client_auth_on.post("/api/v1/auth/login", json={"username": "analyst1", "password": "analypass1"})
    analyst_token = analyst_login.json()["access_token"]
    resp = client_auth_on.post(
        "/api/v1/watchlist", json={"instrument": "600519"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 201
