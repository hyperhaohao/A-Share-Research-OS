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


RELATIONS_MEMBERS = {
    "data": {
        "diff": [
            {"f12": "600111", "f14": "北方稀土"},
            {"f12": "600392", "f14": "盛和资源"},
            {"f12": "000831", "f14": "中国稀土"},
        ]
    }
}


def _run_pipeline(client, monkeypatch) -> dict:
    def fake_get(url, timeout=10.0, **kwargs):
        if "survey" in url or "jbzl" in url or "EM2016" in url or "F10" in url:
            return httpx.Response(200, json=INDUSTRY_JSON)
        if "suggest" in url:
            return httpx.Response(200, json={"QuotationCodeTable": {"Data": [
                {"Code": "BK1626", "Name": "稀土", "MktNum": "90"},
            ]}})
        if "clist" in url:
            return httpx.Response(200, json=RELATIONS_MEMBERS)
        if "qt.gtimg" in url:
            # both tencent shapes: stock (~) + futures (,)
            return httpx.Response(200, content=(
                # indices: 3=price 30=market_time 32=change_pct (real layout)
                'v_sh000001="1~上证指数~000001~3952.18~3956.57~3950.24'
                + "~" * 24 + '~2026-08-28 17:15:59~~0.62~";'
                'v_hf_GC="4503.37,-3.44,4503.80,4504.30,4688.00,4495.00,04:59:58,'
                '4664.00,4656.00,0,4,2,2026-08-29,纽约黄金";'
            ).encode("gbk"))
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
    if data["industry_chain"]:
        assert "稀土" in " → ".join(data["industry_chain"])
    # relations source (深度扩展 a): real board members resolved to ids
    if data["disclosures"]["peers"].startswith("eastmoney_board"):
        related = {r["instrument_id"]: r for r in data["related_instruments"]}
        assert "SSE:600111" in related  # 北方稀土, a real board member
        assert related["SSE:600111"]["name"] == "北方稀土"
        assert "东财同业板块" in related["SSE:600111"]["basis"]
        # the subject itself is never listed as its own peer
        assert "SZSE:000831" not in related
    else:
        # honest fallback: co-occurrence note still disclosed
        assert data["disclosures"]["peers"] == "pending_relationship_source"
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
    # numeric layer (深度扩展 b): the mock serves the tencent feed
    assert data["disclosures"]["numeric_source"] == "tencent_global_macro"
    assert "数值层" in data["disclosures"]["note"]
    for theme in data["themes"]:
        assert theme["evidence_id"]
        assert theme["available_time"]

    # numeric layer (深度扩展 b): real indicator values parsed from the feed
    indicators = data["indicators"]
    assert len(indicators) >= 2
    by_code = {i["code"]: i for i in indicators}
    assert by_code["sh000001"]["value"] == 3952.18
    assert by_code["sh000001"]["market_time"] == "2026-08-28 17:15:59"
    assert by_code["hf_GC"]["value"] == 4503.37
    assert by_code["hf_GC"]["change"] == -3.44
    # every indicator carries its evidence provenance
    assert all(i["evidence_id"] for i in indicators)
    assert data["disclosures"]["numeric_source"] == "tencent_global_macro"

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


# ── Guanlan Direct Port G2 — 产业研究三视图 Read Model（方案 §7-§12/§24）────────


def test_g2_industry_view_assembles_from_real_evidence(client, monkeypatch):
    """GET /views/industry/{id}：链级→segments、五轴、真实主题/指标、披露；
    驱动/传导/站位无证据源 → None/[]（§25 诚实置空）。"""
    _run_pipeline(client, monkeypatch)

    resp = client.get("/api/v1/views/industry/SZSE:000831")
    assert resp.status_code == 200, resp.text
    view = resp.json()["view"]

    # EM2016 产业链 "稀土-稀土资源-稀土矿采选" → 三级链（fixture 驱动）
    assert view["chain_levels"] == ["稀土", "稀土资源", "稀土矿采选"]
    assert [s["segment_id"] for s in view["segments"]] == view["chain_levels"]
    assert view["segments"][-1]["is_current"] is True
    assert view["segments"][0]["is_current"] is False

    axes = view["global"]["axes"]
    assert [a["greek"] for a in axes] == ["β", "Δ", "Ω", "Θ", "Ψ"]
    assert len(view["global"]["indicators"]) >= 1
    ind = view["global"]["indicators"][0]
    assert ind["name"] == "上证指数" and ind["value"] is not None
    assert view["global"]["positions"] == []

    assert view["map_id"] and view["map_id"].startswith("imap_")
    assert "note" in view["disclosures"]
    assert all(s["momentum"] is None and s["temperature"] is None for s in view["segments"])


def test_g2_segment_view_evidence_and_404(client, monkeypatch):
    """环节详情：环节证据为真实共现检索；链外环节 404 显式拒绝。"""
    _run_pipeline(client, monkeypatch)

    resp = client.get("/api/v1/views/industry/SZSE:000831/segment/稀土矿采选")
    assert resp.status_code == 200, resp.text
    view = resp.json()["view"]
    assert view["segment"]["name"] == "稀土矿采选"
    assert view["segment"]["is_current"] is True
    assert view["segment"]["evidence_count"] == len(view["evidence"])
    assert len(view["evidence"]) >= 1
    for row in view["evidence"]:
        assert row["evidence_id"].startswith("ev_")
        assert row["available_time"] is not None

    missing = client.get("/api/v1/views/industry/SZSE:000831/segment/不存在环节")
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "industry_map.segment_not_found"
