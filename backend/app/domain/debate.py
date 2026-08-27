"""Debate and scenario domain (任务书 §35/§37).

Debate discipline (§35): bull/bear argue over the *existing* claims and
evidence of a thesis — arguments are analyst_inference claims that cite the
same evidence base. A debate round never introduces facts; new facts belong
to the EvidenceCollector (M4/M8 loop).

Scenarios (§37): Bear/Base/Bull per thesis with probabilities that must sum
to 100% across the set.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioKind(str, Enum):
    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


class Scenario(BaseModel):
    """One branch of a thesis scenario set (任务书 §37)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    scenario_id: str = Field(default_factory=lambda: f"scn_{uuid4().hex[:16]}")
    thesis_id: str = Field(min_length=8, max_length=24)
    snapshot_id: str = Field(min_length=8, max_length=32)
    instrument_id: str = Field(min_length=3, max_length=32)

    kind: ScenarioKind
    probability: float = Field(ge=0.0, le=100.0)  # percent
    assumptions: tuple[str, ...] = ()
    catalysts: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    trigger_conditions: tuple[str, ...] = ()
    # Valuation fields are attached by the deterministic engine in M10.

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate(self) -> "Scenario":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class ScenarioSet(BaseModel):
    """All scenarios for one thesis — probabilities must total 100 (§37)."""

    model_config = ConfigDict(extra="forbid")

    thesis_id: str = Field(min_length=8, max_length=24)
    snapshot_id: str = Field(min_length=8, max_length=32)
    instrument_id: str = Field(min_length=3, max_length=32)
    scenarios: tuple[Scenario, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate(self) -> "ScenarioSet":
        total = sum(s.probability for s in self.scenarios)
        if abs(total - 100.0) > 1e-6:
            raise ValueError(
                f"scenario probabilities must sum to 100, got {total:.4f}"
            )
        kinds = [s.kind for s in self.scenarios]
        if len(set(kinds)) != len(kinds):
            raise ValueError("scenario kinds must be unique within a set")
        return self


class DebateRole(str, Enum):
    BULL = "bull"
    BEAR = "bear"


class DebateRound(BaseModel):
    """One bull/bear exchange over a thesis (任务书 §35)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    debate_id: str = Field(default_factory=lambda: f"dbt_{uuid4().hex[:16]}")
    thesis_id: str = Field(min_length=8, max_length=24)
    snapshot_id: str = Field(min_length=8, max_length=32)
    instrument_id: str = Field(min_length=3, max_length=32)
    round_no: int = Field(ge=1)

    bull_claim_id: str = Field(min_length=8, max_length=24)
    bear_claim_id: str = Field(min_length=8, max_length=24)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate(self) -> "DebateRound":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self
