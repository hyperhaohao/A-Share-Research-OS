"""Quality gates: real business rules, interception verified (任务书 §31)."""

from datetime import datetime, timedelta, timezone

import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
)
from app.domain.quality import (
    AnalysisQualityGate,
    EvidenceQualityGate,
    FinalReportQualityGate,
    GateStatus,
    ReportGateInput,
)
from app.domain.research import Claim, ClaimType
from app.domain.snapshot import EvidenceSnapshot, SnapshotItem
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository

AS_OF = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


@pytest.fixture()
def dbsession():
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


def _quote_evidence(available: datetime, price: float = 1648.0) -> EvidenceRecord:
    return EvidenceRecord(
        instrument_id="SSE:600519",
        evidence_type=EvidenceType.MARKET_QUOTE,
        title=f"SSE:600519 market_quote {price}",
        summary=f"market quote: price={price}",
        source="tencent_quote",
        source_type="market_data_redistributor",
        authority_level=AuthorityLevel.B2,
        fact_status=FactStatus.CONFIRMED_FACT,
        event_time=available - timedelta(minutes=1),
        available_time=available,
        ingested_time=available + timedelta(minutes=1),
        revision_time=available + timedelta(minutes=1),
        metadata={"price": price},
    )


def _snapshot(items: tuple[SnapshotItem, ...] = ()) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        instrument_id="SSE:600519",
        as_of=AS_OF,
        items=items,
        created_at=AS_OF,
    )


class TestEvidenceQualityGate:
    def test_empty_evidence_fails(self):
        result = EvidenceQualityGate().evaluate(_snapshot(), [])
        assert result.status is GateStatus.FAIL
        assert any(f.code == "evidence.empty" for f in result.findings)
        assert result.blocked

    def test_fresh_evidence_passes(self, dbsession):
        repo = EvidenceRepository(dbsession)
        ev_id, _ = repo.save(_quote_evidence(AS_OF - timedelta(hours=1)))
        snapshot = _snapshot(
            (SnapshotItem(evidence_id=ev_id, content_hash="a" * 64),)
        )
        evidence = repo.list_for_instrument("SSE:600519", visible_at=AS_OF)
        result = EvidenceQualityGate().evaluate(snapshot, evidence)
        assert result.status is GateStatus.PASS
        assert not result.blocked

    def test_stale_quote_fails(self, dbsession):
        repo = EvidenceRepository(dbsession)
        ev_id, _ = repo.save(_quote_evidence(AS_OF - timedelta(days=30)))
        snapshot = _snapshot(
            (SnapshotItem(evidence_id=ev_id, content_hash="a" * 64),)
        )
        evidence = repo.list_for_instrument("SSE:600519", visible_at=AS_OF)
        result = EvidenceQualityGate().evaluate(snapshot, evidence)
        assert result.status is GateStatus.FAIL
        assert any(f.code == "evidence.stale" for f in result.findings)

    def test_source_failure_is_visible(self, dbsession):
        from app.domain.evidence import SourceManifest

        repo = EvidenceRepository(dbsession)
        ev_id, _ = repo.save(_quote_evidence(AS_OF - timedelta(hours=1)))
        manifest = SourceManifest(
            instrument_id="SSE:600519",
            capability="financials",
            requested_as_of=AS_OF,
            final_status="source_unavailable",
        )
        repo.save_manifest(manifest)
        snapshot = _snapshot(
            (SnapshotItem(evidence_id=ev_id, content_hash="a" * 64),)
        )
        evidence = repo.list_for_instrument("SSE:600519", visible_at=AS_OF)
        result = EvidenceQualityGate().evaluate(
            snapshot, evidence, manifests=[manifest]
        )
        assert result.status is GateStatus.WARN
        assert any(f.code == "evidence.source_failure" for f in result.findings)


