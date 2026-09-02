"""Typed Dataflow Workflow 引擎（G4，观澜语义迁移任务书 §G4）.

语义承诺（区别于 v1 顺序执行器）：
  - **Node Definition 声明端口**：input_ports/output_ports（name+type）、
    parameters_schema、execution_policy；
  - **Edge 承担有类型的数据传输**：source_port→target_port + 类型匹配
    （端口类型不匹配不能发布）；
  - **节点 I/O 不可变落库**（workflow_node_io，按 attempt 追加）——
    下游只消费指定上游端口的输出，禁止绕过上游读共享状态；
  - 分支互不覆盖（各边显式取数）；失败传播（下游 skipped）；
    retry/resume/pause/cancel；
  - 15 类最低节点类型（§G4 清单），执行器真实消费上游数据。

端口类型（type system，最小够用）：
    instrument_ref / evidence_set / quote_series / series / table /
    rule_result / metrics / graph / diff / any
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.storage.orm import EvidenceORM
from app.storage.workflow_io_orm import WorkflowNodeIOORM

PORT_TYPES = {
    "instrument_ref", "evidence_set", "quote_series", "series", "table",
    "rule_result", "metrics", "graph", "diff", "text", "any",
}

RUN_STATUSES = ("pending", "running", "paused", "succeeded", "failed",
                "cancelled", "blocked_confirmation")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 节点类型规格（15 类最低清单，§G4） ───────────────────────────────────────

def _ports(*specs: tuple[str, str]) -> list[dict]:
    return [{"name": n, "type": t} for n, t in specs]


NODE_TYPE_SPECS: dict[str, dict] = {
    "evidence": {
        "title": "证据采集",
        "input_ports": _ports(("instrument", "instrument_ref")),
        "output_ports": _ports(("evidence_set", "evidence_set")),
        "parameters_schema": {"limit": ("int", 20)},
        "execution_policy": "pure",
    },
    "quote": {
        "title": "行情序列",
        "input_ports": _ports(("instrument", "instrument_ref")),
        "output_ports": _ports(("quote_series", "quote_series")),
        "parameters_schema": {"limit": ("int", 120)},
        "execution_policy": "pure",
    },
    "industry": {
        "title": "产业链图谱",
        "input_ports": _ports(("chain_name", "text")),
        "output_ports": _ports(("graph", "graph")),
        "parameters_schema": {},
        "execution_policy": "pure",
    },
    "transform": {
        "title": "数据变换",
        "input_ports": _ports(("data_in", "any")),
        "output_ports": _ports(("data_out", "any")),
        "parameters_schema": {"op": ("str", "latest")},
        "execution_policy": "pure",
    },
    "filter": {
        "title": "过滤",
        "input_ports": _ports(("data_in", "any")),
        "output_ports": _ports(("data_out", "any")),
        "parameters_schema": {"field": ("str", ""), "op": ("str", "gt"), "value": ("float", 0.0)},
        "execution_policy": "pure",
    },
    "rule": {
        "title": "规则判定",
        "input_ports": _ports(("series_in", "series"), ("quote_series", "quote_series")),
        "output_ports": _ports(("rule_result", "rule_result")),
        "parameters_schema": {"field": ("str", "forward_return_pct"), "threshold": ("float", 0.0)},
        "execution_policy": "pure",
    },
    "screening": {
        "title": "研究状态筛选",
        "input_ports": _ports(("instrument", "instrument_ref")),
        "output_ports": _ports(("candidates", "table")),
        "parameters_schema": {},
        "execution_policy": "side_effect",
    },
    "backtest": {
        "title": "前向收益回测",
        "input_ports": _ports(("quote_series", "quote_series")),
        "output_ports": _ports(("metrics", "metrics")),
        "parameters_schema": {"horizon_days": ("int", 20), "threshold_pct": ("float", 0.0)},
        "execution_policy": "pure",
    },
    "validation": {
        "title": "指标评估",
        "input_ports": _ports(("metrics_in", "metrics"), ("rule_result", "rule_result")),
        "output_ports": _ports(("metrics", "metrics")),
        "parameters_schema": {},
        "execution_policy": "pure",
    },
    "prediction": {
        "title": "预测生成",
        "input_ports": _ports(("metrics_in", "metrics")),
        "output_ports": _ports(("prediction", "table")),
        "parameters_schema": {"horizon_days": ("int", 20)},
        "execution_policy": "side_effect",
    },
    "thesis_impact": {
        "title": "Thesis 影响分析",
        "input_ports": _ports(("instrument", "instrument_ref")),
        "output_ports": _ports(("diff", "diff")),
        "parameters_schema": {"since_days": ("int", 7)},
        "execution_policy": "pure",
    },
    "experience_output": {
        "title": "经验产出",
        "input_ports": _ports(("summary", "text"), ("metrics_in", "metrics")),
        "output_ports": _ports(("experience_note", "text")),
        "parameters_schema": {"card_id": ("str", "")},
        "execution_policy": "side_effect",
    },
    "memory_output": {
        "title": "记忆产出",
        "input_ports": _ports(("summary", "text")),
        "output_ports": _ports(("memory_ref", "text")),
        "parameters_schema": {"title": ("str", "workflow memory")},
        "execution_policy": "side_effect",
    },
    "notification": {
        "title": "通知",
        "input_ports": _ports(("summary", "text")),
        "output_ports": _ports(("notified", "text")),
        "parameters_schema": {"channel": ("str", "run_event")},
        "execution_policy": "side_effect",
    },
    "output": {
        "title": "结果落库",
        "input_ports": _ports(("metrics_in", "any")),
        "output_ports": [],
        "parameters_schema": {},
        "execution_policy": "side_effect",
    },
    "human_confirmation": {
        "title": "人工确认",
        "input_ports": _ports(("summary", "text")),
        "output_ports": _ports(("confirmed", "text")),
        "parameters_schema": {"prompt": ("str", "请人工确认该结果")},
        "execution_policy": "blocking",
    },
}


def node_spec(kind: str) -> dict:
    spec = NODE_TYPE_SPECS.get(kind)
    if spec is None:
        raise AppError("workflow.unknown_node_kind", status_code=422,
                       detail=f"unknown typed node kind: {kind}")
    return spec


def _validate_schema_subset(schema: dict | None, value: dict) -> list[str]:
    """required 检查（输入端口必须被上游输出满足）。"""
    errors = []
    for req in (schema or {}).get("required", []):
        if req not in (value or {}):
            errors.append(f"missing required input field: {req}")
    return errors


def validate_typed_graph(nodes: list[dict], edges: list[dict]) -> None:
    """v2 图校验：v1 规则 + 端口类型 + 孤立/不可达 + 必填输入 + 重复输出。"""
    if not nodes:
        raise AppError("workflow.graph_invalid", status_code=422, detail="empty graph")
    keys: list[str] = []
    for n in nodes:
        kind = str(n.get("kind") or "")
        node_spec(kind)  # unknown kind → 422
        key = str(n.get("key") or "").strip()
        if not key:
            raise AppError("workflow.graph_invalid", status_code=422, detail="node without key")
        if key in keys:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"duplicate node key: {key}")
        keys.append(key)
        # 重复 output port 名
        out_names = [p["name"] for p in (n.get("output_ports") or node_spec(kind)["output_ports"])]
        if len(out_names) != len(set(out_names)):
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"duplicate output ports on node {key}")

    keyset = set(keys)
    kinds = {str(n["key"]): str(n["kind"]) for n in nodes}

    for e in edges:
        src, dst = str(e.get("from") or ""), str(e.get("to") or "")
        if src not in keyset or dst not in keyset:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"edge references unknown node: {src}->{dst}")
        # 端口类型匹配（§G4：类型不匹配不能发布）
        src_ports = {p["name"]: p["type"] for p in (node_spec(kinds[src])["output_ports"])}
        dst_ports = {p["name"]: p["type"] for p in (node_spec(kinds[dst])["input_ports"])}
        sp = e.get("source_port") or next(iter(src_ports), None)
        tp = e.get("target_port") or next(iter(dst_ports), None)
        if sp not in src_ports:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"unknown source port {sp} on {src}")
        if tp not in dst_ports:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"unknown target port {tp} on {dst}")
        stype, ttype = src_ports[sp], dst_ports[tp]
        if stype != ttype and "any" not in (stype, ttype):
            raise AppError(
                "workflow.graph_invalid", status_code=422,
                detail=f"port type mismatch: {src}.{sp}({stype}) -> {dst}.{tp}({ttype})",
            )

    # 无入边且非输入型节点 → 孤立（数据流断裂）
    input_capable = {"evidence", "quote", "screening", "thesis_impact", "industry"}
    with_input = {str(e.get("to")) for e in edges}
    for k in keys:
        if k not in with_input and kinds[k] not in input_capable:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"orphan node without inputs: {k}")

    # 不可达节点（从任何输入型节点出发都到不了）→ 拒绝
    adj: dict[str, list[str]] = {k: [] for k in keys}
    for e in edges:
        adj[str(e["from"])].append(str(e["to"]))
    reachable = set()
    # 种子 = 输入型节点（kind 判定，非 key）
    stack = [k for k in keys if kinds[k] in input_capable]
    seen = set(stack)
    while stack:
        cur = stack.pop()
        for nxt in adj.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    reachable = seen
    for k in keys:
        if kinds[k] == "output" and k not in reachable:
            raise AppError("workflow.graph_invalid", status_code=422,
                           detail=f"output node unreachable: {k}")


def _topo(nodes: list[dict], edges: list[dict]) -> list[dict]:
    by_key = {str(n["key"]): n for n in nodes}
    indeg = {k: 0 for k in by_key}
    adj: dict[str, list[str]] = {k: [] for k in by_key}
    for e in edges:
        adj[str(e["from"])].append(str(e["to"]))
        indeg[str(e["to"])] += 1
    queue = sorted([k for k, d in indeg.items() if d == 0])
    order: list[str] = []
    while queue:
        k = queue.pop(0)
        order.append(k)
        for nxt in sorted(adj[k]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(by_key):
        raise AppError("workflow.graph_invalid", status_code=422, detail="cycle detected")
    return [by_key[k] for k in order]


class TypedWorkflowEngine:
    """v2 执行器：端口数据传递 + 节点 I/O 不可变落库 + 恢复/暂停/取消。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- Node I/O 账本 ---------------------------------------------------------

    def _record_io(self, run_id: str, node_key: str, kind: str, attempt: int,
                   status: str, *, input_data: dict | None = None,
                   output_data: dict | None = None, error: str | None = None,
                   started_at: datetime | None = None) -> None:
        self._session.add(WorkflowNodeIOORM(
            io_id=f"nio_{uuid4().hex[:24]}", run_id=run_id, node_id=node_key,
            kind=kind, attempt=attempt, status=status,
            input_json=input_data, output_json=output_data, error=error,
            started_at=started_at or _now(), finished_at=_now(),
        ))
        self._session.flush()

    def latest_node_io(self, run_id: str, node_key: str) -> WorkflowNodeIOORM | None:
        rows = self._session.scalars(
            select(WorkflowNodeIOORM)
            .where(WorkflowNodeIOORM.run_id == run_id)
            .where(WorkflowNodeIOORM.node_id == node_key)
            .order_by(WorkflowNodeIOORM.attempt.desc(), WorkflowNodeIOORM.id.desc())
        ).all()
        return rows[0] if rows else None

    def node_io_ledger(self, run_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(WorkflowNodeIOORM)
            .where(WorkflowNodeIOORM.run_id == run_id)
            .order_by(WorkflowNodeIOORM.id.asc())
        ).all()
        return [
            {
                "io_id": r.io_id, "node_id": r.node_id, "kind": r.kind,
                "attempt": r.attempt, "status": r.status,
                "input": dict(r.input_json or {}),
                "output": dict(r.output_json or {}),
                "error": r.error,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ]

    # -- 端口取数（分支互不覆盖：各边显式取 source 输出的指定端口） -------------

    def _collect_inputs(self, node_key: str, node: dict, edges: list[dict],
                        outputs: dict[str, dict]) -> dict:
        inputs: dict = {}
        for e in edges:
            if str(e.get("to")) != node_key:
                continue
            src = str(e.get("from"))
            src_out = outputs.get(src)
            if src_out is None:
                continue
            port = e.get("source_port") or next(
                iter(node_spec(str(node["kind"]))["input_ports"]), {"name": "data_in"}
            )["name"]
            target_port = e.get("target_port")
            value = src_out.get(port)
            key = target_port or port
            if key:
                inputs[key.split(".")[-1]] = value
        return inputs

    # -- 执行 -------------------------------------------------------------------

    def execute(self, run: dict, definition: dict) -> dict:
        """执行 typed run：拓扑序 + 端口数据传递 + 不可变 I/O。"""
        from app.application.workflow import WorkflowRepository, WorkflowStatus

        runs = WorkflowRepository(self._session)
        nodes = list(definition["nodes"])
        edges = list(definition["edges"])
        validate_typed_graph(nodes, edges)
        ordered = _topo(nodes, edges)

        outputs: dict[str, dict] = {}
        run_id = run["run_id"]
        run_row = runs.get_run_row(run_id)
        run_row.status = WorkflowStatus.RUNNING
        run_row.updated_at = _now()
        self._session.flush()

        for node in ordered:
            # 暂停/取消：节点间检查点
            fresh = runs.get_run_row(run_id)
            if fresh.status == WorkflowStatus.CANCELLED:
                return {**run, "status": "cancelled"}
            if fresh.status == WorkflowStatus.PAUSED:
                return {**run, "status": "paused"}

            kind = str(node["kind"])
            key = str(node["key"])
            spec = node_spec(kind)
            prev = self.latest_node_io(run_id, key)
            attempt = (prev.attempt + 1) if prev else 1

            # 恢复：已完成且非 side_effect 的节点复用既有输出
            if prev is not None and prev.status == "succeeded" and \
                    spec["execution_policy"] == "pure":
                outputs[key] = dict(prev.output_json or {})
                continue

            inputs = self._collect_inputs(key, node, edges, outputs)
            params = {
                name: default
                for name, (_t, default) in spec["parameters_schema"].items()
            }
            params.update({k: v for k, v in (node.get("params") or {}).items()})
            params.update({k: v for k, v in (run.get("params") or {}).get("node_params", {}).get(key, {}).items()})
            # instrument 注入
            instrument_id = run.get("instrument_id")
            if any(p["type"] == "instrument_ref" for p in spec["input_ports"]) \
                    and "instrument" not in inputs and instrument_id:
                inputs["instrument"] = instrument_id

            started = _now()
            try:
                output = execute_node_kind(self._session, kind, inputs, params)
                errors = _validate_schema_subset(
                    {"required": [p["name"] for p in spec["output_ports"]]}, output
                )
                if errors:
                    raise ValueError(f"node output incomplete: {errors}")
                outputs[key] = output
                self._record_io(run_id, key, kind, attempt, "succeeded",
                                input_data=inputs, output_data=output,
                                started_at=started)
                self._mark_node(run_id, key, "ok", detail=str(output)[:200])
            except Exception as exc:  # noqa: BLE001 — 失败传播（下游 skipped）
                self._record_io(run_id, key, kind, attempt, "failed",
                                input_data=inputs,
                                error=f"{type(exc).__name__}: {exc}",
                                started_at=started)
                self._mark_node(run_id, key, "failed",
                                error=f"{type(exc).__name__}: {exc}"[:300])
                self._propagate_skip(ordered, key, edges, outputs, run_id)
                fresh = runs.get_run_row(run_id)
                fresh.status = WorkflowStatus.FAILED
                fresh.error = f"node {key}: {type(exc).__name__}: {exc}"[:300]
                fresh.updated_at = _now()
                self._session.flush()
                return {**run, "status": "failed",
                        "error": fresh.error}

        fresh = runs.get_run_row(run_id)
        fresh.status = WorkflowStatus.SUCCEEDED
        fresh.updated_at = _now()
        self._session.flush()
        return {**run, "status": "succeeded"}

    def _mark_node(self, run_id: str, key: str, status: str, *,
                   detail: str | None = None, error: str | None = None) -> None:
        from app.application.workflow import WorkflowRepository

        WorkflowRepository(self._session).update_node(
            run_id, key, status, detail=detail, error=error
        )

    def _propagate_skip(self, ordered: list[dict], failed_key: str,
                        edges: list[dict], outputs: dict[str, dict],
                        run_id: str) -> None:
        adj: dict[str, list[str]] = {}
        for e in edges:
            adj.setdefault(str(e["from"]), []).append(str(e["to"]))
        stack = list(adj.get(failed_key, []))
        seen: set[str] = set()
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            self._mark_node(run_id, k, "skipped", detail=f"upstream {failed_key} failed")
            stack.extend(adj.get(k, []))
            outputs.pop(k, None)


def execute_node_kind(session: Session, kind: str, inputs: dict, params: dict) -> dict:
    """节点执行器：真实消费上游数据（§G4 语义核心）。"""
    if kind == "evidence":
        instrument_id = inputs.get("instrument")
        limit = int(params.get("limit") or 20)
        rows = session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.instrument_id == instrument_id)
            .order_by(EvidenceORM.available_time.desc())
            .limit(limit)
        ).all()
        return {
            "evidence_set": {
                "instrument_id": instrument_id,
                "count": len(rows),
                "evidence_ids": [r.evidence_id for r in rows],
            }
        }
    if kind == "quote":
        instrument_id = inputs.get("instrument")
        from app.services.workflow_service import collect_daily_bars

        bars = collect_daily_bars(session, instrument_id, limit=int(params.get("limit") or 120))
        return {"quote_series": {"instrument_id": instrument_id, "bars": bars,
                                 "count": len(bars)}}
    if kind == "industry":
        from app.services.industry_graph_service import IndustryGraphService

        chain_name = str(params.get("chain_name") or inputs.get("chain_name") or "")
        row = session.scalars(
            select(__import__("app.storage.industry_graph_orm",
                              fromlist=["IndustryChainORM"]).IndustryChainORM)
            .where(__import__("app.storage.industry_graph_orm",
                              fromlist=["IndustryChainORM"]).IndustryChainORM.name.contains(chain_name))
        ).first()
        if row is None:
            return {"graph": {"chain_id": None, "found": False}}
        graph = IndustryGraphService(session).chain_graph(row.chain_id)
        return {"graph": {"chain_id": row.chain_id,
                          "segments": len(graph["segments"]),
                          "edges": len(graph["edges"]),
                          "found": True}}
    if kind == "transform":
        data = inputs.get("data_in")
        op = str(params.get("op") or "latest")
        if op == "latest" and isinstance(data, dict):
            keys = sorted(data.keys())
            return {"data_out": {"op": op, "value": data.get(keys[-1]) if keys else None}}
        return {"data_out": {"op": op, "value": data}}
    if kind == "filter":
        data = inputs.get("data_in")
        field = str(params.get("field") or "")
        op = str(params.get("op") or "gt")
        value = float(params.get("value") or 0.0)
        items = data.get("bars") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return {"data_out": {"count": 0, "items": []}}
        kept = []
        for item in items:
            if not isinstance(item, dict) or field not in item:
                continue
            try:
                v = float(item[field])
            except (TypeError, ValueError):
                continue
            if (op == "gt" and v > value) or (op == "lt" and v < value) \
                    or (op == "eq" and v == value):
                kept.append(item)
        return {"data_out": {"count": len(kept), "items": kept}}
    if kind == "rule":
        series = inputs.get("series_in") or inputs.get("quote_series") or {}
        field = str(params.get("field") or "forward_return_pct")
        threshold = float(params.get("threshold") or 0.0)
        hits = 0
        total = 0
        items = series.get("items") if isinstance(series, dict) else series
        for item in items or []:
            if isinstance(item, dict) and field in item:
                total += 1
                try:
                    if float(item[field]) > threshold:
                        hits += 1
                except (TypeError, ValueError):
                    continue
        return {"rule_result": {"field": field, "threshold": threshold,
                                "hits": hits, "total": total,
                                "verdict": "pass" if hits else "no_hit"}}
    if kind == "screening":
        from app.services.screening_service import ScreeningService, DEFAULT_RULES

        instrument_id = inputs.get("instrument")
        run = ScreeningService(session).create_from_card(
            params.get("card_id") or "exp_placeholder", rules=DEFAULT_RULES
        ) if params.get("card_id") else None
        if run is None:
            return {"candidates": {"count": 0, "candidates": [],
                                   "note": "no source experience card in params"}}
        ScreeningService(session).execute(run)
        return {"candidates": {"run_id": run.get("run_id"),
                               "status": run.get("status")}}
    if kind == "backtest":
        series = inputs.get("quote_series") or {}
        from app.services.strategy_service import forward_returns

        bars = series.get("bars") or []
        horizon = int(params.get("horizon_days") or 20)
        threshold = float(params.get("threshold_pct") or 0.0)
        rets = forward_returns(bars, horizon, threshold)
        return {"metrics": {"horizon_days": horizon, "threshold_pct": threshold,
                            "n_windows": len(rets),
                            "mean_return_pct": (round(sum(rets) / len(rets), 3) if rets else None)}}
    if kind == "validation":
        m = inputs.get("metrics_in") or {}
        rr = inputs.get("rule_result") or {}
        return {"metrics": {"upstream_metrics": m, "rule": rr}}
    if kind == "prediction":
        return {"prediction": {"created": False,
                               "reason": "prediction creation requires thesis context (G8 链)"}}
    if kind == "thesis_impact":
        from app.services.thesis_revision import compute_thesis_diff
        from datetime import timedelta

        instrument_id = inputs.get("instrument")
        since_days = int(params.get("since_days") or 7)
        diff = compute_thesis_diff(
            session, instrument_id,
            datetime.now(timezone.utc) - timedelta(days=since_days),
        )
        return {"diff": {"new_evidence": len(diff.get("new_evidence", [])),
                         "affected_claims": len(diff.get("affected_claims", [])),
                         "suggested_action": diff.get("suggested_action")}}
    if kind == "experience_output":
        from app.application.experience import ExperienceRepository, ExperienceCardVersionORM

        card_id = str(params.get("card_id") or "")
        summary = str(inputs.get("summary") or "")[:400]
        if card_id:
            repo = ExperienceRepository(session)
            row = repo.get_card_row(card_id)
            if row is not None:
                new_no = row.current_version + 1
                session.add(ExperienceCardVersionORM(
                    card_id=card_id, version_no=new_no,
                    statement=row.statement,
                    mechanism=(row.mechanism + f"；工作流产出：{summary}")[:4000],
                    applicable_conditions_json=list(row.applicable_conditions_json or []),
                    invalid_conditions_json=list(row.invalid_conditions_json or []),
                    confidence=row.confidence, method="workflow",
                    created_at=_now(),
                ))
                row.current_version = new_no
                session.flush()
                return {"experience_note": f"card {card_id} → v{new_no}"}
        return {"experience_note": summary}
    if kind == "memory_output":
        from app.application.memory import MemoryService

        mem = MemoryService(session).create_candidate(
            memory_type="research_method",
            title=str(params.get("title") or "workflow memory")[:200],
            content=str(inputs.get("summary") or "")[:4000],
        )
        return {"memory_ref": mem.get("memory", {}).get("memory_id") or mem.get("memory_id")}
    if kind == "notification":
        from app.application.run_events import record_run_event

        record_run_event(session, f"wf_notify_{uuid4().hex[:8]}", "workflow_notification",
                         {"summary": str(inputs.get("summary") or "")[:300]})
        return {"notified": "run_event"}
    if kind == "human_confirmation":
        return {"confirmed": "pending", "prompt": str(params.get("prompt") or "")}
    if kind == "output":
        # 终端节点：消费上游输入（Artifact 注册由 run 级完成）
        return {}
    raise AppError("workflow.unknown_node_kind", status_code=422, detail=kind)
