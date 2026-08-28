"""F0 — Pipeline Integrity verification tests (第二轮整改 §4).

F0.1  FULL_RESEARCH → ResearchPipeline.run(); PERIODIC_FULL_RESEARCH → same
F0.2  AnalysisQualityGate runs AFTER claims exist (timing)
F0.3  Citation gate: report citations ⊆ snapshot evidence
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.scheduler.scheduler import HANDLERS, Scheduler
from app.scheduler.tasks import TaskRepository, TaskType
from app.sources.runtime import reset_runtime
from app.storage.orm import Base, ResearchRunORM
from tests.test_research_api import RAW_OK

def _pit_as_of() -> str:
    """Dynamic PIT timestamp: one hour in the future so freshly collected
    evidence (available_time = now) is always visible (time-bomb fix)."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()



@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    STATE["factory"] = factory

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


STATE: dict = {}


def _canned(monkeypatch):
    """All sources canned: quote + announcements + financials + news."""
    zyzb = (
        '{"data":[{"REPORT_DATE":"2026-06-30 00:00:00","REPORT_TYPE":"中报",'
        '"NOTICE_DATE":"2026-08-15 00:00:00","CURRENCY":"CNY",'
        '"EPSJB":35.57,"BPS":200.99,"ROEJQ":16.75,'
        '"TOTALOPERATEREVE":92278072083.21,"PARENTNETPROFIT":44516880421.86,'
        '"XSMLL":89.55}]}'
    )
    zcfzb = '{"data":[{"TOTAL_ASSETS":3.1e11,"TOTAL_LIABILITIES":4.5e10}]}'
    ann = (
        '{"data":{"list":[{"art_code":"AN1","title":"2026年半年度报告",'
        '"notice_date":"2026-08-15 00:00:00"}]}}'
    )
    industry = (
        '{"jbzl":[{"SECURITY_NAME_ABBR":"贵州茅台",'
        '"EM2016":"食品饮料-饮料-白酒"}]}'
    )
    news = (
        'cb({"result":{"cmsArticleWebOld":[{"date":"2026-08-28 08:18:00",'
        '"code":"n1","title":"白酒动态","content":"x"}]}})'
    )
    bars = ",".join(
        f"2026-08-{i+1:02d},{100+i}.0,{101+i}.0,{102+i}.0,{99+i}.0,1000,1e5,1.0,1.0,1.0,0.5"
        for i in range(9)
    )
    kline = '{"data":{"code":"600519","klines":[' + ",".join(f'"{b}"' for b in bars) + ']}}'

    def fake_get(url, params=None, data=None, headers=None, timeout=10.0,
                 jsonp=False, encoding=None):
        if "gtimg" in url:
            return httpx.Response(200, content=RAW_OK.encode("gbk"))
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
        if "kline/get" in url:
            return httpx.Response(200, content=kline.encode("utf-8"))
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(httpx, "get", fake_get)


class TestF0_1_FullResearchUnification:
    def test_handler_registry_binds_full_pipeline(self):
        """PERIODIC_FULL_RESEARCH → run_full_research_task → ResearchPipeline."""
        handler = HANDLERS[TaskType.PERIODIC_FULL_RESEARCH]
        assert handler.__name__ == "run_full_research_task"
        # single full-research implementation: it goes through the pipeline
        import inspect

        from app.services.pipeline import ResearchPipeline

        src = inspect.getsource(handler)
        assert "ResearchPipeline" in src

    def test_periodic_task_creates_full_run(self, client, monkeypatch):
        """A PERIODIC_FULL_RESEARCH task produces a full ResearchRun with
        analysts' claims (not the old thin market→report path)."""
        _canned(monkeypatch)
        client, factory = client, STATE["factory"]

        task = client.post(
            "/api/v1/tasks",
            json={"instrument": "600519",
                  "task_type": "periodic_full_research",
                  "schedule": "interval:0"},
        ).json()["task"]
        tick = client.post("/api/v1/tasks/scheduler/tick").json()
        assert task["task_id"] in tick["claimed"]
        assert task["task_id"] in tick["succeeded"]

        session = factory()
        try:
            runs = session.scalars(select(ResearchRunORM)).all()
            assert runs, "periodic full research must create a ResearchRun"
            # the full pipeline creates analyst claims — the thin path didn't
            from app.storage.research_orm import ClaimORM

            claims = session.scalars(select(ClaimORM)).all()
            assert claims, "full pipeline creates analyst claims"
        finally:
            session.close()

    def test_monitor_full_decision_runs_pipeline(self, client, monkeypatch):
        """Monitor FULL_RESEARCH → a NEW ResearchRun via the pipeline."""
        client, factory = client, STATE["factory"]
        _canned(monkeypatch)

        # seed: collect + snapshot + report chain (small move → delta first)
        client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
        client.post("/api/v1/monitor/run", params={"instrument": "600519"})

        # big move (≥5%) → FULL → pipeline creates a new ResearchRun
        monkeypatch.setattr(httpx, "get", lambda url, timeout: httpx.Response(
            200, content=RAW_OK.replace("1648.00~1651.00", "1900.00~1651.00", 1).encode("gbk")
        ))
        client.post("/api/v1/monitor/run", params={"instrument": "600519"})

        session = factory()
        try:
            runs = session.scalars(
                select(ResearchRunORM).order_by(ResearchRunORM.as_of)
            ).all()
            full_runs = [r for r in runs if r.run_type == "full_research"]
            assert full_runs, "FULL decision must create a full research run"
        finally:
            session.close()


