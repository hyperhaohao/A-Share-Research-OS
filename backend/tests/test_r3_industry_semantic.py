"""R3 — Industry Semantic Research Engine（方案 §9）.

验收：
  - Driver/Transmission/Narrative/Position 创建必须挂证据，支撑句经引用反查；
  - 无引用/反查失败 → 422 citation_failed（不进正式研究状态）；
  - Append-only 版本化：更新 = 新版本行，历史可回放；
  - Narrative 温度可复算（不足 → insufficient）。
"""

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base, EvidenceORM


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


ANNOUNCE_TEXT = (
    "中国稀土(000831.SZ)公告称，持股5%以上股东广晟控股集团计划自公告披露之日起"
    "15个交易日后的三个月内，以集中竞价方式减持公司股份不超过1061.22万股。"
)


def _insert_evidence(client, *, evidence_id: str, summary: str, authority: str = "B2") -> str:
    """经 save 插入证据（内容寻址 id），返回真实 evidence_id。"""
    from datetime import datetime, timezone

    from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus
    from app.storage.repository import EvidenceRepository

    factory = client.app.state._test_factory
    session = factory()
    try:
        record = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.NEWS,
            title="中国稀土公告",
            summary=summary,
            source="eastmoney_news" + evidence_id[-4:],
            source_type="media",
            authority_level=AuthorityLevel(authority),
            fact_status=FactStatus.MEDIA_REPORT,
            event_time=datetime(2026, 8, 20, tzinfo=timezone.utc),
            available_time=datetime(2026, 8, 20, tzinfo=timezone.utc),
            ingested_time=datetime(2026, 8, 30, tzinfo=timezone.utc),
            revision_time=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        saved_id, _ = EvidenceRepository(session).save(record)
        session.commit()
        return saved_id
    finally:
        session.close()


def _upsert(client, payload):
    return client.post("/api/v1/industry-semantics/driver", json=payload)


def test_driver_create_requires_real_citation(client):
    evidence_id = _insert_evidence(
        client, evidence_id="ev_r3_news0001", summary=ANNOUNCE_TEXT
    )
    ok = _upsert(client, {
        "object_key": "reduce_supply",
        "industry_id": "稀土",
        "instrument_id": "SZSE:000831",
        "title": "广晟控股减持计划带来股份供给压力",
        "mechanism": "股东减持形成二级市场股份供给，短期压制股价表现",
        "status": "active",
        "direction": "negative",
        "evidence_claims": [
            {"evidence_id": evidence_id,
             "support_span": "以集中竞价方式减持公司股份不超过1061.22万股",
             "observed_at": "2026-08-20T10:31:00Z"},
        ],
    })
    assert ok.status_code == 201, ok.text
    body = ok.json()["object"]
    assert body["version"] == 1
    assert body["direction"] == "negative"
    assert body["evidence_refs"][0]["evidence_id"] == evidence_id

    # 反查失败：support_span 不在证据原文 → 422 citation_failed
    bad = _upsert(client, {
        "object_key": "reduce_supply_v2",
        "industry_id": "稀土",
        "title": "无中生有的驱动",
        "status": "active",
        "direction": "positive",
        "evidence_claims": [
            {"evidence_id": evidence_id, "support_span": "这句话不在原文中"},
        ],
    })
    assert bad.status_code == 422
    assert bad.json()["error_code"] == "industry_semantic.citation_failed"

    # 无引用 → 422
    no_ref = _upsert(client, {
        "object_key": "reduce_supply_v3",
        "industry_id": "稀土",
        "title": "无引用驱动",
        "status": "active",
        "direction": "positive",
        "evidence_claims": [],
    })
    assert no_ref.status_code == 422


def test_driver_append_only_versions_and_history(client):
    evidence_id = _insert_evidence(
        client, evidence_id="ev_r3_news0002", summary=ANNOUNCE_TEXT
    )
    base = {
        "object_key": "policy_driver",
        "industry_id": "稀土",
        "title": "行业政策驱动",
        "direction": "positive",
    }
    v1 = _upsert(client, {**base, "status": "emerging",
                          "evidence_claims": [{"evidence_id": evidence_id,
                                               "support_span": "中国稀土(000831.SZ)公告称"}]})
    assert v1.json()["object"]["version"] == 1
    v2 = _upsert(client, {**base, "status": "active",
                          "evidence_claims": [{"evidence_id": evidence_id,
                                               "support_span": "中国稀土(000831.SZ)公告称"}]})
    assert v2.json()["object"]["version"] == 2

    history = client.get("/api/v1/industry-semantics/driver/policy_driver").json()
    assert [v["version"] for v in history["versions"]] == [1, 2]
    assert history["latest"]["status"] == "active"

    listing = client.get(
        "/api/v1/industry-semantics/driver", params={"industry_id": "稀土"}
    ).json()
    assert listing["count"] == 1  # 每个 key 只出最新版本


def test_transmission_and_invalid_direction(client):
    evidence_id = _insert_evidence(
        client, evidence_id="ev_r3_news0003", summary=ANNOUNCE_TEXT
    )
    ok = client.post("/api/v1/industry-semantics/transmission", json={
        "object_key": "reduce_to_price",
        "industry_id": "稀土",
        "title": "股东减持 → 股份供给 → 股价承压",
        "mechanism": "减持形成流通盘供给增量",
        "status": "active",
        "direction": "negative",
        "evidence_claims": [{"evidence_id": evidence_id,
                             "support_span": "以集中竞价方式减持公司股份不超过1061.22万股"}],
    })
    assert ok.status_code == 201, ok.text

    bad_direction = client.post("/api/v1/industry-semantics/driver", json={
        "object_key": "dir_bad", "industry_id": "稀土", "title": "x",
        "status": "active", "direction": "super",
        "evidence_claims": [{"evidence_id": evidence_id, "support_span": "中国稀土(000831.SZ)公告称"}],
    })
    assert bad_direction.status_code == 422


def test_narrative_temperature_insufficient_then_computable(client):
    evidence_id = _insert_evidence(
        client, evidence_id="ev_r3_news0004", summary=ANNOUNCE_TEXT
    )
    span_claim = {"evidence_id": evidence_id,
                  "support_span": "以集中竞价方式减持公司股份不超过1061.22万股",
                  "observed_at": "2026-08-20T10:31:00Z"}
    base = {
        "object_key": "reduce_wave",
        "industry_id": "稀土",
        "title": "稀土板块股东减持潮",
        "instrument_id": "SZSE:000831",
    }
    client.post("/api/v1/industry-semantics/narrative", json={
        **base, "status": "emerging", "evidence_claims": [dict(span_claim)],
    })
    temp = client.get("/api/v1/industry-semantics/narrative/reduce_wave/temperature").json()
    assert temp["temperature"] == "insufficient"  # 证据点不足 → 不展示温度

    # 新版本携带 3 个观察点（近窗 2 + 前窗 1）→ 可复算 warming
    client.post("/api/v1/industry-semantics/narrative", json={
        **base, "status": "active",
        "evidence_claims": [
            {**span_claim, "observed_at": "2026-08-20T10:31:00Z"},
            {**span_claim, "observed_at": "2026-08-29T10:31:00Z"},
            {**span_claim, "observed_at": "2026-08-10T10:31:00Z"},
        ],
    })
    temp2 = client.get("/api/v1/industry-semantics/narrative/reduce_wave/temperature").json()
    assert temp2["temperature"] == "warming"
    assert temp2["recent_obs"] == 2 and temp2["prior_obs"] == 1
