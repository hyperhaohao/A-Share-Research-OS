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
    # R4 §10.1 研究焦点（九类之一；general = 未识别焦点）
    focus: str = "general"
    profile: str = "general"


_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_DAILY_RE = re.compile(r"每天\s*(\d{1,2})[:：点时]\s*(\d{1,2})?")
_MINUTES_RE = re.compile(r"每\s*(\d{1,3})\s*分钟")
_HORIZON_RE = re.compile(r"(\d{1,3})\s*(?:个?)?(?:天|日)")

_INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("prediction", ("预测",)),
    ("continuous", ("持续研究", "定时研究", "定期研究", "每天研究", "自动研究")),
    ("full_research", ("完整研究", "研究", "调研", "分析一下", "出报告")),
]

# R4 §10.1 研究焦点（九类）：不改执行动作，只收敛证据面（profile）与计划问题
_FOCUS_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("event", ("资产整合", "资产注入", "重组", "减持", "增持", "公告", "事件", "股权变化", "监管审批")),
    ("earnings", ("财报", "业绩", "季报", "年报", "中报", "业绩预告", "营收", "净利")),
    ("policy", ("政策", "监管", "部委", "发改委", "工信部")),
    ("mainline", ("主线", "题材", "板块轮动")),
    ("overseas_mapping", ("海外", "美股", "境外")),
    ("thesis_review", ("论点复核", "复核论点", "thesis", "论点变化")),
    ("comparison", ("对比", "比较", "同业对比", "哪个好")),
    ("industry", ("产业", "行业", "产业链", "上游", "下游")),
    ("company", ("公司", "个股", "基本面")),
]

# 焦点 → Agent Profile（方案 §10.4）；未列出的焦点 → general
# R5 §11.1：焦点 → 研究产品类型（P0 四类；其余焦点走公司深度/通用）
_FOCUS_PRODUCT: dict[str, str] = {
    "company": "COMPANY_DEEP_DIVE",
    "industry": "INDUSTRY_DEEP_DIVE",
    "event": "EVENT_INVESTIGATION",
    "thesis_review": "THESIS_REVIEW",
    "general": "COMPANY_DEEP_DIVE",
    "earnings": "COMPANY_DEEP_DIVE",
    "policy": "EVENT_INVESTIGATION",
    "mainline": "COMPANY_DEEP_DIVE",
    "overseas_mapping": "COMPANY_DEEP_DIVE",
}

