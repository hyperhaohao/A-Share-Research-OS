"""WorkflowDefinition / WorkflowVersion persistence（Guanlan Direct Port G4，方案 §15）.

真正的 Editor 后端：图定义（nodes/edges）版本化落库（append-only 版本链），
运行时经 WorkflowService 以拓扑序执行。节点 kinds 与执行器强类型对应
（data/rule/expression/validation/output），ASRO 能执行什么，目录就有什么 ——
不伪造 donor 板库未接引擎的节点。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _short_hex() -> str:
    return uuid4().hex[:12]


class WorkflowDefinitionORM(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    def_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    instrument_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowDefinitionVersionORM(Base):
    __tablename__ = "workflow_definition_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    def_id: Mapped[str] = mapped_column(String(24), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    nodes_json: Mapped[list] = mapped_column(JSON, default=list)
    edges_json: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _def_to_dict(row: WorkflowDefinitionORM) -> dict:
    return {
        "def_id": row.def_id,
        "name": row.name,
        "instrument_id": row.instrument_id,
        "current_version": row.current_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _version_to_dict(row: WorkflowDefinitionVersionORM) -> dict:
    return {
        "version_no": row.version_no,
        "nodes": list(row.nodes_json or []),
        "edges": list(row.edges_json or []),
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class WorkflowDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_definition(
        self, *, name: str, instrument_id: str | None,
        nodes: list[dict], edges: list[dict],
    ) -> dict:
        now = _utc()
        def_id = f"wfdef_{_short_hex()}"
        row = WorkflowDefinitionORM(
            def_id=def_id,
            name=name,
            instrument_id=instrument_id,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        version = WorkflowDefinitionVersionORM(
            def_id=def_id,
            version_no=1,
            nodes_json=nodes,
            edges_json=edges,
            note=None,
            created_at=now,
        )
        self._session.add(version)
        self._session.flush()
        return {**_def_to_dict(row), "nodes": nodes, "edges": edges}

    def get_definition(self, def_id: str) -> dict | None:
        row = self._session.scalars(
            select(WorkflowDefinitionORM).where(WorkflowDefinitionORM.def_id == def_id)
        ).first()
        if row is None:
            return None
        version = self._session.scalars(
            select(WorkflowDefinitionVersionORM)
            .where(
                WorkflowDefinitionVersionORM.def_id == def_id,
                WorkflowDefinitionVersionORM.version_no == row.current_version,
            )
        ).first()
        out = _def_to_dict(row)
        out["nodes"] = list(version.nodes_json or []) if version else []
        out["edges"] = list(version.edges_json or []) if version else []
        return out

    def list_definitions(self, *, limit: int = 20) -> list[dict]:
        rows = self._session.scalars(
            select(WorkflowDefinitionORM)
            .order_by(WorkflowDefinitionORM.updated_at.desc(), WorkflowDefinitionORM.id.desc())
            .limit(limit)
        ).all()
        return [_def_to_dict(r) for r in rows]

    def list_versions(self, def_id: str) -> list[dict]:
        rows = self._session.scalars(
            select(WorkflowDefinitionVersionORM)
            .where(WorkflowDefinitionVersionORM.def_id == def_id)
            .order_by(WorkflowDefinitionVersionORM.version_no.desc())
        ).all()
        return [_version_to_dict(r) for r in rows]

    def get_version(self, def_id: str, version_no: int) -> dict | None:
        row = self._session.scalars(
            select(WorkflowDefinitionVersionORM)
            .where(
                WorkflowDefinitionVersionORM.def_id == def_id,
                WorkflowDefinitionVersionORM.version_no == version_no,
            )
        ).first()
        return None if row is None else _version_to_dict(row)

    def add_version(
        self, def_id: str, *, nodes: list[dict], edges: list[dict], note: str | None,
    ) -> dict:
        row = self._session.scalars(
            select(WorkflowDefinitionORM).where(WorkflowDefinitionORM.def_id == def_id)
        ).first()
        if row is None:
            raise KeyError(def_id)
        version_no = row.current_version + 1
        self._session.add(
            WorkflowDefinitionVersionORM(
                def_id=def_id,
                version_no=version_no,
                nodes_json=nodes,
                edges_json=edges,
                note=note,
                created_at=_utc(),
            )
        )
        row.current_version = version_no
        row.updated_at = _utc()
        self._session.flush()
        return {
            "def_id": def_id,
            "version_no": version_no,
            "nodes": nodes,
            "edges": edges,
            "note": note,
        }

    def touch(self, def_id: str) -> None:
        row = self._session.scalars(
            select(WorkflowDefinitionORM).where(WorkflowDefinitionORM.def_id == def_id)
        ).first()
        if row is not None:
            row.updated_at = _utc()
