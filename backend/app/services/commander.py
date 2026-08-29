"""ResearchCommander (V2 Phase B, 总纲 §39/§42/§71).

不是万能 Agent：命令路由是「确定性的意图解析 → 结构化 ResearchPlan →
Application Services」（§39）。解析器只做关键词与注册表匹配，不发明
事实 —— 无法识别标的时显式拒绝（command.unresolved），绝不猜。

Scope（§87 第一批，只控制现有系统）：
    Search（标的解析）/ ResearchPipeline / Report /
    Continuous Research / Prediction
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.conversation import PlanStatus, PlanStepStatus, ResearchPlanStep
from app.domain.code_norm import InvalidInstrumentCode, normalize_code
from app.domain.prediction import Horizon
from app.services.prediction_builder import PredictionBuilder
from app.storage.instrument_repo import InstrumentRegistryORM
from app.storage.report_repo import ReportORM


@dataclass
class CommandInterpretation:
    """Deterministic parse of one user command."""

    intent: str = "full_research"  # full_research | continuous | prediction
    instrument_hint: str | None = None  # code or registry name found in text
    schedule: str | None = None
    horizon: str = "20D"
    matched_keyword: str | None = None


_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_DAILY_RE = re.compile(r"每天\s*(\d{1,2})[:：点时]\s*(\d{1,2})?")
_MINUTES_RE = re.compile(r"每\s*(\d{1,3})\s*分钟")
_HORIZON_RE = re.compile(r"(\d{1,3})\s*(?:个?)?(?:天|日)")

_INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("prediction", ("预测",)),
    ("continuous", ("持续研究", "定时研究", "定期研究", "每天研究", "自动研究")),
    ("full_research", ("完整研究", "研究", "调研", "分析一下", "出报告")),
]


def interpret_command(text: str) -> CommandInterpretation:
    """Deterministic intent parse (pure; the registry name scan lives in
    :func:`find_registry_name_in_text`). An explicit code in the text wins."""
    text = (text or "").strip()
    if not text:
        return CommandInterpretation(instrument_hint=None)

    schedule: str | None = None
    daily = _DAILY_RE.search(text)
    minutes = _MINUTES_RE.search(text)
    if daily:
        hour, minute = int(daily.group(1)), int(daily.group(2) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            schedule = f"daily:{hour:02d}:{minute:02d}"
    elif minutes:
        schedule = f"interval:{int(minutes.group(1)) * 60}"
    elif "每小时" in text:
        schedule = "interval:3600"

    horizon = "20D"
    if "预测" in text:
        horizon_match = _HORIZON_RE.search(text)
        if horizon_match:
            candidate = f"{min(int(horizon_match.group(1)), 60)}D"
            if candidate in ("5D", "20D", "60D"):
                horizon = candidate

    intent = "full_research"
    matched: str | None = None
    for name, keywords in _INTENT_KEYWORDS:
        keyword = next((k for k in keywords if k in text), None)
        if keyword is not None:
            intent, matched = name, keyword
            break

    interp = CommandInterpretation(
        intent=intent, schedule=schedule, horizon=horizon, matched_keyword=matched
    )

    for code in _CODE_RE.findall(text):
        try:
            normalize_code(code)
        except InvalidInstrumentCode:
            continue
        interp.instrument_hint = code
        return interp

    return interp


def find_registry_name_in_text(session: Session, text: str) -> str | None:
    """Longest registry name that appears verbatim in the text, e.g.
    「研究中国稀土最近是否有资产重组迹象」→ 中国稀土 (None if no match)."""
    rows = session.scalars(select(InstrumentRegistryORM)).all()
    best: str | None = None
    for row in rows:
        name = (row.name or "").strip()
        if len(name) >= 2 and name in text and (best is None or len(name) > len(best)):
            best = name
    return best


def build_plan_steps(interp: CommandInterpretation) -> list[ResearchPlanStep]:
    """Structure the plan (总纲 §40) — the 左栏 renders exactly this."""
    if interp.intent == "continuous":
        return [
            ResearchPlanStep(
                title="解析研究标的", action="resolve_instrument",
                detail=interp.instrument_hint,
            ),
            ResearchPlanStep(
                title="创建持续研究任务", action="create_task",
                detail=interp.schedule or "",
            ),
        ]
    if interp.intent == "prediction":
        return [
            ResearchPlanStep(
                title="解析研究标的", action="resolve_instrument",
                detail=interp.instrument_hint,
            ),
            ResearchPlanStep(
                title=f"由最新报告生成预测（{interp.horizon}）",
                action="create_prediction",
                detail=interp.horizon,
            ),
        ]
    return [
        ResearchPlanStep(
            title="解析研究标的", action="resolve_instrument",
            detail=interp.instrument_hint,
        ),
        ResearchPlanStep(title="运行完整研究管线", action="run_pipeline"),
        ResearchPlanStep(title="打开研究报告", action="open_report"),
    ]


INTENT_TITLES = {
    "full_research": "完整研究",
    "continuous": "持续研究",
    "prediction": "生成预测",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchCommander:
    """Executes one ResearchPlan step by step (worker-thread entry point)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def execute(self, plan: dict) -> dict:
        """Run pending steps in order; the first failure stops the plan and
        is recorded on it (failures are visible, never silent)."""
        from app.application.conversation import ConversationRepository

        repo = ConversationRepository(self._session)
        plan = repo.get_plan(plan["plan_id"]) or plan
        failed: str | None = None

        for step in plan["steps"]:
            if step["status"] in (PlanStepStatus.OK, PlanStepStatus.FAILED):
                continue

            def mutate_running(p: dict, step_id=step["step_id"]) -> dict:
                for s in p["steps"]:
                    if s["step_id"] == step_id:
                        s["status"] = PlanStepStatus.RUNNING
                        s["started_at"] = _now_iso()
                return p
            plan = repo.update_plan(plan["plan_id"], mutate_running)

            try:
                detail, artifact_ids = self._run_step(step, plan)
            except Exception as exc:  # noqa: BLE001 — step failure is plan state
                failed = step["title"]
                error_text = str(exc)[:300]

                def mutate_failed(p: dict, step_id=step["step_id"]) -> dict:
                    for s in p["steps"]:
                        if s["step_id"] == step_id:
                            s["status"] = PlanStepStatus.FAILED
                            s["error"] = error_text
                            s["completed_at"] = _now_iso()
                    return p
                plan = repo.update_plan(plan["plan_id"], mutate_failed)
                break

            def mutate_ok(p: dict, step_id=step["step_id"]) -> dict:
                for s in p["steps"]:
                    if s["step_id"] == step_id:
                        s["status"] = PlanStepStatus.OK
                        s["detail"] = detail
                        s["artifact_ids"] = artifact_ids
                        s["completed_at"] = _now_iso()
                if step["action"] == "run_pipeline":
                    p["run_id"] = detail  # the pipeline run this plan produced
                return p
            plan = repo.update_plan(plan["plan_id"], mutate_ok)

        status = PlanStatus.FAILED if failed else PlanStatus.COMPLETED

        def finalize(p: dict) -> dict:
            p["status"] = status
            if failed:
                p["error"] = failed
            return p
        return repo.update_plan(plan["plan_id"], finalize)

    # -- steps -----------------------------------------------------------------

    def _run_step(self, step: dict, plan: dict) -> tuple[str, list[str]]:
        from app.application.artifacts import ArtifactService
        from app.services.instrument_service import InstrumentService

        action = step["action"]
        instrument_id = plan.get("instrument_id")

        if action == "resolve_instrument":
            hint = step.get("detail")
            if not hint:
                raise ValueError("no instrument bound to this plan")
            instrument_id = InstrumentService(self._session).resolve_id(hint)
            if instrument_id is None:
                raise ValueError(f"cannot resolve instrument: {hint}")
            profile = InstrumentService(self._session).get_profile(
                instrument_id, allow_remote=False
            )

            def bind(p: dict) -> dict:
                p["instrument_id"] = instrument_id
                return p
            from app.application.conversation import ConversationRepository

            ConversationRepository(self._session).update_plan(plan["plan_id"], bind)
            plan["instrument_id"] = instrument_id
            return (f"{profile.name} · {profile.code}" if profile else instrument_id), []

        if instrument_id is None:
            raise ValueError("instrument not resolved")

        if action == "run_pipeline":
            from app.services.pipeline import ResearchPipeline

            outcome = ResearchPipeline(self._session).run(instrument_id)
            report_artifact = ArtifactService(self._session).by_domain(
                "Report", outcome.report_id
            )
            ids = [report_artifact["artifact_id"]] if report_artifact else []
            return outcome.run_id, ids

        if action == "create_task":
            from app.scheduler.tasks import TaskRepository, TaskType

            schedule = step.get("detail") or None
            task = TaskRepository(self._session).create(
                instrument_id=instrument_id,
                task_type=TaskType.PERIODIC_FULL_RESEARCH,
                schedule=schedule,
            )
            return task.task_id, []

        if action == "create_prediction":
            return self._create_prediction_step(instrument_id, step.get("detail") or "20D")

        if action == "open_report":
            return "右侧产物栏已更新", []

        raise ValueError(f"unknown plan action: {action}")

    def _create_prediction_step(self, instrument_id: str, horizon: str) -> tuple[str, list[str]]:
        """Derive a prediction from the instrument's latest report; refuse
        honestly when there is none or the research state underdetermines it."""
        from app.application.artifacts import ArtifactService, RelationType
        from app.services.instrument_service import InstrumentService

        report_row = self._session.scalars(
            select(ReportORM)
            .where(ReportORM.instrument_id == instrument_id)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
        ).first()
        if report_row is None:
            raise ValueError("no existing report for this instrument; run full research first")

        prediction = PredictionBuilder(self._session).build_and_save(
            report_row.report_id, Horizon(horizon)
        )

        service = ArtifactService(self._session)
        profile = InstrumentService(self._session).get_profile(
            instrument_id, allow_remote=False
        )
        name = f"{profile.name} · {profile.code}" if profile else instrument_id
        prediction_artifact = service.register(
            artifact_type="prediction",
            domain_type="PredictionRecord",
            domain_id=prediction.prediction_id,
            title=f"{name} · {prediction.horizon.value} 预测",
            instrument_ids=(instrument_id,),
            as_of_time=prediction.as_of,
            created_by="commander",
            route="/predictions",
        )
        report_artifact = service.by_domain("Report", report_row.report_id)
        if report_artifact is not None:
            service.link(
                from_artifact_id=prediction_artifact,
                to_artifact_id=report_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
        detail = (
            f"{prediction.expected_direction.value} "
            f"[{prediction.expected_return_range[0]}, {prediction.expected_return_range[1]}]%"
        )
        return detail, [prediction_artifact]
