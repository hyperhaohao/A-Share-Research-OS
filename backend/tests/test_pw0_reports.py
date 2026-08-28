"""PW2 — report library list-all + latest version summary."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


@pytest.fixture()
def client():
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
    app.state._test_factory = factory
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def test_reports_list_all_newest_first_with_versions(client):
    from app.db import session_scope
    from app.storage.manifest_repo import ReportVersion, ReportVersionRepository
    from app.storage.report_repo import ReportRepository

    with session_scope(client.app.state._test_factory) as session:
        repo = ReportRepository(session)
        first = repo.save(
            instrument_id="SZSE:000831", snapshot_id="snap_000831aaa",
            language="zh-CN", gate_status="pass", published=False,
            markdown="", html="", content={},
        )
        second = repo.save(
            instrument_id="SSE:600519", snapshot_id="snap_600519aaa",
            language="zh-CN", gate_status="pass", published=False,
            markdown="", html="", content={},
        )
        versions = ReportVersionRepository(session)
        versions.save(ReportVersion(report_id=first, version_no=1, language="zh-CN",
                                    markdown="", html=""))
        versions.save(ReportVersion(report_id=first, version_no=2, language="zh-CN",
                                    parent_version_id="ver_1", change_reason="revision",
                                    markdown="", html=""))

    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    # newest first
    assert body["results"][0]["report_id"] == second
    by_id = {r["report_id"]: r for r in body["results"]}
    assert by_id[first]["latest_version_no"] == 2
    assert by_id[second]["latest_version_no"] == 1
    # per-instrument filtering still works
    scoped = client.get("/api/v1/reports", params={"instrument_id": "SZSE:000831"})
    assert scoped.json()["count"] == 1
