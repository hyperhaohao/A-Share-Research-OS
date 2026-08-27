"""Run manifest + report version API (M12)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.domain.manifest import ReportVersion, RunManifest
from app.storage.manifest_repo import ManifestRepository, ReportVersionRepository

router = APIRouter(tags=["manifest"])


class ManifestIn(BaseModel):
    run_id: str = Field(min_length=3, max_length=64)
    as_of: datetime
    code_commit: str = Field(min_length=7, max_length=64)
    config_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    random_seed: int
    snapshot_id: str | None = None
    started_at: datetime
    status: str = Field(default="running", pattern="^(pending|running|succeeded|failed|interrupted)$")
    mode: str = Field(default="live", pattern="^(live|replay|backtest)$")


class VersionIn(BaseModel):
    change_reason: str | None = Field(default=None, max_length=1000)
    changed_sections: list[str] = Field(default_factory=list)
    language: str = Field(pattern="^(zh-CN|en-US)$")
    markdown: str
    html: str = ""
    content_json: dict = Field(default_factory=dict)


def _manifest_payload(m: RunManifest) -> dict:
    return {
        "manifest_id": m.manifest_id,
        "run_id": m.run_id,
        "mode": m.mode,
        "as_of": m.as_of.isoformat(),
        "code_commit": m.code_commit,
        "config_digest": m.config_digest,
        "random_seed": m.random_seed,
        "status": m.status,
        "snapshot_id": m.snapshot_id,
        "started_at": m.started_at.isoformat(),
        "finished_at": m.finished_at.isoformat() if m.finished_at else None,
        "provider_payload_digests": [d.model_dump(mode="json") for d in m.provider_payload_digests],
        "model_versions": [v.model_dump(mode="json") for v in m.model_versions],
        "prompt_versions": [v.model_dump(mode="json") for v in m.prompt_versions],
        "environment": [v.model_dump(mode="json") for v in m.environment],
        "checkpoints": [c.model_dump(mode="json") for c in m.checkpoints],
    }


def _version_payload(v: ReportVersion) -> dict:
    return {
        "version_id": v.version_id,
        "report_id": v.report_id,
        "version_no": v.version_no,
        "parent_version_id": v.parent_version_id,
        "change_reason": v.change_reason,
        "changed_sections": list(v.changed_sections),
        "language": v.language,
        "markdown": v.markdown,
        "html": v.html,
        "created_at": v.created_at.isoformat(),
    }


@router.post("/run-manifests", status_code=201)
def create_manifest(payload: ManifestIn, session: Session = Depends(get_session)) -> dict:
    try:
        manifest = RunManifest(
            run_id=payload.run_id,
            mode=payload.mode,  # type: ignore[arg-type]
            as_of=payload.as_of,
            code_commit=payload.code_commit,
            config_digest=payload.config_digest,
            random_seed=payload.random_seed,
            snapshot_id=payload.snapshot_id,
            started_at=payload.started_at,
            status=payload.status,  # type: ignore[arg-type]
        )
        manifest_id = ManifestRepository(session).save(manifest)
    except ValidationError as exc:
        raise AppError("manifest.invalid", status_code=422, detail=str(exc)) from None
    saved = ManifestRepository(session).get_for_run(payload.run_id)
    assert saved is not None and saved.manifest_id == manifest_id
    return {"manifest": _manifest_payload(saved)}


@router.get("/run-manifests")
def get_manifest(
    run_id: str = Query(min_length=3, max_length=64),
    session: Session = Depends(get_session),
) -> dict:
    manifest = ManifestRepository(session).get_for_run(run_id)
    if manifest is None:
        raise AppError("manifest.not_found", status_code=404)
    return {"manifest": _manifest_payload(manifest)}


@router.post("/reports/{report_id}/versions", status_code=201)
def create_report_version(
    report_id: str,
    payload: VersionIn,
    session: Session = Depends(get_session),
) -> dict:
    versions = ReportVersionRepository(session)
    chain = versions.list_chain(report_id)

    if not chain:
        # Seed V1 from the currently stored report artifact (compile flow).
        from app.storage.report_repo import ReportRepository

        stored = ReportRepository(session).get(report_id)
        if stored is None:
            raise AppError("report.not_found", status_code=404)
        version = ReportVersion(
            report_id=report_id,
            version_no=1,
            language=stored["language"],  # type: ignore[arg-type]
            markdown=stored["markdown"],
            html=stored["html"],
            content_json=stored.get("content_json", {}),
        )
    else:
        previous = chain[-1]
        try:
            version = ReportVersion(
                report_id=report_id,
                version_no=previous.version_no + 1,
                parent_version_id=previous.version_id,
                change_reason=payload.change_reason,
                changed_sections=tuple(payload.changed_sections),
                language=payload.language,  # type: ignore[arg-type]
                markdown=payload.markdown,
                html=payload.html,
                content_json=payload.content_json,
            )
        except ValidationError as exc:
            raise AppError("report.invalid_version", status_code=422, detail=str(exc)) from None
    try:
        version_id = versions.save(version)
    except ValidationError as exc:
        raise AppError("report.invalid_version", status_code=422, detail=str(exc)) from None
    saved = versions.get(version_id)
    assert saved is not None
    return {"version": _version_payload(saved)}


@router.get("/reports/{report_id}/versions")
def list_report_versions(
    report_id: str,
    session: Session = Depends(get_session),
) -> dict:
    chain = ReportVersionRepository(session).list_chain(report_id)
    return {"count": len(chain), "results": [_version_payload(v) for v in chain]}


@router.get("/reports/{report_id}/versions/{version_id}")
def get_report_version(
    report_id: str,
    version_id: str,
    session: Session = Depends(get_session),
) -> dict:
    version = ReportVersionRepository(session).get(version_id)
    if version is None or version.report_id != report_id:
        raise AppError("report.version_not_found", status_code=404)
    return {"version": _version_payload(version)}