_FOCUS_PROFILE: dict[str, str] = {
    "company": "company",
    "industry": "industry",
    "event": "event",
    "earnings": "earnings",
    "policy": "policy",
    "mainline": "general",
    "overseas_mapping": "general",
    "thesis_review": "general",
    "comparison": "general",
    "general": "general",
}


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

    # R4 §10.1：焦点识别（首个命中；识别不了 → general，不猜）
    focus = "general"
    focus_matched: str | None = None
    for name, keywords in _FOCUS_KEYWORDS:
        hit = next((k for k in keywords if k in text), None)
        if hit is not None:
            focus, focus_matched = name, hit
            break

    interp = CommandInterpretation(
        intent=intent, schedule=schedule, horizon=horizon, matched_keyword=matched,
        focus=focus, profile=_FOCUS_PROFILE[focus],
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


# R4 §10.2 结构化计划：每个焦点的 研究问题/必需要素/完成标准（研究启发，非事实）
_FOCUS_PLAN_META: dict[str, dict] = {
    "general": {
        "questions": ["公司基本面的当前状态与变化方向？", "当前最重要的反方证据是什么？"],
        "required_sources": ["T0/T1 交易所公告或官方表态", "T2/T3 研报与主流报道"],
        "completion_criteria": ["核心 Claim 均有可定位的证据引用", "反方证据已检索"],
    },
    "company": {
        "questions": ["公司基本面当前状态与变化方向？", "公司层面最重要的风险与催化剂？"],
        "required_sources": ["T0 公司公告/定期报告", "T2/T3 研报与报道"],
        "completion_criteria": ["核心 Claim 均有可定位的证据引用", "风险清单已生成"],
    },
    "industry": {
        "questions": ["该产业链当前由什么因素驱动？", "产业环节间的传导路径是否成立？"],
        "required_sources": ["行业数据证据", "T3 行业报道"],
        "completion_criteria": ["行业面 Claim 有证据引用", "产业链标签已更新"],
    },
    "event": {
        "questions": ["事件事实与时间线是什么？", "事件处于哪个阶段（酝酿/披露/审批/落地）？", "对股本结构与股东的影响路径？"],
        "required_sources": ["T0 交易所公告", "T1 集团/国资委表态", "T3 财经媒体报道"],
        "completion_criteria": ["事件时间线 ≥1 条 T0/T1 证据", "反方证据已检索", "Invalidator 已列出"],
    },
    "earnings": {
        "questions": ["本期营收/利润的关键变化及原因？", "与市场预期的差异？"],
        "required_sources": ["T0 定期报告/业绩预告", "T3 报道"],
        "completion_criteria": ["财务 Claim 有证据引用", "Missing Data 显式披露"],
    },
    "policy": {
        "questions": ["政策的核心变化点？", "对公司/行业的传导路径与时间窗？"],
        "required_sources": ["T1 官方机构发布", "T3 主流媒体解读"],
        "completion_criteria": ["政策原文句已被引用", "影响路径已说明"],
    },
    "mainline": {
        "questions": ["当前市场主线叙事是什么？", "有哪些证据支持/反对该叙事延续？"],
        "required_sources": ["T3 市场报道", "行业证据"],
        "completion_criteria": ["叙事状态已标注（emerging/active/…）"],
    },
    "overseas_mapping": {
        "questions": ["海外事件对全球产业的影响路径？", "中国/A 股侧的映射环节与证据？"],
        "required_sources": ["海外事件证据", "国内映射环节证据"],
        "completion_criteria": ["每条映射均有证据引用（禁止无证据荐股）"],
    },
    "thesis_review": {
        "questions": ["当前 Thesis 的支撑/反对证据结构？", "哪些 Invalidator 已被触发或临近？"],
        "required_sources": ["既有 Thesis 及其证据", "新近证据"],
        "completion_criteria": ["Thesis Diff 已生成", "新版本走质量门"],
    },
    "comparison": {
        "questions": ["对比对象各自的核心 Claim 结构？", "差异的证据基础？"],
        "required_sources": ["双方标的证据"],
        "completion_criteria": ["对比结论均有双侧证据引用"],
    },
}


def build_plan_meta(interp: CommandInterpretation) -> dict:
    """R4 §10.2：结构化计划元数据（objective/questions/required_sources/
    completion_criteria/focus/profile/max_collection_passes）。"""
    focus_meta = _FOCUS_PLAN_META.get(interp.focus) or _FOCUS_PLAN_META["general"]
    return {
        "objective": f"{interp.focus} 研究：{interp.instrument_hint or '未定标的'}",
        "focus": interp.focus,
        "profile": interp.profile,
        "product_type": _FOCUS_PRODUCT[interp.focus],
        "questions": list(focus_meta["questions"]),
        "required_sources": list(focus_meta["required_sources"]),
        "completion_criteria": list(focus_meta["completion_criteria"]),
        "expected_artifacts": ["report", "report_version"],
        "max_collection_passes": 2,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchCommander:
    """Executes one ResearchPlan step by step (worker-thread entry point)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def execute(self, plan: dict) -> dict:
        """Run pending steps in order; the first failure stops the plan and
        is recorded on it (failures are visible, never silent).

        F5：全程发帷幄事件（step_started/step_updated/tool_call/tool_result/
        tool_error/run_completed/run_failed，correlation=corr_<plan>_<step>）。
        """
        from app.application.command_events import append_event
        from app.application.conversation import ConversationRepository

        repo = ConversationRepository(self._session)
        plan = repo.get_plan(plan["plan_id"]) or plan
        failed: str | None = None
        sid = plan.get("session_id")

        for step in plan["steps"]:
            if step["status"] in (PlanStepStatus.OK, PlanStepStatus.FAILED):
                continue
            correlation = f"corr_{plan['plan_id']}_{step['step_id']}"
            if sid:
                append_event(
                    self._session, sid, "step_started",
                    plan_id=plan["plan_id"], correlation_id=correlation,
                    status="running",
                    payload={"step_id": step["step_id"], "title": step["title"],
                             "action": step.get("action")},
                )
                append_event(
                    self._session, sid, "tool_call",
                    plan_id=plan["plan_id"], correlation_id=correlation,
                    status="running",
                    payload={"tool": step.get("action"), "step_id": step["step_id"],
                             "title": step["title"]},
                )

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
                if sid:
                    append_event(
                        self._session, sid, "tool_error",
                        plan_id=plan["plan_id"], correlation_id=correlation,
                        status="failed",
                        payload={"step_id": step["step_id"], "error": error_text},
                    )

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
            if sid:
                append_event(
                    self._session, sid, "tool_result",
                    plan_id=plan["plan_id"], correlation_id=correlation,
                    status="completed",
                    payload={"step_id": step["step_id"], "detail": str(detail)[:200]},
                    artifact_ids=list(artifact_ids or []),
                )
                append_event(
                    self._session, sid, "step_updated",
                    plan_id=plan["plan_id"], correlation_id=correlation,
                    status="ok",
                    payload={"step_id": step["step_id"], "title": step["title"],
                             "detail": str(detail)[:200]},
                    artifact_ids=list(artifact_ids or []),
                )
                if artifact_ids:
                    append_event(
                        self._session, sid, "artifact_created",
                        plan_id=plan["plan_id"], correlation_id=correlation,
                        payload={"step_id": step["step_id"]},
                        artifact_ids=list(artifact_ids),
                    )
                    # F8：Artifact 自动打开 Workbench 页面（§8.7 非仅链接）
                    from app.services.workbench import open_for_artifacts

                    open_for_artifacts(self._session, sid, list(artifact_ids))

        status = PlanStatus.FAILED if failed else PlanStatus.COMPLETED

        def finalize(p: dict) -> dict:
            p["status"] = status
            if failed:
                p["error"] = failed
            return p
        plan = repo.update_plan(plan["plan_id"], finalize)
        if sid:
            if failed:
                append_event(
                    self._session, sid, "run_failed",
                    plan_id=plan["plan_id"], status="failed",
                    payload={"failed_step": failed},
                )
            else:
                append_event(
                    self._session, sid, "run_completed",
                    plan_id=plan["plan_id"], status="completed",
                    payload={"run_id": plan.get("run_id")},
                )
        return plan

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

            meta = plan.get("meta") or {}
            outcome = ResearchPipeline(self._session).run(
                instrument_id,
                profile=meta.get("profile"),
                max_collection_passes=int(meta.get("max_collection_passes") or 1),
                product_type=meta.get("product_type"),
            )
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
