"""G9 — Research Products 产品化（观澜语义迁移任务书 §G9）.

覆盖：
  - compile+register → 版本落库 + Artifact（临时 dict 不再冒充产品）；
  - 未确认 → 422；未知 kind → 404；
  - 每版可查看与上一版变化（diff_vs_previous）；
  - Overseas 诚实命名（OVERSEAS_EVIDENCE_RADAR + missing_chain）；
  - compiles 列表 + 版本 diff 端点。
"""

from __future__ import annotations

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


def test_compile_register_version_and_artifact(client):
    r1 = client.post("/api/v1/research-products/daily-brief/compile",
                     json={"confirm": True})
    assert r1.status_code == 201, r1.text
    c1 = r1.json()
    assert c1["version"] == 1
    assert c1["artifact_id"], "product must register an artifact"
    assert c1["provenance_status"] == "complete"

    r2 = client.post("/api/v1/research-products/daily-brief/compile",
                     json={"confirm": True}).json()
    assert r2["version"] == 2
    assert r2["diff_vs_previous"]["previous_version"] == 1

    # 列表
    lst = client.get("/api/v1/research-products/compiles",
                     params={"product_type": "DAILY_RESEARCH_BRIEF"}).json()
    assert lst["count"] == 2

    # 版本 diff
    diff = client.get("/api/v1/research-products/compiles/diff",
                      params={"product_type": "DAILY_RESEARCH_BRIEF",
                              "v1": 1, "v2": 2}).json()
    assert diff["v1"] == 1 and diff["v2"] == 2


def test_unconfirmed_compile_rejected(client):
    r = client.post("/api/v1/research-products/daily-brief/compile",
                    json={"confirm": False})
    assert r.status_code == 422
    assert r.json()["error_code"] == "research_products.compile_needs_confirm"


def test_unknown_kind_404(client):
    r = client.post("/api/v1/research-products/no-such/compile",
                    json={"confirm": True})
    assert r.status_code == 404


def test_overseas_radar_honest_naming(client):
    r = client.post("/api/v1/research-products/overseas-mapping/compile",
                    json={"confirm": True})
    assert r.status_code == 201
    product = r.json()["product"]
    assert product["product_type"] == "OVERSEAS_EVIDENCE_RADAR"
    assert product["mapping_depth"] == "evidence_radar"
    assert len(product["missing_chain"]) == 4
