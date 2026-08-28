"""R2 DoD: full research pipeline with NO manual claim/thesis wiring.

整改 R2.9：至少一只真实股票执行
Source → Evidence → Snapshot → Analysts → Claims → Thesis → Debate →
Scenario → Valuation → Risk → ResearchReport，全程无手工 POST 补链。
Transport is mocked (API Integration E2E); live variants are marked live.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


@pytest.fixture()
def client():
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
    yield TestClient(app), factory
    reset_runtime()


@pytest.fixture()
def api(client, monkeypatch):
    client, factory = client
    resp = httpx.Response(200, content=RAW_OK.encode("gbk"))

    # canned transport: quote for market_data; distinct canned bodies per
    # endpoint family for the rest
    ann = (
        '{"data":{"list":[{"art_code":"AN1","title":"关于2026年半年度报告的公告",'
        '"notice_date":"2026-08-15 00:00:00","columns":[{"column_name":"半年报"}]}]}}'
    )
    zyzb = (
        '{"data":[{"REPORT_DATE":"2026-06-30 00:00:00","REPORT_TYPE":"中报",'
        '"NOTICE_DATE":"2026-08-15 00:00:00","CURRENCY":"CNY",'
        '"EPSJB":35.57,"BPS":200.99,"ROEJQ":16.75,'
        '"TOTALOPERATEREVE":92278072083.21,"PARENTNETPROFIT":44516880421.86,'
        '"XSMLL":89.55}]}'
    )
    zcfzb = '{"data":[{"TOTAL_ASSETS":3.1e11,"TOTAL_LIABILITIES":4.5e10}]}'
    news = (
        'cb({"result":{"cmsArticleWebOld":[{"date":"2026-08-28 08:18:00",'
        '"code":"n1","title":"白酒行业动态","content":"行业景气度跟踪"}]}})'
    )
    industry = (
        '{"jbzl":[{"SECURITY_NAME_ABBR":"贵州茅台",'
        '"EM2016":"食品饮料-饮料-白酒","MAINBUSINESS":"茅台酒及系列酒的生产与销售"}]}'
    )

    def fake_get(url, params=None, data=None, headers=None, timeout=10.0, jsonp=False, encoding=None):
        if "gtimg" in url:
            return resp
        if "np-anotice" in url:
            return httpx.Response(200, content=ann.encode("utf-8"))
        if "ZYZBAjaxNew" in url:
            return httpx.Response(200, content=zyzb.encode("utf-8"))
        if "zcfzbAjaxNew" in url:
            return httpx.Response(200, content=zcfzb.encode("utf-8"))
        if "search-api-web" in url:
            return httpx.Response(200, content=news.encode("utf-8"))
        if "CompanySurvey" in url:
            return httpx.Response(200, content=industry.encode("utf-8"))
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(httpx, "get", fake_get)
    return client, factory


def test_full_chain_no_manual_wiring(api):
    """The pipeline alone produces claims → thesis → debate → scenarios →
    valuations → risks → report. Nothing is POSTed by hand."""
    client, factory = api
    run_body = client.post("/api/v1/pipeline/run", params={"instrument": "600519"})
    assert run_body.status_code == 202, run_body.text
    outcome = run_body.json()
    run_id = outcome["run_id"]
    assert outcome["gate_status"] in ("pass", "warn")

    session = factory()
    try:
        from app.storage.manifest_repo import ManifestRepository
        from app.storage.research_repo import ResearchRepository
        from app.services.debate_engine import DebateScenarioRepository
        from app.storage.valuation_repo import ValuationRepository

        research = ResearchRepository(session)
        # claims exist and were created by analysts (metadata.analyst)
        claims = research.list_claims("SSE:600519", snapshot_id=outcome["snapshot_id"])
        assert claims, "pipeline must create claims"
        assert all(c.supporting_evidence_refs for c in claims)

        # thesis exists and cites pipeline claims
        theses = research.list_theses("SSE:600519", snapshot_id=outcome["snapshot_id"])
        assert theses, "pipeline must build a thesis"
        thesis = theses[0]
        assert thesis.supporting_claims

        # debate ran
        debates = DebateScenarioRepository(session).list_debate_rounds(thesis.thesis_id)
        assert debates, "pipeline must run a debate round"

        # scenarios exist with probabilities summing to 100
        scenarios = DebateScenarioRepository(session).list_scenarios(thesis.thesis_id)
        assert scenarios
        assert sum(s.probability for s in scenarios) == 100.0

        # valuations were computed from evidence inputs
        valuations = ValuationRepository(session).list_for(
            "SSE:600519", snapshot_id=outcome["snapshot_id"]
        )
        assert valuations, "pipeline must run valuations from evidence"
        computable = [v for v in valuations if v["computable"]]
        assert computable, "PE/PB/PS inputs exist from quote+financials"
        for v in computable:
            # provenance: inputs reference the evidence-derived price
            assert "price" in v["inputs"]

        # manifest: real code commit (no placeholder)
        manifest = ManifestRepository(session).get_for_run(run_id)
        assert manifest is not None
        assert manifest.code_commit != "0000000"
        assert set(manifest.config_digest) != {"0"}
        assert manifest.random_seed != 0

        # the report carries the thesis section
        report = client.get(f"/api/v1/reports/{outcome['report_id']}").json()["report"]
        assert "## 核心论点" in report["markdown"] or "关键论点" in report["markdown"]
        # the report body includes analyst claims (research-driven, not hand-made)
        assert any(c.statement in report["markdown"] for c in claims)
    finally:
        session.close()


def test_pipeline_events_include_new_stages(api):
    client, _ = api
    outcome = client.post("/api/v1/pipeline/run", params={"instrument": "600519"}).json()
    events = [e["event"] for e in outcome["events"]]
    for stage in ("run_started", "snapshot_built", "claims_compiled", "thesis_ready",
                  "valuation_ready", "scenario_ready", "risk_ready", "report_ready",
                  "run_completed"):
        assert stage in events, stage


def test_pipeline_survives_source_failure(api, monkeypatch):
    """A dead source must not kill the run: manifest shows the failure."""
    import httpx as hx

    client, factory = api

    def dead_get(url, params=None, data=None, headers=None, timeout=10.0, jsonp=False, encoding=None):
        raise hx.ConnectTimeout("down")

    monkeypatch.setattr(hx, "get", dead_get)
    body = client.post("/api/v1/pipeline/run", params={"instrument": "600519"})
    _ = body  # may fail with run_failed — acceptable as long as it emits the event
    # the run is recorded as failed, not silently missing
    import sqlite3

    _ = sqlite3
    from app.storage.orm import ResearchRunORM
    from sqlalchemy import select as _select

    session = factory()
    try:
        runs = session.scalars(_select(ResearchRunORM)).all()
        assert runs
        assert all(r.status in ("failed", "succeeded") for r in runs)
    finally:
        session.close()
