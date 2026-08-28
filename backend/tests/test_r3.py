"""R3 tests: quant engine (fixed numbers), delta research, narrative layer."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.quant.engine import Bar, factor_snapshot, max_drawdown, run_backtest
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


class TestQuantEngine:
    """Fixed-number backtest math (整改 R3.5)."""

    def _bars(self, closes: list[float]) -> list[Bar]:
        return [
            Bar(date=f"2026-08-{i+1:02d}", open=c, close=c, high=c, low=c, volume=1000)
            for i, c in enumerate(closes)
        ]

    def test_upward_series_invested_and_positive(self):
        closes = [100.0] * 5 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
        result = run_backtest(self._bars(closes), momentum_window=5)
        # momentum turns positive after day 6; strategy rides the uptrend
        assert result["strategy_total_return_pct"] > 0
        assert result["invested_days"] >= 1
        # in a monotonic uptrend, long/flat matches buy&hold once invested
        assert result["buyhold_total_return_pct"] == pytest.approx(7.0, abs=0.01)

    def test_flat_series_zero_activity(self):
        closes = [100.0] * 10
        result = run_backtest(self._bars(closes), momentum_window=5)
        # momentum exactly 0 → not > 0 → never invested
        assert result["invested_days"] == 0
        assert result["strategy_total_return_pct"] == 0.0

    def test_max_drawdown_known_value(self):
        # equity curve 1.0 → 1.1 → 0.99 → 1.05: drawdown = (0.99/1.1 - 1) = -10%
        assert max_drawdown([1.0, 1.1, 0.99, 1.05]) == pytest.approx(-10.0)

    def test_factor_snapshot(self):
        closes = [float(i) for i in range(1, 31)]  # 1..30
        factors = factor_snapshot(self._bars(closes))
        assert factors["momentum_5d"] == pytest.approx(30 / 25 - 1)
        assert factors["momentum_20d"] == pytest.approx(30 / 10 - 1)
        assert factors["volatility_20d"] is not None

    def test_insufficient_bars_rejected(self):
        with pytest.raises(ValueError):
            run_backtest(self._bars([100.0, 101.0]))


class TestQuantInPipeline:
    @pytest.fixture()
    def client(self):
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

    def _canned(self, monkeypatch, kline_bars: str):
        def fake_get(url, params=None, data=None, headers=None, timeout=10.0,
                     jsonp=False, encoding=None):
            if "gtimg" in url:
                return httpx.Response(200, content=RAW_OK.encode("gbk"))
            if "kline/get" in url:
                return httpx.Response(
                    200, content=kline_bars.encode("utf-8")
                )
            if "np-anotice" in url:
                return httpx.Response(200, content=b'{"data":{"list":[]}}')
            if "ZYZBAjaxNew" in url or "zcfzbAjaxNew" in url:
                return httpx.Response(200, content=b'{"data":[]}')
            if "search-api-web" in url:
                return httpx.Response(200, content=b'cb({"result":{"cmsArticleWebOld":[]}})')
            if "CompanySurvey" in url:
                return httpx.Response(200, content=b'{"jbzl":[]}')
            raise AssertionError(f"unexpected url {url}")

        monkeypatch.setattr(httpx, "get", fake_get)

    def test_quant_brief_in_pipeline(self, client, monkeypatch):
        client, factory = client
        # 8 rising closes → momentum strategy invests; each bar is its own
        # comma-joined string in the klines list (API shape)
        bars = [
            f"2026-08-{i+1:02d},{100+i}.0,{100+i+1}.0,{100+i+2}.0,{99+i}.0,"
            f"1000,{100000}.0,1.0,{1.0},1.0,0.5"
            for i in range(8)
        ]
        body = '{"data":{"code":"600519","klines":[' + ",".join(f'"{b}"' for b in bars) + ']}}'
        self._canned(monkeypatch, body)

        outcome = client.post("/api/v1/pipeline/run", params={"instrument": "600519"}).json()
        assert outcome["gate_status"] in ("pass", "warn", "fail")
        quant_events = [
            e for e in outcome["events"]
            if e["event"] == "analyst_progress" and e.get("analyst") == "quant"
        ]
        assert quant_events
        assert quant_events[-1].get("status") == "ok", quant_events[-1]
        metrics = quant_events[-1]["metrics"]
        assert metrics["invested_days"] >= 1
        assert metrics["n_days"] == 7

        # the quant brief exists in the research state
        session = factory()
        try:
            from app.storage.agent_repo import AgentRepository

            briefs = AgentRepository(session).list_briefs(outcome["snapshot_id"])
            quant_briefs = [b for b in briefs if b.analyst_type.value == "quant"]
            assert quant_briefs
            assert quant_briefs[0].conclusions
        finally:
            session.close()


class TestDeltaResearch:
    @pytest.fixture()
    def client(self):
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

    def test_delta_creates_new_report_version(self, client, monkeypatch):
        """Monitor DELTA decision via the scheduler → new ReportVersion (R3.7)."""
        client, factory = client
        monkeypatch.setattr(httpx, "get", lambda url, timeout: httpx.Response(
            200, content=RAW_OK.encode("gbk")
        ))
        client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": "600519", "as_of": "2026-08-01T15:00:00+00:00"},
        ).json()["snapshot"]
        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
        ).json()["report"]
        client.post(
            f"/api/v1/reports/{report['report_id']}/versions",
            json={"language": "zh-CN", "markdown": report["markdown"]},
        )

        # monitor pass #1: same quote → NO_MATERIAL_CHANGE (only /monitor/run
        # with act=True... default act dispatches; same evidence → no-op)
        client.post("/api/v1/monitor/run", params={"instrument": "600519"})

        # create a scheduled monitor task
        task = client.post(
            "/api/v1/tasks",
            json={"instrument": "600519", "task_type": "monitor",
                  "schedule": "interval:0"},
        ).json()["task"]

        # price moves 1.94% (< 5% FULL threshold) → DELTA
        monkeypatch.setattr(httpx, "get", lambda url, timeout: httpx.Response(
            200, content=RAW_OK.replace("1648.00~1651.00", "1680.00~1651.00", 1).encode("gbk")
        ))
        tick = client.post("/api/v1/tasks/scheduler/tick").json()
        assert task["task_id"] in tick["claimed"], tick

        chain = client.get(
            f"/api/v1/reports/{report['report_id']}/versions"
        ).json()["results"]
        deltas = [v for v in chain if v["change_reason"] and "delta" in v["change_reason"]]
        assert deltas, f"delta must append a version; chain={[v['version_no'] for v in chain]}"
        assert deltas[0]["version_no"] == chain[-1]["version_no"]


class TestNarrative:
    def test_llm_translation_fills_text_en(self):
        from app.ai.llm_provider import DeterministicStubProvider
        from app.ai.narrative import narrativize_report
        from app.domain.report import ReportSection, StructuredReport
        from datetime import datetime, timezone

        report = StructuredReport(
            instrument_id="SSE:600519",
            snapshot_id="snap_x",
            as_of=datetime.now(timezone.utc),
            generated_at=datetime.now(timezone.utc),
        )
        section = report.section("executive_summary")
        section.items.append(
            {
                "text_zh": "估值处于低位",
                "text_en": None,
                "text_language": "zh-CN",
                "evidence_ids": ["ev_1"],
            }
        )

        class TranslatingProvider(DeterministicStubProvider):
            def generate_structured(self, prompt, *, schema_hint, system=None):
                return {"executive_summary#0": "Valuation sits at a five-year low."}

        summary = narrativize_report(report, provider=TranslatingProvider())
        assert summary["translated"] == 1
        assert report.sections["executive_summary"].items[0]["text_en"] == (
            "Valuation sits at a five-year low."
        )

    def test_deterministic_fallback_keeps_original(self):
        from app.ai.narrative import narrativize_report
        from app.domain.report import ReportSection, StructuredReport
        from datetime import datetime, timezone

        report = StructuredReport(
            instrument_id="SSE:600519",
            snapshot_id="snap_x",
            as_of=datetime.now(timezone.utc),
            generated_at=datetime.now(timezone.utc),
        )
        section = report.section("executive_summary")
        section.items.append(
            {"text_zh": "估值处于低位", "text_en": None,
             "text_language": "zh-CN", "evidence_ids": ["ev_1"]}
        )
        summary = narrativize_report(report, provider=None)
        assert summary["fallback"] == 1
        # original preserved, language marker set
        assert report.sections["executive_summary"].items[0]["text_en"] == "估值处于低位"
        assert report.sections["executive_summary"].items[0]["text_language"] == "zh-CN"
