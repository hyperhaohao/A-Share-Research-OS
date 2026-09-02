"""R6 — Experience 非量化改造（方案 §12）.

验收：
  - 非量化验证方法（反例搜索/历史证据/跨公司/人工复核）各有确定性真实行为；
  - 反例搜索命中即引用落档；搜不到 → 措辞如实（未见≠不存在）；
  - Playbook 检索只出已批准卡片，且不携带 authority/fact_status
    （Memory/Playbook ≠ Evidence 边界由结构锁死）；
  - LLM 结构化精炼：无 KEY → 422 显式拒绝（有 KEY 路径由 LLM 集成测试覆盖）。
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


def _make_card(client, monkeypatch) -> dict:
    import pytest as _pytest

    from tests.test_phase_c_experience import _run_pipeline

    body = None
    with _pytest.MonkeyPatch.context() as mp:
        body = _run_pipeline(client, mp)
    created = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]}
    )
    assert created.status_code == 201, created.text
    return created.json()["card"]


def test_non_quant_validation_methods(client, monkeypatch):
    card = _make_card(client, monkeypatch)

    # 反例搜索：真实语料检索，命中与否都落档（措辞如实）
    resp = client.post(
        f"/api/v1/experience-cards/{card['card_id']}/validate-non-quant",
        json={"method": "counterexample_search"},
    )
    assert resp.status_code == 201, resp.text
    v = resp.json()["validation"]
    assert v["method"] == "counterexample_search"
    assert "未见反例" in v["summary"] or "命中" in v["summary"]

    # 历史证据验证：PIT 前向核对（fixture 快照/报价齐备时可算）
    resp2 = client.post(
        f"/api/v1/experience-cards/{card['card_id']}/validate-non-quant",
        json={"method": "historical_evidence_validation"},
    )
    assert resp2.status_code in (201, 422)  # 422 = 无历史快照对（显式拒绝）
    if resp2.status_code == 201:
        v2 = resp2.json()["validation"]
        assert v2["method"] == "historical_evidence_validation"
        assert v2["cases_json"], "历史验证必须携带案例"

    # 人工复核：留档
    resp3 = client.post(
        f"/api/v1/experience-cards/{card['card_id']}/validate-non-quant",
        json={"method": "expert_review", "note": "复核通过：机制描述与公告一致"},
    )
    assert resp3.status_code == 201
    assert resp3.json()["validation"]["method"] == "expert_review"

    # 未知方法 → 422 显形
    bad = client.post(
        f"/api/v1/experience-cards/{card['card_id']}/validate-non-quant",
        json={"method": "ic_backtest"},
    )
    assert bad.status_code == 422
    assert bad.json()["error_code"] == "experience.validation_refused"


def test_playbook_search_only_approved_no_evidence_fields(client, monkeypatch):
    card = _make_card(client, monkeypatch)

    # 未批准 → 不进 Playbook
    empty = client.get("/api/v1/experience-cards/playbook/search", params={"q": ""}).json()
    assert all(r["card_id"] != card["card_id"] for r in empty["results"])

    # 验证（case+反例 pass）+ 批准 → 进 Playbook（G3.3 需 ≥1 PASS 验证）
    client.post(f"/api/v1/experience-cards/{card['card_id']}/validate")
    client.post(
        f"/api/v1/experience-cards/{card['card_id']}/validate-non-quant",
        json={"method": "counterexample_search"},
    )
    conf = client.post("/api/v1/command/confirmations", json={
        "tool_name": "approve_experience_card",
        "arguments": {"card_id": card["card_id"], "card_version": 1},
    }).json()["confirmation"]
    client.post(f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
                json={"decision": "approved"})
    client.post(f"/api/v1/experience-cards/{card['card_id']}/approve", json={
        "confirmation_id": conf["confirmation_id"]})
    found = client.get("/api/v1/experience-cards/playbook/search", params={"q": ""}).json()
    hits = [r for r in found["results"] if r["card_id"] == card["card_id"]]
    assert hits, "approved card must appear in playbook"
    # Playbook ≠ Evidence：条目不携带 authority/fact_status 字段
    assert "authority_level" not in hits[0]
    assert "fact_status" not in hits[0]


def test_structured_refine_requires_key(client, monkeypatch):
    card = _make_card(client, monkeypatch)
    resp = client.post(f"/api/v1/experience-cards/{card['card_id']}/refine-structured")
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "experience.refine_unavailable"
