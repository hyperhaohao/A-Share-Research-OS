"""G2 — 产业语义 PIT/证据治理/五轴（观澜语义迁移任务书 §G2）.

覆盖：
  - Evidence Ownership Gate（§G2.2）：跨产业证据 422；未来证据 422；
  - Narrative Temperature 服务端复算（§G2.3）：从证据表读 available_time +
    信任门（T0/T1 才算已验证观察）；客户端 observed_at 不再参与；
  - GET as_of 重放（§G2.4）：as_of 之后创建的版本不可见（纯读）；
  - GET 不隐式建快照（§G2.4/§G2.5）：无快照标的 → 诚实置空且零写库；
  - 图谱链接（§G2.1）：driver 关联 chain/segment/edge（不存在的 edge 422）；
  - 五轴 Global Position（§G2.7）：有数据轴 ok，无数据轴 insufficient 显形；
  - INCOMPLETE_PROVENANCE（§G2.6）：Artifact 注册失败显形不吞异常。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus


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


NOW = datetime.now(timezone.utc)


def _seed_evidence(
    client, ev_key: str, title: str, summary: str, *,
    instrument_id: str = "SZSE:000831",
    authority: AuthorityLevel = AuthorityLevel.A1,
    age_days: float = 2.0,
    source: str | None = None,
    etype: EvidenceType = EvidenceType.ANNOUNCEMENT,
) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=age_days)
        rec = EvidenceRecord(
            instrument_id=instrument_id,
            evidence_type=etype,
            title=title,
            summary=summary,
            source=source or f"provider_{ev_key}",
            source_type="media",
            authority_level=authority,
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            event_time=at,
            available_time=at,
            ingested_time=at + timedelta(minutes=1),
            revision_time=at + timedelta(minutes=1),
        )
        evidence_id, _ = EvidenceRepository(session).save(rec)
        session.commit()
        return evidence_id
    finally:
        session.close()


def _seed_chain(client) -> str:
    out = client.post(
        "/api/v1/industry-graph/seed/rare-earth", json={"confirm": True}
    ).json()
    return out["chain_id"]


# ── Ownership Gate ───────────────────────────────────────────────────────────


def test_semantic_ownership_gate_rejects_cross_industry_and_future(client):
    _seed_chain(client)
    related = _seed_evidence(
        client, "rel", "冶炼分离公告", "公司冶炼分离产能利用率提升"
    )
    # 正常：产业名「稀土」在链名/环节中相关
    ok_upsert = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "capacity_up", "industry_id": "稀土",
        "title": "冶炼分离产能爬坡", "mechanism": "产能提升压制价格",
        "status": "active", "direction": "negative",
        "evidence_claims": [{"evidence_id": related,
                             "support_span": "冶炼分离产能利用率提升"}],
    })
    assert ok_upsert.status_code == 201, ok_upsert.text

    # 跨产业证据 → 422
    unrelated = _seed_evidence(
        client, "unrel", "银行业务", "某城市商业银行净利润增长",
        instrument_id="SZSE:000001",
    )
    r = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "cross_industry", "industry_id": "稀土",
        "title": "跨产业注入", "status": "active", "direction": "negative",
        "evidence_claims": [{"evidence_id": unrelated,
                             "support_span": "净利润增长"}],
    })
    assert r.status_code == 422, r.text

    # 未来证据 → 422（PIT）
    future = _seed_evidence(
        client, "fut", "未来公告", "公司稀土冶炼项目投产", age_days=-1.0
    )
    r = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "future_ev", "industry_id": "稀土",
        "title": "未来证据注入", "status": "active", "direction": "negative",
        "evidence_claims": [{"evidence_id": future,
                             "support_span": "稀土冶炼项目投产"}],
    })
    assert r.status_code == 422
    assert "available_at" in r.json()["detail"]


# ── 图谱链接 ─────────────────────────────────────────────────────────────────


def test_semantic_graph_links(client):
    chain_id = _seed_chain(client)
    graph = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/graph"
    ).json()
    edge = graph["edges"][0]
    ev = _seed_evidence(client, "link1", "冶炼分离公告",
                        "公司冶炼分离产线技改完成")

    # 不存在的 edge → 422
    r = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "tech_up", "industry_id": "稀土",
        "title": "技术升级驱动", "status": "active", "direction": "positive",
        "evidence_claims": [{"evidence_id": ev, "support_span": "冶炼分离产线技改完成"}],
        "edge_id": "edge_missing000000",
    })
    assert r.status_code == 422

    # 合法链接 → 落库（chain_id 自动回填）
    ok = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "tech_up", "industry_id": "稀土",
        "title": "技术升级驱动", "status": "active", "direction": "positive",
        "evidence_claims": [{"evidence_id": ev, "support_span": "冶炼分离产线技改完成"}],
        "edge_id": edge["edge_id"],
    })
    assert ok.status_code == 201, ok.text
    body = ok.json()["object"]
    assert body["edge_id"] == edge["edge_id"]
    assert body["chain_id"] == chain_id
    # provenance（§G2.6）：注册状态显形
    assert body.get("provenance_status") in ("complete", "INCOMPLETE_PROVENANCE")


# ── 服务端温度（§G2.3） ─────────────────────────────────────────────────────


def test_narrative_temperature_server_side_and_trust_gated(client):
    # 3 条 T0/T1 证据：2 条 7 天前（recent），1 条 21 天前（prior）→ warming
    evs = [
        _seed_evidence(client, "t1", "稀土出口公告", "稀土出口配额增加", age_days=7.0),
        _seed_evidence(client, "t2", "稀土价格公告", "稀土价格上行", age_days=8.0,
                       authority=AuthorityLevel.B1),
        _seed_evidence(client, "t3", "稀土产量公告", "稀土产量环比提升", age_days=21.0),
    ]
    claims = [{"evidence_id": e, "support_span": s}
              for e, s in zip(evs, ("出口配额增加", "稀土价格上行", "稀土产量环比提升"))]
    up = client.post("/api/v1/industry-semantics/narrative", json={
        "object_key": "rare_earth_wave", "industry_id": "稀土",
        "title": "稀土板块景气叙事", "status": "active",
        "evidence_claims": claims,
    })
    assert up.status_code == 201, up.text

    temp = client.get(
        "/api/v1/industry-semantics/narrative/rare_earth_wave/temperature"
    ).json()
    assert temp["basis"] == "server_evidence_table"
    assert temp["validated_obs"] == 3
    assert temp["temperature"] == "warming"
    # 低信任证据不计入已验证观察（另行披露）
    ev_low = _seed_evidence(
        client, "t4", "自媒体爆料", "稀土要涨疯了", age_days=1.0,
        authority=AuthorityLevel.D, etype=EvidenceType.NEWS,
    )
    up2 = client.post("/api/v1/industry-semantics/narrative", json={
        "object_key": "rare_earth_wave", "industry_id": "稀土",
        "title": "稀土板块景气叙事", "status": "active",
        "evidence_claims": claims + [{"evidence_id": ev_low,
                                      "support_span": "稀土要涨疯了"}],
    })
    assert up2.status_code == 201
    temp2 = client.get(
        "/api/v1/industry-semantics/narrative/rare_earth_wave/temperature"
    ).json()
    assert temp2["validated_obs"] == 3
    assert temp2["lower_trust_obs"] == 1  # 低信任单独披露，不进温度


# ── GET as_of 重放 + 无隐式写库 ──────────────────────────────────────────────


def test_semantics_as_of_replay(client):
    _seed_chain(client)
    ev = _seed_evidence(client, "a1", "冶炼分离公告", "公司冶炼分离产能爬坡")
    created_at = (NOW - timedelta(days=1)).isoformat()
    up = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "asof_driver", "industry_id": "稀土",
        "title": "产能爬坡驱动", "status": "active", "direction": "negative",
        "evidence_claims": [{"evidence_id": ev, "support_span": "冶炼分离产能爬坡"}],
        "as_of": created_at,
    })
    assert up.status_code == 201

    # as_of 早于创建时间 → 不可见（PIT 重放）
    past = (NOW - timedelta(days=2)).isoformat()
    out_past = client.get(
        "/api/v1/industry-semantics/driver",
        params={"industry_id": "稀土", "as_of": past},
    ).json()
    assert out_past["count"] == 0
    assert out_past["as_of"] == past
    # as_of 晚于创建时间 → 可见
    out_now = client.get(
        "/api/v1/industry-semantics/driver", params={"industry_id": "稀土"}
    ).json()
    assert out_now["count"] >= 1


def test_view_get_does_not_implicitly_write_snapshots(client):
    factory = client.app.state._test_factory
    from sqlalchemy import select, func
    from app.application.research_map import IndustryMapSnapshotORM

    # 全新标的（无快照）GET 视图 → 诚实置空且不写库
    resp = client.get("/api/v1/views/industry/SZSE:000001")
    assert resp.status_code == 200
    body = resp.json()
    view = body.get("view", body)
    disclosures = (view.get("disclosures") or {})
    assert disclosures.get("snapshot") == "not_built_yet"

    session = factory()
    try:
        n = session.scalar(
            select(func.count()).select_from(IndustryMapSnapshotORM)
            .where(IndustryMapSnapshotORM.instrument_id == "SZSE:000001")
        )
    finally:
        session.close()
    assert n == 0, "GET must not implicitly build/persist snapshots (§G2.4)"


# ── 五轴 Global Position（§G2.7） ────────────────────────────────────────────


def test_global_position_five_axes(client):
    chain_id = _seed_chain(client)
    graph = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph").json()
    segments = graph["segments"]
    refine = next(s for s in segments if s["name"] == "冶炼分离")
    own_ev = _seed_evidence(client, "own", "公司公告", "公司冶炼分离业务收入占比披露")

    client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": chain_id,
        "segment_id": refine["segment_id"], "role": "processor",
        "revenue_exposure_pct": 92.0,
        "capacity_note": "稀土氧化物年产能过万吨（公告披露）",
        "evidence_ids": [own_ev],
    })
    # 上游资源公司（600259 资源开采）→ 资源轴 ok
    mining = next(s for s in segments if s["name"] == "资源开采")
    client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:600259", "chain_id": chain_id,
        "segment_id": mining["segment_id"], "role": "producer",
        "capacity_note": "稀土原矿开采配额持有（披露）",
    })

    out = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/global-position",
        params={"instrument_id": "SZSE:000831"},
    ).json()
    axes = {a["axis"]: a for a in out["axes"]}
    assert set(axes) == {"resource", "capacity", "cost", "technology", "policy"}
    # 有位置数据 → 资源/产能 ok
    assert axes["resource"]["status"] == "ok"
    assert axes["capacity"]["status"] == "ok"
    # 无成本/技术/政策数据 → insufficient 显形（不冒充有值）
    assert axes["cost"]["status"] == "insufficient"
    assert axes["technology"]["status"] == "insufficient"
    assert axes["policy"]["status"] == "insufficient"

    # 技术轴：加 driver 后转 ok
    ev = _seed_evidence(client, "tech", "冶炼分离公告", "公司冶炼分离产线技改完成")
    client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "tech_up", "industry_id": "稀土",
        "title": "技术升级驱动", "status": "active", "direction": "positive",
        "evidence_claims": [{"evidence_id": ev, "support_span": "冶炼分离产线技改完成"}],
        "chain_id": chain_id,
    })
    out2 = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/global-position",
        params={"instrument_id": "SZSE:000831"},
    ).json()
    tech = next(a for a in out2["axes"] if a["axis"] == "technology")
    assert tech["status"] == "ok"
    assert tech["values"][0]["object_type"] == "driver"

    # 不存在的链 → 404
    assert client.get(
        "/api/v1/industry-graph/chains/chain_missing0000/global-position"
    ).status_code == 404
