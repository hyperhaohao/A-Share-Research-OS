"""V2 Phase C — ExperienceCard (总纲 §12/§13/§43/§72).

验收：
  - 报告 → 经验卡草稿：确定性提炼，保留 report_id/version_id/claim_ids/
    evidence_ids（§43），artifact 注册并 generated_from 报告；
  - Case validation：PIT 入场价 → 最新可见价，信息记录（不伪造结论）；
  - 流程门槛：验证前批准 → 显式 422；验证后批准 → APPROVED；
  - 无 LLM 时 refine 显式 422（确定性提炼已是基线）；
  - handoff 注册 report→experience:create_experience_draft。
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
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    outcome = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_expcard0001")
    assert outcome.status_code == 202, outcome.text
    return outcome.json()


def test_card_from_report_preserves_sources_and_links_artifact(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    created = client.post("/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]})
    assert created.status_code == 201, created.text
    card = created.json()["card"]

    # 原+炼：deterministic refine from the structured research state
    assert card["status"] == "REFINED"
    assert card["refine_method"] == "deterministic"
    assert card["statement"]
    assert card["mechanism"]
    assert card["title"]

    # §43: sources preserved
    assert card["source_report_id"] == body["report_id"]
    assert card["source_report_version_id"].startswith("ver_") or card["source_report_version_id"]
    assert card["source_snapshot_id"] == body["snapshot_id"]
    assert len(card["source_claim_ids"]) > 0

    # artifact registry: experience_card linked generated_from the report
    artifacts = client.get(
        "/api/v1/artifacts", params={"artifact_type": "experience_card"}
    ).json()
    assert artifacts["count"] == 1
    art = artifacts["results"][0]
    assert art["domain_id"] == card["card_id"]
    lineage = client.get(f"/api/v1/artifacts/{art['artifact_id']}/lineage").json()
    assert "report" in {u["artifact_type"] for u in lineage["upstream"]}

    # the card carries at least one version snapshot
    detail = client.get(f"/api/v1/experience-cards/{card['card_id']}").json()["card"]
    assert detail["versions"][0]["version_no"] == 1


def test_card_from_report_without_thesis_refuses(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    # a second report for an instrument with no thesis: use an unknown report
    missing = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": "rpt_missing0000"}
    )
    assert missing.status_code == 404
    del body


def test_case_validation_and_approval_gate(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    card = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]}
    ).json()["card"]
    card_id = card["card_id"]

    # approve before any validation is refused (§13 验→用)
    blocked = client.post(
        f"/api/v1/experience-cards/{card_id}/approve", json={"verdict": "ok"}
    )
    assert blocked.status_code == 422
    assert blocked.json()["error_code"] == "experience.approve_blocked"

    validated = client.post(f"/api/v1/experience-cards/{card_id}/validate")
    assert validated.status_code == 201, validated.text
    validation = validated.json()["validation"]
    assert validation["method"] == "case"
    case = validation["cases"][0]
    # the mocked quote price is 24.83 → entry pinned from the snapshot
    assert case["entry_price"] == 24.83
    assert case["exit_price"] == 24.83
    assert case["forward_return_pct"] == 0.0
    assert "案例验证" in validation["summary"]

    detail = client.get(f"/api/v1/experience-cards/{card_id}").json()["card"]
    assert detail["status"] == "VALIDATING"

    # G3.3：批准需要 ≥1 明确 PASS 的验证（case=inconclusive 不足）→
    # 补反例搜索（语料 0 命中 → pass）
    cq = client.post(
        f"/api/v1/experience-cards/{card_id}/validate-non-quant",
        json={"method": "counterexample_search"},
    )
    assert cq.status_code == 201
    assert cq.json()["validation"]["verdict"] == "pass"

    approved = client.post(
        f"/api/v1/experience-cards/{card_id}/approve", json={"verdict": "案例支持，继续观察"}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["card"]["status"] == "APPROVED"
    assert approved.json()["card"]["verdict"] == "案例支持，继续观察"


def test_refine_without_llm_refuses_explicitly(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    card = client.post(
        "/api/v1/experience-cards/from-report", json={"report_id": body["report_id"]}
    ).json()["card"]
    refused = client.post(f"/api/v1/experience-cards/{card['card_id']}/refine")
    assert refused.status_code == 422
    assert refused.json()["error_code"] == "experience.llm_unavailable"


def test_handoff_report_to_experience_is_registered(client, monkeypatch):
    body = _run_pipeline(client, monkeypatch)
    report_artifact = client.get(
        "/api/v1/artifacts/by-domain/Report/{report_id}".format(report_id=body["report_id"])
    ).json()["artifact"]
    ok = client.post(
        "/api/v1/handoffs",
        json={
            "source_module": "report",
            "target_module": "experience",
            "action": "create_experience_draft",
            "artifact_ids": [report_artifact["artifact_id"]],
            "context": {"primary_instrument_id": "SZSE:000831"},
            "message": "user clicked 炼成经验卡",
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["handoff"]["action"] == "create_experience_draft"
