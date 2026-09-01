"""帷幄 Tool Registry（F6，第三轮整改任务书 §8.5 P0-WEIWO）.

白名单 Tool Registry —— 禁止任意函数名执行或 eval。每个工具声明：

    name / description / input_schema / output_schema / risk_level /
    requires_confirmation / timeout_s / idempotency_policy /
    artifact_contract / executor

规则（§8.5）：
  - 只能执行注册表内的工具；参数经 input_schema 校验（必需/类型/枚举/
    长度/上下界），校验失败 → 显式 422；
  - requires_confirmation=True 的高风险工具在未获批时拒绝执行
    （confirmation_required；F7 审批门提供 token 后放行）；
  - 每个工具返回结构化 Result（不使用自然语言「已完成」替代真实结果）；
    失败显形（tool_error 事件 + 错误码）；
  - 执行产生 tool_call / tool_result / tool_error 事件（可选挂 session）；
  - artifact_contract 声明可产出的 Artifact 类型，可反查事件。

首批跨模块工具（§8.5 首批清单 → ASRO 现有服务编排）：
  search_evidence / build_pit_snapshot / open_current_thesis /
  analyze_thesis_diff / submit_thesis_revision(高) / create_experience_card /
  start_validation_workflow / run_screening / assemble_strategy /
  create_strategy_monitor(高) / generate_market_product / memory_search / open_page
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.application.command_events import append_event

RISK_READ = "read"
RISK_WRITE = "write"
RISK_HIGH = "high"

# ── 输入 schema 校验（JSON-Schema 常用子集；无第三方依赖） ────────────────────

_TYPE_CHECKS: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
}


def validate_against_schema(schema: dict, value: Any, *, path: str = "root") -> list[str]:
    """校验 value 是否符合 schema 子集；返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    expected = schema.get("type")
    if expected and not isinstance(value, _TYPE_CHECKS.get(expected, (object,))):
        # bool 不是 integer（Python bool 是 int 子类）
        if not (expected == "integer" and isinstance(value, bool)):
            return [f"{path}: expected {expected}, got {type(value).__name__}"]

    if expected == "object":
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in (value or {}):
                errors.append(f"{path}.{req}: required")
        for key, sub in (value or {}).items():
            if key in props:
                errors.extend(
                    validate_against_schema(props[key], sub, path=f"{path}.{key}")
                )
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: unknown property")
        return errors

    if expected == "array":
        items = schema.get("items")
        if items:
            for i, item in enumerate(value or []):
                errors.extend(
                    validate_against_schema(items, item, path=f"{path}[{i}]")
                )
        return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: '{value}' not in enum {schema['enum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength={schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength={schema['maxLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum={schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum={schema['maximum']}")
    return errors


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    risk_level: str  # read | write | high
    requires_confirmation: bool
    timeout_s: int
    idempotency_policy: str  # idempotent | at_most_once | merge
    artifact_contract: tuple[str, ...]
    executor: Callable[..., dict]

    def manifest(self) -> dict:
        """对外清单（不暴露 executor 本体）。"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
            "timeout_s": self.timeout_s,
            "idempotency_policy": self.idempotency_policy,
            "artifact_contract": list(self.artifact_contract),
        }


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    if spec.name in TOOL_REGISTRY:
        raise ValueError(f"tool already registered: {spec.name}")
    if spec.risk_level not in (RISK_READ, RISK_WRITE, RISK_HIGH):
        raise ValueError(f"invalid risk_level: {spec.risk_level}")
    if spec.idempotency_policy not in ("idempotent", "at_most_once", "merge"):
        raise ValueError(f"invalid idempotency_policy: {spec.idempotency_policy}")
    TOOL_REGISTRY[spec.name] = spec


def list_tools() -> list[dict]:
    return [TOOL_REGISTRY[k].manifest() for k in sorted(TOOL_REGISTRY)]


def get_tool(name: str) -> ToolSpec | None:
    return TOOL_REGISTRY.get(name)


# ── 执行内核 ─────────────────────────────────────────────────────────────────

_CONFIRMATION_TOKENS: dict[str, dict] = {}


def issue_confirmation(tool_name: str, arguments_digest: str, *, lease_s: int = 300) -> dict:
    """F7 审批门衔接：高风险工具获批后签发一次性 lease token。"""
    token = f"conf_{time.monotonic_ns()}"
    _CONFIRMATION_TOKENS[token] = {
        "tool": tool_name,
        "arguments_digest": arguments_digest,
        "expires_at": time.monotonic() + lease_s,
        "used": False,
    }
    return {"confirmation_token": token, "lease_s": lease_s}


def consume_confirmation(token: str, tool_name: str, arguments_digest: str) -> str | None:
    """一次性消费：过期/复用/参数不符 → None（防 TOCTOU）。"""
    info = _CONFIRMATION_TOKENS.get(token)
    if info is None or info["used"]:
        return None
    if time.monotonic() > info["expires_at"]:
        _CONFIRMATION_TOKENS.pop(token, None)
        return None
    if info["tool"] != tool_name or info["arguments_digest"] != arguments_digest:
        return None
    info["used"] = True
    return "ok"


def execute_tool(
    session: Session,
    name: str,
    arguments: dict,
    *,
    command_session_id: str | None = None,
    correlation_id: str | None = None,
    confirmation_token: str | None = None,
) -> dict:
    """执行注册表工具：校验 → 门 → executor → 结构化结果 + 事件。"""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {
            "ok": False, "error_code": "tool.not_found",
            "detail": f"unknown tool: {name}", "tool": name,
        }

    errors = validate_against_schema(spec.input_schema, arguments or {})
    if errors:
        return {
            "ok": False, "error_code": "tool.arguments_invalid",
            "detail": "; ".join(errors), "tool": name,
        }

    digest_src = repr(sorted((arguments or {}).items()))
    if spec.requires_confirmation:
        if not confirmation_token:
            return {
                "ok": False, "error_code": "tool.confirmation_required",
                "detail": "high-risk tool requires server-issued confirmation",
                "tool": name, "risk_level": spec.risk_level,
                "arguments_digest": digest_src,
            }
        if consume_confirmation(confirmation_token, name, digest_src) is None:
            return {
                "ok": False, "error_code": "tool.confirmation_invalid",
                "detail": "confirmation token expired, reused, or digest mismatch",
                "tool": name,
            }

    started = time.monotonic()
    if command_session_id:
        append_event(
            session, command_session_id, "tool_call",
            correlation_id=correlation_id, status="running",
            payload={"tool": name, "arguments": arguments},
        )
    try:
        result = spec.executor(session, arguments or {})
        if not isinstance(result, dict):
            raise ValueError("executor returned non-dict result")
    except Exception as exc:  # noqa: BLE001 — 失败必须显形（§8.5）
        duration_ms = int((time.monotonic() - started) * 1000)
        if command_session_id:
            append_event(
                session, command_session_id, "tool_error",
                correlation_id=correlation_id, status="failed",
                payload={"tool": name, "error": f"{type(exc).__name__}: {exc}"[:300]},
            )
        return {
            "ok": False, "error_code": "tool.execution_failed",
            "detail": f"{type(exc).__name__}: {exc}"[:500], "tool": name,
            "duration_ms": duration_ms,
        }

    duration_ms = int((time.monotonic() - started) * 1000)
    artifact_ids = list(result.get("artifact_ids") or [])
    out = {
        "ok": True, "tool": name, "result": result,
        "artifact_ids": artifact_ids, "duration_ms": duration_ms,
        "risk_level": spec.risk_level,
    }
    if command_session_id:
        append_event(
            session, command_session_id, "tool_result",
            correlation_id=correlation_id, status="completed",
            payload={"tool": name, "result": _small(result)},
            artifact_ids=artifact_ids,
        )
        if artifact_ids:
            append_event(
                session, command_session_id, "artifact_created",
                correlation_id=correlation_id,
                payload={"tool": name}, artifact_ids=artifact_ids,
            )
    return out


def _small(result: dict, limit: int = 40) -> dict:
    """事件 payload 只放摘要，避免大结果进事件流。"""
    return {
        k: (v if isinstance(v, (int, float, bool)) else str(v)[:120])
        for k, v in list(result.items())[:limit]
    }


# ── 首批工具 executor（复用既有服务，不建第二套业务） ─────────────────────────


def _exec_search_evidence(session: Session, args: dict) -> dict:
    from app.storage.orm import EvidenceORM
    from sqlalchemy import select

    stmt = (
        select(EvidenceORM)
        .where(EvidenceORM.instrument_id == args["instrument_id"])
        .order_by(EvidenceORM.available_time.desc())
        .limit(int(args.get("limit") or 10))
    )
    if args.get("evidence_type"):
        stmt = stmt.where(EvidenceORM.evidence_type == args["evidence_type"])
    rows = session.scalars(stmt).all()
    return {
        "count": len(rows),
        "results": [
            {
                "evidence_id": r.evidence_id,
                "title": r.title,
                "summary": (r.summary or "")[:200],
                "evidence_type": r.evidence_type,
                "available_time": r.available_time.isoformat() if r.available_time else None,
            }
            for r in rows
        ],
    }


def _exec_build_pit_snapshot(session: Session, args: dict) -> dict:
    from datetime import datetime, timezone

    from app.storage.repository import EvidenceRepository
    from app.storage.snapshot_repo import SnapshotRepository

    snap = SnapshotRepository(session).build(
        args["instrument_id"], datetime.now(timezone.utc),
        evidence_repo=EvidenceRepository(session),
    )
    return {"snapshot_id": snap.snapshot_id, "pinned_evidence": len(snap.items)}


def _exec_open_current_thesis(session: Session, args: dict) -> dict:
    from app.services.current_thesis import get_current_thesis

    row = get_current_thesis(session, args["instrument_id"])
    if row is None:
        return {"found": False, "thesis": None}
    return {
        "found": True,
        "thesis": {
            "thesis_id": row.thesis_id,
            "title": row.title,
            "description": row.description,
            "snapshot_id": row.snapshot_id,
            "supporting_count": len(row.supporting_claims_json or []),
            "opposing_count": len(row.opposing_claims_json or []),
        },
    }


def _exec_analyze_thesis_diff(session: Session, args: dict) -> dict:
    from datetime import datetime, timedelta, timezone

    from app.services.thesis_revision import compute_thesis_diff

    since = args.get("since")
    since_dt = (
        datetime.fromisoformat(str(since).replace("Z", "+00:00"))
        if since else datetime.now(timezone.utc) - timedelta(days=7)
    )
    return compute_thesis_diff(session, args["instrument_id"], since_dt)


def _exec_submit_thesis_revision(session: Session, args: dict) -> dict:
    from datetime import datetime, timedelta, timezone

    from app.services.thesis_revision import apply_thesis_revision

    since = args.get("since")
    since_dt = (
        datetime.fromisoformat(str(since).replace("Z", "+00:00"))
        if since else datetime.now(timezone.utc) - timedelta(days=7)
    )
    out = apply_thesis_revision(
        session, instrument_id=args["instrument_id"],
        revised_statement=args["revised_statement"], since_dt=since_dt,
    )
    artifact = None
    from app.application.artifacts import ArtifactService

    art = ArtifactService(session).by_domain("Thesis", out["thesis_id"])
    if art:
        artifact = art["artifact_id"]
        out["artifact_ids"] = [artifact]
    return out


def _exec_create_experience_card(session: Session, args: dict) -> dict:
    from app.services.experience_service import ExperienceService

    out = ExperienceService(session).create_from_report(args["report_id"])
    card = out.get("card") or {}
    return {"card_id": card.get("card_id"), "status": card.get("status")}


def _exec_start_validation_workflow(session: Session, args: dict) -> dict:
    from app.services.workflow_service import WorkflowService

    draft = WorkflowService(session).create_from_card(
        args["card_id"],
        horizon_days=int(args.get("horizon_days") or 20),
        threshold_pct=float(args.get("threshold_pct") or 0.0),
    )
    return {"run_id": draft.get("run_id") or draft.get("workflow_run_id"), "status": draft.get("status")}


def _exec_run_screening(session: Session, args: dict) -> dict:
    from app.services.screening_service import ScreeningService

    run = ScreeningService(session).create_from_card(args["card_id"])
    ScreeningService(session).execute(run)
    return {"screening_run_id": run.get("run_id") or run.get("screening_run_id"),
            "status": run.get("status")}


def _exec_assemble_strategy(session: Session, args: dict) -> dict:
    from app.services.strategy_service import StrategyService

    service = StrategyService(session)
    version = service.create_from_screening(args["screening_run_id"], args["name"])
    return {"strategy_version_id": version.get("version_id"), "version_no": version.get("version_no")}


def _exec_create_strategy_monitor(session: Session, args: dict) -> dict:
    from app.services.strategy_monitor_service import StrategyMonitorService

    out = StrategyMonitorService(session).create_monitor(
        args["version_id"], interval_seconds=int(args.get("interval_seconds") or 3600)
    )
    return {"monitor_id": out.get("monitor_id"), "status": out.get("status")}


def _exec_generate_market_product(session: Session, args: dict) -> dict:
    from app.services.research_products_compiler import MarketProductCompiler

    kind = args["kind"]
    compiler = MarketProductCompiler(session)
    if kind == "mainline_radar":
        return compiler.compile_mainline_radar()
    if kind == "overseas_mapping":
        return compiler.compile_overseas_mapping()
    return compiler.compile_daily_brief()


def _exec_memory_search(session: Session, args: dict) -> dict:
    from app.application.memory import MemoryService

    results = MemoryService(session).search(
        memory_type=args.get("memory_type"),
        status=args.get("status") or "active",
        instrument_id=args.get("instrument_id"),
        q=args.get("q"),
        limit=int(args.get("limit") or 10),
    )
    return {
        "count": len(results),
        "results": [
            {k: m.get(k) for k in ("memory_id", "memory_type", "title", "status", "content")}
            for m in results
        ],
    }


PAGE_WHITELIST = (
    "instrument-workspace", "thesis-center", "industry-map", "global-macro",
    "experience", "workflows", "screening", "strategy", "monitoring",
    "command-center", "research-graph", "reports", "daily-brief",
)


def _exec_open_page(session: Session, args: dict) -> dict:
    page = args["page"]
    if page not in PAGE_WHITELIST:
        return {"ok": False, "error_code": "tool.page_not_allowed",
                "allowed": list(_EXEC_PAGE_WHITELIST)}
    return {"page": page, "payload": args.get("payload") or {},
            "open_mode": "workbench_tab"}


# ── 注册首批（§8.5） ─────────────────────────────────────────────────────────

register_tool(ToolSpec(
    name="search_evidence",
    description="搜索某标的的证据层（真实 Evidence，含信任层）",
    input_schema={
        "type": "object", "required": ["instrument_id"],
        "properties": {
            "instrument_id": {"type": "string", "minLength": 4, "maxLength": 32},
            "evidence_type": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        },
    },
    output_schema={"type": "object", "properties": {"count": {"type": "integer"}}},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=15,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_search_evidence,
))

register_tool(ToolSpec(
    name="build_pit_snapshot",
    description="构建当前 PIT 快照（pin 全部当前可见证据）",
    input_schema={
        "type": "object", "required": ["instrument_id"],
        "properties": {"instrument_id": {"type": "string", "minLength": 4, "maxLength": 32}},
    },
    output_schema={"type": "object", "properties": {"snapshot_id": {"type": "string"}}},
    risk_level=RISK_WRITE, requires_confirmation=False, timeout_s=30,
    idempotency_policy="idempotent", artifact_contract=("snapshot",),
    executor=_exec_build_pit_snapshot,
))

register_tool(ToolSpec(
    name="open_current_thesis",
    description="读取标的当前 Thesis（唯一 Current）",
    input_schema={
        "type": "object", "required": ["instrument_id"],
        "properties": {"instrument_id": {"type": "string", "minLength": 4, "maxLength": 32}},
    },
    output_schema={"type": "object"},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=10,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_open_current_thesis,
))

register_tool(ToolSpec(
    name="analyze_thesis_diff",
    description="Thesis Diff 影响分析（新证据 → 七关系 impacts）",
    input_schema={
        "type": "object", "required": ["instrument_id"],
        "properties": {
            "instrument_id": {"type": "string", "minLength": 4, "maxLength": 32},
            "since": {"type": "string", "maxLength": 40},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=30,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_analyze_thesis_diff,
))

register_tool(ToolSpec(
    name="submit_thesis_revision",
    description="提交 Thesis 修订（原子：新快照 + carry forward + Current 切换）",
    input_schema={
        "type": "object", "required": ["instrument_id", "revised_statement"],
        "properties": {
            "instrument_id": {"type": "string", "minLength": 4, "maxLength": 32},
            "revised_statement": {"type": "string", "minLength": 4, "maxLength": 400},
            "since": {"type": "string", "maxLength": 40},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_HIGH, requires_confirmation=True, timeout_s=120,
    idempotency_policy="at_most_once", artifact_contract=("thesis",),
    executor=_exec_submit_thesis_revision,
))

register_tool(ToolSpec(
    name="create_experience_card",
    description="由报告提炼经验卡（原→炼）",
    input_schema={
        "type": "object", "required": ["report_id"],
        "properties": {"report_id": {"type": "string", "minLength": 6, "maxLength": 40}},
    },
    output_schema={"type": "object"},
    risk_level=RISK_WRITE, requires_confirmation=False, timeout_s=60,
    idempotency_policy="merge", artifact_contract=("experience_card",),
    executor=_exec_create_experience_card,
))

register_tool(ToolSpec(
    name="start_validation_workflow",
    description="由经验卡发起验证工作流（后台执行）",
    input_schema={
        "type": "object", "required": ["card_id"],
        "properties": {
            "card_id": {"type": "string", "minLength": 6, "maxLength": 40},
            "horizon_days": {"type": "integer", "minimum": 1, "maximum": 250},
            "threshold_pct": {"type": "number", "minimum": -100, "maximum": 100},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_WRITE, requires_confirmation=False, timeout_s=30,
    idempotency_policy="merge", artifact_contract=("workflow_run",),
    executor=_exec_start_validation_workflow,
))

register_tool(ToolSpec(
    name="run_screening",
    description="由已批准经验卡发起智能选股（后台执行）",
    input_schema={
        "type": "object", "required": ["card_id"],
        "properties": {"card_id": {"type": "string", "minLength": 6, "maxLength": 40}},
    },
    output_schema={"type": "object"},
    risk_level=RISK_WRITE, requires_confirmation=False, timeout_s=30,
    idempotency_policy="merge", artifact_contract=("screening_run",),
    executor=_exec_run_screening,
))

register_tool(ToolSpec(
    name="assemble_strategy",
    description="由筛选运行组装策略版本（校场 §46）",
    input_schema={
        "type": "object", "required": ["screening_run_id", "name"],
        "properties": {
            "screening_run_id": {"type": "string", "minLength": 6, "maxLength": 40},
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_WRITE, requires_confirmation=False, timeout_s=30,
    idempotency_policy="merge", artifact_contract=("strategy_version",),
    executor=_exec_assemble_strategy,
))

register_tool(ToolSpec(
    name="create_strategy_monitor",
    description="创建策略盯盘（席位；须已验证策略版本）",
    input_schema={
        "type": "object", "required": ["version_id"],
        "properties": {
            "version_id": {"type": "string", "minLength": 6, "maxLength": 40},
            "interval_seconds": {"type": "integer", "minimum": 60, "maximum": 86400},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_HIGH, requires_confirmation=True, timeout_s=30,
    idempotency_policy="at_most_once", artifact_contract=("strategy_monitor",),
    executor=_exec_create_strategy_monitor,
))

register_tool(ToolSpec(
    name="generate_market_product",
    description="编译市场级研究产品（mainline_radar / overseas_mapping / daily_brief）",
    input_schema={
        "type": "object", "required": ["kind"],
        "properties": {
            "kind": {"type": "string",
                     "enum": ["mainline_radar", "overseas_mapping", "daily_brief"]},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=60,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_generate_market_product,
))

register_tool(ToolSpec(
    name="memory_search",
    description="检索研究记忆（Playbook 检索，已治理条目）",
    input_schema={
        "type": "object",
        "properties": {
            "q": {"type": "string", "maxLength": 100},
            "memory_type": {"type": "string", "maxLength": 24},
            "status": {"type": "string", "maxLength": 16},
            "instrument_id": {"type": "string", "maxLength": 32},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=15,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_memory_search,
))

register_tool(ToolSpec(
    name="open_page",
    description="请求打开产品页面（白名单；Workbench Handoff 的数据面）",
    input_schema={
        "type": "object", "required": ["page"],
        "properties": {
            "page": {"type": "string", "enum": list(PAGE_WHITELIST)},
            "payload": {"type": "object"},
        },
    },
    output_schema={"type": "object"},
    risk_level=RISK_READ, requires_confirmation=False, timeout_s=5,
    idempotency_policy="idempotent", artifact_contract=(),
    executor=_exec_open_page,
))
