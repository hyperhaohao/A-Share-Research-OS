"""WorkflowDefinition API（Guanlan Direct Port G4，方案 §15/§24/§35）.

真正的 Editor 后端：创建/读取图定义、保存新版本（append-only）、
从定义发起运行（202 后台拓扑执行）。图校验失败 → 422 显式拒绝。
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import get_session
from app.services.workflow_definition_service import (
    WorkflowDefinitionService,
    WorkflowGraphError,
)

router = APIRouter(prefix="/workflow-definitions", tags=["workflow-definitions"])


class GraphNodeIn(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    kind: str = Field(min_length=2, max_length=24)
    title: str | None = Field(default=None, max_length=80)
    params: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeIn(BaseModel):
    From: str = Field(alias="from", min_length=1, max_length=40)
    To: str = Field(alias="to", min_length=1, max_length=40)

    model_config = {"populate_by_name": True}


class DefinitionCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    instrument_id: str | None = Field(default=None, max_length=32)
    nodes: list[GraphNodeIn] = Field(min_length=1, max_length=24)
    edges: list[GraphEdgeIn] = Field(default_factory=list, max_length=48)


class VersionSaveIn(BaseModel):
    nodes: list[GraphNodeIn] = Field(min_length=1, max_length=24)
    edges: list[GraphEdgeIn] = Field(default_factory=list, max_length=48)
    note: str | None = Field(default=None, max_length=500)


def _execute_in_background(engine, run_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.application.workflow import WorkflowRepository
    from app.db import session_scope
    from app.services.workflow_service import WorkflowService

    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with session_scope(factory) as worker_session:
        run = WorkflowRepository(worker_session).get_run(run_id)
        if run is None:
            return
        try:
            WorkflowService(worker_session).execute(run)
        except Exception:  # noqa: BLE001 — never kill the process on a workflow
            worker_session.rollback()
            WorkflowRepository(worker_session).update_run(
                run_id, lambda p: {**p, "status": "failed", "error": "workflow execution crashed"}
            )


def _nodes_in(nodes: list[GraphNodeIn]) -> list[dict]:
    return [
        {"key": n.key.strip(), "kind": n.kind.strip(), "title": n.title, "params": n.params}
        for n in nodes
    ]


def _edges_in(edges: list[GraphEdgeIn]) -> list[dict]:
    return [{"from": e.From.strip(), "to": e.To.strip()} for e in edges]


@router.get("")
def list_definitions(
    limit: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    results = WorkflowDefinitionService(session).list_definitions(limit=limit)
    return {"count": len(results), "results": results}


@router.post("", status_code=201)
def create_definition(payload: DefinitionCreateIn, session: Session = Depends(get_session)) -> dict:
    try:
        definition = WorkflowDefinitionService(session).create_definition(
            name=payload.name.strip(),
            nodes=_nodes_in(payload.nodes),
            edges=_edges_in(payload.edges),
            instrument_id=payload.instrument_id,
        )
    except WorkflowGraphError as exc:
        raise AppError("workflow.graph_invalid", status_code=422, detail=exc.reason) from None
    session.commit()
    return {"definition": definition}


@router.get("/{def_id}")
def get_definition(def_id: str, session: Session = Depends(get_session)) -> dict:
    return {"definition": WorkflowDefinitionService(session).get_definition(def_id)}


@router.post("/{def_id}/versions", status_code=201)
def save_version(def_id: str, payload: VersionSaveIn, session: Session = Depends(get_session)) -> dict:
    try:
        version = WorkflowDefinitionService(session).save_version(
            def_id, nodes=_nodes_in(payload.nodes), edges=_edges_in(payload.edges),
            note=payload.note,
        )
    except WorkflowGraphError as exc:
        raise AppError("workflow.graph_invalid", status_code=422, detail=exc.reason) from None
    session.commit()
    return {"version": version}


@router.post("/{def_id}/run", status_code=202)
def run_definition(
    def_id: str,
    version_no: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
) -> dict:
    service = WorkflowDefinitionService(session)
    run = service.run_definition(def_id, version_no=version_no)
    session.commit()
    thread = threading.Thread(
        target=_execute_in_background,
        args=(session.get_bind(), run["run_id"]),
        daemon=True,
    )
    thread.start()
    return {"run": run}
