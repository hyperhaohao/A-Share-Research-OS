"""Research pipeline: orchestrates one research run end-to-end with SSE.

Remediation R2 full chain (整改 §7):

    InstrumentResolver (caller) → EvidenceCollector → EvidenceSnapshot →
    EvidenceQualityGate → Analyst Orchestrator (industry → financial →
    event → news → capital_flow → market) → AnalystBrief[] →
    ClaimCompiler (claims created by analysts, aggregated here) →
    AnalysisQualityGate → ThesisBuilder → Bull/Bear (debate) →
    ScenarioEngine → ValuationEngine (inputs from evidence) →
    RiskManager → ResearchManager (this orchestration) → ReportCompiler →
    FinalReportQualityGate → ReportVersion

SSE stages (任务书 §67): run_started → source_progress → evidence_ready →
snapshot_built → quality_gate → analyst_progress → claims_compiled →
thesis_ready → debate_ready → valuation_ready → scenario_ready →
risk_ready → report_ready → run_completed | run_failed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import update as _update
from sqlalchemy.orm import Session

from app.core.events import get_event_bus
from app.domain.evidence import utc_now
from app.domain.manifest import ReportVersion
from app.domain.manifest import ArtifactDigest, RunManifest, VersionRef
from app.services.analysts import (
    CapitalFlowAnalyst,
    EventAnalyst,
    FinancialAnalyst,
    IndustryAnalyst,
    MacroPolicyAnalyst,
    NewsAnalyst,
)
from app.services.evidence_collector import collect_capability_evidence
from app.services.market_analyst import MarketAnalyst
from app.services.quant_brief import QuantBriefService
from app.services.report_compiler import ReportCompiler
from app.services.research_synthesis import (
    RiskManager,
    ScenarioEngine,
    ThesisBuilder,
    ValuationInputBuilder,
)
from app.storage.manifest_repo import (
    ManifestRepository,
    ReportVersionRepository,
    RunManifest,
)
from app.storage.orm import ResearchRunORM
from app.storage.report_repo import ReportRepository
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import (
    ResearchRunRepository,
    ResearchRunStatus,
    ResearchRunType,
    SnapshotRepository,
)

_COLLECT_CAPABILITIES = [
    "market_data",
    "announcements",
    "financials",
    "news",
    "capital_flow",
    "industry",
    "historical_data",
]


@dataclass
class PipelineOutcome:
    run_id: str
    snapshot_id: str
    report_id: str
    gate_status: str
    thesis_id: str | None = None
    claim_count: int = 0
    valuation_count: int = 0
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
        # V2 Phase A: every live event is also persisted (回放/任务历史/失败分析)
        from app.application.run_events import record_run_event

        record_run_event(self._session, run_id, event, payload)
        recorded.append({"event": event, **payload})

    def _instrument_name(self, instrument_id: str) -> str:
        from app.services.instrument_service import InstrumentService

        profile = InstrumentService(self._session).get_profile(
            instrument_id, allow_remote=False
        )
        return profile.name if profile else instrument_id

    def _register_artifacts(
        self,
        *,
        run_id: str,
        instrument_id: str,
        snapshot_as_of,
        report_id: str,
        version_id: str,
        version_no: int,
    ) -> None:
        """Register this run's outputs on the Artifact Registry (V2 §85)."""
        from app.application.artifacts import ArtifactService, RelationType

        name = self._instrument_name(instrument_id)
        service = ArtifactService(self._session)
        run_artifact = service.register(
            artifact_type="research_run",
            domain_type="ResearchRun",
            domain_id=run_id,
            title=f"{name} · 完整研究 {run_id[:16]}",
            instrument_ids=(instrument_id,),
            as_of_time=snapshot_as_of,
            created_by="pipeline",
            route=f"/instrument/{instrument_id}",
        )
        report_artifact = service.register(
            artifact_type="report",
            domain_type="Report",
            domain_id=report_id,
            title=f"{name} · 完整研究报告",
            instrument_ids=(instrument_id,),
            as_of_time=snapshot_as_of,
            created_by="pipeline",
            route=f"/reports/{report_id}",
        )
        version_artifact = service.register(
            artifact_type="report_version",
            domain_type="ReportVersion",
            domain_id=version_id,
            title=f"{name} · 完整研究报告 v{version_no}",
            instrument_ids=(instrument_id,),
            as_of_time=snapshot_as_of,
            version=version_no,
            created_by="pipeline",
            route=f"/reports/{report_id}",
        )
        service.link(
            from_artifact_id=run_artifact,
            to_artifact_id=version_artifact,
            relation=RelationType.PRODUCED,
        )
        # the stable report handle derives its content from the version
        service.link(
            from_artifact_id=report_artifact,
            to_artifact_id=version_artifact,
            relation=RelationType.DERIVED_FROM,
        )

    def _code_commit(self) -> str:
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

    def _config_digest(self) -> str:
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
        env_overrides = {k: v for k, v in os.environ.items() if k.startswith("ASRO_")}
        payload["env"] = dict(sorted(env_overrides.items()))
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def run(self, instrument_id: str, *, language: str = "zh-CN", run_id: str | None = None) -> PipelineOutcome:
        run_id = run_id or f"run_{uuid4().hex[:12]}"
        events: list[dict] = []
        now = utc_now()

        run = self._runs.create(
            run_id, instrument_id, now, run_type=ResearchRunType.FULL
        )
        self._emit(run_id, "run_started", {"instrument_id": instrument_id}, events)

        try:
            # ---- 1) collect every capability ------------------------------
            for capability in _COLLECT_CAPABILITIES:
                self._emit(
                    run_id, "source_progress",
                    {"capability": capability, "status": "fetching"}, events,
                )
                outcome = collect_capability_evidence(
                    instrument_id, capability, repo=self._evidence
                )
                self._emit(
                    run_id, "evidence_ready",
                    {
                        "capability": capability,
                        "status": outcome.manifest.final_status,
                        "created": len(outcome.created_ids),
                    },
                    events,
                )

            # macro/policy needs a topic: derive it from the industry chain
            industry_label = self._industry_label(instrument_id)
            if industry_label:
                macro_outcome = collect_capability_evidence(
                    instrument_id, "macro_policy",
                    repo=self._evidence,
                    params={"keyword": industry_label, "subject": instrument_id},
                )
                self._emit(
                    run_id, "evidence_ready",
                    {"capability": "macro_policy",
                     "status": macro_outcome.manifest.final_status,
                     "created": len(macro_outcome.created_ids)},
                    events,
                )

            # ---- 2) snapshot (PIT gate) -----------------------------------
            # as_of is captured AFTER collection completes: the snapshot pins
            # exactly the evidence this run collected (all of it was
            # available by now), and nothing that arrives later.
            snapshot_as_of = utc_now()
            snapshot = self._snapshots.build(
                instrument_id, snapshot_as_of, evidence_repo=self._evidence
            )
            self._emit(
                run_id, "snapshot_built",
                {"snapshot_id": snapshot.snapshot_id, "evidence_count": len(snapshot.items)},
                events,
            )

            # ---- 3) evidence quality gate (before analysts) ----------------
            from app.services.quality_service import QualityService

            quality_service = QualityService(self._session)
            evidence_gate = quality_service.run_evidence_gate(snapshot.snapshot_id)
            self._emit(
                run_id, "quality_gate",
                {"gate": "evidence", "status": evidence_gate.status.value,
                 "blocked": evidence_gate.blocked},
                events,
            )

            # ---- 4) analyst orchestration ----------------------------------
            claim_ids: list[str] = []
            brief_risks: list[str] = []
            # business keys drive the per-analyst live UI (整改方案 §5):
            # the enum values collide (financial/industry → fundamental,
            # event/news/macro → news), so emit a distinct key per analyst
            analysts = [
                ("industry", IndustryAnalyst()),
                ("financial", FinancialAnalyst()),
                ("event", EventAnalyst()),
                ("news", NewsAnalyst()),
                ("capital_flow", CapitalFlowAnalyst()),
                ("macro_policy", MacroPolicyAnalyst()),
                ("market", MarketAnalyst()),
            ]
            thesis_id: str | None = None
            for analyst_key, analyst in analysts:
                self._emit(
                    run_id, "analyst_progress",
                    {"analyst": analyst_key, "status": "running"}, events,
                )
                try:
                    outcome = analyst.analyze(
                        snapshot.snapshot_id, session=self._session,
                        run_id=run_id, collect_missing=False,
                    )
                    claim_ids.extend(outcome.created_claim_ids)
                    brief_risks.extend(outcome.brief.risks)
                    self._emit(
                        run_id, "analyst_progress",
                        {"analyst": analyst_key, "status": "ok"}, events,
                    )
                except Exception as exc:  # noqa: BLE001 — one analyst must not
                    # kill the run; its missing-data stays disclosed via briefs
                    self._emit(
                        run_id, "analyst_progress",
                        {"analyst": analyst_key,
                         "status": "failed", "error": str(exc)[:200]},
                        events,
                    )

            # quant loop over historical bars
            try:
                quant_brief, quant_result = QuantBriefService().analyze(
                    snapshot.snapshot_id, session=self._session, run_id=run_id
                )
                claim_ids.extend(quant_brief.claim_refs)
                self._emit(
                    run_id, "analyst_progress",
                    {"analyst": "quant", "status": "ok",
                     "metrics": quant_result.get("metrics")}, events,
                )
            except Exception as exc:  # noqa: BLE001 — quant must not kill the run
                self._emit(
                    run_id, "analyst_progress",
                    {"analyst": "quant", "status": "failed", "error": str(exc)[:200]},
                    events,
                )

            claim_ids = list(dict.fromkeys(claim_ids))
            self._emit(
                run_id, "claims_compiled", {"count": len(claim_ids)}, events
            )

            # ---- 5) analysis quality gate (AFTER claims — F0.2) -------------
            analysis_gate = quality_service.run_analysis_gate(snapshot.snapshot_id)
            self._emit(
                run_id, "quality_gate",
                {"gate": "analysis", "status": analysis_gate.status.value,
                 "blocked": analysis_gate.blocked},
                events,
            )

            # ---- 6) thesis --------------------------------------------------
            if claim_ids:
                builder = ThesisBuilder(self._session)
                thesis_outcome = builder.build(
                    instrument_id, snapshot.snapshot_id, claim_ids,
                    industry_label=industry_label,
                    brief_risks=brief_risks,
                )
                thesis_id = thesis_outcome.thesis_id
                self._emit(
                    run_id, "thesis_ready",
                    {"thesis_id": thesis_id,
                     "supporting": len(thesis_outcome.supporting_claim_ids),
                     "opposing": len(thesis_outcome.opposing_claim_ids)},
                    events,
                )

                # ---- 7) debate (deterministic baseline, cited) --------------
                from app.services.debate_engine import DebateEngine
                from app.storage.research_repo import ReferenceNotFoundError

                try:
                    debate = DebateEngine(self._session).run_round(thesis_id)
                    self._emit(
                        run_id, "debate_ready",
                        {"debate_id": debate.debate_id, "round": debate.round_no},
                        events,
                    )
                except (ReferenceNotFoundError, ValueError):
                    self._emit(
                        run_id, "debate_ready", {"status": "skipped"}, events,
                    )

                # ---- 8) valuation from evidence -----------------------------
                input_builder = ValuationInputBuilder(self._session)
                built = input_builder.build(instrument_id, snapshot)
                assumptions = built.pop("__assumptions__", [])
                methods = built.pop("__methods__", [])
                valuation_results = input_builder.compute_from_evidence(
                    instrument_id, snapshot
                )
                self._emit(
                    run_id, "valuation_ready",
                    {"methods": methods, "computable": sum(
                        1 for r in valuation_results if r.computable)},
                    events,
                )

                # ---- 9) scenarios -------------------------------------------
                base_value = self._median_implied_price(valuation_results)
                scenario_engine = ScenarioEngine(self._session)
                scenario_ids = scenario_engine.build_for(
                    thesis_id, snapshot.snapshot_id, instrument_id,
                    base_value=base_value, assumptions=assumptions,
                )
                self._emit(
                    run_id, "scenario_ready", {"scenarios": len(scenario_ids)}, events,
                )

                # ---- 10) risks ----------------------------------------------
                risk_manager = RiskManager(self._session)
                risks = risk_manager.build(
                    instrument_id, snapshot, [thesis_id]
                )
                self._emit(
                    run_id, "risk_ready", {"risks": len(risks)}, events,
                )

            # ---- 11) report + gate + version --------------------------------
            compiler = ReportCompiler(self._session)
            structured = compiler.compile(snapshot.snapshot_id)
            # F1.1: narrative layer — en-US reports get LLM-translated prose
            narrative_summary = {"translated": 0, "kind": "skipped"}
            if language == "en-US":
                from app.ai.llm_provider import get_llm_provider
                from app.ai.narrative import narrativize_report

                narrative_summary = narrativize_report(
                    structured, provider=get_llm_provider(), target_language="en-US",
                )
            rendered = compiler.render_and_gate(structured, language=language)
            self._emit(
                run_id, "quality_gate",
                {"gate": "final_report", "status": rendered["gate"]["status"],
                 "blocked": rendered["gate"]["blocked"]},
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
            version_id = self._versions.save(
                ReportVersion(
                    report_id=report_id,
                    version_no=1,
                    language=language,  # type: ignore[arg-type]
                    markdown=rendered["markdown"],
                    html=rendered["html"],
                    content_json={"citations": sorted(set(structured.citations))},
                )
            )
            self._register_artifacts(
                run_id=run_id,
                instrument_id=instrument_id,
                snapshot_as_of=snapshot.as_of,
                report_id=report_id,
                version_id=version_id,
                version_no=1,
            )
            self._emit(run_id, "report_ready", {"report_id": report_id}, events)

            # ---- 12) bind run + real manifest --------------------------------
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
                code_commit=self._code_commit(),
                config_digest=self._config_digest(),
                random_seed=_run_random_seed(run_id),
                snapshot_id=snapshot.snapshot_id,
                started_at=now,
                finished_at=utc_now(),
                status="succeeded",
                provider_payload_digests=(
                    ArtifactDigest(name="snapshot", sha256=snapshot.content_hash),
                ),
                environment=(
                    VersionRef(component="pipeline", version="2"),
                    VersionRef(component="provider:tencent_quote", version="1"),
                    VersionRef(component="provider:eastmoney_suite", version="1"),
                ),
                # F0.4: record the real LLM model/prompt when one participates
                # in the run (narrative layer); empty when LLM-less.
                model_versions=_llm_model_versions(),
                prompt_versions=_llm_prompt_versions(),
            )
            self._manifests.save(manifest)

            self._emit(
                run_id, "run_completed",
                {
                    "report_id": report_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "thesis_id": thesis_id,
                    "claims": len(claim_ids),
                },
                events,
            )
            return PipelineOutcome(
                run_id=run_id,
                snapshot_id=snapshot.snapshot_id,
                report_id=report_id,
                gate_status=rendered["gate"]["status"],
                thesis_id=thesis_id,
                claim_count=len(claim_ids),
                valuation_count=sum(1 for r in valuation_results if r.computable)
                if claim_ids else 0,
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

    def _industry_label(self, instrument_id: str) -> str | None:
        evidence = self._evidence.list_for_instrument(instrument_id)
        for e in reversed(evidence):  # newest first
            if e.evidence_type.value == "industry_data":
                chain = (e.metadata or {}).get("industry_chain") or []
                if chain:
                    return chain[0]
        return None

    def _median_implied_price(self, valuation_results) -> float | None:
        values = sorted(r.value for r in valuation_results if r.computable)
        if not values:
            return None
        n = len(values)
        mid = n // 2
        if n % 2:
            return values[mid]
        return round((values[mid - 1] + values[mid]) / 2, 4)


def _run_random_seed(run_id: str) -> int:
    import hashlib

    return int.from_bytes(hashlib.sha256(run_id.encode()).digest()[:4], "big")


def _llm_model_versions() -> tuple:
    """Real LLM model identity when a provider participates in the run;
    empty tuple when the run is LLM-less (both are honest states)."""
    from app.ai.llm_provider import get_llm_provider

    provider = get_llm_provider()
    if provider is None:
        return ()
    info = provider.model_info()
    return (VersionRef(component=f"llm:{info.get('model', 'unknown')}",
                       version=str(info.get("kind", "unknown"))),)


def _llm_prompt_versions() -> tuple:
    import hashlib
    import json

    from app.ai.llm_provider import get_llm_provider

    provider = get_llm_provider()
    if provider is None:
        return ()
    prompts = {
        "copilot_system": "Evidence-first research copilot. Use only the provided context.",
        "narrative_system": "Financial research translator. Never add or alter facts.",
    }
    return tuple(
        VersionRef(
            component=f"prompt:{name}",
            version=hashlib.sha256(json.dumps(text, ensure_ascii=False).encode()).hexdigest()[:16],
        )
        for name, text in sorted(prompts.items())
    )
