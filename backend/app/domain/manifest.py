"""RunManifest + ReportVersion domain (任务书 §40/§41).

RunManifest contract blueprint: OpenAlpha CN ``domain/run.py`` (MIT,
Copyright (c) 2026 ss8875), adapted to this project's run lifecycle.

ReportVersion (§41): an append-only version chain. Creating V1.1 never
touches V1.0 — old versions are permanent (任务书 §78). zh/en renderings of
the same version share one research state (§41).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.evidence import utc_now


class ArtifactDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=256)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class VersionRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=256)


class CheckpointRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    recorded_at: datetime
    state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunManifest(BaseModel):
    """Everything required to reproduce one research run (任务书 §40)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    manifest_id: str = Field(default_factory=lambda: f"man_{uuid4().hex[:16]}")
    run_id: str = Field(min_length=3, max_length=64)
    mode: Literal["live", "replay", "backtest"] = "live"
    as_of: datetime
    code_commit: str = Field(min_length=7, max_length=64)
    config_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_payload_digests: tuple[ArtifactDigest, ...] = ()
    model_versions: tuple[VersionRef, ...] = ()
    prompt_versions: tuple[VersionRef, ...] = ()
    random_seed: int
    environment: tuple[VersionRef, ...] = ()
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal["pending", "running", "succeeded", "failed", "interrupted"] = "running"
    checkpoints: tuple[CheckpointRecord, ...] = ()
    snapshot_id: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> "RunManifest":
        for name in ("as_of", "started_at", "finished_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.status in ("succeeded", "failed", "interrupted") and self.finished_at is None:
            raise ValueError("finished_at required for terminal status")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class ReportVersion(BaseModel):
    """One immutable report version in an append-only chain (任务书 §41)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    version_id: str = Field(default_factory=lambda: f"ver_{uuid4().hex[:16]}")
    report_id: str = Field(min_length=8, max_length=24)
    version_no: int = Field(ge=1)
    parent_version_id: str | None = None

    change_reason: str | None = Field(default=None, max_length=1000)
    changed_sections: tuple[str, ...] = ()

    language: str = Field(pattern=r"^(zh-CN|en-US)$")
    markdown: str
    html: str
    content_json: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate(self) -> "ReportVersion":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        # Only the first version may lack a parent.
        if self.version_no > 1 and self.parent_version_id is None:
            raise ValueError("version_no > 1 requires a parent_version_id")
        if self.version_no == 1 and self.parent_version_id is not None:
            raise ValueError("version 1 cannot have a parent")
        # A revision needs a reason for the change (§41 change_reason).
        if self.version_no > 1 and not self.change_reason:
            raise ValueError("change_reason required for revisions")
        return self
