"""PW2 — PredictionBuilder: report → prediction from persisted research state.

The builder is honest by contract: a missing thesis, quote, or computable
valuation raises PredictionNotDerivable — ranges are never invented.
"""

import pytest

from app.db import session_scope
from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
    utc_now,
)
from app.domain.prediction import Horizon
from app.domain.research import Claim, ClaimType, InvestmentThesis
from app.domain.valuation import ValuationMethod, ValuationResult
from app.services.prediction_builder import PredictionBuilder, PredictionNotDerivable
from app.storage.prediction_repo import PredictionRepository
from app.storage.report_repo import ReportRepository
from app.storage.repository import EvidenceRepository
from app.storage.research_repo import ResearchRepository
from app.storage.snapshot_repo import SnapshotRepository
from app.storage.valuation_repo import ValuationIn, ValuationRepository


@pytest.fixture()
def factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.storage.orm import Base

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


QUOTE_METADATA = {"price": 24.83, "name": "中国稀土"}


def _seed_state(factory, *, with_thesis=True, with_valuation=True, valuation_values=None):
    """Real research state: quote evidence → snapshot → claim → thesis → valuation."""
    with session_scope(factory) as session:
        evidence_repo = EvidenceRepository(session)
        now = utc_now()
        record = EvidenceRecord(
            instrument_id="SZSE:000831",
            evidence_type=EvidenceType.MARKET_QUOTE,
            title="实时行情",
            summary="最新价 24.83",
            source="tencent_quote",
            source_type="market",
            authority_level=AuthorityLevel.B2,
            fact_status=FactStatus.CONFIRMED_FACT,
            event_time=now,
            available_time=now,
            ingested_time=now,
            revision_time=now,
            metadata=QUOTE_METADATA,
        )
        evidence_id, _ = evidence_repo.save(record)
        snapshot = SnapshotRepository(session).build(
            "SZSE:000831", utc_now(), evidence_repo=evidence_repo
        )
        research = ResearchRepository(session)
        thesis_id = None
        if with_thesis:
            claim = Claim(
                instrument_id="SZSE:000831",
                snapshot_id=snapshot.snapshot_id,
                statement="稀土价格上行",
                claim_type=ClaimType.FUNDAMENTAL_FACT,
                supporting_evidence_refs=(evidence_id,),
                fact_status=FactStatus.CONFIRMED_FACT,
                confidence=0.8,
            )
            claim_id = research.save_claim(claim)
            thesis = InvestmentThesis(
                instrument_id="SZSE:000831",
                snapshot_id=snapshot.snapshot_id,
                title="SZSE:000831 研究综合论点",
                description="支撑多于对立",
                supporting_claims=(claim_id,),
                opposing_claims=(),
                confidence=0.72,
            )
            thesis_id = research.save_thesis(thesis)
        if with_valuation:
            pairs = valuation_values or ((ValuationMethod.PE, 30.0), (ValuationMethod.PB, 27.314))
            for method, value in pairs:
                ValuationRepository(session).save(
                    ValuationResult(method=method, value=value, inputs_used={}, detail={}),
                    ValuationIn(
                        instrument_id="SZSE:000831",
                        snapshot_id=snapshot.snapshot_id,
                        thesis_id=thesis_id,
                        method=method,
                    ),
                )
        report_id = ReportRepository(session).save(
            instrument_id="SZSE:000831",
            snapshot_id=snapshot.snapshot_id,
            language="zh-CN",
            gate_status="pass",
            published=False,
            markdown="",
            html="",
            content={},
        )
    return report_id


def test_prediction_from_report_derives_from_research_state(factory):
    report_id = _seed_state(factory)
    with session_scope(factory) as session:
        prediction = PredictionBuilder(session).build_and_save(report_id, Horizon.D5)
        assert prediction.instrument_id == "SZSE:000831"
        assert prediction.expected_direction.value == "up"
        lo, hi = prediction.expected_return_range
        assert lo == pytest.approx(round((27.314 / 24.83 - 1) * 100, 2))
        assert hi == pytest.approx(round((30.0 / 24.83 - 1) * 100, 2))
        assert prediction.confidence == pytest.approx(0.72)
        assert prediction.horizon is Horizon.D5
        # persisted once, retrievable (immutable record)
        assert PredictionRepository(session).get(prediction.prediction_id) is not None


def test_prediction_from_report_without_thesis_is_underivable(factory):
    report_id = _seed_state(factory, with_thesis=False)
    with session_scope(factory) as session:
        with pytest.raises(PredictionNotDerivable):
            PredictionBuilder(session).build_and_save(report_id, Horizon.D20)


def test_prediction_from_missing_report_is_keyerror(factory):
    with session_scope(factory) as session:
        with pytest.raises(KeyError):
            PredictionBuilder(session).build_and_save("rpt_missing0000", Horizon.D60)




def test_payload_discloses_direction_range_conflict(factory):
    """看多论点 + 低于现价的估值 → payload 携带 conflict 显式说明（红线8）。"""
    from app.api.predictions import _payload

    report_id = _seed_state(
        factory,
        valuation_values=((ValuationMethod.PE, 5.0), (ValuationMethod.PB, 8.0)),
    )
    with session_scope(factory) as session:
        prediction = PredictionBuilder(session).build_and_save(report_id, Horizon.D5)
        payload = _payload(prediction)
    lo, hi = prediction.expected_return_range
    assert hi < 0  # both implied prices below the 24.83 quote
    assert payload["consistency"] == "conflict"
    assert "方向与估值区间异号" in payload["consistency_note"]


def test_payload_consistent_when_same_side(factory):
    from app.api.predictions import _payload

    report_id = _seed_state(factory)  # PE 30 / PB 27.314 → range above the quote
    with session_scope(factory) as session:
        prediction = PredictionBuilder(session).build_and_save(report_id, Horizon.D5)
        payload = _payload(prediction)
    lo, hi = prediction.expected_return_range
    assert hi > 0 and lo > 0
    assert payload["consistency"] == "consistent"