class TestF0_2_AnalysisGateTiming:
    def test_analysis_gate_sees_pipeline_claims(self, client, monkeypatch):
        client, factory = client, STATE["factory"]
        _canned(monkeypatch)
        outcome = client.post("/api/v1/pipeline/run", params={"instrument": "600519"}).json()

        # the analysis gate event fired AFTER claims_compiled
        events = outcome["events"]
        names = [e["event"] for e in events]
        assert names.index("claims_compiled") < max(
            i for i, e in enumerate(events)
            if e["event"] == "quality_gate" and e.get("gate") == "analysis"
        )
        analysis_gates = [
            e for e in outcome["events"]
            if e["event"] == "quality_gate" and e.get("gate") == "analysis"
        ]
        assert analysis_gates  # ran

        # and the persisted analysis-gate result saw the real claims
        session = factory()
        try:
            from app.services.quality_service import QualityService

            service = QualityService(session)
            history = service.history(outcome["snapshot_id"])
            analysis = [h for h in history if h["gate"] == "analysis_quality"]
            assert analysis
        finally:
            session.close()

    def test_dangling_claim_fails_analysis_gate(self, client, monkeypatch):
        """A claim citing non-existent evidence must FAIL the analysis gate."""
        client, factory = client, STATE["factory"]
        _canned(monkeypatch)
        client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": "600519", "as_of": _pit_as_of()},
        ).json()["snapshot"]

        from app.domain.research import Claim, ClaimType, FactStatus
        from app.services.quality_service import QualityService
        from app.storage.research_repo import ResearchRepository

        session = factory()
        try:
            # simulate post-hoc corruption: insert the claim row directly
            # (bypassing the repository's write-time integrity check) exactly
            # as a DB-level corruption or future bug would
            from app.storage.research_orm import ClaimORM
            from datetime import datetime, timezone as _tz

            session.add(
                ClaimORM(
                    claim_id="clm_corrupted000000000",
                    instrument_id="SSE:600519",
                    snapshot_id=snapshot["snapshot_id"],
                    statement="引用不存在证据的损坏主张",
                    claim_type="fundamental_fact",
                    supporting_evidence_refs_json=["ev_corrupted"],
                    opposing_evidence_refs_json=[],
                    fact_status="confirmed_fact",
                    confidence=0.9,
                    status="proposed",
                    created_at=datetime.now(_tz.utc),
                )
            )
            session.flush()

            gate = QualityService(session).run_analysis_gate(snapshot["snapshot_id"])
            assert gate.status.value == "fail"
            assert any(f.code == "analysis.dangling_reference" for f in gate.findings)
        finally:
            session.close()


class TestF0_3_CitationGate:
    def test_citation_universe_is_snapshot(self, client, monkeypatch):
        client, factory = client, STATE["factory"]
        _canned(monkeypatch)
        collected = client.post("/api/v1/evidence/collect", params={"instrument": "600519"}).json()
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": "600519", "as_of": _pit_as_of()},
        ).json()["snapshot"]
        evidence_id = collected["evidence"][0]["evidence_id"]
        claim = client.post(
            "/api/v1/claims",
            json={
                "instrument_id": "SSE:600519",
                "snapshot_id": snapshot["snapshot_id"],
                "statement": "估值低位（快照内引用）",
                "claim_type": "valuation_assessment",
                "supporting_evidence_refs": [evidence_id],
                "fact_status": "confirmed_fact",
                "confidence": 0.8,
            },
        ).json()["claim"]
        client.post(
            "/api/v1/theses",
            json={
                "instrument_id": "SSE:600519",
                "snapshot_id": snapshot["snapshot_id"],
                "title": "估值修复",
                "description": "低位",
                "supporting_claims": [claim["claim_id"]],
                "confidence": 0.8,
                "risks": ["消费疲软"],
            },
        )

        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
        ).json()["report"]
        # gate input uses snapshot universe; the report's citation is inside it
        assert report["gate_status"] in ("pass", "warn")

        # now forge a report citation outside the snapshot via a new compile
        # on the same snapshot but with a corrupted citation set — simulate by
        # a direct gate evaluation
        from app.domain.quality import FinalReportQualityGate, ReportGateInput

        forged = ReportGateInput(
            known_evidence_ids=tuple(snapshot["evidence_ids"]),
            citations=(f"{evidence_id}", "ev_outside_snapshot"),
            claim_support={"clm_1": (evidence_id,)},
            risk_section=True,
            data_quality_section=True,
            disclaimer=True,
        )
        result = FinalReportQualityGate().evaluate(forged)
        assert result.status.value == "fail"
        assert any(f.code == "report.invalid_citation" for f in result.findings)
