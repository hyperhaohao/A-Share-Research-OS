"""Research pipeline: orchestrates one research run end-to-end with SSE.

Pipeline stages (任务书 §67 event names):
    run_started → source_progress → evidence_ready → snapshot_built →
    quality_gate → analyst_progress → valuation_ready → report_ready →
    run_completed | run_failed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import update as _update
from sqlalchemy.orm import Session

from app.core.events import get_event_bus
from app.domain.evidence import utc_now
from app.services.evidence_collector import collect_capability_evidence
from app.services.market_analyst import MarketAnalyst
from app.services.report_compiler import ReportCompiler
from app.storage.manifest_repo import (
    ArtifactDigest,
    ManifestRepository,
    RunManifest,
    ReportVersionRepository,
    VersionRef,
)
from app.domain.manifest import ReportVersion
from app.storage.orm import ResearchRunORM
from app.storage.report_repo import ReportRepository
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import ResearchRunRepository, SnapshotRepository, ResearchRunStatus, ResearchRunType


@dataclass
class PipelineOutcome:
    run_id: str
    snapshot_id: str
    report_id: str
    gate_status: str
    events: list[dict] = field(default_factory=list)


class ResearchPipeline:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._bus = get_event_bus()
        self._snapshots = SnapshotRepository(session)
        self._runs = ResearchRunRepository(session)
        self._evidence = EvidenceRepository(session)
        self._research = ResearchRepository(session)
        self._reports = ReportRepository(session)
        self._versions = ReportVersionRepository(session)
        self._manifests = ManifestRepository(session)

    def _emit(self, run_id: str, event: str, payload: dict, recorded: list) -> None:
        self._bus.publish(run_id, event, payload)
        recorded.append({"event": event, **payload})

    def run(self, instrument_id: str, *, language: str = "zh-CN", run_id: str | None = None) -> PipelineOutcome:
        run_id = run_id or f"run_{uuid4().hex[:12]}"
        events: list[dict] = []
        now = utc_now()

        run = self._runs.create(
            run_id, instrument_id, now, run_type=ResearchRunType.FULL
        )
        self._emit(run_id, "run_started", {"instrument_id": instrument_id}, events)

        try:
            # 1) source collection
            self._emit(
                run_id, "source_progress",
                {"capability": "market_data", "status": "fetching"}, events,
            )
            outcome = collect_capability_evidence(
                instrument_id, "market_data", repo=self._evidence
            )
            self._emit(
                run_id, "evidence_ready",
                {"created": len(outcome.created_ids), "capability": "market_data"},
                events,
            )

            # 2) snapshot (PIT gate)
            snapshot = self._snapshots.build(
                instrument_id, now, evidence_repo=self._evidence
            )

            # 3) analyst
            self._emit(run_id, "analyst_progress", {"analyst": "market"}, events)
            analyst = MarketAnalyst().analyze(
                snapshot.snapshot_id, session=self._session, run_id=run_id,
                collect_missing=False,
            )
            _ = analyst

            # 4) report + valuation readiness
            self._emit(run_id, "valuation_ready", {}, events)
            compiler = ReportCompiler(self._session)
            structured = compiler.compile(snapshot.snapshot_id)
            rendered = compiler.render_and_gate(structured, language=language)
            self._emit(
                run_id, "quality_gate",
                {"status": rendered["gate"]["status"], "blocked": rendered["gate"]["blocked"]},
                events,
            )

            report_id = self._reports.save(
                instrument_id=instrument_id,
                snapshot_id=snapshot.snapshot_id,
                language=language,
                gate_status=rendered["gate"]["status"],
                published=False,
                markdown=rendered["markdown"],
                html=rendered["html"],
                content={"citations": sorted(set(structured.citations))},
            )
            # seed the immutable version chain (V1)
            self._versions.save(
                ReportVersion(
                    report_id=report_id,
                    version_no=1,
                    language=language,  # type: ignore[arg-type]
                    markdown=rendered["markdown"],
                    html=rendered["html"],
                    content_json={"citations": sorted(set(structured.citations))},
                )
            )
            self._emit(run_id, "report_ready", {"report_id": report_id}, events)

            # 5) bind the run to the snapshot + record its manifest
            self._session.execute(
                _update(ResearchRunORM)
                .where(ResearchRunORM.run_id == run_id)
                .values(snapshot_id=snapshot.snapshot_id, status=ResearchRunStatus.SUCCEEDED.value,
                        finished_at=datetime.now(timezone.utc))
            )
            self._session.flush()

            manifest = RunManifest(
                run_id=run_id,
                mode="live",
                as_of=now,
                code_commit=_code_commit(),
                config_digest=_config_digest(),
                random_seed=_run_random_seed(run_id),
                snapshot_id=snapshot.snapshot_id,
                started_at=now,
                finished_at=utc_now(),
                status="succeeded",
                provider_payload_digests=(
                    ArtifactDigest(
                        name="market_data", sha256=snapshot.content_hash
                    ),
                ),
                environment=(
                    VersionRef(component="pipeline", version="1"),
                    VersionRef(component="provider:tencent_quote", version="1"),
                ),
            )
            self._manifests.save(manifest)

            self._emit(
                run_id, "run_completed",
                {"report_id": report_id, "snapshot_id": snapshot.snapshot_id},
                events,
            )
            return PipelineOutcome(
                run_id=run_id,
                snapshot_id=snapshot.snapshot_id,
                report_id=report_id,
                gate_status=rendered["gate"]["status"],
                events=events,
            )
        except Exception as exc:  # noqa: BLE001 — pipeline failures emit run_failed
            self._emit(run_id, "run_failed", {"error": str(exc)[:300]}, events)
            self._session.execute(
                _update(ResearchRunORM)
                .where(ResearchRunORM.run_id == run_id)
                .values(status=ResearchRunStatus.FAILED.value,
                        finished_at=datetime.now(timezone.utc))
            )
            self._session.flush()
            raise


def _code_commit() -> str:
    """Real code commit: env override → git rev-parse → explicit unknown.

    Docker images carry no .git; builds pass ASRO_CODE_COMMIT as a build arg
    (see Dockerfile), so a real hash is always available in deployments.
    """
    import os
    import subprocess

    env = os.environ.get("ASRO_CODE_COMMIT")
    if env:
        return env[:64]
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=".", timeout=5)
            .decode()
            .strip()[:64]
        )
    except Exception:  # noqa: BLE001 — no git metadata available
        return "unversioned"


def _config_digest() -> str:
    """SHA256 over the canonical runtime configuration (real config digest)."""
    import hashlib
    import json

    import os

    from app.config import get_settings

    settings = get_settings()
    payload = {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "cors_origins": sorted(settings.cors_origins),
        "database_url_kind": settings.database_url.split(":", 1)[0],
    }
    env_overrides = {
        k: v for k, v in os.environ.items() if k.startswith("ASRO_")
    }
    payload["env"] = dict(sorted(env_overrides.items()))
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_random_seed(run_id: str) -> int:
    """Deterministic-per-run seed derived from the unique run id (not a constant)."""
    import hashlib

    return int.from_bytes(hashlib.sha256(run_id.encode()).digest()[:4], "big")
