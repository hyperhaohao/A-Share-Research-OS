"""Structured analyst agents (任务书 §30).

Analysts are constrained to the research state: they may only cite evidence
pinned by their EvidenceSnapshot, and any data they need but cannot find is
disclosed as ``missing_data`` and turned into a ``ResearchRequest`` — which
the collector fulfills for the *next* run (PIT: a run never uses data that
did not exist at its as_of).

M8 ships the deterministic market analyst. LLM-driven analysts plug into the
same contract later: same brief shape, same integrity checks, no private
fact stores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalystType(str, Enum):
    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    VALUATION = "valuation"
    NEWS = "news"
    CAPITAL_FLOW = "capital_flow"
    QUANT = "quant"


class ResearchRequestStatus(str, Enum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    FAILED = "failed"


class MissingData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str
    reason: str
    evidence_type: str | None = None


class AnalystBrief(BaseModel):
    """Uniform agent output contract (任务书 §30)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    brief_id: str = Field(default_factory=lambda: f"brf_{uuid4().hex[:16]}")
    analyst_type: AnalystType
    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)
    run_id: str | None = None

    # conclusions carry structured facts so reports render bilingually from
    # one shared research state (任务书 §10)
    conclusions: tuple[dict[str, Any], ...] = ()
    claim_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    missing_data: tuple[MissingData, ...] = ()
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    key_questions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate(self) -> "AnalystBrief":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class ResearchRequest(BaseModel):
    """A request for missing data, fulfilled by the collector (任务书 §30)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    capability: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=1000)
    requested_by: str = Field(min_length=1, max_length=64)  # analyst type
    snapshot_id: str = Field(min_length=8, max_length=32)

    status: ResearchRequestStatus = ResearchRequestStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def _validate(self) -> "ResearchRequest":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self
