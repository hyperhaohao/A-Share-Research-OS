"""G4 — Typed Dataflow Workflow（观澜语义迁移任务书 §G4）.

覆盖：
  - 端口类型不匹配不能发布（422）；孤立节点/不可达 output 拒绝；
  - 真实数据流：evidence→transform→output（下游消费上游端口输出，
    节点 I/O 不可变落账）；
  - 分支隔离：同一 source 两条边不同 params → 输出互不覆盖；
  - 失败传播：上游失败 → 下游 skipped + run failed；
  - retry：失败节点重跑 attempt+1；pure 节点复用输出（恢复语义）；
  - 控制面：succeeded 后 pause/cancel 422。
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


def _seed_evidence(client, summary: str, *, instrument_id: str = "SZSE:000831") -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id=instrument_id,
            evidence_type=EvidenceType.ANNOUNCEMENT,
            title="公告",
            summary=summary,
            source=f"provider_{abs(hash(summary)) % 10 ** 8}",
            source_type="exchange",
            authority_level=AuthorityLevel.A1,
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


def _def_payload(nodes: list[dict], edges: list[dict], name: str = "typed-g4") -> dict:
    return {"name": name, "instrument_id": "SZSE:000831",
            "nodes": [{"key": n["key"], "kind": n["kind"], "params": n.get("params", {})}
                      for n in nodes],
            "edges": edges}


# ── 图校验（发布门槛） ───────────────────────────────────────────────────────


def test_port_type_mismatch_rejected(client):
    nodes = [
        {"key": "q", "kind": "quote"},
        {"key": "v", "kind": "validation"},
        {"key": "out", "kind": "output"},
    ]
    # quote.quote_series(type=quote_series) → validation.metrics_in(type=metrics) 不匹配
    edges = [
        {"from": "q", "to": "v", "source_port": "quote_series", "target_port": "metrics_in"},
        {"from": "v", "to": "out", "source_port": "metrics", "target_port": "metrics_in"},
    ]
    r = client.post("/api/v1/workflows-typed/definitions",
                    json=_def_payload(nodes, edges))
    assert r.status_code == 422
    assert "port type mismatch" in r.json()["detail"]


def test_orphan_and_unreachable_rejected(client):
    # 孤立 rule 节点（无输入）
    nodes = [
        {"key": "e", "kind": "evidence"},
        {"key": "rule", "kind": "rule"},
        {"key": "out", "kind": "output"},
    ]
    edges = [{"from": "e", "to": "out", "source_port": "evidence_set",
              "target_port": "metrics_in"}]
    r = client.post("/api/v1/workflows-typed/definitions",
                    json=_def_payload(nodes, edges))
    assert r.status_code == 422
    assert "orphan" in r.json()["detail"]

    # 不可达 output（从输入节点到不了）
    nodes2 = [
        {"key": "e", "kind": "evidence"},
        {"key": "out", "kind": "output"},
        {"key": "out2", "kind": "output"},
    ]
    edges2 = [{"from": "e", "to": "out", "source_port": "evidence_set",
               "target_port": "metrics_in"}]
    r2 = client.post("/api/v1/workflows-typed/definitions",
                     json=_def_payload(nodes2, edges2))
    assert r2.status_code == 422


# ── 真实数据流 + 节点 I/O 账本 ───────────────────────────────────────────────


def test_real_dataflow_with_node_io_ledger(client):
    _seed_evidence(client, "公司冶炼分离产能爬坡公告")
    nodes = [
        {"key": "ev", "kind": "evidence", "params": {"limit": 5}},
        {"key": "tr", "kind": "transform", "params": {"op": "latest"}},
        {"key": "out", "kind": "output"},
    ]
    edges = [
        {"from": "ev", "to": "tr", "source_port": "evidence_set", "target_port": "data_in"},
        {"from": "tr", "to": "out", "source_port": "data_out", "target_port": "metrics_in"},
    ]
    created = client.post("/api/v1/workflows-typed/definitions",
                          json=_def_payload(nodes, edges, "dataflow-g4")).json()
    def_id = created["definition"]["def_id"]

    run = client.post("/api/v1/workflows-typed/runs",
                      json={"def_id": def_id}).json()["run"]
    assert run["status"] == "succeeded", run

    detail = client.get(f"/api/v1/workflows-typed/runs/{run['run_id']}").json()
    ledger = detail["node_io"]
    assert len(ledger) >= 3
    # 下游输入来自指定上游端口输出（数据真实传递）
    tr_io = next(e for e in ledger if e["node_id"] == "tr")
    assert tr_io["status"] == "succeeded"
    assert tr_io["input"]["data_in"]["count"] >= 1  # evidence_set 数据流入
    assert tr_io["input"]["data_in"]["instrument_id"] == "SZSE:000831"
    # attempt 账本不可变追加
    assert all(e["attempt"] >= 1 for e in ledger)


def test_branch_isolation(client):
    _seed_evidence(client, "公告一")
    _seed_evidence(client, "公告二")
    nodes = [
        {"key": "ev", "kind": "evidence"},
        {"key": "f1", "kind": "transform", "params": {"op": "latest"}},
        {"key": "f2", "kind": "transform", "params": {"op": "count"}},
        {"key": "out", "kind": "output"},
    ]
    edges = [
        {"from": "ev", "to": "f1", "source_port": "evidence_set", "target_port": "data_in"},
        {"from": "ev", "to": "f2", "source_port": "evidence_set", "target_port": "data_in"},
        {"from": "f1", "to": "out", "source_port": "data_out", "target_port": "metrics_in"},
        {"from": "f2", "to": "out", "source_port": "data_out", "target_port": "metrics_in"},
    ]
    created = client.post("/api/v1/workflows-typed/definitions",
                          json=_def_payload(nodes, edges, "branch-g4")).json()
    def_id = created["definition"]["def_id"]
    run = client.post("/api/v1/workflows-typed/runs", json={"def_id": def_id}).json()["run"]
    assert run["status"] == "succeeded", run

    detail = client.get(f"/api/v1/workflows-typed/runs/{run['run_id']}").json()
    ledger = detail["node_io"]
    f1 = next(e for e in ledger if e["node_id"] == "f1" and e["status"] == "succeeded")
    f2 = next(e for e in ledger if e["node_id"] == "f2" and e["status"] == "succeeded")
    # 两分支各自消费上游输出，参数不同 → 输出不同（互不覆盖）
    assert f1["output"]["data_out"]["op"] == "latest"
    assert f2["output"]["data_out"]["op"] == "count"


def test_failure_propagation_and_retry(client):
    # screening 引用不存在的经验卡 → 执行失败 → 下游 skipped（真实失败路径）
    nodes = [
        {"key": "sc", "kind": "screening", "params": {"card_id": "exp_missing000001"}},
        {"key": "out", "kind": "output"},
    ]
    edges = [{"from": "sc", "to": "out", "source_port": "candidates",
              "target_port": "metrics_in"}]
    created = client.post("/api/v1/workflows-typed/definitions",
                          json=_def_payload(nodes, edges, "fail-g4")).json()
    def_id = created["definition"]["def_id"]
    run = client.post("/api/v1/workflows-typed/runs", json={"def_id": def_id}).json()["run"]
    assert run["status"] == "failed"

    detail = client.get(f"/api/v1/workflows-typed/runs/{run['run_id']}").json()
    ledger = detail["node_io"]
    sc = next(e for e in ledger if e["node_id"] == "sc")
    assert sc["status"] == "failed"
    assert sc["attempt"] == 1
    out_node = detail["run"]["nodes"][0]
    out_row = next(n for n in detail["run"]["nodes"] if n["key"] == "out")
    assert out_row["status"] == "skipped"  # 失败传播

    # retry：失败节点重跑（attempt 2 落账本；卡不存在 → 仍 failed）
    retried = client.post(
        f"/api/v1/workflows-typed/runs/{run['run_id']}/control",
        json={"action": "retry"},
    ).json()["run"]
    assert retried["status"] == "failed"
    detail2 = client.get(f"/api/v1/workflows-typed/runs/{run['run_id']}").json()
    sc2 = next(e for e in detail2["node_io"]
               if e["node_id"] == "sc" and e["attempt"] == 2)
    assert sc2["status"] == "failed"


def test_control_states(client):
    nodes = [{"key": "e", "kind": "evidence"}, {"key": "out", "kind": "output"}]
    edges = [{"from": "e", "to": "out", "source_port": "evidence_set",
              "target_port": "metrics_in"}]
    created = client.post("/api/v1/workflows-typed/definitions",
                          json=_def_payload(nodes, edges, "ctrl-g4")).json()
    run = client.post("/api/v1/workflows-typed/runs",
                      json={"def_id": created["definition"]["def_id"]}).json()["run"]
    # succeeded 后 pause/cancel 拒绝
    r = client.post(f"/api/v1/workflows-typed/runs/{run['run_id']}/control",
                    json={"action": "pause"})
    assert r.status_code == 422
    r = client.post(f"/api/v1/workflows-typed/runs/{run['run_id']}/control",
                    json={"action": "cancel"})
    assert r.status_code == 422
    # 未知 action
    r = client.post(f"/api/v1/workflows-typed/runs/{run['run_id']}/control",
                    json={"action": "teleport"})
    assert r.status_code == 422
