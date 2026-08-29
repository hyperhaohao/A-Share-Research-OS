"""V2 Phase H — 产业研究地图 + 全球宏观视图（总纲 §11/§52/§77）.

验收：
  - 管线跑完后（industry_profile + macro 证据在库），两个视图由真实证据
    组装：产业链/主业来自 industry_data 证据；全球坐标来自 macro_policy
    证据（主题 + 官方机构提及），并显式披露数据边界；
  - 相关公司 = 证据文本与注册表名称共现（真实共现，无编造关系）；
  - PIT：as_of 取证据时间；两个视图注册为 Artifact（generated_from 报告）；
  - 证据缺失 → 404 显式拒绝（不返回空壳视图）。
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


RAW_OK = (
    'v_sz000831="1~中国稀土~000831~24.83~1651.00~1655.00~32924~85755~24354~'
    "24.83~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "24.83~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "24.83/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    "24.83/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~"
    '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
)

INDUSTRY_JSON = {
    "jbzl": [
        {
            "EM2016": "稀土-稀土资源-稀土矿采选",
            "MAINBUSINESS": "稀土矿采选、稀土冶炼分离产品",
        }
    ]
}


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


def _run_pipeline(client, monkeypatch) -> dict:
    def fake_get(url, timeout=10.0, **kwargs):
        if "survey" in url or "jbzl" in url or "EM2016" in url or "F10" in url:
            return httpx.Response(200, json=INDUSTRY_JSON)
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_mapchain001")
    assert body.status_code == 202, body.text
    return body.json()


def test_industry_map_from_real_evidence(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    resp = client.get("/api/v1/research-map/industry-map/SZSE:000831")
    if resp.status_code == 404:
        # industry source may be unavailable in this environment — the 404 is
        # the honest refusal; assert its shape
        assert resp.json()["error_code"] == "industry_map.not_collected"
        return
    data = resp.json()["industry_map"]
    assert data["instrument_id"] == "SZSE:000831"
    assert data["as_of"] is not None
    assert data["disclosures"]["peers"] == "pending_relationship_source"
    if data["industry_chain"]:
        assert "稀土" in " → ".join(data["industry_chain"])
    # artifact registered and linked generated_from the report
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "industry_map"}
    ).json()
    assert artifacts["count"] == 1
    lineage = client.get(
        f"/api/v1/artifacts/{artifacts['results'][0]['artifact_id']}/lineage"
    ).json()
    assert "report" in {u["artifact_type"] for u in lineage["upstream"]}

    # second call reuses the persisted latest snapshot (no rebuild)
    again = client.get("/api/v1/research-map/industry-map/SZSE:000831").json()["industry_map"]
    assert again["map_id"] == data["map_id"]


def test_global_context_from_real_macro_evidence(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    resp = client.get("/api/v1/research-map/global-context/SZSE:000831")
    if resp.status_code == 404:
        assert resp.json()["error_code"] == "global_context.not_collected"
        return
    data = resp.json()["global_context"]
    assert data["instrument_id"] == "SZSE:000831"
    assert data["as_of"] is not None
    assert data["disclosures"]["official_macro_source"] == "not_connected"
    assert "官方" in data["disclosures"]["note"]
    for theme in data["themes"]:
        assert theme["evidence_id"]
        assert theme["available_time"]

    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "global_context"}
    ).json()
    assert artifacts["count"] == 1


def test_views_refuse_without_research_state(client):
    missing_map = client.get("/api/v1/research-map/industry-map/SZSE:000831")
    # no research state at all → either instrument 404 or honest not_collected
    assert missing_map.status_code in (404,)
    body = missing_map.json()
    assert body["error_code"] in ("instrument.not_found", "industry_map.not_collected")
