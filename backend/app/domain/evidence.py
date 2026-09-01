"""Evidence domain (任务书 §22-26).

Evidence is the atom of research discipline: everything a Claim asserts must
point to Evidence, and every Evidence carries its full provenance plus the
four time clocks that make Point-in-Time research enforceable (M5).

Identity is content-addressed: ``evidence_id`` derives from the subject,
type, clocks and content hash, so re-ingesting the same fact from the same
source is idempotent (dedup by ``content_hash`` + source).

Domain-contract blueprint: OpenAlpha CN ``domain/evidence.py`` and
``domain/time.py`` (MIT, Copyright (c) 2026 ss8875), extended with the
authority/fact-status taxonomy required by 任务书 §25-26.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuthorityLevel(str, Enum):
    """Source authority taxonomy (任务书 §25)."""

    A1 = "A1"  # primary_regulatory_or_company_disclosure
    A2 = "A2"  # statutory_disclosure_platform
    B1 = "B1"  # official_company_or_government
    B2 = "B2"  # major_financial_media / large market-data redistributor
    C1 = "C1"  # professional_research
    C2 = "C2"  # secondary_media
    D = "D"  # rumor_or_unverified


class FactStatus(str, Enum):
    """Fact-status taxonomy (任务书 §26 / §8 evidence discipline)."""

    CONFIRMED_FACT = "confirmed_fact"
    OFFICIAL_DISCLOSURE = "official_disclosure"
    REGULATORY_DOCUMENT = "regulatory_document"
    MANAGEMENT_STATEMENT = "management_statement"
    MEDIA_REPORT = "media_report"
    MARKET_EXPECTATION = "market_expectation"
    ANALYST_INFERENCE = "analyst_inference"
    RUMOR = "rumor"


class EvidenceType(str, Enum):
    """Kinds of evidence the system ingests (extensible, non-exhaustive)."""

    MARKET_QUOTE = "market_quote"
    ANNOUNCEMENT = "announcement"
    FINANCIAL_REPORT = "financial_report"
    NEWS = "news"
    RESEARCH_REPORT = "research_report"
    CORPORATE_ACTION = "corporate_action"
    MACRO_INDICATOR = "macro_indicator"
    CAPITAL_FLOW = "capital_flow"
    INDUSTRY_DATA = "industry_data"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("evidence clocks must be timezone-aware")
    return value.astimezone(timezone.utc)


class EvidenceRecord(BaseModel):
    """Immutable-by-value evidence atom with full provenance."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    instrument_id: str = Field(min_length=3, max_length=32)
    evidence_type: EvidenceType

    title: str = Field(min_length=1, max_length=256)
    summary: str = Field(min_length=1, max_length=4000)
    excerpt: str | None = Field(default=None, max_length=8000)

    source: str = Field(min_length=1, max_length=128)  # provider id
    source_type: str = Field(min_length=1, max_length=64)  # exchange/media/...
    source_url: str | None = Field(default=None, max_length=2048)
    source_document_id: str | None = Field(default=None, max_length=128)

    # F4: 来源独立性字段（第三轮整改任务书 §7.2）
    publisher: str | None = Field(default=None, max_length=128)   # 发布者（媒体/机构）
    origin_url: str | None = Field(default=None, max_length=2048)  # 原始出处 URL
    canonical_url: str | None = Field(default=None, max_length=2048)  # 规范化 URL（多镜像归一）
    source_group: str | None = Field(default=None, max_length=64)  # 通讯社/集团稿件组
    original_source: str | None = Field(default=None, max_length=256)  # 二次报道引用的原始来源
    published_at: datetime | None = None  # 原始发布时间

    authority_level: AuthorityLevel
    fact_status: FactStatus

    event_time: datetime  # when the underlying event happened
    available_time: datetime  # when the market could first know it
    ingested_time: datetime  # when our system ingested it
    revision_time: datetime  # last revision of the underlying datum

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_clocks(self) -> "EvidenceRecord":
        for name in ("event_time", "available_time", "ingested_time", "revision_time"):
            value = getattr(self, name)
            if value.tzinfo is None:
                raise ValueError("evidence clocks must be timezone-aware")
            # bypass assignment validation to avoid validator recursion
            object.__setattr__(self, name, value.astimezone(timezone.utc))
        # ingested/revision cannot precede availability (OpenAlpha blueprint)
        if self.ingested_time < self.available_time:
            raise ValueError("ingested_time cannot precede available_time")
        if self.revision_time < self.available_time:
            raise ValueError("revision_time cannot precede available_time")
        return self

    # -- content addressing --------------------------------------------------
    @property
    def content_hash(self) -> str:
        """SHA-256 over the canonical identity+content tuple."""
        identity = "|".join(
            [
                self.instrument_id,
                self.evidence_type.value,
                self.source,
                self.title,
                self.summary,
                self.excerpt or "",
                self.event_time.isoformat() if self.event_time else "",
                self.available_time.isoformat(),
                _stable_json(self.metadata),
            ]
        )
        return sha256(identity.encode("utf-8")).hexdigest()

    @property
    def evidence_id(self) -> str:
        return f"ev_{self.content_hash[:24]}"

    def visible_at(self, as_of: datetime) -> bool:
        """PIT visibility rule (task书 §23): available_time <= as_of."""
        return self.available_time <= _aware(as_of)


def _stable_json(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


class SourceManifest(BaseModel):
    """Ledger of one collection pass: which providers were tried and how (§40 前身)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    manifest_id: str = Field(default_factory=lambda: uuid4().hex)
    instrument_id: str
    capability: str
    requested_as_of: datetime
    created_at: datetime = Field(default_factory=utc_now)

    providers_attempted: tuple[dict[str, Any], ...] = ()
    final_status: str = "pending"  # SourceStatus value of the winning result
    final_source: str | None = None
    evidence_ids: tuple[str, ...] = ()
    from_cache: bool = False

    @model_validator(mode="after")
    def _validate(self) -> "SourceManifest":
        for name in ("requested_as_of", "created_at"):
            value = getattr(self, name)
            if value.tzinfo is None:
                raise ValueError("manifest clocks must be timezone-aware")
        return self
