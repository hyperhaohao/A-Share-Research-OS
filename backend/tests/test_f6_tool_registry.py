"""F6 — 帷幄 Tool Orchestration（第三轮整改任务书 §8.5）.

覆盖：
  - Registry 清单：§8.5 全声明字段（schema/risk/confirmation/timeout/
    idempotency/artifact_contract），不暴露 executor；
  - 白名单外工具 404；参数 schema 校验 422；
  - 只读工具真实执行（search_evidence / open_page 白名单）；
  - 高风险工具确认门：confirmation_required → issue token → 放行；
    token 复用/参数替换 → invalid（防 TOCTOU）；
  - 执行产生 tool_call/tool_result 事件（correlation_id 关联）；
  - 失败显形：executor 异常 → tool.execution_failed（非自然语言「已完成」）。
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
from app.domain.research import Claim, ClaimStatus, ClaimType, InvestmentThesis
from app.storage.research_orm import ThesisORM
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.services.current_thesis import get_current_thesis


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
TARGET = "SZSE:000831"


def _seed_evidence(session, ev_key, title, summary, *, age_days: float = 1.0):
    at = NOW - timedelta(days=age_days)
    rec = EvidenceRecord(
        instrument_id=TARGET,
        evidence_type=EvidenceType.ANNOUNCEMENT,
        title=title,
        summary=summary,
        source=f"provider_{ev_key}",
        source_type="exchange",
        authority_level=AuthorityLevel.A1,
        fact_status=FactStatus.OFFICIAL_DISCLOSURE,
        event_time=at,
        available_time=at,
        ingested_time=at + timedelta(minutes=1),
        revision_time=at + timedelta(minutes=1),
    )
    evidence_id, _ = EvidenceRepository(session).save(rec)
    return evidence_id


def _seed_thesis_with_claims(client, n=2) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        evs = [
            _seed_evidence(
                session, f"ev{i}",
                f"股东减持披露 {i}",
                f"广晟控股集团披露减持计划，拟减持不超过1%股份（{i}）",
                age_days=2.0,
            )
            for i in range(n)
        ]
        # 修订所需的新证据（旧快照 as_of=1 天前 → 不 pin 此条）
        _seed_evidence(
            session, "ev_new", "减持计划进展",
            "广晟控股集团披露减持计划实施进展公告",
            age_days=0.1,
        )
        snap = SnapshotRepository(session).build(
            TARGET, NOW - timedelta(days=1),
            evidence_repo=EvidenceRepository(session),
        )
        claim_ids = []
        for i, ev in enumerate(evs):
            cid = ResearchRepository(session).save_claim(
                Claim(
                    instrument_id=TARGET,
                    snapshot_id=snap.snapshot_id,
                    statement=f"广晟控股减持计划或影响股份供给（{i}）",
                    claim_type=ClaimType.FUNDAMENTAL_FACT,
                    supporting_evidence_refs=(ev,),
                    fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                    confidence=0.8,
                    status=ClaimStatus.PROPOSED,
                )
            )
            claim_ids.append(cid)
        thesis_id = ResearchRepository(session).save_thesis(
            InvestmentThesis(
                instrument_id=TARGET,
                snapshot_id=snap.snapshot_id,
                title="中国稀土 研究综合论点",
                description="减持观察",
                supporting_claims=tuple(claim_ids),
                opposing_claims=(),
                confidence=0.7,
            )
        )
        row = session.scalars(
            ThesisORM.__table__.select().where(ThesisORM.thesis_id == thesis_id)
        ).first()
        from app.storage.research_orm import ThesisORM as T

        t_row = session.scalars(
            __import__("sqlalchemy").select(T).where(T.thesis_id == thesis_id)
        ).first()
        t_row.meta_json = {"is_current": True, "added_evidence_ids": []}
        session.commit()
        return thesis_id
    finally:
        session.close()


def _execute(client, name, arguments, **extra):
    return client.post(
        f"/api/v1/command/tools/{name}/execute",
        json={"arguments": arguments, **extra},
    )


# ── Registry 清单 + 白名单 ───────────────────────────────────────────────────


def test_registry_manifest_declaration_fields(client):
    out = client.get("/api/v1/command/tools").json()
    assert out["count"] >= 13
    required = {
        "name", "description", "input_schema", "output_schema", "risk_level",
        "requires_confirmation", "timeout_s", "idempotency_policy",
        "artifact_contract",
    }
    for tool in out["results"]:
        assert required <= set(tool), tool["name"]
        assert tool["risk_level"] in ("read", "write", "high")
        assert tool["idempotency_policy"] in ("idempotent", "at_most_once", "merge")
        assert "executor" not in tool  # 不暴露执行体
    names = {t["name"] for t in out["results"]}
    assert {
        "search_evidence", "build_pit_snapshot", "open_current_thesis",
        "analyze_thesis_diff", "submit_thesis_revision", "create_experience_card",
        "start_validation_workflow", "run_screening", "assemble_strategy",
        "create_strategy_monitor", "generate_market_product", "memory_search",
        "open_page",
    } <= names


def test_unknown_tool_is_404(client):
    assert (
        _execute(client, "run_arbitrary_function", {}).status_code == 404
    )


# ── Schema 校验 ──────────────────────────────────────────────────────────────


def test_arguments_schema_validation(client):
    # 缺 required
    r = _execute(client, "search_evidence", {})
    assert r.status_code == 422
    assert r.json()["error_code"] == "tool.arguments_invalid"
    assert "instrument_id" in r.json()["detail"]
    # 类型错误
    r = _execute(client, "search_evidence", {"instrument_id": 123})
    assert r.status_code == 422
    # enum 违规（open_page 白名单外页面）
    r = _execute(client, "open_page", {"page": "http://evil.example"})
    assert r.status_code == 422


# ── 只读工具真实执行 ─────────────────────────────────────────────────────────


def test_read_tools_execute_with_structured_results(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        _seed_evidence(session, "ev0", "股东减持披露",
                       "广晟控股集团披露减持计划，拟减持不超过1%股份")
        session.commit()
    finally:
        session.close()

    r = _execute(client, "search_evidence",
                 {"instrument_id": TARGET, "limit": 5})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["ok"] is True
    assert out["result"]["count"] >= 1
    assert out["result"]["results"][0]["evidence_id"]

    r = _execute(client, "open_page",
                 {"page": "thesis-center", "payload": {"instrument_id": TARGET}})
    assert r.status_code == 200
    assert r.json()["result"]["page"] == "thesis-center"


# ── 高风险工具确认门（§8.6 状态机的执行面） ──────────────────────────────────


def test_high_risk_tool_requires_confirmation(client):
    _seed_thesis_with_claims(client)
    # 未带 token → confirmation_required + arguments_digest（服务端权威）
    r = _execute(client, "submit_thesis_revision", {
        "instrument_id": TARGET,
        "revised_statement": "修订：减持计划披露后供给压力上升。",
    })
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "tool.confirmation_required"
    assert body["arguments_digest"]

    # 签发 token（digest 绑定参数）→ 放行
    from app.services.tool_registry import issue_confirmation

    digest = body["arguments_digest"]
    args = {
        "instrument_id": TARGET,
        "revised_statement": "修订：减持计划披露后供给压力上升。",
    }
    token = issue_confirmation("submit_thesis_revision", digest)["confirmation_token"]
    r2 = _execute(client, "submit_thesis_revision", args,
                  confirmation_token=token)
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"] is True
    assert r2.json()["result"]["thesis_id"]

    # token 一次性：复用 → invalid
    r3 = _execute(client, "submit_thesis_revision", args,
                  confirmation_token=token)
    assert r3.status_code == 422
    assert r3.json()["error_code"] == "tool.confirmation_invalid"

    # 参数替换（digest 不匹配）→ invalid（防 TOCTOU）
    token2 = issue_confirmation("submit_thesis_revision", digest)["confirmation_token"]
    r4 = _execute(client, "submit_thesis_revision",
                  {"instrument_id": TARGET,
                   "revised_statement": "被替换的参数：恶意修订。"},
                  confirmation_token=token2)
    assert r4.status_code == 422
    assert r4.json()["error_code"] == "tool.confirmation_invalid"


# ── 事件发射 + 失败显形 ──────────────────────────────────────────────────────


def test_tool_execution_emits_events(client):
    sid = client.post("/api/v1/command/sessions").json()["session"]["session_id"]
    factory = client.app.state._test_factory
    session = factory()
    try:
        _seed_evidence(session, "ev0", "股东减持披露",
                       "广晟控股集团披露减持计划，拟减持不超过1%股份")
        session.commit()
    finally:
        session.close()

    corr = "corr_tool_test_0001"
    r = _execute(client, "search_evidence", {"instrument_id": TARGET},
                 command_session_id=sid, correlation_id=corr)
    assert r.status_code == 200

    evs = client.get(
        f"/api/v1/command/sessions/{sid}/events", params={"after_sequence": 0}
    ).json()["results"]
    types = [(e["event_type"], e["correlation_id"]) for e in evs]
    assert ("tool_call", corr) in types
    assert ("tool_result", corr) in types


def test_tool_failure_is_explicit(client):
    # 不存在的 card → executor 异常 → 结构化失败（不是「已完成」）
    r = _execute(client, "create_experience_card", {"report_id": "rpt_missing00"})
    assert r.status_code == 500
    body = r.json()
    assert body["ok"] is False
    assert body["error_code"] == "tool.execution_failed"
    assert body["detail"]
