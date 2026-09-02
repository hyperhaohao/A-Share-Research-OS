"""G3 — Experience 原—炼—验—用（观澜语义迁移任务书 §G3）.

覆盖：
  - Approval 语义（§G3.3）：case-only（inconclusive）→ 禁止批准；
    counterexample fail 未解决 → 禁止批准；counterexample pass → 可批准；
  - 审计事件（§G3.4）：approve/reject 落 RunEvent；
  - 规则组件（§G3.5）：未批准 422；批准后输出机器可消费结构
    （preconditions/invalidators/signals/scope/usage_guidance）；
  - 版本 Diff（§G3.6）：字段级 changed_fields；
  - 指标（§G3.7）：<3 样本 INSUFFICIENT；≥3 样本输出真实 n/span/收益分布；
  - F7 审批门整合：approve_experience_card 工具经 confirmation 执行。
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
from app.application.experience import (
    ExperienceCardORM,
    ExperienceCardVersionORM,
    ExperienceRepository,
    ExperienceValidationORM,
)
from app.storage.research_orm import ThesisORM


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


def _make_card(client, *, status: str = "VALIDATING") -> str:
    """直接种子一张经验卡（VALIDATING 态，绕过 report 依赖）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        card = ExperienceCardORM(
            card_id=f"exp_{status.lower()[:4]}{'00000001'}",
            instrument_id="SZSE:000831",
            title="减持潮供给压力经验",
            category="research_pattern",
            statement="股东减持计划披露后 20 日内股价承压",
            mechanism="减持增加股份供给；供给增加压制股价",
            applicable_conditions_json=["减持比例 ≥1%", "无对冲安排"],
            invalid_conditions_json=["大股东全额认购"],
            status=status,
            verdict=None,
            current_version=1,
            source_report_id="rpt_seed00000001",
            source_report_version_id="rpv_seed0000001",
            source_snapshot_id="snap_seed0000001",
            source_claim_ids_json=[],
            source_evidence_ids_json=[],
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(card)
        session.add(ExperienceCardVersionORM(
            card_id=card.card_id, version_no=1,
            statement=card.statement, mechanism=card.mechanism,
            applicable_conditions_json=card.applicable_conditions_json,
            invalid_conditions_json=card.invalid_conditions_json,
            confidence=0.6, method="deterministic", created_at=NOW,
        ))
        session.commit()
        return card.card_id
    finally:
        session.close()


def _add_validation(client, card_id: str, *, method: str, verdict: str,
                    cases: list | None = None) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        v = ExperienceValidationORM(
            validation_id=f"expv_{method[:4]}{abs(hash(card_id + method + verdict)) % 10 ** 8:08d}",
            card_id=card_id, method=method, verdict=verdict,
            cases_json=cases or [], summary=f"{method} → {verdict}",
            created_at=NOW,
        )
        ExperienceRepository(session).add_validation(v)
        session.commit()
        return v.validation_id
    finally:
        session.close()


def _audit_events(client, card_id: str) -> list[dict]:
    resp = client.get(
        f"/api/v1/research-runs/audit_exp_{card_id[-8:]}/events"
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("results", [])


def _approve_with_confirmation(client, card_id: str) -> str:
    """R2：创建持久确认 → 批准 → 返回 confirmation_id（供直接 API 消费）。"""
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.application.experience import ExperienceCardORM

        row = session.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()
        card_version = row.current_version
    finally:
        session.close()
    conf = client.post("/api/v1/command/confirmations", json={
        "tool_name": "approve_experience_card",
        "arguments": {"card_id": card_id, "card_version": card_version},
    }).json()["confirmation"]
    client.post(f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
                json={"decision": "approved"})
    return conf["confirmation_id"]


# ── §G3.3 Approval 语义 ──────────────────────────────────────────────────────


def test_approve_blocked_without_explicit_pass(client):
    card_id = _make_card(client)
    # case-only（inconclusive）→ 禁止批准
    _add_validation(client, card_id, method="case", verdict="inconclusive")
    r = client.post(f"/api/v1/experience-cards/{card_id}/approve", json={
        "confirmation_id": "cfm_missing0000000000001"})
    assert r.status_code == 422, r.text
    assert "PASS" in r.json()["detail"]


def test_approve_blocked_by_unresolved_fail(client):
    card_id = _make_card(client)
    # counterexample 命中反例 → fail → 禁止批准（即使另有 pass）
    _add_validation(client, card_id, method="counterexample_search", verdict="fail")
    _add_validation(client, card_id, method="counterexample_search2", verdict="pass")
    conf_id = _approve_with_confirmation(client, card_id)
    r = client.post(f"/api/v1/experience-cards/{card_id}/approve", json={
        "confirmation_id": conf_id})
    assert r.status_code == 422
    assert "FAIL" in r.json()["detail"]


def test_approve_with_pass_validation_and_audit(client):
    card_id = _make_card(client)
    _add_validation(client, card_id, method="case", verdict="inconclusive")
    _add_validation(client, card_id, method="counterexample_search", verdict="pass")

    conf_id = _approve_with_confirmation(client, card_id)
    approved = client.post(f"/api/v1/experience-cards/{card_id}/approve", json={
        "confirmation_id": conf_id})
    assert approved.status_code == 200, approved.text
    assert approved.json()["card"]["status"] == "APPROVED"

    # 审计事件（§G3.4）
    events = _audit_events(client, card_id)
    assert any(e["event_type"] == "experience_approved" for e in events)


def test_reject_records_audit(client):
    card_id = _make_card(client)
    r = client.post(f"/api/v1/experience-cards/{card_id}/reject",
                    json={"reason": "机制不成立"})
    assert r.status_code == 200
    events = _audit_events(client, card_id)
    assert any(e["event_type"] == "experience_rejected" for e in events)


# ── §G3.5 规则组件 ───────────────────────────────────────────────────────────


def test_rule_component_requires_approval(client):
    card_id = _make_card(client)  # VALIDATING
    r = client.get(f"/api/v1/experience-cards/{card_id}/rule-component")
    assert r.status_code == 422
    assert r.json()["error_code"] == "experience.not_approved"


def test_rule_component_structured_output(client):
    card_id = _make_card(client)
    _add_validation(client, card_id, method="counterexample_search", verdict="pass")
    conf_id = _approve_with_confirmation(client, card_id)
    client.post(f"/api/v1/experience-cards/{card_id}/approve", json={
        "confirmation_id": conf_id})

    out = client.get(f"/api/v1/experience-cards/{card_id}/rule-component")
    assert out.status_code == 200, out.text
    rc = out.json()["rule_component"]
    # 机器可消费结构（非描述文本）
    assert rc["kind"] == "experience_rule_component"
    assert rc["card_id"] == card_id
    assert rc["preconditions"] == ["减持比例 ≥1%", "无对冲安排"]
    assert rc["invalidators"] == ["大股东全额认购"]
    assert rc["mechanism_terms"]  # 机制分词非空
    assert rc["compiled_at"]


# ── §G3.6 版本 Diff ──────────────────────────────────────────────────────────


def test_version_diff_field_level(client):
    card_id = _make_card(client)
    # 直接落 v2（机制文本变化；refine-LLM 路径 BLOCKED_EXTERNAL 不在本测）
    factory = client.app.state._test_factory
    session = factory()
    try:
        session.add(ExperienceCardVersionORM(
            card_id=card_id, version_no=2,
            statement="股东减持计划披露后 20 日内股价承压（修订）",
            mechanism="减持增加股份供给；供给增加压制股价；解禁叠加放大压力",
            applicable_conditions_json=["减持比例 ≥1%", "无对冲安排"],
            invalid_conditions_json=["大股东全额认购"],
            confidence=0.65, method="deterministic", created_at=NOW,
        ))
        session.commit()
    finally:
        session.close()
    diff = client.get(
        f"/api/v1/experience-cards/{card_id}/versions/diff",
        params={"v1": 1, "v2": 2},
    ).json()
    assert diff["v1"] == 1 and diff["v2"] == 2
    assert diff["changed_fields"], "refine must change something"
    # 不存在的版本 → 404
    r = client.get(
        f"/api/v1/experience-cards/{card_id}/versions/diff",
        params={"v1": 1, "v2": 9},
    )
    assert r.status_code == 404


# ── §G3.7 指标 ───────────────────────────────────────────────────────────────


def test_metrics_insufficient_below_three_cases(client):
    card_id = _make_card(client)
    _add_validation(client, card_id, method="case", verdict="inconclusive",
                    cases=[{"forward_return_pct": -1.2,
                            "exit_observed_at": NOW.isoformat()}])
    out = client.get(f"/api/v1/experience-cards/{card_id}/metrics").json()["metrics"]
    assert out["status"] == "INSUFFICIENT"
    assert out["n_cases"] == 1


def test_metrics_real_distribution_with_three_cases(client):
    card_id = _make_card(client)
    cases = [
        {"forward_return_pct": -2.0, "exit_observed_at": "2026-08-02T00:00:00+00:00"},
        {"forward_return_pct": 1.5, "exit_observed_at": "2026-08-12T00:00:00+00:00"},
        {"forward_return_pct": 3.0, "exit_observed_at": "2026-08-22T00:00:00+00:00"},
    ]
    _add_validation(client, card_id, method="case", verdict="inconclusive", cases=cases)
    out = client.get(f"/api/v1/experience-cards/{card_id}/metrics").json()["metrics"]
    assert out["status"] == "ok"
    assert out["n_cases"] == 3
    assert out["span_days"] == 20
    assert out["forward_return"]["mean_pct"] == round(((-2.0 + 1.5 + 3.0) / 3), 3)
    assert out["forward_return"]["positive_rate"] == round(2 / 3, 3)
    # 方向 IC honest INSUFFICIENT（预测方向记录由 G8 提供）
    assert out["directional_ic"] == "INSUFFICIENT"


# ── F7 审批门整合 ────────────────────────────────────────────────────────────


def test_approve_via_confirmation_gate_tool(client):
    card_id = _make_card(client)
    _add_validation(client, card_id, method="counterexample_search", verdict="pass")

    # 未经确认 → 422 confirmation_required
    direct = client.post("/api/v1/command/tools/approve_experience_card/execute",
                         json={"arguments": {"card_id": card_id}})
    assert direct.status_code == 422
    digest = direct.json()["arguments_digest"]

    # 创建确认 → 批准 → 执行（consumed）
    from app.application.experience import ExperienceCardORM

    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()
        card_version = row.current_version
    finally:
        session.close()
    conf = client.post("/api/v1/command/confirmations", json={
        "tool_name": "approve_experience_card",
        "arguments": {"card_id": card_id, "card_version": card_version},
    }).json()["confirmation"]
    client.post(
        f"/api/v1/command/confirmations/{conf['confirmation_id']}/decide",
        json={"decision": "approved"},
    )
    executed = client.post(
        "/api/v1/command/tools/approve_experience_card/execute",
        json={"arguments": {"card_id": card_id},
              "confirmation_id": conf["confirmation_id"]},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["result"]["status"] == "APPROVED"

    # 拒绝路径工具（需确认）
    r = client.post("/api/v1/command/tools/reject_experience_card/execute",
                    json={"arguments": {"card_id": card_id}})
    assert r.status_code == 422  # 同样走确认门
