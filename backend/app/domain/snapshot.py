"""EvidenceSnapshot — frozen research-time evidence sets (任务书 §24).

A snapshot pins exactly which evidence a research run may rely on at
``as_of``. Invariants:

  - PIT gate: only evidence with ``available_time <= as_of`` enters a
    snapshot (任务书 §23/§74 — future information is invisible);
  - immutability: a stored snapshot never changes when later data arrives;
    rebuilds for the same (instrument_id, as_of) return the stored snapshot;
  - content addressing: ``snapshot_id``/``content_hash`` derive from the
    pinned evidence identities, so equal content ⇒ equal identity.

Domain-contract blueprint: OpenAlpha CN ``domain/evidence.py`` (MIT,
Copyright (c) 2026 ss8875), adapted to the task-book §24 field set.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SnapshotItem(BaseModel):
    """One evidence pinned by a snapshot (id + content hash pair)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=3, max_length=32)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    instrument_id: str = Field(min_length=3, max_length=32)
    as_of: datetime
    items: tuple[SnapshotItem, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> "EvidenceSnapshot":
        if self.as_of.tzinfo is None:
            raise ValueError("snapshot as_of must be timezone-aware")
        if self.created_at.tzinfo is None:
            raise ValueError("snapshot created_at must be timezone-aware")
        ids = [item.evidence_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("snapshot items must be unique by evidence_id")
        return self

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.items)

    @property
    def content_hash(self) -> str:
        identity = "|".join(
            [self.instrument_id, self.as_of.isoformat()]
            + [f"{item.evidence_id}:{item.content_hash}" for item in self.items]
        )
        return sha256(identity.encode("utf-8")).hexdigest()

    @property
    def snapshot_id(self) -> str:
        return f"snap_{self.content_hash[:24]}"


class ResearchRunStatus(str, Enum):
    """ResearchRun lifecycle (full ledger arrives with M12)."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchRunType(str, Enum):
    FULL = "full_research"
    MONITOR = "monitor"
    DELTA = "delta_research"


class ResearchRun(BaseModel):
    """Minimal run carrier binding a run to its frozen evidence snapshot."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: str = Field(min_length=3, max_length=64)
    instrument_id: str = Field(min_length=3, max_length=32)
    as_of: datetime
    run_type: ResearchRunType = ResearchRunType.FULL
    status: ResearchRunStatus = ResearchRunStatus.PENDING
    snapshot_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def _validate(self) -> "ResearchRun":
        for name in ("as_of", "started_at", "finished_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.finished_at is not None and self.started_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError("finished_at cannot precede started_at")
        return self