class TestAnalysisQualityGate:
    def _claim(self, statement: str, supporting: tuple, confidence: float = 0.6, **kw):
        return Claim(
            instrument_id="SSE:600519",
            snapshot_id="snap_test000000000000",
            statement=statement,
            claim_type=ClaimType.VALUATION_ASSESSMENT,
            supporting_evidence_refs=supporting,
            fact_status=FactStatus.CONFIRMED_FACT,
            confidence=confidence,
            **kw,
        )

    def test_prediction_language_in_fact_claim_fails(self):
        claim = self._claim("预计2027年净利润将增长20%", ("ev_a",))
        result = AnalysisQualityGate().evaluate([claim], {"ev_a": object()})
        assert result.status is GateStatus.FAIL
        assert any(f.code == "analysis.fact_prediction_mix" for f in result.findings)

    def test_dangling_evidence_reference_fails(self):
        claim = self._claim("干净陈述", ("ev_missing",))
        result = AnalysisQualityGate().evaluate([claim], {})
        assert result.status is GateStatus.FAIL
        assert any(f.code == "analysis.dangling_reference" for f in result.findings)

    def test_unexplained_conflict_warns(self):
        from app.domain.research import FactStatus as _FS

        claim = self._claim(
            "多空并存且已说明",
            ("ev_a", "ev_b"),
            confidence=0.5,
            opposing_evidence_refs=("ev_b",),
            metadata={"conflict_note": "两种口径差异已解释"},
        )
        _ = _FS
        result = AnalysisQualityGate().evaluate([claim], {"ev_a": object(), "ev_b": object()})
        assert not any(f.code == "analysis.conflict_unexplained" for f in result.findings)

    def test_thin_support_with_high_confidence_warns(self):
        claim = self._claim("单一来源高置信", ("ev_a",), confidence=0.9)
        result = AnalysisQualityGate().evaluate([claim], {"ev_a": object()})
        assert any(f.code == "analysis.thin_support_high_confidence" for f in result.findings)

    def test_clean_claim_set_passes(self):
        # R2 契约升级：confirmed_fact 的证据需满足 source-trust 门槛
        # （§8.3），干净证据桩带 A1 authority；unknown-authority 证据视为
        # T4，会在 test_r2_source_trust.py 的升级规则测试中单测。
        evidence = {
            "ev_a": SimpleNamespace(evidence_id="ev_a", authority_level="A1"),
            "ev_b": SimpleNamespace(evidence_id="ev_b", authority_level="A1"),
        }
        claim = self._claim("公司2026年上半年净利率保持稳定", ("ev_a", "ev_b"), confidence=0.6)
        result = AnalysisQualityGate().evaluate([claim], evidence)
        assert result.status is GateStatus.PASS


class TestFinalReportQualityGate:
    def _clean_report(self, **kw) -> ReportGateInput:
        base = dict(
            known_evidence_ids=("ev_1", "ev_2"),
            citations=("ev_1", "ev_2"),
            claim_support={"clm_1": ("ev_1",)},
            has_valuation=True,
            valuation_assumptions=("PE 25x 基于行业均值",),
            risk_section=True,
            data_quality_section=True,
            disclaimer=True,
        )
        base.update(kw)
        return ReportGateInput(**base)

    def test_clean_report_passes(self):
        result = FinalReportQualityGate().evaluate(self._clean_report())
        assert result.status is GateStatus.PASS
        assert not result.blocked

    def test_invalid_citation_blocks(self):
        result = FinalReportQualityGate().evaluate(
            self._clean_report(citations=("ev_1", "ev_404"))
        )
        assert result.status is GateStatus.FAIL
        assert any(f.code == "report.invalid_citation" for f in result.findings)

    def test_unsupported_claim_blocks(self):
        result = FinalReportQualityGate().evaluate(
            self._clean_report(claim_support={"clm_1": (), "clm_2": ("ev_1",)})
        )
        assert result.status is GateStatus.FAIL
        assert any(f.code == "report.unsupported_claim" for f in result.findings)

    def test_valuation_without_assumptions_blocks(self):
        result = FinalReportQualityGate().evaluate(
            self._clean_report(valuation_assumptions=())
        )
        assert result.status is GateStatus.FAIL
        assert any(f.code == "report.valuation_without_assumptions" for f in result.findings)

    def test_missing_risks_block_and_missing_data_quality_warn(self):
        result = FinalReportQualityGate().evaluate(
            self._clean_report(risk_section=False, data_quality_section=False)
        )
        assert result.status is GateStatus.FAIL
        codes = {f.code for f in result.findings}
        assert "report.risks_missing" in codes
        assert "report.data_quality_missing" in codes
