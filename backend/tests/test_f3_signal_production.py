"""F3 — Signal Production API（第三轮整改任务书 §6.3/§6.4）.

§6.4 Golden 必测语义（真实 BUILTIN_SIGNAL_RULES + 真实 API，无 Mock 规则）：
  1. 股东减持披露 → share_reduction 事件，资产整合 Signal = NONE
  2. 否认筹划重大重组 → 不得为 A
  3. 正式停牌筹划重组公告（Trust/Type/Entity 满足）→ A
  4. T4 传闻「即将注入」→ 不得为 A
  5. 同业竞争解决进入具体方案 → B
  6. 其他公司重大重组公告 → 不得污染 000831
  7. 终止重大资产重组 → 独立负向事件，不得识别为正向 A

另覆盖 §6.3 返回契约键（trust_gate/type_gate/entity_gate/state_transition/
rejected_reasons）与 Ownership Gate。
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
TARGET = "SZSE:000831"


def _make_evidence(
    session, ev_key: str, title: str, summary: str, *,
    instrument_id: str = TARGET,
    authority: AuthorityLevel = AuthorityLevel.A1,
    etype: EvidenceType = EvidenceType.ANNOUNCEMENT,
) -> str:
    at = NOW - timedelta(days=1)
    rec = EvidenceRecord(
        instrument_id=instrument_id,
        evidence_type=etype,
        title=title,
        summary=summary,
        source=f"provider_{ev_key}",
        source_type="exchange",
        authority_level=authority,
        fact_status=FactStatus.OFFICIAL_DISCLOSURE,
        event_time=at,
        available_time=at,
        ingested_time=at + timedelta(minutes=1),
        revision_time=at + timedelta(minutes=1),
    )
    evidence_id, _ = EvidenceRepository(session).save(rec)
    return evidence_id


def _evaluate(client, ev_ids: list[str] | None = None, instrument_id: str = TARGET):
    payload = {"instrument_id": instrument_id}
    url = f"/api/v1/research-inbox/signal-ladder/evaluate-evidence?instrument_id={instrument_id}"
    if ev_ids:
        url += "&" + "&".join(f"evidence_ids={e}" for e in ev_ids)
    resp = client.post(url, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── 1）股东减持披露 → 资产整合 Signal = NONE ─────────────────────────────────


def test_share_reduction_is_not_integration_signal(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "reduce", "股东减持计划公告",
            "广东省广晟控股集团有限公司拟以集中竞价方式减持公司股份不超过1061.22万股",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    integration = [
        r for r in out["results"]
        if r["event_type"] in ("restructuring", "asset_injection")
    ]
    assert integration == []  # 减持 ≠ 资产整合（§6.4-1）
    assert out["rejected_evidence"] == []


# ── 2）否认筹划重大重组 → 不得为 A ───────────────────────────────────────────


def test_denial_cannot_be_level_a(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "deny", "澄清公告",
            "公司澄清公告：不存在筹划重大资产重组的情形",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    assert not [r for r in out["results"] if r["signal_level"] == "A"]
    negative_rejects = [
        t for t in out["rejected"]["trace"]
        if t["rule_id"] == "restructuring_formal_launch"
        and any(r.startswith("negative_pattern:") for r in t["rejected_reasons"])
    ]
    assert negative_rejects, "denial must be rejected by negative pattern"


# ── 3）正式停牌筹划重组公告 → A（Trust/Type/Entity 全过）─────────────────────


def test_formal_restructuring_announcement_is_level_a(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "formal", "重大资产重组停牌公告",
            "公司正在筹划重大资产重组事项，公司股票自本公告披露之日起停牌",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    a_signals = [r for r in out["results"] if r["signal_level"] == "A"]
    assert a_signals, out
    sig = next(r for r in a_signals if r["rule_id"] == "restructuring_formal_launch")
    # §6.3 返回契约
    for key in ("rule_id", "signal_level", "event_type", "matched_evidence_ids",
                "trust_gate", "type_gate", "entity_gate", "state_transition",
                "rejected_reasons"):
        assert key in sig, key
    assert sig["matched_evidence_ids"] == [ev]
    assert sig["trust_gate"]["passed"] is True
    assert sig["type_gate"]["passed"] is True
    assert sig["state_transition"] == "B → A"
    assert sig["rejected_reasons"] == []


# ── 4）T4 传闻「即将注入」→ 不得为 A ─────────────────────────────────────────


def test_t4_rumor_cannot_be_level_a(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "rumor", "市场传闻",
            "市场传闻资产注入预案即将公布",
            authority=AuthorityLevel.D, etype=EvidenceType.NEWS,
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    assert not [r for r in out["results"] if r["signal_level"] == "A"]
    trust_rejects = [
        t for t in out["rejected"]["trace"]
        if t["rule_id"] == "asset_injection_explicit"
        and any(r.startswith("trust_gate:") for r in t["rejected_reasons"])
    ]
    assert trust_rejects, "T4 rumor must be rejected by trust gate"


# ── 5）同业竞争解决进入具体方案 → B ──────────────────────────────────────────


def test_related_party_solution_is_level_b(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "related", "同业竞争解决方案公告",
            "控股股东披露同业竞争解决方案，明确业务边界调整安排",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    b_signals = [r for r in out["results"] if r["signal_level"] == "B"]
    assert any(r["rule_id"] == "related_party_boundary_change" for r in b_signals), out


# ── 6）其他公司重大重组公告 → 不得污染 000831 ────────────────────────────────


def test_cross_instrument_evidence_is_rejected(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev_other = _make_evidence(
            session, "otherco", "他司公告",
            "另一家公司筹划重大资产重组事项",
            instrument_id="SZSE:000999",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev_other])
    assert out["results"] == []  # 不污染 000831
    assert any(
        r["reason"] == "cross_instrument" for r in out["rejected_evidence"]
    ), out["rejected_evidence"]


# ── 7）终止重大资产重组 → 不得识别为正向 A ───────────────────────────────────


def test_terminated_restructuring_is_not_positive(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = _make_evidence(
            session, "terminated", "终止公告",
            "公司终止筹划本次重大资产重组事项",
        )
        session.commit()
    finally:
        session.close()

    out = _evaluate(client, [ev])
    assert not [r for r in out["results"] if r["signal_level"] == "A"]
    negative_rejects = [
        t for t in out["rejected"]["trace"]
        if t["rule_id"] == "restructuring_formal_launch"
        and any("negative_pattern:终止" in r for r in t["rejected_reasons"])
    ]
    assert negative_rejects, "termination must be a negative-pattern rejection"


# ── 契约：所有权门 + 默认证据加载 + 无自定义规则入口 ─────────────────────────


def test_default_load_and_contract_shape(client):
    factory = client.app.state._test_factory
    session = factory()
    try:
        _make_evidence(session, "formal2", "重大资产重组停牌公告",
                       "公司正在筹划重大资产重组事项，股票停牌")
        session.commit()
    finally:
        session.close()

    # 不传 evidence_ids → 默认加载本标的最近证据
    out = _evaluate(client)
    assert out["evaluated"]["evidence_count"] >= 1
    assert out["instrument_id"] == TARGET
    assert out["evaluated"]["rules"] >= 6

    # 生产契约：调用方不能注入自定义规则/级别（schema 无该参数，
    # 传了也会被 pydantic/query 忽略——这里是行为面断言）
    resp = client.post(
        f"/api/v1/research-inbox/signal-ladder/evaluate-evidence?instrument_id={TARGET}",
        json={"instrument_id": TARGET, "level": "A", "keywords": ["随意"],
              "label": "自定义", "ladder": [{"level": "A"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    fired_rules = {r["rule_id"] for r in body["results"]}
    assert fired_rules <= {
        "restructuring_formal_launch", "asset_injection_explicit",
        "regulatory_approval_progress", "assets_securitization_upgrade",
        "related_party_boundary_change", "ownership_structure_change",
    }
