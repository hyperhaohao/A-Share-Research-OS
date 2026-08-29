"""V2 Phase B — ResearchCommander / ResearchPlan / ConversationSession.

验收（总纲 §40/§41/§42/§71/§87）：
  - 用户一句话 → 确定性解析 → ResearchPlan（左栏结构）→ 后台执行 →
    ReportVersion → Artifact（§42 闭环）；
  - 无法识别标的 → 显式拒绝回复（记录为 commander turn），绝不猜；
  - 预测意图 → 由最新报告 honest 推导，artifact generated_from 报告；
  - 计划失败 → 步骤级 error 落库（失败显形）。
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.services.commander import interpret_command
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


def _mock_sources(monkeypatch) -> None:
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)


def _await_plan(client, plan_id: str, *, timeout_s: float = 60.0) -> dict:
    import time

    deadline = timeout_s
    plan = None
    while deadline > 0:
        plan = client.get(f"/api/v1/command/plans/{plan_id}").json()["plan"]
        if plan["status"] != "running":
            return plan
        time.sleep(0.1)
        deadline -= 0.1
    raise AssertionError(f"plan did not finish: {plan}")


# -- deterministic interpreter --------------------------------------------------


def test_interpreter_parses_intent_schedule_and_code():
    interp = interpret_command("每天08:30持续研究000831")
    assert interp.intent == "continuous"
    assert interp.schedule == "daily:08:30"
    assert interp.instrument_hint == "000831"

    interp = interpret_command("预测000831未来20日")
    assert interp.intent == "prediction"
    assert interp.horizon == "20D"
    assert interp.instrument_hint == "000831"

    interp = interpret_command("研究中国稀土最近是否有资产重组迹象")
    assert interp.intent == "full_research"
    assert interp.matched_keyword == "研究"
    assert interp.instrument_hint is None  # registry name scan is session-bound

    interp = interpret_command("每30分钟自动研究600519")
    assert interp.intent == "continuous"
    assert interp.schedule == "interval:1800"

    assert interpret_command("今天天气不错").instrument_hint is None


# -- API: session + explicit refusal --------------------------------------------


def test_session_and_explicit_refusal(client):
    session = client.post("/api/v1/command/sessions").json()["session"]
    assert session["session_id"].startswith("ses_")

    outcome = client.post(
        f"/api/v1/command/sessions/{session['session_id']}/turns",
        json={"text": "今天天气不错"},
    )
    assert outcome.status_code == 202
    body = outcome.json()
    assert body["plan"] is None
    assert "无法" in body["reply"]["text"]

    detail = client.get(f"/api/v1/command/sessions/{session['session_id']}").json()
    roles = [t["role"] for t in detail["turns"]]
    assert roles == ["user", "commander"]
    assert detail["plans"] == []

    assert client.get("/api/v1/command/sessions/ses_missing0000").status_code == 404


# -- API: full research closed loop (§42) ----------------------------------------


def test_full_research_plan_flow(client, monkeypatch):
    _mock_sources(monkeypatch)
    session = client.post("/api/v1/command/sessions").json()["session"]

    outcome = client.post(
        f"/api/v1/command/sessions/{session['session_id']}/turns",
        json={"text": "研究000831最近的资产重组迹象"},
    )
    assert outcome.status_code == 202, outcome.text
    plan = outcome.json()["plan"]
    assert plan["title"].startswith("完整研究")
    assert [s["action"] for s in plan["steps"]] == [
        "resolve_instrument", "run_pipeline", "open_report",
    ]

    plan = _await_plan(client, plan["plan_id"])
    assert plan["status"] == "completed", plan
    assert plan["instrument_id"] == "SZSE:000831"
    assert plan["run_id"]
    by_action = {s["action"]: s for s in plan["steps"]}
    assert "中国稀土" in by_action["resolve_instrument"]["detail"]
    assert by_action["run_pipeline"]["detail"] == plan["run_id"]
    # the produced report artifact is referenced by the plan step (§41)
    artifact_ids = by_action["run_pipeline"]["artifact_ids"]
    assert len(artifact_ids) == 1
    artifact = client.get(f"/api/v1/artifacts/{artifact_ids[0]}").json()["artifact"]
    assert artifact["artifact_type"] == "report"
    assert "中国稀土" in artifact["title"]

    # conversation recorded both turns; commander turn references the plan
    detail = client.get(f"/api/v1/command/sessions/{session['session_id']}").json()
    assert detail["turns"][1]["plan_id"] == plan["plan_id"]
    assert detail["plans"][0]["plan_id"] == plan["plan_id"]

    # the plan's research run replay works (§37)
    replay = client.get(f"/api/v1/research-runs/{plan['run_id']}/events")
    assert replay.status_code == 200
    assert replay.json()["count"] > 0


def test_commander_refusal_records_no_plan(client):
    """A text that resolves a code but nothing else still plans research;
    only unresolvable text refuses (covered here via unknown name)."""
    session = client.post("/api/v1/command/sessions").json()["session"]
    outcome = client.post(
        f"/api/v1/command/sessions/{session['session_id']}/turns",
        json={"text": "研究不存在公司123456"},
    )
    assert outcome.status_code == 202
    body = outcome.json()
    # 123456 matches no A-share code prefix rules → explicit refusal
    assert body["plan"] is None
    assert "无法" in body["reply"]["text"]


# -- API: prediction from the latest report ---------------------------------------


def _seed_valuations(factory) -> None:
    from sqlalchemy import select

    from app.db import session_scope
    from app.domain.valuation import ValuationMethod, ValuationResult
    from app.storage.orm import SnapshotORM
    from app.storage.valuation_repo import ValuationIn, ValuationRepository

    with session_scope(factory) as session:
        snapshot = session.scalars(select(SnapshotORM)).first()
        assert snapshot is not None
        repo = ValuationRepository(session)
        for method, value in ((ValuationMethod.PE, 30.0), (ValuationMethod.PB, 27.314)):
            repo.save(
                ValuationResult(method=method, value=value, inputs_used={}, detail={}),
                ValuationIn(
                    instrument_id="SZSE:000831",
                    snapshot_id=snapshot.snapshot_id,
                    method=method,
                ),
            )


def test_prediction_plan_flow(client, monkeypatch):
    _mock_sources(monkeypatch)
    body = client.post("/api/v1/pipeline/run?instrument=000831").json()
    _seed_valuations(client.app.state._test_factory)

    session = client.post("/api/v1/command/sessions").json()["session"]
    outcome = client.post(
        f"/api/v1/command/sessions/{session['session_id']}/turns",
        json={"text": "预测000831未来5日"},
    )
    assert outcome.status_code == 202, outcome.text
    plan = outcome.json()["plan"]
    assert plan["title"].startswith("生成预测")

    plan = _await_plan(client, plan["plan_id"])
    assert plan["status"] == "completed", plan
    by_action = {s["action"]: s for s in plan["steps"]}
    prediction_step = by_action["create_prediction"]
    assert prediction_step["status"] == "ok"
    assert len(prediction_step["artifact_ids"]) == 1

    artifact = client.get(
        f"/api/v1/artifacts/{prediction_step['artifact_ids'][0]}"
    ).json()["artifact"]
    assert artifact["artifact_type"] == "prediction"
    lineage = client.get(f"/api/v1/artifacts/{artifact['artifact_id']}/lineage").json()
    upstream = {u["artifact_type"] for u in lineage["upstream"]}
    assert "report" in upstream


def test_prediction_plan_without_report_fails_honestly(client, monkeypatch):
    _mock_sources(monkeypatch)
    # no pipeline run, no report → create_prediction must fail with a
    # visible step error, plan marked failed
    session = client.post("/api/v1/command/sessions").json()["session"]
    outcome = client.post(
        f"/api/v1/command/sessions/{session['session_id']}/turns",
        json={"text": "预测000831"},
    )
    plan = _await_plan(client, outcome.json()["plan"]["plan_id"])
    assert plan["status"] == "failed"
    by_action = {s["action"]: s for s in plan["steps"]}
    step = by_action["create_prediction"]
    assert step["status"] == "failed"
    assert "no existing report" in step["error"]
