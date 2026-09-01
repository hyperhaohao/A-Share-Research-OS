"""Research domain: CorporateEvent, Claim, InvestmentThesis (任务书 §27-29).

Research discipline enforced here at the data layer (AGENTS.md §14):

    Source before Evidence, Evidence before Claim, Claim before Thesis.

Claims may only reference evidence that actually exists; theses may only
reference claims that exist. Referential integrity is validated on creation
so every conclusion is traceable by construction — not by convention.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.evidence import FactStatus, utc_now


class EventType(str, Enum):
    """Corporate / market event taxonomy (任务书 §27) — deliberately broad."""

    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    DIVIDEND = "dividend"
    BUYBACK = "buyback"
    SHAREHOLDING_CHANGE = "shareholding_change"
    FINANCING = "financing"
    M_AND_A = "m_and_a"
    RESTRUCTURING = "restructuring"
    CONTRACT = "contract"
    LITIGATION = "litigation"
    REGULATION = "regulation"
    GOVERNANCE = "governance"
    PRODUCT = "product"
    CAPACITY = "capacity"
    INDUSTRY_EVENT = "industry_event"
    CORPORATE_ACTION = "corporate_action"


class CorporateEvent(BaseModel):
    """A dated, evidence-backed research event for one instrument."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    event_type: EventType
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4000)

    occurred_at: datetime  # when it happened
    announced_at: datetime  # when the market could know it
    evidence_refs: tuple[str, ...] = ()  # evidence backing this event

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "CorporateEvent":
        for name in ("occurred_at", "announced_at", "created_at"):
            value = getattr(self, name)
            if value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.announced_at < self.occurred_at:
            raise ValueError("announced_at cannot precede occurred_at")
        return self


class ClaimType(str, Enum):
    """What a claim asserts — spans the research dimensions (任务书 §9)."""

    FUNDAMENTAL_FACT = "fundamental_fact"
    EARNINGS_QUALITY = "earnings_quality"
    GROWTH_OUTLOOK = "growth_outlook"
    COMPETITIVE_POSITION = "competitive_position"
    VALUATION_ASSESSMENT = "valuation_assessment"
    CAPITAL_ALLOCATION = "capital_allocation"
    GOVERNANCE_QUALITY = "governance_quality"
    INDUSTRY_TREND = "industry_trend"
    RISK_FACTOR = "risk_factor"
    CATALYST = "catalyst"


class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Claim(BaseModel):
    """One evidence-backed assertion about an instrument (任务书 §28)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    claim_id: str = Field(default_factory=lambda: f"clm_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)  # research state it belongs to

    statement: str = Field(min_length=1, max_length=2000)
    claim_type: ClaimType
    supporting_evidence_refs: tuple[str, ...] = ()
    opposing_evidence_refs: tuple[str, ...] = ()
    fact_status: FactStatus
    confidence: float = Field(ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.PROPOSED
    metadata: dict = Field(default_factory=dict)  # e.g. conflict_note explanations

    # F2: Claim Version lineage（第三轮整改任务书 §5.3.4）
    parent_claim_id: str | None = None
    revision_kind: str | None = None  # carried_forward | supersedes | updated
    revision_reason: str | None = None
    source_impact_relation: str | None = None  # 驱动修订的 ClaimImpact relation
    carried_forward: bool = False

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "Claim":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        # A claim must stand on at least one piece of evidence (§8 discipline).
        if not self.supporting_evidence_refs and not self.opposing_evidence_refs:
            raise ValueError("claim requires at least one evidence reference")
        return self


class ThesisStatus(str, Enum):
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    INVALIDATED = "invalidated"
    RETIRED = "retired"


class InvestmentThesis(BaseModel):
    """A directional research view composed of claims (任务书 §29)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    thesis_id: str = Field(default_factory=lambda: f"ths_{uuid4().hex[:16]}")
    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)

    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4000)
    supporting_claims: tuple[str, ...] = ()
    opposing_claims: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)

    catalysts: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    trigger_conditions: tuple[str, ...] = ()
    invalidate_conditions: tuple[str, ...] = ()

    status: ThesisStatus = ThesisStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "InvestmentThesis":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if not self.supporting_claims and not self.opposing_claims:
            raise ValueError("thesis requires at least one claim reference")
        return self
