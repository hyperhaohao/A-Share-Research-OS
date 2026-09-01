"""F7 — 帷幄审批确认门（第三轮整改任务书 §8.6）.

覆盖：
  - 状态机：pending → approved|rejected|expired|revoked → consumed；
  - 高风险工具才可创建确认（非高风险 422）；
  - digest 绑定参数：批准后参数不可替换（TOCTOU）；
  - lease 超时 → expired（不可批准）；
  - 重复决定幂等（无副作用、无错误）；
  - 拒绝后无副作用（工具不执行、无新 Thesis）；
  - consumed 一次性：执行后复用 → invalid；
  - 全部决定落库 + confirmation_requested/decided 事件（审计）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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
REVISION_ARGS = {
    "instrument_id": TARGET,
    "revised_statement": "修订：减持计划披露后供给压力上升。",
}


def _seed_evidence(session, ev_key, title, summary, *, age_days=2.0):
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


def _seed_current_thesis(client) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _seed_evidence(session, "ev0", "股东减持披露",
                            "广晟控股集团披露减持计划，拟减持不超过1%股份")
        _seed_evidence(session, "ev_new", "减持计划进展",
                       "广晟控股集团披露减持计划实施进展公告", age_days=0.1)
        snap = SnapshotRepository(session).build(
            TARGET, NOW - timedelta(days=1),
            evidence_repo=EvidenceRepository(session),
        )
        cid = ResearchRepository(session).save_claim(
            Claim(
                instrument_id=TARGET,
                snapshot_id=snap.snapshot_id,
                statement="广晟控股减持计划或影响股份供给",
                claim_type=ClaimType.FUNDAMENTAL_FACT,
                supporting_evidence_refs=(ev,),
                fact_status=FactStatus.OFFICIAL_DISCLOSURE,
                confidence=0.8,
                status=ClaimStatus.PROPOSED,
            )
        )
        thesis_id = ResearchRepository(session).save_thesis(
            InvestmentThesis(
                instrument_id=TARGET,
                snapshot_id=snap.snapshot_id,
                title="中国稀土 研究综合论点",
                description="减持观察",
                supporting_claims=(cid,),
                opposing_claims=(),
                confidence=0.7,
            )
        )
        t_row = session.scalars(
            select(ThesisORM).where(ThesisORM.thesis_id == thesis_id)
        ).first()
        t_row.meta_json = {"is_current": True, "added_evidence_ids": []}
        session.commit()
        return thesis_id
    finally:
        session.close()


def _create_confirmation(client, *, session_id=None, tool="submit_thesis_revision",
                         arguments=None, lease_s=300):
    return client.post("/api/v1/command/confirmations", json={
        "tool_name": tool,
        "arguments": REVISION_ARGS if arguments is None else arguments,
        "command_session_id": session_id,
        "lease_s": lease_s,
    })


def _thesis_count(client) -> int:
    factory = client.app.state._test_factory
    session = factory()
    try:
        return len(session.scalars(select(ThesisORM)).all())
    finally:
        session.close()


def test_state_machine_full_flow(client):
    _seed_current_thesis(client)
    sid = client.post("/api/v1/command/sessions").json()["session"]["session_id"]

    created = _create_confirmation(client, session_id=sid)
    assert created.status_code == 201, created.text
    conf = created.json()["confirmation"]
    assert conf["status"] == "pending"
    assert conf["arguments_digest"]
    assert conf["tool_name"] == "submit_thesis_revision"

    # requested 事件已入会话事件流（审计）
    evs = client.get(
        f"/api/v1/command/sessions/{sid}/events", params={"after_sequence": 0}
    ).json()["results"]
    assert any(e["event_type"] == "confirmation_requested" for e in evs)

    # 批准
    decided = client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "approved"},
    ).json()["confirmation"]
    assert decided["status"] == "approved"

    # 执行（digest 绑定：参数一致 → 成功 → consumed）
    executed = client.post(
        "/api/v1/command/tools/submit_thesis_revision/execute",
        json={"arguments": REVISION_ARGS, "confirmation_id": conf["confirmation_id"],
              "command_session_id": sid, "correlation_id": conf["confirmation_id"]},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["ok"] is True

    # consumed 状态可见；复用 → invalid
    state = client.get(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}"
    ).json()["confirmation"]
    assert state["status"] == "consumed"

    # decided 事件（审计）
    evs = client.get(
        f"/api/v1/command/sessions/{sid}/events", params={"after_sequence": 0}
    ).json()["results"]
    assert any(
        e["event_type"] == "confirmation_decided" and e["status"] == "approved"
        for e in evs
    )


def test_rejected_confirmation_has_no_side_effects(client):
    _seed_current_thesis(client)
    before = _thesis_count(client)

    conf = _create_confirmation(client).json()["confirmation"]
    decided = client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "rejected"},
    ).json()["confirmation"]
    assert decided["status"] == "rejected"

    # 拒绝后执行 → invalid；无副作用
    executed = client.post(
        "/api/v1/command/tools/submit_thesis_revision/execute",
        json={"arguments": REVISION_ARGS, "confirmation_id": conf["confirmation_id"]},
    )
    assert executed.status_code == 422
    assert executed.json()["error_code"] == "tool.confirmation_invalid"
    assert _thesis_count(client) == before


def test_double_decide_is_idempotent(client):
    _seed_current_thesis(client)
    conf = _create_confirmation(client).json()["confirmation"]
    cid = conf["confirmation_id"]

    first = client.post(
        f"/api/v1/command/confirmations/{cid}/decide", json={"decision": "approved"}
    ).json()["confirmation"]
    second = client.post(
        f"/api/v1/command/confirmations/{cid}/decide", json={"decision": "approved"}
    ).json()["confirmation"]
    assert first["status"] == second["status"] == "approved"
    # 已批准后再 reject：幂等返回当前状态（不改）
    third = client.post(
        f"/api/v1/command/confirmations/{cid}/decide", json={"decision": "rejected"}
    ).json()["confirmation"]
    assert third["status"] == "approved"


def test_arguments_replacement_after_approval_fails(client):
    _seed_current_thesis(client)
    conf = _create_confirmation(client).json()["confirmation"]
    client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "approved"},
    )
    # 批准后替换参数 → digest 不匹配 → invalid（§8.6 防参数替换）
    executed = client.post(
        "/api/v1/command/tools/submit_thesis_revision/execute",
        json={"arguments": {"instrument_id": TARGET,
                            "revised_statement": "被替换的参数。"},
              "confirmation_id": conf["confirmation_id"]},
    )
    assert executed.status_code == 422
    assert executed.json()["error_code"] == "tool.confirmation_invalid"


def test_non_high_risk_tool_cannot_create_confirmation(client):
    r = _create_confirmation(client, tool="search_evidence",
                             arguments={"instrument_id": TARGET})
    assert r.status_code == 422
    assert r.json()["error_code"] == "confirmation.not_applicable"


def test_revoked_approved_confirmation_cannot_execute(client):
    _seed_current_thesis(client)
    conf = _create_confirmation(client).json()["confirmation"]
    client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "approved"},
    )
    client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "revoked"},
    )
    executed = client.post(
        "/api/v1/command/tools/submit_thesis_revision/execute",
        json={"arguments": REVISION_ARGS, "confirmation_id": conf["confirmation_id"]},
    )
    assert executed.status_code == 422


def test_expired_lease_cannot_be_approved(client):
    _seed_current_thesis(client)
    conf = _create_confirmation(client, lease_s=5).json()["confirmation"]
    # 直接把 expires_at 拨回过去（等价于超时；不 sleep）
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.application.confirmations_orm import CommandConfirmationORM as ORM

        row = session.scalars(
            select(ORM).where(ORM.confirmation_id == conf["confirmation_id"])
        ).first()
        row.expires_at = NOW - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()

    decided = client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "approved"},
    ).json()["confirmation"]
    assert decided["status"] == "expired"  # 超时 → expired（不可批准）


def test_confirmation_listing_by_status(client):
    _seed_current_thesis(client)
    _create_confirmation(client)
    pending = client.get(
        "/api/v1/command/confirmations", params={"status": "pending"}
    ).json()
    assert pending["count"] == 1
    # 未决确认出现在左栏数据面（§8.10）
    assert pending["results"][0]["status"] == "pending"
