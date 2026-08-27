"""RunManifest + ReportVersion chain tests (任务书 §40/§41/§78)."""

import hashlib
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.manifest_repo import ManifestRepository, ReportVersionRepository
from app.storage.orm import Base
from tests.test_research_api import RAW_OK

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)


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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


class TestRunManifest:
    def test_manifest_roundtrip(self, client):
        digest = hashlib.sha256(b"config").hexdigest()
        body = client.post(
            "/api/v1/run-manifests",
            json={
                "run_id": "run_abc",
                "as_of": NOW.isoformat(),
                "code_commit": "abcdef1234567",
                "config_digest": digest,
                "random_seed": 42,
                "snapshot_id": "snap_test000000000000",
                "started_at": (NOW - timedelta(minutes=5)).isoformat(),
                "status": "running",
            },
        )
        assert body.status_code == 201, body.text
        manifest = body.json()["manifest"]
        assert manifest["random_seed"] == 42
        assert manifest["code_commit"] == "abcdef1234567"

        fetched = client.get("/api/v1/run-manifests", params={"run_id": "run_abc"}).json()["manifest"]
        assert fetched["manifest_id"] == manifest["manifest_id"]
        assert fetched["snapshot_id"] == "snap_test000000000000"

    def test_terminal_status_requires_finished_at(self, client):
        digest = hashlib.sha256(b"config").hexdigest()
        resp = client.post(
            "/api/v1/run-manifests",
            json={
                "run_id": "run_bad",
                "as_of": NOW.isoformat(),
                "code_commit": "abcdef1234567",
                "config_digest": digest,
                "random_seed": 1,
                "started_at": NOW.isoformat(),
                "status": "succeeded",  # terminal without finished_at
            },
        )
        assert resp.status_code == 422


class TestReportVersionChain:
    def _seed_report(self, client, monkeypatch):
        resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
        monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
        client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": "600519", "as_of": "2026-08-28T15:00:00+00:00"},
        ).json()["snapshot"]
        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
        ).json()["report"]
        return report

    def test_v1_seeded_then_revision_creates_v11_keeping_v10(self, client, monkeypatch):
        """§78: V1.0 → review → accept → V1.1; V1.0 must still exist."""
        report = self._seed_report(client, monkeypatch)

        # first version call seeds V1 from the stored artifact
        v1 = client.post(
            f"/api/v1/reports/{report['report_id']}/versions",
            json={"language": "zh-CN", "markdown": report["markdown"], "html": report["html"]},
        ).json()["version"]
        assert v1["version_no"] == 1
        assert v1["parent_version_id"] is None

        # revision → V1.1 with a change reason
        v11 = client.post(
            f"/api/v1/reports/{report['report_id']}/versions",
            json={
                "language": "zh-CN",
                "markdown": report["markdown"] + "\n\n<!-- revised -->",
                "changed_sections": ["valuation"],
                "change_reason": "accept revision: updated valuation note",
            },
        ).json()["version"]
        assert v11["version_no"] == 2
        assert v11["parent_version_id"] == v1["version_id"]
        assert v11["change_reason"]

        # both versions still exist, V1.0 content unchanged
        chain = client.get(f"/api/v1/reports/{report['report_id']}/versions").json()
        assert chain["count"] == 2
        v1_fetched = client.get(f"/api/v1/reports/{report['report_id']}/versions/{v1['version_id']}").json()["version"]
        assert "<!-- revised -->" not in v1_fetched["markdown"]
        assert v1_fetched["markdown"] == report["markdown"]

    def test_revision_requires_change_reason(self, client, monkeypatch):
        report = self._seed_report(client, monkeypatch)
        client.post(
            f"/api/v1/reports/{report['report_id']}/versions",
            json={"language": "zh-CN", "markdown": report["markdown"]},
        )
        resp = client.post(
            f"/api/v1/reports/{report['report_id']}/versions",
            json={"language": "zh-CN", "markdown": "x", "change_reason": None},
        )
        assert resp.status_code == 422

    def test_unknown_report_is_404(self, client):
        resp = client.post(
            "/api/v1/reports/rpt_doesnotexist/versions",
            json={"language": "zh-CN", "markdown": "x"},
        )
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "report.not_found"
