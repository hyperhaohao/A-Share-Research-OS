"""LLM provider + Copilot boundary tests (整改 R3.1/R3.3)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.llm_provider import DeterministicStubProvider, LLMNotConfigured
from app.db import get_session
from app.main import create_app
from app.services.report_qa import ReportQAService
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


class TestLLMProvider:
    def test_stub_never_invents(self):
        provider = DeterministicStubProvider()
        text = provider.generate_text("context only")
        assert text.startswith("[stub]")
        assert "context only" in text

    def test_openai_provider_generate(self, monkeypatch):
        from app.ai.llm_provider import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            base_url="https://llm.example/v1", api_key="k", model="m1"
        )
        body = {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        def fake_post(url, **kw):
            assert "chat/completions" in url
            assert kw["headers"]["Authorization"] == "Bearer k"
            return httpx.Response(200, json=body)

        monkeypatch.setattr(httpx, "post", fake_post)
        text = provider.generate_text("q")
        assert text == "answer"
        usage = provider.usage()
        assert usage["calls"] == 1 and usage["prompt_tokens"] == 10

    def test_openai_provider_structured(self, monkeypatch):
        from app.ai.llm_provider import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            base_url="https://llm.example/v1", api_key="k", model="m1"
        )
        body = {
            "choices": [{"message": {"content": '{"answer": "yes", "cites": ["clm_1"]}'}}],
            "usage": {},
        }
        monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(200, json=body))
        parsed = provider.generate_structured("q", schema_hint='{"answer": "str"}')
        assert parsed["answer"] == "yes"

    def test_openai_provider_stream(self, monkeypatch):
        from app.ai.llm_provider import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            base_url="https://llm.example/v1", api_key="k", model="m1"
        )
        sse = (
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
            b"data: [DONE]\n\n"
        )

        class FakeStream:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def iter_lines(self):
                for line in sse.split(b"\n\n"):
                    if line:
                        yield line.decode()

        def fake_stream(method, url, **kw):
            assert method == "POST" and "chat/completions" in url
            return FakeStream()

        monkeypatch.setattr(httpx, "stream", fake_stream)
        assert "".join(provider.stream("q")) == "Hello"


class TestCopilotBoundary:
    """整改 §16: LLM narrative cannot cite outside the provided context."""

    @pytest.fixture()
    def qa_setup(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
        session = factory()
        yield session
        session.close()

    def test_llm_citation_validation(self, qa_setup, monkeypatch):
        session = qa_setup
        from app.domain.evidence import (
            AuthorityLevel,
            EvidenceRecord,
            EvidenceType,
            FactStatus,
        )
        from app.domain.research import Claim, ClaimType
        from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
        from app.storage.repository import EvidenceRepository
        from app.storage.snapshot_repo import SnapshotRepository

        available = (
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        )
        ev_id, _ = EvidenceRepository(session).save(
            EvidenceRecord(
                instrument_id="SSE:600519",
                evidence_type=EvidenceType.MARKET_QUOTE,
                title="quote",
                summary="market quote",
                source="tencent_quote",
                source_type="market_data_redistributor",
                authority_level=AuthorityLevel.B2,
                fact_status=FactStatus.CONFIRMED_FACT,
                event_time=available,
                available_time=available,
                ingested_time=available,
                revision_time=available,
                metadata={},
            )
        )
        snapshot = EvidenceSnapshot(
            instrument_id="SSE:600519",
            as_of=available,
            items=(SnapshotItem(evidence_id=ev_id, content_hash="a" * 64),),
            created_at=available,
        )
        SnapshotRepository(session)._session.add(
            __import__("app.storage.orm", fromlist=["SnapshotORM"]).SnapshotORM(
                snapshot_id=snapshot.snapshot_id,
                content_hash=snapshot.content_hash,
                instrument_id=snapshot.instrument_id,
                as_of=snapshot.as_of,
                items_json=[i.model_dump(mode="json") for i in snapshot.items],
                created_at=snapshot.created_at,
            )
        )
        session.flush()
        from app.storage.research_repo import ResearchRepository

        claim_id = ResearchRepository(session).save_claim(
            Claim(
                instrument_id="SSE:600519",
                snapshot_id=snapshot.snapshot_id,
                statement="估值处于低位",
                claim_type=ClaimType.VALUATION_ASSESSMENT,
                supporting_evidence_refs=(ev_id,),
                fact_status=FactStatus.CONFIRMED_FACT,
                confidence=0.8,
            )
        )
        report_row = {
            "report_id": "rpt_x",
            "snapshot_id": snapshot.snapshot_id,
            "instrument_id": "SSE:600519",
        }

        # a hostile LLM citing an unknown claim — boundary must flag it
        class HostileProvider(DeterministicStubProvider):
            def generate_text(self, prompt, *, system=None, temperature=0.2):
                return (
                    "答案 [claim:clm_ffffffffffffffffffffffff] "
                    "以及编造的数字 12345.67"
                )

        import app.services.report_qa as rq_mod

        monkeypatch.setattr(rq_mod, "_get_provider", lambda: HostileProvider())
        service = ReportQAService(session)
        result = service.explain_with_llm(report_row, "估值怎么样")
        assert result["narrative_kind"] == "llm"
        assert result["invalid_citations"] == ["clm_ffffffffffffffffffffffff"]
        # no claims/evidence were created by the LLM path
        from sqlalchemy import func, select as _select

        from app.storage.orm import EvidenceORM
        from app.storage.research_orm import ClaimORM

        n_claims = session.scalars(_select(func.count()).select_from(ClaimORM)).one()
        assert n_claims == 1  # only the seeded claim
        n_evidence = session.scalars(_select(func.count()).select_from(EvidenceORM)).one()
        assert n_evidence == 1

    def test_unconfigured_provider_falls_back_to_deterministic(self, qa_setup, monkeypatch):
        import app.services.report_qa as rq_mod

        session = qa_setup
        from app.domain.evidence import (
            AuthorityLevel,
            EvidenceRecord,
            EvidenceType,
            FactStatus,
        )
        from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
        from app.storage.repository import EvidenceRepository
        from app.storage.snapshot_repo import SnapshotRepository

        available = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
        ev_id, _ = EvidenceRepository(session).save(
            EvidenceRecord(
                instrument_id="SSE:600519",
                evidence_type=EvidenceType.MARKET_QUOTE,
                title="quote",
                summary="market quote",
                source="tencent_quote",
                source_type="market_data_redistributor",
                authority_level=AuthorityLevel.B2,
                fact_status=FactStatus.CONFIRMED_FACT,
                event_time=available,
                available_time=available,
                ingested_time=available,
                revision_time=available,
                metadata={},
            )
        )
        snapshot = EvidenceSnapshot(
            instrument_id="SSE:600519",
            as_of=available,
            items=(SnapshotItem(evidence_id=ev_id, content_hash="a" * 64),),
            created_at=available,
        )
        from app.storage.orm import SnapshotORM

        session.add(
            SnapshotORM(
                snapshot_id=snapshot.snapshot_id,
                content_hash=snapshot.content_hash,
                instrument_id=snapshot.instrument_id,
                as_of=snapshot.as_of,
                items_json=[i.model_dump(mode="json") for i in snapshot.items],
                created_at=snapshot.created_at,
            )
        )
        session.flush()

        monkeypatch.setattr(rq_mod, "_get_provider", lambda: None)
        service = ReportQAService(session)
        result = service.explain_with_llm(
            {
                "report_id": "rpt_x",
                "snapshot_id": snapshot.snapshot_id,
                "instrument_id": "SSE:600519",
            },
            "anything",
        )
        assert result["narrative_kind"] == "deterministic"


class TestCopilotAPI:
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

    def test_ask_mode_copilot_uses_llm_when_configured(self, client, monkeypatch):
        client, factory = client
        resp = httpx.Response(200, content=RAW_OK.encode("gbk"))
        monkeypatch.setattr(httpx, "get", lambda url, timeout: resp)
        client.post("/api/v1/evidence/collect", params={"instrument": "600519"})
        snapshot = client.post(
            "/api/v1/snapshots",
            params={"instrument": "600519", "as_of": "2026-08-28T15:00:00+00:00"},
        ).json()["snapshot"]
        report = client.post(
            "/api/v1/reports/compile",
            params={"snapshot_id": snapshot["snapshot_id"], "language": "zh-CN"},
        ).json()["report"]

        import app.services.report_qa as rq_mod

        stub = DeterministicStubProvider()
        monkeypatch.setattr(rq_mod, "_get_provider", lambda: stub)
        body = client.post(
            f"/api/v1/reports/{report['report_id']}/ask",
            json={"question": "估值 依据", "mode": "explain", "copilot": True},
        ).json()
        assert body["narrative_kind"] == "llm"
        assert body["narrative"].startswith("[stub]")
