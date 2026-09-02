"""Artifact Registry + Provenance (V2 Phase A, 总纲 §27-§31/§62).

The registry is ONLY a cross-domain index for navigation / lineage /
search / handoff — it never replaces the strongly-typed domain objects
(红线 2). ``domain_type + domain_id`` point at the real row; every
artifact registration is idempotent per (domain_type, domain_id).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.storage.orm import Base


class ArtifactType(str, Enum):
    """First batch = existing objects (总纲 §85); later phases append."""

    RESEARCH_RUN = "research_run"
    REPORT = "report"
    REPORT_VERSION = "report_version"
    PREDICTION = "prediction"
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    CLAIM = "claim"
    THESIS = "thesis"
    EXPERIENCE_CARD = "experience_card"
    WORKFLOW_RUN = "workflow_run"
    SCREENING_RUN = "screening_run"
    STRATEGY_VERSION = "strategy_version"
    STRATEGY_BACKTEST = "strategy_backtest"
    STRATEGY_MONITOR = "strategy_monitor"  # G9：盯盘进入全库图谱（方案 §40）
    INDUSTRY_MAP = "industry_map"
    GLOBAL_CONTEXT = "global_context"
    REVIEW = "review"
    # R9（方案 §15.1）：研究语义对象进图谱
    INDUSTRY_DRIVER = "industry_driver"
    INDUSTRY_TRANSMISSION = "industry_transmission"
    INDUSTRY_NARRATIVE = "industry_narrative"
    INDUSTRY_POSITION = "industry_position"
    RESEARCH_MEMORY = "research_memory"


class RelationType(str, Enum):
    DERIVED_FROM = "derived_from"
    SUPPORTED_BY = "supported_by"
    GENERATED_FROM = "generated_from"
    VALIDATED_BY = "validated_by"
    SUPERSEDES = "supersedes"
    TRIGGERED_BY = "triggered_by"
    PRODUCED = "produced"
    USED_BY = "used_by"


# Which side of the edge is the UPSTREAM side, per relation:
#   "from_upstream" — from --relation--> to   (from 是上游，如 run produced version)
#   "to_upstream"   — from --relation--> to   (to 是上游，如 prediction generated_from report)
RELATION_DIRECTION = {
    RelationType.PRODUCED.value: "from_upstream",
    RelationType.VALIDATED_BY.value: "from_upstream",
    RelationType.SUPERSEDES.value: "from_upstream",
    RelationType.DERIVED_FROM.value: "to_upstream",
    RelationType.GENERATED_FROM.value: "to_upstream",
    RelationType.SUPPORTED_BY.value: "to_upstream",
    RelationType.TRIGGERED_BY.value: "to_upstream",
    RelationType.USED_BY.value: "to_upstream",
}


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactORM(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(32), index=True)
    domain_type: Mapped[str] = mapped_column(String(32))
    domain_id: Mapped[str] = mapped_column(String(64))

    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    instrument_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    as_of_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")

    created_by: Mapped[str] = mapped_column(String(32), default="system")
    route: Mapped[str] = mapped_column(String(256), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("domain_type", "domain_id", name="uq_artifact_domain"),
    )


class ProvenanceEdgeORM(Base):
    __tablename__ = "provenance_edges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    from_artifact_id: Mapped[str] = mapped_column(String(24), index=True)
    to_artifact_id: Mapped[str] = mapped_column(String(24), index=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "from_artifact_id", "to_artifact_id", "relation_type",
            name="uq_provenance_edge",
        ),
    )


class ArtifactService:
    """Registry + provenance writes/reads; session-scoped like other repos."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- registration ----------------------------------------------------------

    def register(
        self,
        *,
        artifact_type: ArtifactType | str,
        domain_type: str,
        domain_id: str,
        title: str,
        summary: str | None = None,
        instrument_ids: tuple[str, ...] | list[str] = (),
        as_of_time: datetime | None = None,
        version: int | None = None,
        created_by: str = "system",
        route: str = "",
        metadata: dict | None = None,
    ) -> str:
        """Idempotent per (domain_type, domain_id): existing rows get their
        title/version refreshed, never duplicated."""
        type_value = (
            artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
        )
        row = self._session.scalars(
            select(ArtifactORM).where(
                ArtifactORM.domain_type == domain_type,
                ArtifactORM.domain_id == domain_id,
            )
        ).first()
        if row is not None:
            row.title = title or row.title
            row.summary = summary if summary is not None else row.summary
            if version is not None:
                row.version = version
            row.status = "active"
            self._session.flush()
            return row.artifact_id
        artifact_id = f"art_{uuid4().hex[:16]}"
        self._session.add(
            ArtifactORM(
                artifact_id=artifact_id,
                artifact_type=type_value,
                domain_type=domain_type,
                domain_id=domain_id,
                title=title,
                summary=summary,
                instrument_ids_json=list(instrument_ids),
                as_of_time=as_of_time,
                version=version,
                status="active",
                created_by=created_by,
                route=route,
                metadata_json=metadata or {},
                created_at=_utc(),
            )
        )
        self._session.flush()
        return artifact_id

    def link(
        self,
        *,
        from_artifact_id: str,
        to_artifact_id: str,
        relation: RelationType | str,
        metadata: dict | None = None,
    ) -> str | None:
        """Idempotent provenance edge; missing endpoints are refused
        explicitly (a provenance edge to nothing is a bug, not a stub)."""
        relation_value = relation.value if isinstance(relation, RelationType) else str(relation)
        for endpoint in (from_artifact_id, to_artifact_id):
            if self.get(endpoint) is None:
                raise ValueError(f"artifact not found: {endpoint}")
        existing = self._session.scalars(
            select(ProvenanceEdgeORM).where(
                ProvenanceEdgeORM.from_artifact_id == from_artifact_id,
                ProvenanceEdgeORM.to_artifact_id == to_artifact_id,
                ProvenanceEdgeORM.relation_type == relation_value,
            )
        ).first()
        if existing is not None:
            return existing.edge_id
        edge_id = f"pe_{uuid4().hex[:16]}"
        self._session.add(
            ProvenanceEdgeORM(
                edge_id=edge_id,
                from_artifact_id=from_artifact_id,
                to_artifact_id=to_artifact_id,
                relation_type=relation_value,
                created_at=_utc(),
                metadata_json=metadata or {},
            )
        )
        self._session.flush()
        return edge_id

    # -- reads -------------------------------------------------------------------

    def get(self, artifact_id: str) -> dict | None:
        row = self._session.scalars(
            select(ArtifactORM).where(ArtifactORM.artifact_id == artifact_id)
        ).first()
        return None if row is None else self._row_to_dict(row)

    def by_domain(self, domain_type: str, domain_id: str) -> dict | None:
        row = self._session.scalars(
            select(ArtifactORM).where(
                ArtifactORM.domain_type == domain_type,
                ArtifactORM.domain_id == domain_id,
            )
        ).first()
        return None if row is None else self._row_to_dict(row)

    def search(
        self,
        query: str = "",
        *,
        artifact_type: str | None = None,
        instrument_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        stmt = select(ArtifactORM).order_by(ArtifactORM.created_at.desc(), ArtifactORM.id.desc())
        if query:
            pattern = f"%{query.upper()}%"
            stmt = stmt.where(func.upper(ArtifactORM.title).like(pattern))
        if artifact_type is not None:
            stmt = stmt.where(ArtifactORM.artifact_type == artifact_type)
        if instrument_id is not None:
            # JSON array containment is engine-specific; bounded registry
            # scale → project and filter in Python for portability.
            rows = self._session.scalars(stmt.limit(500)).all()
            return [
                self._row_to_dict(r)
                for r in rows
                if instrument_id in (r.instrument_ids_json or [])
            ][:limit]
        return [self._row_to_dict(r) for r in self._session.scalars(stmt.limit(limit)).all()]

    def edges_among(self, node_ids: set[str]) -> list[dict]:
        """Every provenance edge whose BOTH endpoints are in the node set."""
        from sqlalchemy import or_

        if not node_ids:
            return []
        rows = self._session.scalars(
            select(ProvenanceEdgeORM).where(
                or_(
                    ProvenanceEdgeORM.from_artifact_id.in_(node_ids),
                    ProvenanceEdgeORM.to_artifact_id.in_(node_ids),
                )
            )
        ).all()
        out = []
        for e in rows:
            if e.from_artifact_id in node_ids and e.to_artifact_id in node_ids:
                out.append(
                    {
                        "edge_id": e.edge_id,
                        "from": e.from_artifact_id,
                        "to": e.to_artifact_id,
                        "relation": e.relation_type,
                    }
                )
        return out

    def _adjacent(self, node: str, direction: str) -> list[tuple[str, str]]:
        """Neighbors of ``node`` in the given direction, honoring each
        relation's upstream side (RELATION_DIRECTION)."""
        adjacent: list[tuple[str, str]] = []
        outgoing = self._session.scalars(
            select(ProvenanceEdgeORM).where(ProvenanceEdgeORM.from_artifact_id == node)
        ).all()
        incoming = self._session.scalars(
            select(ProvenanceEdgeORM).where(ProvenanceEdgeORM.to_artifact_id == node)
        ).all()
        for edge in outgoing:
            upstream_side = RELATION_DIRECTION.get(edge.relation_type)
            if direction == "upstream" and upstream_side == "to_upstream":
                adjacent.append((edge.to_artifact_id, edge.relation_type))
            if direction == "downstream" and upstream_side == "from_upstream":
                adjacent.append((edge.to_artifact_id, edge.relation_type))
        for edge in incoming:
            upstream_side = RELATION_DIRECTION.get(edge.relation_type)
            if direction == "upstream" and upstream_side == "from_upstream":
                adjacent.append((edge.from_artifact_id, edge.relation_type))
            if direction == "downstream" and upstream_side == "to_upstream":
                adjacent.append((edge.from_artifact_id, edge.relation_type))
        return adjacent

    def neighbors(self, artifact_id: str, direction: str, *, max_depth: int = 10) -> list[dict]:
        """BFS over provenance edges with per-relation direction semantics."""
        seen: dict[str, int] = {artifact_id: 0}
        frontier = [artifact_id]
        result: list[dict] = []
        for _ in range(max(1, max_depth)):
            next_frontier: list[str] = []
            for node in frontier:
                for other_id, relation in self._adjacent(node, direction):
                    if other_id in seen:
                        continue
                    seen[other_id] = seen[node] + 1
                    artifact = self.get(other_id)
                    if artifact is not None:
                        result.append(
                            {**artifact, "relation": relation, "depth": seen[other_id]}
                        )
                        next_frontier.append(other_id)
            frontier = next_frontier
            if not frontier:
                break
        return result

    def lineage(self, artifact_id: str, *, max_depth: int = 10) -> dict:
        return {
            "artifact": self.get(artifact_id),
            "upstream": self.neighbors(artifact_id, "upstream", max_depth=max_depth),
            "downstream": self.neighbors(artifact_id, "downstream", max_depth=max_depth),
        }

    @staticmethod
    def _row_to_dict(r: ArtifactORM) -> dict:
        return {
            "artifact_id": r.artifact_id,
            "artifact_type": r.artifact_type,
            "domain_type": r.domain_type,
            "domain_id": r.domain_id,
            "title": r.title,
            "summary": r.summary,
            "instrument_ids": list(r.instrument_ids_json or []),
            "as_of_time": r.as_of_time.isoformat() if r.as_of_time else None,
            "version": r.version,
            "status": r.status,
            "created_by": r.created_by,
            "route": r.route,
            "metadata": r.metadata_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
