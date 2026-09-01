"""F5 — 帷幄 Event Foundation（第三轮整改任务书 §8.3/§8.4）.

覆盖：
  - 事件 Envelope（§8.3 全键）+ sequence 单调递增 + append-only；
  - user_message / plan_created / assistant_message / step_* / tool_* /
    run_* 事件在真实计划执行链上出现，tool_call↔tool_result 经
    correlation_id 关联，artifact_created 携 artifact_ids；
  - Replay：events?after_sequence=N（纯读）；Snapshot：session snapshot；
  - Live SSE：id/event/data 帧、replay、heartbeat、断线重连不丢不重；
  - 敏感字段不进明文事件；Session 隔离（B 会话看不到 A 会话事件）。
"""

from __future__ import annotations

import time

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


@pytest.fixture()
def mocked_sources(monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)


def _await_plan(client, plan_id: str, *, timeout_s: float = 60.0) -> dict:
    deadline = timeout_s
    while deadline > 0:
        plan = client.get(f"/api/v1/command/plans/{plan_id}").json()["plan"]
        if plan["status"] != "running":
            return plan
        time.sleep(0.1)
        deadline -= 0.1
    raise AssertionError(f"plan did not finish: {plan}")


def _new_session(client) -> str:
    return client.post("/api/v1/command/sessions").json()["session"]["session_id"]


def _events(client, sid: str, after: int = 0) -> dict:
    return client.get(
        f"/api/v1/command/sessions/{sid}/events",
        params={"after_sequence": after},
    ).json()


# ── Envelope + sequence + 事件链 ─────────────────────────────────────────────


def test_event_envelope_and_execution_chain(client, mocked_sources):
    sid = _new_session(client)
    turn = client.post(
        f"/api/v1/command/sessions/{sid}/turns",
        json={"text": "研究000831最近是否有资产重组迹象"},
    ).json()
    plan_id = turn["plan"]["plan_id"]
    plan = _await_plan(client, plan_id)
    assert plan["status"] == "completed", plan

    out = _events(client, sid)
    evs = out["results"]
    assert out["count"] == len(evs) >= 6

    # §8.3 Envelope 全键
    envelope_keys = {
        "event_id", "session_id", "sequence", "event_type", "created_at",
        "correlation_id", "plan_id", "task_id", "status", "payload",
        "artifact_ids", "provenance",
    }
    for ev in evs:
        assert envelope_keys <= set(ev), ev["event_type"]
        assert ev["payload"].get("schema_version") == "v1"

    # sequence 单调递增、无重复
    seqs = [e["sequence"] for e in evs]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)
    assert seqs[0] == 1

    # 事件链：会话 → 用户消息 → 计划 → 步骤/工具 → 完成
    types = [e["event_type"] for e in evs]
    assert types[0] == "session_created"
    assert "user_message" in types
    assert "plan_created" in types
    assert "assistant_message" in types
    assert "step_started" in types
    assert "tool_call" in types
    assert "tool_result" in types
    assert "run_completed" in types
    assert types[-1] == "run_completed"

    # tool_call ↔ tool_result 通过 correlation_id 关联
    calls = [e for e in evs if e["event_type"] == "tool_call"]
    results = {e["correlation_id"] for e in evs if e["event_type"] == "tool_result"}
    for call in calls:
        assert call["correlation_id"] in results, call

    # plan_created 的 plan_id 落事件；artifact_created 携带真实 artifact ids
    plan_created = next(e for e in evs if e["event_type"] == "plan_created")
    assert plan_created["plan_id"] == plan_id
    artifacts = [e for e in evs if e["event_type"] == "artifact_created"]
    if artifacts:
        for e in artifacts:
            assert e["artifact_ids"], "artifact event must reference artifacts"


# ── Replay：after_sequence 断点续传（纯读） ──────────────────────────────────


def test_replay_after_sequence(client, mocked_sources):
    sid = _new_session(client)
    client.post(
        f"/api/v1/command/sessions/{sid}/turns",
        json={"text": "研究000831最近是否有资产重组迹象"},
    )
    out = _events(client, sid)
    all_events = out["results"]
    assert len(all_events) >= 2

    mid = all_events[0]["sequence"]
    rest = _events(client, sid, after=mid)["results"]
    assert [e["sequence"] for e in rest] == [e["sequence"] for e in all_events[1:]]
    assert all(e["sequence"] > mid for e in rest)


