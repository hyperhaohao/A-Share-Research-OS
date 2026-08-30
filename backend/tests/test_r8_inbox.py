"""R8 — Research Inbox / Thesis Diff / Signal Ladder（方案 §14）.

验收：
  - Inbox 聚合真实数据（新证据/重要性决策/研究请求/到期预测/失败采集）；
  - Thesis Diff：新证据 → 影响分析（affected_claims/affected_theses/
    suggested_action）；apply → 新 Thesis 行 append-only + Artifact 链；
  - Signal Ladder：A/B 分级确定性 + 证据引用强制（伪造 evidence → 422）。
"""

import httpx
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


RAW_OK = (
    'v_sz000831="1~中国稀土~000831~24.83~1651.00~1655.00~32924~85755~24354~'
    "24.83~12~1647.90~8~1647.80~21~1647.70~4~1647.60~100~"
    "24.83~15~1648.20~6~1648.30~9~1648.40~3~1648.50~7~"
    "24.83/34~20260828150123~-3.00~-0.18~1656.00~1645.00~"
    '24.83/54280/895070000~54280~89507~2.34~20.86~~1656.00~1645.00~'
    '4.59~20711.00~20771.00~8.50~1816.10~1485.90~0.98"\n'
)


def _run_pipeline(client, monkeypatch) -> dict:
    def fake_get(url, timeout=10.0, **kw):
        return httpx.Response(200, content=RAW_OK.encode("gbk"))

    monkeypatch.setattr(httpx, "get", fake_get)
    outcome = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_r8inbox0001")
    assert outcome.status_code == 202
    return outcome.json()


def test_inbox_aggregates_real_data(client, monkeypatch):
    _run_pipeline(client, monkeypatch)
    inbox = client.get("/api/v1/research-inbox").json()["inbox"]
    assert inbox["count"] >= 0
    assert "new_evidence" in inbox
    assert "materiality_alerts" in inbox
    assert "open_research_requests" in inbox
    assert "failed_collections" in inbox
    assert inbox["total_snapshots"] >= 1


def test_thesis_diff_detects_and_applies(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)

    # Thesis Diff：pipeline 刚跑完，窗口内有新证据
    diff = client.get(
        "/api/v1/research-inbox/thesis-diff",
        params={"instrument_id": "SZSE:000831", "since": "2026-08-01T00:00:00Z"},
    ).json()["diff"]
    assert diff["new_evidence"], "pipeline-collected evidence must appear as new"
    assert diff["suggested_action"] in ("delta_research", "monitor_only")

    # snapshot 绑定（apply 需要证据 pinned by snapshot — PIT）
    theses = client.get(
        "/api/v1/theses", params={"instrument_id": "SZSE:000831"}
    ).json()
    theses_list = theses.get("results") or theses.get("theses") or []
    assert theses_list, "pipeline must have produced a thesis"
    old_thesis_id = theses_list[0]["thesis_id"]

    revised = "修订：减持计划披露后，股份供给压力上升，观察窗口 15 交易日。"
    applied = client.post(
        "/api/v1/research-inbox/thesis-diff/apply",
        json={
            "instrument_id": "SZSE:000831",
            "revised_statement": revised,
        },
    )
    assert applied.status_code == 201, applied.text
    new_thesis_id = applied.json()["thesis_id"]
    assert new_thesis_id != old_thesis_id

    # append-only：旧 Thesis 仍可读，未被覆盖
    old_check = client.get(
        "/api/v1/theses", params={"instrument_id": "SZSE:000831"}
    ).json()
    old_list = old_check.get("results") or old_check.get("theses") or []
    assert any(t["thesis_id"] == old_thesis_id for t in old_list)

    # artifact provenance：新 Thesis artifact generated_from 旧 Thesis
    new_art = client.get(f"/api/v1/artifacts/by-domain/Thesis/{new_thesis_id}").json()["artifact"]
    lineage = client.get(f"/api/v1/artifacts/{new_art['artifact_id']}/lineage").json()
    assert "thesis" in {u["artifact_type"] for u in lineage["upstream"]}


def test_signal_ladder_evaluates_with_evidence_refusal(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)

    # 伪造 evidence → 422（引用强制）
    forged = client.post("/api/v1/research-inbox/signal-ladder/evaluate", json={
        "ladder": [
            {"level": "B", "keywords": ["减持"], "label": "减持披露"},
            {"level": "A", "keywords": ["重组"], "label": "重组公告"},
        ],
        "observations": [
            {"observation_id": "o1", "text": "公司披露减持计划",
             "evidence_ids": ["ev_nonexistent00"]},
        ],
    })
    assert forged.status_code == 422
    assert forged.json()["error_code"] == "signal_ladder.evidence_not_found"

    # 真实 evidence：跑 pipeline 已有真实证据 — 用第一条
    evs = client.get(
        "/api/v1/evidence", params={"instrument_id": "SZSE:000831", "limit": 1}
    ).json()["results"]
    assert evs
    real_id = evs[0]["evidence_id"]
    ok = client.post("/api/v1/research-inbox/signal-ladder/evaluate", json={
        "ladder": [
            {"level": "B", "keywords": ["减持"], "label": "减持披露"},
        ],
        "observations": [
            {"observation_id": "o1",
             "text": "股东广晟控股集团披露减持计划 不超过1061.22万股",
             "evidence_ids": [real_id]},
        ],
    })
    assert ok.status_code == 200
    results = ok.json()["results"]
    assert results and results[0]["level"] == "B"
    assert results[0]["evidence_ids"] == [real_id]
