"""G1 — 真实 Industry Graph（观澜语义迁移任务书 §G1）.

覆盖：
  - 稀土 Golden 链种子：≥5 环节、≥5 传导边（≥4 跨环节传导）；
  - 9 类 relation_type 校验；自环拒绝；跨链环节拒绝；
  - Evidence Ownership Gate：跨产业证据拒绝 + 未来证据拒绝（PIT）；
  - 置信派生：独立来源组 → strength/confidence/status；
    删关键证据自动降级（active→degraded→insufficient）；
  - 公司多链位置 + 位置证据归属（必须本公司披露）+ 000831/600259 隔离；
  - Peer 来自同环节共位（明确关系），非关键词共现；
  - as_of 可重放（未来证据不进入历史状态）。
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
    etype: EvidenceType = EvidenceType.ANNOUNCEMENT,
    age_days: float = 2.0,
    source: str | None = None,
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


def _seed_chain(client) -> dict:
    out = client.post(
        "/api/v1/industry-graph/seed/rare-earth", json={"confirm": True}
    )
    assert out.status_code == 200, out.text
    data = out.json()
    chain_id = data["chain_id"]
    graph = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph").json()
    return {**data, "graph": graph}


# ── 结构：≥5 环节、≥5 传导边 ─────────────────────────────────────────────────


def test_seed_rare_earth_chain_structure(client):
    st = _seed_chain(client)
    assert st["seeded"] is True
    graph = st["graph"]
    assert len(graph["segments"]) >= 5
    assert len(graph["edges"]) >= 5
    # 跨环节传导边 ≥4（其余为约束边）
    cross = [e for e in graph["edges"]
             if e["source_segment_id"] != e["target_segment_id"]]
    assert len(cross) >= 4
    # relation_type 覆盖 material_flow + demand/price/supply
    relations = {e["relation_type"] for e in graph["edges"]}
    assert {"material_flow", "demand_transmission", "supply_constraint"} <= relations
    # 无证据 → 诚实 insufficient（不可发布）
    assert all(e["status"] == "insufficient" for e in graph["edges"])
    assert all(e["confidence_level"] == "insufficient" for e in graph["edges"])
    # 幂等：重复 seed 返回已存在
    again = client.post(
        "/api/v1/industry-graph/seed/rare-earth", json={"confirm": True}
    ).json()
    assert again["seeded"] is False


def test_edge_validation_rules(client):
    st = _seed_chain(client)
    chain_id = st["chain_id"]
    segments = st["graph"]["segments"]
    # 非法 relation_type
    r = client.post("/api/v1/industry-graph/edges", json={
        "chain_id": chain_id,
        "source_segment_id": segments[0]["segment_id"],
        "target_segment_id": segments[1]["segment_id"],
        "relation_type": "vibes",
    })
    assert r.status_code == 422
    # 自环拒绝
    r = client.post("/api/v1/industry-graph/edges", json={
        "chain_id": chain_id,
        "source_segment_id": segments[0]["segment_id"],
        "target_segment_id": segments[0]["segment_id"],
        "relation_type": "material_flow",
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "industry_graph.self_edge"
    # 跨链环节拒绝
    other = client.post("/api/v1/industry-graph/chains",
                        json={"name": "光储产业链"}).json()["chain"]
    r = client.post("/api/v1/industry-graph/edges", json={
        "chain_id": chain_id,
        "source_segment_id": segments[0]["segment_id"],
        "target_segment_id": "seg_belongstoother",
        "relation_type": "material_flow",
    })
    assert r.status_code == 422


# ── Evidence Ownership Gate ─────────────────────────────────────────────────


def test_evidence_ownership_gate(client):
    st = _seed_chain(client)
    chain_id = st["chain_id"]
    edges = st["graph"]["edges"]
    target = next(e for e in edges if e["relation_type"] == "material_flow")

    # 相关证据：标的在链上（后挂 position）或文本提及环节名
    related = _seed_evidence(
        client, "rel1", "冶炼分离公告",
        "公司冶炼分离产能扩产，稀土氧化物产量提升",
    )
    attached = client.post(
        f"/api/v1/industry-graph/edges/{target['edge_id']}/evidence",
        json={"evidence_id": related},
    )
    assert attached.status_code == 201, attached.text

    # 跨产业证据：无链上位置、无链/环节提及 → 拒绝
    unrelated = _seed_evidence(
        client, "unrel", "银行业务公告",
        "某城市商业银行净利润增长，净息差收窄",
        instrument_id="SZSE:000001",
    )
    r = client.post(
        f"/api/v1/industry-graph/edges/{target['edge_id']}/evidence",
        json={"evidence_id": unrelated},
    )
    assert r.status_code == 422
    assert r.json()["error_code"] == "industry_graph.evidence_ownership_rejected"


def test_future_evidence_rejected_pit(client):
    st = _seed_chain(client)
    edge = st["graph"]["edges"][0]
    # 未来证据（available_time 在 as_of 之后）→ 422
    future = _seed_evidence(
        client, "fut", "未来公告", "公司稀土冶炼分离项目投产", age_days=-1.0
    )
    r = client.post(
        f"/api/v1/industry-graph/edges/{edge['edge_id']}/evidence",
        json={"evidence_id": future, "as_of": NOW.isoformat()},
    )
    assert r.status_code == 422
    assert r.json()["error_code"] == "industry_graph.evidence_not_yet_available"


# ── 置信派生与降级 ───────────────────────────────────────────────────────────


def test_confidence_derivation_and_downgrade(client):
    st = _seed_chain(client)
    edge = st["graph"]["edges"][0]
    edge_id = edge["edge_id"]

    # 两条不同来源（独立组=2）支撑 → high/active
    ev1 = _seed_evidence(client, "s1", "冶炼分离公告",
                         "公司冶炼分离产能利用率提升", source="providerA")
    ev2 = _seed_evidence(client, "s2", "行业报道冶炼分离",
                         "行业冶炼分离环节开工率上行", source="providerB",
                         authority=AuthorityLevel.B2, etype=EvidenceType.NEWS)
    for ev in (ev1, ev2):
        r = client.post(
            f"/api/v1/industry-graph/edges/{edge_id}/evidence",
            json={"evidence_id": ev},
        )
        assert r.status_code == 201, r.text
    edge_now = client.get(f"/api/v1/industry-graph/edges/{edge_id}").json()["edge"]
    assert edge_now["confidence_level"] == "high"
    assert edge_now["status"] == "active"
    assert edge_now["strength"] >= 0.7

    # 删除一条关键证据 → 降级（active→degraded）
    downgraded = client.delete(
        f"/api/v1/industry-graph/edges/{edge_id}/evidence/{ev2}"
    ).json()["edge"]
    assert downgraded["status"] == "degraded"
    assert downgraded["confidence_level"] != "high"

    # 全部删除 → insufficient（不可发布）
    empty = client.delete(
        f"/api/v1/industry-graph/edges/{edge_id}/evidence/{ev1}"
    ).json()["edge"]
    assert empty["status"] == "insufficient"


# ── 公司位置：多链 + 证据归属 + 隔离 ────────────────────────────────────────


def test_company_positions_multi_chain_and_ownership(client):
    st = _seed_chain(client)
    chain_id = st["chain_id"]
    segments = st["graph"]["segments"]
    refine = next(s for s in segments if s["name"] == "冶炼分离")

    own_ev = _seed_evidence(client, "own", "公司公告",
                            "公司冶炼分离业务收入占比披露")
    other_ev = _seed_evidence(client, "other", "他司公告",
                              "另一公司冶炼分离产能",
                              instrument_id="SZSE:600259")

    pos = client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": chain_id,
        "segment_id": refine["segment_id"], "role": "processor",
        "revenue_exposure_pct": 92.0,
        "capacity_note": "稀土氧化物年产能过万吨（公告披露）",
        "evidence_ids": [own_ev],
    })
    assert pos.status_code == 201, pos.text

    # 位置证据归属：他司证据不能支撑本公司位置
    r = client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": chain_id,
        "segment_id": refine["segment_id"], "role": "processor",
        "evidence_ids": [other_ev],
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "industry_graph.position_evidence_ownership_rejected"

    # 第二条链：一家公司可位于多个产业链
    other_chain = client.post("/api/v1/industry-graph/chains",
                              json={"name": "永磁材料产业链"}).json()["chain"]
    magnet = client.post("/api/v1/industry-graph/segments", json={
        "chain_id": other_chain["chain_id"], "name": "磁材加工", "stage_order": 0,
    }).json()["segment"]
    pos2 = client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:000831", "chain_id": other_chain["chain_id"],
        "segment_id": magnet["segment_id"], "role": "consumer",
    })
    assert pos2.status_code == 201
    positions = client.get(
        "/api/v1/industry-graph/instruments/SZSE:000831/positions"
    ).json()["results"]
    chains = {p["chain_id"] for p in positions}
    assert chains == {chain_id, other_chain["chain_id"]}

    # 000831 与 600259 位置隔离：不同链上位置互不串
    pos_600259 = client.get(
        "/api/v1/industry-graph/instruments/SZSE:600259/positions"
    ).json()
    assert pos_600259["count"] == 0  # 未建位置 → 不冒充链上公司


def test_peers_from_segment_colocation_not_keywords(client):
    st = _seed_chain(client)
    chain_id = st["chain_id"]
    segments = st["graph"]["segments"]
    refine = next(s for s in segments if s["name"] == "冶炼分离")
    mining = next(s for s in segments if s["name"] == "资源开采")

    for iid, seg in (("SZSE:000831", refine), ("SZSE:600259", mining)):
        r = client.post("/api/v1/industry-graph/positions", json={
            "instrument_id": iid, "chain_id": chain_id,
            "segment_id": seg["segment_id"], "role": "producer",
        })
        assert r.status_code == 201

    # 同环节共位 → peer；不同环节 → 不进 peer（明确关系语义）
    peers = client.get(
        "/api/v1/industry-graph/instruments/SZSE:000831/peers"
    ).json()
    assert peers["count"] == 0  # 000831 在冶炼分离、600259 在资源开采 → 非 peer

    # 同环节：把 600259 也放进冶炼分离 → 成为 peer
    client.post("/api/v1/industry-graph/positions", json={
        "instrument_id": "SZSE:600259", "chain_id": chain_id,
        "segment_id": refine["segment_id"], "role": "processor",
    })
    peers = client.get(
        "/api/v1/industry-graph/instruments/SZSE:000831/peers"
    ).json()["results"]
    assert any(p["instrument_id"] == "SZSE:600259" for p in peers)
    assert all("冶炼分离" in p["shared_segments"] for p in peers)


# ── as_of 可重放（PIT） ─────────────────────────────────────────────────────


def test_graph_as_of_replay(client):
    st = _seed_chain(client)
    chain_id = st["chain_id"]
    edge = st["graph"]["edges"][0]

    ev = _seed_evidence(client, "pit1", "冶炼分离公告",
                        "公司冶炼分离产线技改完成", age_days=1.0)
    client.post(
        f"/api/v1/industry-graph/edges/{edge['edge_id']}/evidence",
        json={"evidence_id": ev},
    )

    # as_of = 3 天前（边与证据均未存在/未可用）→ 边不进入历史状态（PIT）
    past = (NOW - timedelta(days=3)).isoformat()
    g_past = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/graph",
        params={"as_of": past},
    ).json()
    assert all(e["edge_id"] != edge["edge_id"] for e in g_past["edges"])

    # as_of = 现在 → 证据可见
    g_now = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph").json()
    e_now = next(e for e in g_now["edges"] if e["edge_id"] == edge["edge_id"])
    assert len(e_now["evidence"]) == 1
    assert e_now["evidence"][0]["evidence_id"] == ev

    # 未来结构不进入历史：as_of 之前创建的图不可见新环节
    new_seg = client.post("/api/v1/industry-graph/segments", json={
        "chain_id": chain_id, "name": "回收再生", "stage_order": 9,
    }).json()["segment"]
    g_hist = client.get(
        f"/api/v1/industry-graph/chains/{chain_id}/graph",
        params={"as_of": past},
    ).json()
    assert all(s["segment_id"] != new_seg["segment_id"] for s in g_hist["segments"])
    g_now2 = client.get(f"/api/v1/industry-graph/chains/{chain_id}/graph").json()
    assert any(s["segment_id"] == new_seg["segment_id"] for s in g_now2["segments"])