# ── Live SSE：replay / heartbeat / 断线重连不丢不重 ──────────────────────────


def test_sse_replay_and_reconnect(client, mocked_sources):
    sid = _new_session(client)
    turn = client.post(
        f"/api/v1/command/sessions/{sid}/turns",
        json={"text": "研究000831最近是否有资产重组迹象"},
    ).json()
    _await_plan(client, turn["plan"]["plan_id"])

    # 全量重放：帧格式 id/event/data，sequence 单调
    frames: list[dict] = []
    with client.stream(
        "GET",
        f"/api/v1/command/sessions/{sid}/stream",
        params={"after_sequence": 0, "max_seconds": 8},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        saw_heartbeat = False
        for line in resp.iter_lines():
            if line.startswith("id: "):
                frames.append({"id": int(line[4:])})
            elif line.startswith("event: ") and frames:
                frames[-1]["event"] = line[7:]
            elif line == ": heartbeat":
                saw_heartbeat = True
                if len(frames) >= 5:
                    break
            if len(frames) >= 5 and saw_heartbeat:
                break
    assert len(frames) >= 5
    ids = [f["id"] for f in frames]
    assert ids == sorted(ids)

    # 断线重连：以最后 sequence 续传 → 不重复
    last = ids[-1]
    with client.stream(
        "GET",
        f"/api/v1/command/sessions/{sid}/stream",
        params={"after_sequence": last, "max_seconds": 5},
    ) as resp:
        replayed = []
        for line in resp.iter_lines():
            if line.startswith("id: "):
                replayed.append(int(line[4:]))
            if replayed:
                break
            if line == ": heartbeat":
                # 空闲后心跳到达且无重复事件帧 → 断言完成
                break
    fresh = [i for i in replayed if i <= last]
    assert fresh == [], f"reconnect replayed old events: {fresh}"


# ── 敏感字段脱敏 + Session 隔离 ──────────────────────────────────────────────


def test_payload_sanitization_and_session_isolation(client):
    from app.application.command_events import append_event

    sid_a = _new_session(client)
    sid_b = _new_session(client)

    factory = client.app.state._test_factory
    session = factory()
    try:
        ev = append_event(
            session, sid_a, "assistant_message",
            payload={"api_key": "sk-secret", "note": "hello", "token": "t-1"},
        )
        session.commit()
    finally:
        session.close()

    assert ev["payload"]["api_key"] == "[redacted]"
    assert ev["payload"]["token"] == "[redacted]"
    assert ev["payload"]["note"] == "hello"

    # 隔离：B 会话事件流不含 A 会话事件
    out_b = _events(client, sid_b)
    assert all(e["session_id"] == sid_b for e in out_b["results"])
    assert all(e["sequence"] == 1 for e in out_b["results"])  # 只有 session_created

    out_a = _events(client, sid_a)
    assert all(e["session_id"] == sid_a for e in out_a["results"])
    assert any(e["payload"].get("note") == "hello" for e in out_a["results"])


# ── append-only：无覆写/删除路径 ─────────────────────────────────────────────


def test_events_append_only_no_mutation_paths(client):
    sid = _new_session(client)
    # PUT/DELETE/PATCH 事件端点不存在（append-only，§8.3）
    assert (
        client.put(f"/api/v1/command/sessions/{sid}/events", json={}).status_code == 405
    )
    assert (
        client.delete(f"/api/v1/command/sessions/{sid}/events").status_code == 405
    )
    # 未知事件类型拒绝
    from app.application.command_events import append_event

    factory = client.app.state._test_factory
    session = factory()
    try:
        with pytest.raises(ValueError):
            append_event(session, sid, "hacked_event", payload={})
    finally:
        session.close()


# ── Snapshot：刷新恢复数据源 ─────────────────────────────────────────────────


def test_session_snapshot(client, mocked_sources):
    sid = _new_session(client)
    client.post(
        f"/api/v1/command/sessions/{sid}/turns",
        json={"text": "研究000831最近是否有资产重组迹象"},
    )
    snap = client.get(f"/api/v1/command/sessions/{sid}/snapshot").json()
    assert snap["session"]["session_id"] == sid
    assert snap["latest_sequence"] >= 1
    assert snap["turns"], "turns present for refresh recovery"
    assert snap["plans"], "plans present for refresh recovery"
    # 未知会话 404
    assert (
        client.get("/api/v1/command/sessions/ses_missing000000/snapshot").status_code
        == 404
    )
