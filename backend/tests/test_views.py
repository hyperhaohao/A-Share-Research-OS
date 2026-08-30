"""UX Foundation — UI Read Models（评审 §12-§16）.

验收：
  - GET /views/watchlist 一次返回卡片全量（identity/quote/research/report/
    prediction/monitor），前端不再串多个 API 拼装；
  - GET /views/instruments/{id}/overview 一次返回工作台总览；
  - 纯只读投影：不写任何业务表。
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
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _research_flow(client, monkeypatch):
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
    monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
    body = client.post("/api/v1/pipeline/run?instrument=000831&run_id=run_views0001")
    assert body.status_code == 202
    # watchlist add
    added = client.post("/api/v1/watchlist", json={"instrument": "000831"})
    assert added.status_code == 201
    return body.json()


def test_watchlist_view_aggregates_in_one_request(client, monkeypatch):
    _research_flow(client, monkeypatch)
    resp = client.get("/api/v1/views/watchlist")
    assert resp.status_code == 200
    cards = resp.json()["results"]
    assert len(cards) == 1
    card = cards[0]
    # identity: business name, not raw instrument id
    assert card["instrument"]["name"] == "中国稀土"
    assert card["instrument"]["code"] == "000831"
    assert card["instrument"]["exchange"] == "SZSE"
    # quote from the pinned evidence
    assert card["quote"]["price"] == 24.83
    # research state
    assert card["research"]["confidence"] is not None
    assert card["research"]["support_balance"] is not None  # P0-09: support balance, not vote
    # report exists with its own section
    assert card["report"]["report_id"]
    # prediction section (absent — none created) is an explicit null
    assert card["prediction"] is None
    assert card["monitor"] is None


def test_experience_cards_view_rows(client, monkeypatch):
    _research_flow(client, monkeypatch)
    body = client.post(
        "/api/v1/experience-cards/from-report",
        json={"report_id": client.get("/api/v1/reports?limit=1").json()["results"][0]["report_id"]},
    )
    assert body.status_code == 201, body.text
    card = body.json()["card"]

    resp = client.get("/api/v1/views/experience-cards")
    assert resp.status_code == 200
    rows = resp.json()["results"]
    row = next(r for r in rows if r["card_id"] == card["card_id"])
    assert row["title"] == card["title"]
    assert row["status"] == "REFINED"
    assert row["validation_count"] == 0
    assert row["source_report_id"] == card["source_report_id"]


def test_instrument_overview_view_aggregates(client, monkeypatch):
    _research_flow(client, monkeypatch)
    resp = client.get("/api/v1/views/instruments/SZSE:000831/overview")
    assert resp.status_code == 200
    ov = resp.json()["overview"]
    assert ov["instrument"]["name"] == "中国稀土"
    assert ov["quote"]["price"] == 24.83
    assert ov["research"]["support_balance"] is not None
    assert ov["data_quality"]["evidence_count"] > 0
    assert ov["report"]["report_id"]
    # catalysts/risks may be empty on the mocked flow but the sections exist
    assert isinstance(ov["catalysts"], list)
    assert isinstance(ov["risks"], list)


def test_overview_unknown_instrument_is_404(client):
    resp = client.get("/api/v1/views/instruments/SZSE:999999/overview")
    assert resp.status_code == 404


def test_command_center_report_library_continuous_prediction_views(client, monkeypatch):
    _research_flow(client, monkeypatch)

    cc = client.get("/api/v1/views/command-center").json()["view"]
    assert "running_runs" in cc and "recent_runs" in cc
    assert "current_plan" in cc and "recent_plans" in cc
    assert "names" in cc and cc["generated_at"]
    # 000831 succeeded run lands in recent_runs with a business name available
    assert any(r["instrument_id"] == "SZSE:000831" for r in cc["recent_runs"])
    assert cc["names"]["SZSE:000831"]["name"] == "中国稀土"

    lib = client.get("/api/v1/views/report-library").json()
    assert lib["count"] >= 1
    row = lib["results"][0]
    assert row["name"] == "中国稀土"
    assert row["judgment"] == "up"

    tasks = client.get("/api/v1/views/continuous-research").json()
    assert tasks["count"] == 0  # none created in this flow

    preds = client.get("/api/v1/views/prediction-review").json()
    assert preds["count"] == 0
    assert preds["kpi"]["direction_accuracy"] is None
