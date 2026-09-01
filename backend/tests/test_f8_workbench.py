"""F8 — 帷幄 Dynamic Workbench（第三轮整改任务书 §8.7）.

覆盖：
  - Artifact → 注册表页面受控 Handoff（page/route/title/payload 契约）；
  - 未映射 Artifact 类型 422 显形；page 白名单外 422（禁 URL 注入）；
  - 同 artifact 复用已开 Tab（不重复）；单激活模型；关闭激活次新；
  - 每会话独立 Tab 状态 + 刷新恢复；
  - Artifact 自动打开：计划执行产出 report → Workbench 自动出现报告 Tab
    （非仅链接）；
  - workbench_open_requested 事件入会话事件流。
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
    raise AssertionError("plan did not finish")


def _register_artifact(client, *, artifact_type: str, domain_type: str,
                       domain_id: str, title: str) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        from app.application.artifacts import ArtifactService

        art = ArtifactService(session).register(
            artifact_type=artifact_type,
            domain_type=domain_type,
            domain_id=domain_id,
            title=title,
            instrument_ids=("SZSE:000831",),
            created_by="test",
            route="/test",
        )
        session.commit()
        return art
    finally:
        session.close()


# ── Handoff 契约 + 白名单 + 复用 ─────────────────────────────────────────────


def test_artifact_handoff_and_tab_reuse(client):
    sid = client.post("/api/v1/command/sessions").json()["session"]["session_id"]
    artifact_id = _register_artifact(
        client, artifact_type="report", domain_type="Report",
        domain_id="rpt_test0000001", title="中国稀土 · 事件调查",
    )

    opened = client.post(
        f"/api/v1/command/sessions/{sid}/workbench/open",
        json={"artifact_id": artifact_id},
    )
    assert opened.status_code == 201, opened.text
    tab = opened.json()["tab"]
    # §8.7 Handoff 契约
    assert tab["page"] == "research-report"
    assert tab["route"] == "/reports/{report_id}"
    assert tab["payload"]["report_id"] == "rpt_test0000001"
    assert tab["payload"]["artifact_id"] == artifact_id
    assert tab["artifact_id"] == artifact_id
    assert tab["is_active"] is True

    # 同 artifact 再次打开 → 复用同一 Tab（不重复）
    again = client.post(
        f"/api/v1/command/sessions/{sid}/workbench/open",
        json={"artifact_id": artifact_id},
    ).json()["tab"]
    assert again["tab_id"] == tab["tab_id"]

    # 打开第二个 Tab → 单激活
    other = client.post(
        f"/api/v1/command/sessions/{sid}/workbench/open",
        json={"page": "thesis-center"},
    ).json()["tab"]
    assert other["is_active"] is True
    tabs = client.get(f"/api/v1/command/sessions/{sid}/workbench").json()["tabs"]
    actives = [t for t in tabs if t["is_active"]]
    assert len(actives) == 1
    assert actives[0]["tab_id"] == other["tab_id"]

    # 激活切换 + 关闭激活 Tab → 次新激活
    client.post(
        f"/api/v1/command/sessions/{sid}/workbench/{tab['tab_id']}/activate"
    )
    closed = client.delete(
        f"/api/v1/command/sessions/{sid}/workbench/{tab['tab_id']}"
    )
    assert closed.status_code == 200
    tabs = client.get(f"/api/v1/command/sessions/{sid}/workbench").json()["tabs"]
    assert all(t["tab_id"] != tab["tab_id"] for t in tabs)
    actives = [t for t in tabs if t["is_active"]]
    assert len(actives) == 1 and actives[0]["tab_id"] == other["tab_id"]


def test_page_whitelist_and_unmapped_artifact(client):
    sid = client.post("/api/v1/command/sessions").json()["session"]["session_id"]
    # 白名单外 page → 422（禁 URL 注入）
    bad = client.post(
        f"/api/v1/command/sessions/{sid}/workbench/open",
        json={"page": "http://evil.example"},
    )
    assert bad.status_code == 422
    assert bad.json()["error_code"] == "workbench.page_not_allowed"

    # 未映射 artifact 类型 → 422 显形
    from app.application.artifacts import ArtifactService

    factory = client.app.state._test_factory
    session = factory()
    try:
        unmapped = ArtifactService(session).register(
            artifact_type="source_health",
            domain_type="SourceHealth",
            domain_id="sh_0000000001",
            title="源健康",
            instrument_ids=(),
            created_by="test",
            route="/test",
        )
        session.commit()
    finally:
        session.close()
    opened = client.post(
        f"/api/v1/command/sessions/{sid}/workbench/open",
        json={"artifact_id": unmapped},
    )
    assert opened.status_code == 422
    assert opened.json()["error_code"] == "workbench.page_unmapped"


def test_session_isolation_and_refresh_recovery(client):
    sid_a = client.post("/api/v1/command/sessions").json()["session"]["session_id"]
    sid_b = client.post("/api/v1/command/sessions").json()["session"]["session_id"]

    client.post(
        f"/api/v1/command/sessions/{sid_a}/workbench/open",
        json={"page": "thesis-center"},
    )
    # B 会话没有 A 的 Tab（多会话不串线）
    tabs_b = client.get(f"/api/v1/command/sessions/{sid_b}/workbench").json()["tabs"]
    assert tabs_b == []
    # A 刷新恢复
    tabs_a = client.get(f"/api/v1/command/sessions/{sid_a}/workbench").json()["tabs"]
    assert len(tabs_a) == 1 and tabs_a[0]["page"] == "thesis-center"


# ── Artifact 自动打开（真实计划执行产出 report） ─────────────────────────────


def test_artifact_auto_open_on_plan_completion(client, mocked_sources):
    sid = client.post("/api/v1/command/sessions").json()["session"]["session_id"]
    turn = client.post(
        f"/api/v1/command/sessions/{sid}/turns",
        json={"text": "研究000831最近是否有资产重组迹象"},
    ).json()
    _await_plan(client, turn["plan"]["plan_id"])

    tabs = client.get(f"/api/v1/command/sessions/{sid}/workbench").json()["tabs"]
    report_tabs = [t for t in tabs if t["page"] == "research-report"]
    assert report_tabs, "plan report artifact must auto-open a workbench tab"
    assert report_tabs[0]["payload"].get("report_id")

    # 事件流含 workbench_open_requested（§8.7 → §8.3 事件协议贯通）
    evs = client.get(
        f"/api/v1/command/sessions/{sid}/events", params={"after_sequence": 0}
    ).json()["results"]
    opens = [e for e in evs if e["event_type"] == "workbench_open_requested"]
    assert opens, "workbench open must be visible in event stream"
