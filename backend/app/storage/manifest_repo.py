"""RunManifest + ReportVersion persistence (M12)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, func, select, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.manifest import (
    ArtifactDigest,
    CheckpointRecord,
    ReportVersion,
    RunManifest,
    VersionRef,
)
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base


def _digests_json(digests) -> list[dict]:
    return [d.model_dump(mode="json") for d in digests]


def _refs_json(refs) -> list[dict]:
    return [r.model_dump(mode="json") for r in refs]


def _digests_domain(items) -> tuple:
    return tuple(ArtifactDigest(**i) for i in (items or []))


def _refs_domain(items) -> tuple:
    return tuple(VersionRef(**i) for i in (items or []))


class RunManifestORM(Base):
    __tablename__ = "run_manifests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manifest_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)

    mode: Mapped[str] = mapped_column(String(16))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    code_commit: Mapped[str] = mapped_column(String(64))
    config_digest: Mapped[str] = mapped_column(String(64))
    provider_payload_digests_json: Mapped[list] = mapped_column(JSON, default=list)
    model_versions_json: Mapped[list] = mapped_column(JSON, default=list)
    prompt_versions_json: Mapped[list] = mapped_column(JSON, default=list)
    random_seed: Mapped[int] = mapped_column(Integer)
    environment_json: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    checkpoints_json: Mapped[list] = mapped_column(JSON, default=list)
    snapshot_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "manifest_id", name="uq_manifest_run"),
    )


class ReportVersionORM(Base):
    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    report_id: Mapped[str] = mapped_column(String(24), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    parent_version_id: Mapped[str | None] = mapped_column(String(24), nullable=True)

    change_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    changed_sections_json: Mapped[list] = mapped_column(JSON, default=list)

    language: Mapped[str] = mapped_column(String(8))
    markdown: Mapped[str] = mapped_column(default="")
    html: Mapped[str] = mapped_column(default="")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Append-only chain: one row per (report, version number).
        UniqueConstraint("report_id", "version_no", name="uq_report_version_no"),
    )


class ManifestRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(self, manifest: RunManifest) -> str:
        row = RunManifestORM(
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            mode=manifest.mode,
            as_of=manifest.as_of,
            code_commit=manifest.code_commit,
            config_digest=manifest.config_digest,
            provider_payload_digests_json=_digests_json(manifest.provider_payload_digests),
            model_versions_json=_refs_json(manifest.model_versions),
            prompt_versions_json=_refs_json(manifest.prompt_versions),
            random_seed=manifest.random_seed,
            environment_json=_refs_json(manifest.environment),
            started_at=manifest.started_at,
            finished_at=manifest.finished_at,
            status=manifest.status,
            checkpoints_json=[c.model_dump(mode="json") for c in manifest.checkpoints],
            snapshot_id=manifest.snapshot_id,
        )
        self._session.add(row)
        self._session.flush()
        return row.manifest_id

    def get_for_run(self, run_id: str) -> RunManifest | None:
        row = self._session.scalars(
            select(RunManifestORM).where(RunManifestORM.run_id == run_id)
        ).first()
        if row is None:
            return None
        return RunManifest(
            manifest_id=row.manifest_id,
            run_id=row.run_id,
            mode=row.mode,  # type: ignore[arg-type]
            as_of=_ensure_utc(row.as_of),
            code_commit=row.code_commit,
            config_digest=row.config_digest,
            provider_payload_digests=_digests_domain(row.provider_payload_digests_json),
            model_versions=_refs_domain(row.model_versions_json),
            prompt_versions=_refs_domain(row.prompt_versions_json),
            random_seed=row.random_seed,
            environment=_refs_domain(row.environment_json),
            started_at=_ensure_utc(row.started_at),
            finished_at=_ensure_utc(row.finished_at),
            status=row.status,  # type: ignore[arg-type]
            checkpoints=tuple(CheckpointRecord(**c) for c in (row.checkpoints_json or [])),
            snapshot_id=row.snapshot_id,
        )


class ReportVersionRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def next_version_no(self, report_id: str) -> int:
        rows = self._session.scalars(
            select(ReportVersionORM.version_no).where(
                ReportVersionORM.report_id == report_id
            )
        ).all()
        return (max(rows) + 1) if rows else 1

    def save(self, version: ReportVersion) -> str:
        row = ReportVersionORM(
            version_id=version.version_id,
            report_id=version.report_id,
            version_no=version.version_no,
            parent_version_id=version.parent_version_id,
            change_reason=version.change_reason,
            changed_sections_json=list(version.changed_sections),
            language=version.language,
            markdown=version.markdown,
            html=version.html,
            content_json=version.content_json,
            created_at=version.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row.version_id

    def list_chain(self, report_id: str) -> list[ReportVersion]:
        rows = self._session.scalars(
            select(ReportVersionORM)
            .where(ReportVersionORM.report_id == report_id)
            .order_by(ReportVersionORM.version_no)
        ).all()
        return [self._row_to_domain(r) for r in rows]

    def get(self, version_id: str) -> ReportVersion | None:
        row = self._session.scalars(
            select(ReportVersionORM).where(ReportVersionORM.version_id == version_id)
        ).first()
        return None if row is None else self._row_to_domain(row)

    def latest_version_nos(self, report_ids: list[str]) -> dict[str, int]:
        """Max version_no per report (报告库 card display)."""
        if not report_ids:
            return {}
        rows = self._session.execute(
            select(ReportVersionORM.report_id, func.max(ReportVersionORM.version_no))
            .where(ReportVersionORM.report_id.in_(report_ids))
            .group_by(ReportVersionORM.report_id)
        ).all()
        return {report_id: max_no for report_id, max_no in rows}

    @staticmethod
    def _row_to_domain(r: ReportVersionORM) -> ReportVersion:
        return ReportVersion(
            version_id=r.version_id,
            report_id=r.report_id,
            version_no=r.version_no,
            parent_version_id=r.parent_version_id,
            change_reason=r.change_reason,
            changed_sections=tuple(r.changed_sections_json or ()),
            language=r.language,  # type: ignore[arg-type]
            markdown=r.markdown,
            html=r.html,
            content_json=r.content_json or {},
            created_at=_ensure_utc(r.created_at),
        )
