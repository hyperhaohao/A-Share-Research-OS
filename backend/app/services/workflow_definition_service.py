"""WorkflowDefinition service（Guanlan Direct Port G4，方案 §15/§35）.

图校验（kinds 强类型 / 必须有 data 源 / 恰好一个 output / 无环）+ 版本链 +
从定义发起运行（拓扑序展开为 run nodes，节点参数随节点落库）。
执行器仍是 WorkflowService（不建第二套执行内核）。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.workflow import WorkflowRepository
from app.application.workflow_defs import WorkflowDefinitionRepository
from app.core.errors import AppError

# ASRO 执行器支持的 kinds（donor 25 类目录中可真实执行的部分；§25 不伪造）
NODE_KINDS: dict[str, dict] = {
    "data": {"title": "采集历史日线", "defaults": {"limit": 1200}},
    "rule": {"title": "前向收益规则", "defaults": {"horizon_days": 20, "threshold_pct": 0.0}},
    "expression": {"title": "量化规则表达式", "defaults": {"expr": ""}},
    "validation": {"title": "指标评估", "defaults": {}},
    "output": {"title": "落库与注册", "defaults": {}},
}


class WorkflowGraphError(Exception):
    """Graph validation failure — API layer maps to 422 workflow.graph_invalid."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_graph(nodes: list[dict], edges: list[dict]) -> None:
    if not nodes:
        raise WorkflowGraphError("empty graph")
    keys = []
    for n in nodes:
        kind = str(n.get("kind") or "")
        if kind not in NODE_KINDS:
            raise WorkflowGraphError(f"unknown node kind: {kind}")
        key = str(n.get("key") or "").strip()
        if not key:
            raise WorkflowGraphError("node without key")
        if key in keys:
            raise WorkflowGraphError(f"duplicate node key: {key}")
        keys.append(key)
    keyset = set(keys)
    kinds = {str(n["key"]): str(n["kind"]) for n in nodes}
    if not any(k == "data" for k in kinds.values()):
        raise WorkflowGraphError("graph needs at least one data node")
    outputs = [k for k, v in kinds.items() if v == "output"]
    if len(outputs) != 1:
        raise WorkflowGraphError("graph needs exactly one output node")
    for e in edges:
        src = str(e.get("from") or "")
        dst = str(e.get("to") or "")
        if src not in keyset or dst not in keyset:
            raise WorkflowGraphError(f"edge references unknown node: {src}->{dst}")
    # acyclic (Kahn)
    indeg = {k: 0 for k in keys}
    adj: dict[str, list[str]] = {k: [] for k in keys}
    for e in edges:
        adj[str(e["from"])].append(str(e["to"]))
        indeg[str(e["to"])] += 1
    queue = [k for k in keys if indeg[k] == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen != len(keys):
        raise WorkflowGraphError("graph has a cycle")
    # output must be reachable from data (weak check: data upstream of output)
    reach = set()
    stack = [k for k, v in kinds.items() if v == "data"]
    while stack:
        cur = stack.pop()
        if cur in reach:
            continue
        reach.add(cur)
        stack.extend(adj[cur])
    if outputs[0] not in reach:
        raise WorkflowGraphError("output node not reachable from any data node")


def topo_order(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Kahn with stable key order — the executor walks the returned list."""
    keys = [str(n["key"]) for n in nodes]
    indeg = {k: 0 for k in keys}
    adj: dict[str, list[str]] = {k: [] for k in keys}
    for e in edges:
        adj[str(e["from"])].append(str(e["to"]))
        indeg[str(e["to"])] += 1
    order: list[str] = []
    queue = [k for k in keys if indeg[k] == 0]
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    by_key = {str(n["key"]): n for n in nodes}
    return [by_key[k] for k in order if k in by_key]


class WorkflowDefinitionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = WorkflowDefinitionRepository(session)
        self._runs = WorkflowRepository(session)

    def create_definition(
        self, *, name: str, nodes: list[dict], edges: list[dict],
        instrument_id: str | None = None,
    ) -> dict:
        validate_graph(nodes, edges)
        return self._repo.create_definition(
            name=name, instrument_id=instrument_id, nodes=nodes, edges=edges,
        )

    def save_version(
        self, def_id: str, *, nodes: list[dict], edges: list[dict], note: str | None = None,
    ) -> dict:
        validate_graph(nodes, edges)
        try:
            version = self._repo.add_version(def_id, nodes=nodes, edges=edges, note=note)
        except KeyError:
            raise AppError("workflow.def_not_found", status_code=404) from None
        return version

    def get_definition(self, def_id: str) -> dict:
        definition = self._repo.get_definition(def_id)
        if definition is None:
            raise AppError("workflow.def_not_found", status_code=404)
        definition["versions"] = [
            {"version_no": v["version_no"], "note": v["note"], "created_at": v["created_at"]}
            for v in self._repo.list_versions(def_id)
        ]
        return definition

    def list_definitions(self, *, limit: int = 20) -> list[dict]:
        return self._repo.list_definitions(limit=limit)

    def run_definition(self, def_id: str, *, version_no: int | None = None) -> dict:
        definition = self._repo.get_definition(def_id)
        if definition is None:
            raise AppError("workflow.def_not_found", status_code=404)
        version = (
            self._repo.get_version(def_id, version_no)
            if version_no is not None
            else self._repo.get_version(def_id, definition["current_version"])
        )
        if version is None:
            raise AppError("workflow.version_not_found", status_code=404)
        nodes = list(version["nodes"])
        edges = list(version["edges"])
        validate_graph(nodes, edges)

        ordered = topo_order(nodes, edges)
        node_params = {
            str(n["key"]): {**NODE_KINDS[str(n["kind"])]["defaults"], **(n.get("params") or {})}
            for n in ordered
        }
        run_nodes = [
            {
                "node_id": f"n_{n['key']}",
                "kind": str(n["kind"]),
                "title": str(n.get("title") or NODE_KINDS[str(n["kind"])]["title"]),
                "status": "pending",
                "detail": None,
                "error": None,
            }
            for n in ordered
        ]
        run = self._runs.create_run(
            instrument_id=definition.get("instrument_id") or "DEFINITION",
            kind="definition",
            params={
                "definition": {"def_id": def_id, "version_no": version["version_no"]},
                "node_params": node_params,
            },
            nodes=run_nodes,
            card_id=None,
        )
        self._repo.touch(def_id)
        return run
