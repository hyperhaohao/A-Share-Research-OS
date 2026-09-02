"""Typed Workflow API（G4，观澜语义迁移任务书 §G4）.

v2 定义（端口/schema/data_contract）+ typed run 执行/控制/账本。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session, session_scope

router = APIRouter(prefix="/workflows-typed", tags=["workflow-typed"])


class TypedNodeIn(BaseModel):
    key: str = Field(min_length=1, max_length=48)
    kind: str = Field(min_length=2, max_length=32)
    title: str | None = Field(default=None, max_length=120)
    params: dict = Field(default_factory=dict)
    input_ports: list[dict] | None = None
    output_ports: list[dict] | None = None


class TypedEdgeIn(BaseModel):
    from_node: str = Field(alias="from", min_length=1, max_length=48)
    to: str = Field(min_length=1, max_length=48)
    source_port: str | None = Field(default=None, max_length=48)
    target_port: str | None = Field(default=None, max_length=48)


class TypedDefinitionIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    instrument_id: str | None = Field(default=None, max_length=32)
    nodes: list[TypedNodeIn] = Field(min_length=1, max_length=40)
    edges: list[TypedEdgeIn] = Field(default_factory=list, max_length=60)
    note: str | None = Field(default=None, max_length=500)


class TypedRunIn(BaseModel):
    def_id: str = Field(min_length=6, max_length=32)
    version_no: int | None = Field(default=None, ge=1)


def _dump_nodes(nodes: list[TypedNodeIn]) -> list[dict]:
    out = []
    for n in nodes:
        d = {"key": n.key, "kind": n.kind, "params": n.params}
        if n.title:
            d["title"] = n.title
        if n.input_ports is not None:
            d["input_ports"] = n.input_ports
        if n.output_ports is not None:
            d["output_ports"] = n.output_ports
        out.append(d)
    return out


def _dump_edges(edges: list[TypedEdgeIn]) -> list[dict]:
    return [
        {"from": e.from_node, "to": e.to,
         "source_port": e.source_port, "target_port": e.target_port}
        for e in edges
    ]


@router.post("/definitions", status_code=201)
def create_typed_definition(payload: TypedDefinitionIn,
                            session: Session = Depends(get_session)) -> dict:
    from app.application.workflow_defs import WorkflowDefinitionRepository
    from app.services.workflow_typed import validate_typed_graph

    nodes, edges = _dump_nodes(payload.nodes), _dump_edges(payload.edges)
    validate_typed_graph(nodes, edges)  # 端口类型不匹配 → 422（不能发布）
    repo = WorkflowDefinitionRepository(session)
    out = repo.create_definition(
        name=payload.name, instrument_id=payload.instrument_id,
        nodes=nodes, edges=edges,
    )
    session.commit()
    return {"definition": out}


@router.post("/runs", status_code=202)
def run_typed_definition(payload: TypedRunIn,
                         session: Session = Depends(get_session)) -> dict:
    from app.application.workflow import WorkflowRepository
    from app.application.workflow_defs import WorkflowDefinitionRepository
    from app.services.workflow_typed import TypedWorkflowEngine

    defs = WorkflowDefinitionRepository(session)
    definition = defs.get_definition(payload.def_id)
    if definition is None:
        raise AppError("workflow.def_not_found", status_code=404)
    version = defs.get_version(
        payload.def_id,
        payload.version_no if payload.version_no is not None else definition["current_version"],
    )
    if version is None:
        raise AppError("workflow.version_not_found", status_code=404)

    runs = WorkflowRepository(session)
    run = runs.create_run(
        instrument_id=definition.get("instrument_id") or "DEFINITION",
        kind="typed",
        params={"definition": {"def_id": payload.def_id,
                               "version_no": version["version_no"]}},
        nodes=[
            {"node_id": f"n_{n['key']}", "key": n["key"], "kind": n["kind"],
             "title": str(n.get("title") or n["key"]),
             "status": "pending", "detail": None, "error": None}
            for n in version["nodes"]
        ],
        card_id=None,
    )
    session.commit()

    engine = TypedWorkflowEngine(session)
    result = engine.execute(run, version)
    session.commit()
    return {"run": result}


@router.get("/runs/{run_id}")
def get_typed_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    from app.application.workflow import WorkflowRepository
    from app.services.workflow_typed import TypedWorkflowEngine

    run = WorkflowRepository(session).get_run(run_id)
    if run is None:
        raise AppError("workflow.run_not_found", status_code=404)
    ledger = TypedWorkflowEngine(session).node_io_ledger(run_id)
    return {"run": run, "node_io": ledger}


class TypedControlIn(BaseModel):
    action: str = Field(min_length=4, max_length=10)


@router.post("/runs/{run_id}/control")
def control_typed_run(run_id: str, payload: TypedControlIn,
                      session: Session = Depends(get_session)) -> dict:
    """pause / resume / cancel / retry（§G4 运行控制）。"""
    from app.application.workflow import WorkflowRepository, WorkflowStatus
    from app.application.workflow_defs import WorkflowDefinitionRepository
    from app.services.workflow_typed import TypedWorkflowEngine

    runs = WorkflowRepository(session)
    row = runs.get_run_row(run_id)
    if row is None:
        raise AppError("workflow.run_not_found", status_code=404)
    action = payload.action
    if action == "pause":
        if row.status != WorkflowStatus.RUNNING:
            raise AppError("workflow.not_pausable", status_code=422,
                           detail=f"status={row.status}")
        row.status = WorkflowStatus.PAUSED
    elif action == "resume":
        if row.status != WorkflowStatus.PAUSED:
            raise AppError("workflow.not_resumable", status_code=422,
                           detail=f"status={row.status}")
        row.status = WorkflowStatus.RUNNING
    elif action == "cancel":
        if row.status not in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED, "pending"):
            raise AppError("workflow.not_cancellable", status_code=422,
                           detail=f"status={row.status}")
        row.status = WorkflowStatus.CANCELLED
    elif action == "retry":
        if row.status not in (WorkflowStatus.FAILED, WorkflowStatus.CANCELLED,
                              WorkflowStatus.PAUSED):
            raise AppError("workflow.not_retryable", status_code=422,
                           detail=f"status={row.status}")
        definition_version = (row.params_json or {}).get("definition") or {}
        defs = WorkflowDefinitionRepository(session)
        version = defs.get_version(definition_version.get("def_id"),
                                   definition_version.get("version_no"))
        if version is None:
            raise AppError("workflow.version_not_found", status_code=404) from None
        # 重新执行（恢复：纯节点复用既有输出；失败节点重跑 attempt+1）
        run = runs.get_run(run_id)
        result = TypedWorkflowEngine(session).execute(run, version)
        session.commit()
        return {"run": result}
    else:
        raise AppError("workflow.bad_action", status_code=422,
                       detail="action must be pause|resume|cancel|retry") from None
    row.updated_at = __import__("datetime", fromlist=["timezone"]).datetime.now(
        __import__("datetime", fromlist=["timezone"]).timezone.utc)
    session.commit()
    return {"run_id": run_id, "status": row.status}
