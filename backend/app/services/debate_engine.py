"""Debate + scenario persistence and the deterministic debate engine (M9)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.debate import DebateRole, DebateRound, Scenario, ScenarioKind
from app.domain.research import (
    Claim,
    ClaimStatus,
    ClaimType,
    FactStatus,
)
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base
from app.storage.research_repo import ResearchRepository, ReferenceNotFoundError


class ScenarioORM(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    thesis_id: Mapped[str] = mapped_column(String(24), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)

    kind: Mapped[str] = mapped_column(String(8))
    probability: Mapped[float] = mapped_column(Float)

    assumptions_json: Mapped[list] = mapped_column(JSON, default=list)
    catalysts_json: Mapped[list] = mapped_column(JSON, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, default=list)
    trigger_conditions_json: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("thesis_id", "kind", name="uq_scenario_thesis_kind"),
    )


class DebateRoundORM(Base):
    __tablename__ = "debate_rounds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    thesis_id: Mapped[str] = mapped_column(String(24), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    round_no: Mapped[int] = mapped_column(Integer)

    bull_claim_id: Mapped[str] = mapped_column(String(24))
    bear_claim_id: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("thesis_id", "round_no", name="uq_debate_thesis_round"),
        Index("ix_debate_thesis_snapshot", "thesis_id", "snapshot_id"),
    )


class DebateScenarioRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session
        self._research = ResearchRepository(session)

    # -- scenarios -----------------------------------------------------------
    def save_scenario_set(self, scenarios: list[Scenario]) -> list[str]:
        from app.domain.debate import ScenarioSet

        scenario_set = ScenarioSet(
            thesis_id=scenarios[0].thesis_id,
            snapshot_id=scenarios[0].snapshot_id,
            instrument_id=scenarios[0].instrument_id,
            scenarios=tuple(scenarios),
        )
        ids: list[str] = []
        for scenario in scenario_set.scenarios:
            row = ScenarioORM(
                scenario_id=scenario.scenario_id,
                thesis_id=scenario.thesis_id,
                snapshot_id=scenario.snapshot_id,
                instrument_id=scenario.instrument_id,
                kind=scenario.kind.value,
                probability=scenario.probability,
                assumptions_json=list(scenario.assumptions),
                catalysts_json=list(scenario.catalysts),
                risks_json=list(scenario.risks),
                trigger_conditions_json=list(scenario.trigger_conditions),
                created_at=scenario.created_at,
            )
            self._session.add(row)
            self._session.flush()
            ids.append(row.scenario_id)
        return ids

    def list_scenarios(self, thesis_id: str) -> list[Scenario]:
        rows = self._session.scalars(
            select(ScenarioORM)
            .where(ScenarioORM.thesis_id == thesis_id)
            .order_by(ScenarioORM.created_at)
        ).all()
        return [_scenario_row_to_domain(r) for r in rows]

    # -- debate rounds -------------------------------------------------------
    def save_debate_round(self, debate: DebateRound) -> str:
        self._research._require_claims((debate.bull_claim_id, debate.bear_claim_id))
        row = DebateRoundORM(
            debate_id=debate.debate_id,
            thesis_id=debate.thesis_id,
            snapshot_id=debate.snapshot_id,
            instrument_id=debate.instrument_id,
            round_no=debate.round_no,
            bull_claim_id=debate.bull_claim_id,
            bear_claim_id=debate.bear_claim_id,
            created_at=debate.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.debate_id

    def list_debate_rounds(self, thesis_id: str) -> list[DebateRound]:
        rows = self._session.scalars(
            select(DebateRoundORM)
            .where(DebateRoundORM.thesis_id == thesis_id)
            .order_by(DebateRoundORM.round_no)
        ).all()
        return [
            DebateRound(
                debate_id=r.debate_id,
                thesis_id=r.thesis_id,
                snapshot_id=r.snapshot_id,
                instrument_id=r.instrument_id,
                round_no=r.round_no,
                bull_claim_id=r.bull_claim_id,
                bear_claim_id=r.bear_claim_id,
                created_at=_ensure_utc(r.created_at),
            )
            for r in rows
        ]


def _scenario_row_to_domain(r: ScenarioORM) -> Scenario:
    return Scenario(
        scenario_id=r.scenario_id,
        thesis_id=r.thesis_id,
        snapshot_id=r.snapshot_id,
        instrument_id=r.instrument_id,
        kind=r.kind,  # type: ignore[arg-type]
        probability=r.probability,
        assumptions=tuple(r.assumptions_json or ()),
        catalysts=tuple(r.catalysts_json or ()),
        risks=tuple(r.risks_json or ()),
        trigger_conditions=tuple(r.trigger_conditions_json or ()),
        created_at=_ensure_utc(r.created_at),
    )


class DebateEngine:
    """Deterministic bull/bear debate over an existing thesis (§35).

    Arguments are analyst_inference claims citing the thesis's own evidence
    base. No new facts are invented: the claims reference evidence that
    already exists (referential integrity rejects anything else).
    """

    max_rounds = 3

    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session
        self._research = ResearchRepository(session)
        self._repo = DebateScenarioRepository(session)

    def run_round(self, thesis_id: str, *, round_no: int | None = None) -> DebateRound:
        thesis = self._research.get_thesis(thesis_id)
        if thesis is None:
            raise KeyError(thesis_id)

        existing_rounds = self._repo.list_debate_rounds(thesis_id)
        next_round = round_no or (len(existing_rounds) + 1)
        if next_round > self.max_rounds:
            raise ValueError(f"debate exhausted at {self.max_rounds} rounds")

        # Evidence base = evidence cited by the thesis's own claims.
        claim_ids = tuple(thesis.supporting_claims) + tuple(thesis.opposing_claims)
        claims = [self._research.get_claim(cid) for cid in claim_ids]
        claims = [c for c in claims if c is not None]
        evidence_base = tuple(
            dict.fromkeys(
                ref
                for c in claims
                for ref in (c.supporting_evidence_refs + c.opposing_evidence_refs)
            )
        )
        if not evidence_base:
            raise ReferenceNotFoundError(
                f"thesis {thesis_id} has no cited evidence to debate over"
            )

        bull_statement = (
            f"看多论点（第{next_round}轮）：基于已引用证据，{thesis.title} 的支撑逻辑成立——"
            + "；".join(
                self._research.get_claim(cid).statement
                for cid in thesis.supporting_claims
                if self._research.get_claim(cid)
            )
        )
        bear_statement = (
            f"看空论点（第{next_round}轮）：基于已引用证据的反面检验——"
            + "；".join(f"风险：{r}" for r in thesis.risks)
            + "；".join(
                f"反证：{self._research.get_claim(cid).statement}"
                for cid in thesis.opposing_claims
                if self._research.get_claim(cid)
            )
        )

        bull_claim = Claim(
            instrument_id=thesis.instrument_id,
            snapshot_id=thesis.snapshot_id,
            statement=bull_statement,
            claim_type=ClaimType.COMPETITIVE_POSITION,
            supporting_evidence_refs=evidence_base,
            fact_status=FactStatus.ANALYST_INFERENCE,
            confidence=0.55 + 0.05 * min(next_round, 3),
            status=ClaimStatus.PROPOSED,
            metadata={"debate_role": DebateRole.BULL.value, "debate_round": next_round},
        )
        bear_claim = Claim(
            instrument_id=thesis.instrument_id,
            snapshot_id=thesis.snapshot_id,
            statement=bear_statement,
            claim_type=ClaimType.RISK_FACTOR,
            supporting_evidence_refs=evidence_base,
            fact_status=FactStatus.ANALYST_INFERENCE,
            confidence=0.55,
            status=ClaimStatus.PROPOSED,
            metadata={"debate_role": DebateRole.BEAR.value, "debate_round": next_round},
        )
        bull_id = self._research.save_claim(bull_claim)
        bear_id = self._research.save_claim(bear_claim)

        debate = DebateRound(
            thesis_id=thesis_id,
            snapshot_id=thesis.snapshot_id,
            instrument_id=thesis.instrument_id,
            round_no=next_round,
            bull_claim_id=bull_id,
            bear_claim_id=bear_id,
        )
        self._repo.save_debate_round(debate)
        return debate
