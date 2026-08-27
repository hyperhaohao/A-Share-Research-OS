"""Debate + scenario API (M9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.debate import ScenarioKind
from app.services.debate_engine import DebateEngine, DebateScenarioRepository
from app.storage.research_repo import ReferenceNotFoundError

router = APIRouter(tags=["debate"])


class ScenarioIn(BaseModel):
    thesis_id: str = Field(min_length=8, max_length=24)
    snapshot_id: str = Field(min_length=8, max_length=32)
    instrument_id: str = Field(min_length=3, max_length=32)
    kind: ScenarioKind
    probability: float = Field(ge=0.0, le=100.0)
    assumptions: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    trigger_conditions: list[str] = Field(default_factory=list)


class ScenarioSetIn(BaseModel):
    scenarios: list[ScenarioIn] = Field(min_length=1)


def _scenario_payload(s) -> dict:
    return {
        "scenario_id": s.scenario_id,
        "thesis_id": s.thesis_id,
        "snapshot_id": s.snapshot_id,
        "instrument_id": s.instrument_id,
        "kind": s.kind.value,
        "probability": s.probability,
        "assumptions": list(s.assumptions),
        "catalysts": list(s.catalysts),
        "risks": list(s.risks),
        "trigger_conditions": list(s.trigger_conditions),
        "created_at": s.created_at.isoformat(),
    }


def _debate_payload(d) -> dict:
    return {
        "debate_id": d.debate_id,
        "thesis_id": d.thesis_id,
        "snapshot_id": d.snapshot_id,
        "round_no": d.round_no,
        "bull_claim_id": d.bull_claim_id,
        "bear_claim_id": d.bear_claim_id,
        "created_at": d.created_at.isoformat(),
    }


@router.post("/scenarios", status_code=201)
def create_scenario_set(payload: ScenarioSetIn, session: Session = Depends(get_session)) -> dict:
    from app.domain.debate import Scenario

    repo = DebateScenarioRepository(session)
    scenarios = [
        Scenario(
            thesis_id=s.thesis_id,
            snapshot_id=s.snapshot_id,
            instrument_id=s.instrument_id,
            kind=s.kind,
            probability=s.probability,
            assumptions=tuple(s.assumptions),
            catalysts=tuple(s.catalysts),
            risks=tuple(s.risks),
            trigger_conditions=tuple(s.trigger_conditions),
        )
        for s in payload.scenarios
    ]
    try:
        ids = repo.save_scenario_set(scenarios)
    except ValueError as exc:
        raise AppError("scenario.invalid_set", status_code=422, detail=str(exc)) from None
    return {"scenario_ids": ids}


@router.get("/scenarios")
def list_scenarios(
    thesis_id: str = Query(min_length=8, max_length=24),
    session: Session = Depends(get_session),
) -> dict:
    scenarios = DebateScenarioRepository(session).list_scenarios(thesis_id)
    total = sum(s.probability for s in scenarios)
    return {
        "count": len(scenarios),
        "probability_total": total,
        "results": [_scenario_payload(s) for s in scenarios],
    }


@router.post("/debates/run", status_code=201)
def run_debate_round(
    thesis_id: str = Query(min_length=8, max_length=24),
    session: Session = Depends(get_session),
) -> dict:
    try:
        debate = DebateEngine(session).run_round(thesis_id)
    except KeyError:
        raise AppError("thesis.not_found", status_code=404) from None
    except ReferenceNotFoundError as exc:
        raise AppError("debate.no_evidence", status_code=422, detail=str(exc)) from None
    except ValueError as exc:
        raise AppError("debate.exhausted", status_code=422, detail=str(exc)) from None
    return {"debate": _debate_payload(debate)}


@router.get("/debates")
def list_debates(
    thesis_id: str = Query(min_length=8, max_length=24),
    session: Session = Depends(get_session),
) -> dict:
    rounds = DebateScenarioRepository(session).list_debate_rounds(thesis_id)
    return {"count": len(rounds), "results": [_debate_payload(d) for d in rounds]}
