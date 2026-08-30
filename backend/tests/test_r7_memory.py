"""R7 — Research Memory（方案 §13）.

验收：
  - Memory 创建一律 candidate（不自动 active）；
  - 晋升门：candidate→active→retired，禁跳级；
  - 检索按 type/scope/q；
  - 已批准经验 → candidate Memory（源引用保留）；未批准 → 422；
  - Memory≠Evidence：条目结构无 authority/fact_status 字段。
"""

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


def _make_approved_card(client, monkeypatch) -> dict:
    from tests.test_phase_c_experience import _run_pipeline

    with pytest.MonkeyPatch.context() as mp:
        body = _run_pipeline(client, mp)
    created = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]}
    )
    card = created.json()["card"]
    client.post(f"/api/v1/experience-cards/{card['card_id']}/validate")
    client.post(
        f"/api/v1/experience-cards/{card['card_id']}/approve", json={}
    )
    return client.get(f"/api/v1/experience-cards/{card['card_id']}").json()["card"]


def test_memory_candidate_promote_flow(client):
    created = client.post("/api/v1/memories", json={
        "memory_type": "event_playbook",
        "title": "减持事件研究方法",
        "content": "先查 T0 公告，再查集团/国资委表态，最后查媒体；时间线按披露日排序。",
        "instrument_id": "SZSE:000831",
        "event_type": "shareholder_reduction",
        "tags": ["减持", "公告"],
    })
    assert created.status_code == 201, created.text
    mem = created.json()["memory"]
    assert mem["status"] == "candidate"
    # 结构边界：Memory 条目无 authority/fact_status（那些是 Evidence 字段）
    assert "authority_level" not in mem
    assert "fact_status" not in mem

    promoted = client.post(f"/api/v1/memories/{mem['memory_id']}/promote")
    assert promoted.status_code == 200
    assert promoted.json()["memory"]["status"] == "active"

    retired = client.post(f"/api/v1/memories/{mem['memory_id']}/promote")
    assert retired.json()["memory"]["status"] == "retired"

    unknown = client.post("/api/v1/memories", json={
        "memory_type": "not_a_type", "title": "x", "content": "y",
    })
    assert unknown.status_code == 422


def test_memory_search_by_scope_and_q(client):
    client.post("/api/v1/memories", json={
        "memory_type": "event_playbook",
        "title": "减持事件研究方法",
        "content": "公告 → 集团 → 国资委 → 产权交易所。",
        "instrument_id": "SZSE:000831",
        "event_type": "shareholder_reduction",
    })
    client.post("/api/v1/memories", json={
        "memory_type": "research_method",
        "title": "产业驱动核查清单",
        "content": "先核配额，再核价格，再核下游需求。",
        "industry_id": "稀土",
    })
    hits = client.get(
        "/api/v1/memories",
        params={"instrument_id": "SZSE:000831", "q": "公告", "status": "candidate"},
    ).json()
    assert hits["count"] == 1
    assert hits["results"][0]["memory_type"] == "event_playbook"

    by_industry = client.get(
        "/api/v1/memories", params={"industry_id": "稀土", "memory_type": "research_method", "status": "candidate"}
    ).json()
    assert by_industry["count"] == 1


def test_experience_to_memory_candidate_flow(client, monkeypatch):
    from tests.test_phase_c_experience import _run_pipeline

    with pytest.MonkeyPatch.context() as mp:
        body = _run_pipeline(client, mp)
    created = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]}
    )
    card_id = created.json()["card"]["card_id"]

    # 未批准 → 422（不自动吸收）
    refused = client.post(f"/api/v1/memories/from-experience/{card_id}")
    assert refused.status_code == 422

    client.post(f"/api/v1/experience-cards/{card_id}/validate")
    client.post(f"/api/v1/experience-cards/{card_id}/approve", json={})
    ok = client.post(f"/api/v1/memories/from-experience/{card_id}")
    assert ok.status_code == 201, ok.text
    mem = ok.json()["memory"]
    assert mem["status"] == "candidate"
    assert card_id in mem["source_experiences"]
    assert mem["source_artifacts"], "experience artifact provenance kept"

    promote = client.post(f"/api/v1/memories/{mem['memory_id']}/promote")
    assert promote.json()["memory"]["status"] == "active"
