"""Research Graph (任务书 §47): derived traceability graph + traversal.

Node kinds mirror the research state:
    source → evidence → snapshot → claim → thesis → report_version
plus corporate_event, research_run, valuation where present.

Edges are the reference relations that already exist between objects:
    evidence   --pinned-by-->  snapshot
    source     --produced-->   evidence
    claim      --cites-->      evidence
    thesis     --composed-of-> claim
    report     --renders-->    thesis / claim / evidence (via content)
    run        --bound-to-->   snapshot

Upstream traversal from a node answers "where did this come from";
downstream traversal answers "what does this influence" (§95).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.manifest_repo import ReportVersionORM, _ensure_utc
from app.storage.orm import EvidenceORM, ResearchRunORM, SnapshotORM
from app.storage.prediction_repo import PredictionORM, ValidationORM
from app.storage.research_orm import ClaimORM, CorporateEventORM, ThesisORM
from app.storage.report_repo import ReportORM
from app.storage.valuation_repo import ValuationORM


@dataclass
class GraphNode:
    node_id: str
    kind: str
    label: str
    created_at: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    src: str  # upstream node id
    dst: str  # downstream node id
    relation: str


class ResearchGraph:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adj: dict[str, list[GraphEdge]] = defaultdict(list)
        self._radj: dict[str, list[GraphEdge]] = defaultdict(list)

    # -- construction ---------------------------------------------------------
    def build_for_instrument(self, instrument_id: str) -> "ResearchGraph":
        claims = self._session.scalars(
            select(ClaimORM).where(ClaimORM.instrument_id == instrument_id)
        ).all()
        theses = self._session.scalars(
            select(ThesisORM).where(ThesisORM.instrument_id == instrument_id)
        ).all()
        evidence_rows = self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.instrument_id == instrument_id)
        ).all()
        snapshots = self._session.scalars(
            select(SnapshotORM).where(SnapshotORM.instrument_id == instrument_id)
        ).all()
        runs = self._session.scalars(
            select(ResearchRunORM).where(ResearchRunORM.instrument_id == instrument_id)
        ).all()
        reports = self._session.scalars(
            select(ReportORM).where(ReportORM.instrument_id == instrument_id)
        ).all()
        versions = self._session.scalars(select(ReportVersionORM)).all()
        versions = [v for v in versions if v.report_id in {r.report_id for r in reports}]
        events = self._session.scalars(
            select(CorporateEventORM).where(CorporateEventORM.instrument_id == instrument_id)
        ).all()
        valuations = self._session.scalars(
            select(ValuationORM).where(ValuationORM.instrument_id == instrument_id)
        ).all()
        all_predictions = self._session.scalars(
            select(PredictionORM).where(PredictionORM.instrument_id == instrument_id)
        ).all()
        all_validations = self._session.scalars(select(ValidationORM)).all()
        validation_by_prediction = {
            v.prediction_id: v for v in all_validations
        }

        # source → evidence
        for ev in evidence_rows:
            src_id = f"source:{ev.source}"
            ev_id = f"evidence:{ev.evidence_id}"
            self._add_node(GraphNode(src_id, "source", ev.source))
            self._add_node(
                GraphNode(
                    ev_id, "evidence", ev.title[:80],
                    created_at=_ensure_utc(ev.available_time).isoformat()
                    if ev.available_time else None,
                    detail={"authority": ev.authority_level, "fact_status": ev.fact_status},
                )
            )
            self._add_edge(src_id, ev_id, "produced")

        # evidence → snapshot
        for snap in snapshots:
            snap_id = f"snapshot:{snap.snapshot_id}"
            self._add_node(
                GraphNode(
                    snap_id, "snapshot", f"snapshot ({len(snap.items_json or [])} items)",
                    created_at=_ensure_utc(snap.created_at).isoformat()
                    if snap.created_at else None,
                )
            )
            for item in snap.items_json or []:
                ev_id = f"evidence:{item['evidence_id']}"
                if ev_id in self.nodes:
                    self._add_edge(ev_id, snap_id, "pinned-by")

        # claim → evidence; snapshot → claim
        for c in claims:
            claim_id = f"claim:{c.claim_id}"
            self._add_node(
                GraphNode(
                    claim_id, "claim", c.statement[:80],
                    created_at=_ensure_utc(c.created_at).isoformat()
                    if c.created_at else None,
                    detail={"claim_type": c.claim_type, "confidence": c.confidence},
                )
            )
            for ref in (c.supporting_evidence_refs_json or []) + (
                c.opposing_evidence_refs_json or []
            ):
                ev_id = f"evidence:{ref}"
                if ev_id in self.nodes:
                    self._add_edge(ev_id, claim_id, "cited-by")
            snap_id = f"snapshot:{c.snapshot_id}"
            if snap_id in self.nodes:
                self._add_edge(snap_id, claim_id, "produced-in")

        # claim → thesis
        for t in theses:
            thesis_id = f"thesis:{t.thesis_id}"
            self._add_node(
                GraphNode(
                    thesis_id, "thesis", t.title[:80],
                    created_at=_ensure_utc(t.created_at).isoformat()
                    if t.created_at else None,
                    detail={"status": t.status, "confidence": t.confidence},
                )
            )
            for cid in (t.supporting_claims_json or []) + (t.opposing_claims_json or []):
                c_id = f"claim:{cid}"
                if c_id in self.nodes:
                    self._add_edge(c_id, thesis_id, "supports-or-opposes")

        # corporate events: evidence → event
        for ev_row in events:
            ev_node = f"corporate_event:{ev_row.event_id}"
            self._add_node(
                GraphNode(
                    ev_node, "corporate_event", ev_row.title[:80],
                    created_at=_ensure_utc(ev_row.occurred_at).isoformat()
                    if ev_row.occurred_at else None,
                    detail={"event_type": ev_row.event_type},
                )
            )
            for ref in ev_row.evidence_refs_json or []:
                ev_id = f"evidence:{ref}"
                if ev_id in self.nodes:
                    self._add_edge(ev_id, ev_node, "evidences")

        # run → snapshot
        for r in runs:
            run_id = f"run:{r.run_id}"
            self._add_node(
                GraphNode(
                    run_id, "research_run", f"research run ({r.run_type})",
                    created_at=_ensure_utc(r.as_of).isoformat() if r.as_of else None,
                    detail={"status": r.status},
                )
            )
            if r.snapshot_id:
                snap_id = f"snapshot:{r.snapshot_id}"
                if snap_id in self.nodes:
                    self._add_edge(snap_id, run_id, "bound-to")

        # valuation nodes: claim/evidence → valuation
        for v in valuations:
            val_node = f"valuation:{v.valuation_id}"
            self._add_node(
                GraphNode(
                    val_node, "valuation", f"{v.method} → {v.value if v.computable else 'N/A'}",
                    created_at=_ensure_utc(v.created_at).isoformat()
                    if v.created_at else None,
                    detail={"method": v.method, "computable": v.computable},
                )
            )
            if v.thesis_id:
                t_id = f"thesis:{v.thesis_id}"
                if t_id in self.nodes:
                    self._add_edge(t_id, val_node, "valued-by")

        # prediction/validation nodes
        for p in all_predictions:
            pred_node = f"prediction:{p.prediction_id}"
            self._add_node(
                GraphNode(
                    pred_node, "prediction", f"{p.horizon} {p.expected_direction}",
                    created_at=_ensure_utc(p.created_at).isoformat()
                    if p.created_at else None,
                    detail={"confidence": p.confidence},
                )
            )
            if p.research_run_id:
                run_id_node = f"run:{p.research_run_id}"
                if run_id_node in self.nodes:
                    self._add_edge(run_id_node, pred_node, "predicted-in")

            val = validation_by_prediction.get(p.prediction_id)
            if val:
                val_node = f"validation:{val.validation_id}"
                self._add_node(
                    GraphNode(
                        val_node, "validation",
                        f"return {val.instrument_return_pct:.2f}%",
                        created_at=_ensure_utc(val.validated_at).isoformat()
                        if val.validated_at else None,
                        detail={"direction_correct": val.direction_correct,
                                "range_hit": val.range_hit},
                    )
                )
                self._add_edge(pred_node, val_node, "validated-by")

        # thesis/claim/evidence → report version
        for rep in reports:
            rep_base = f"report:{rep.report_id}"
            self._add_node(
                GraphNode(
                    rep_base, "report", f"report ({rep.language})",
                    created_at=rep.created_at.isoformat() if rep.created_at else None,
                )
            )
            for v in versions:
                if v.report_id != rep.report_id:
                    continue
                ver_id = f"report_version:{v.version_id}"
                self._add_node(
                    GraphNode(
                        ver_id, "report_version", f"v{v.version_no} ({v.language})",
                        created_at=_ensure_utc(v.created_at).isoformat()
                        if v.created_at else None,
                        detail={"version_no": v.version_no, "gate": rep.gate_status},
                    )
                )
                self._add_edge(rep_base, ver_id, "versioned-as")
                for t in theses:
                    self._add_edge(f"thesis:{t.thesis_id}", ver_id, "compiled-into")
                # citations
                for ev_id_key in (v.content_json or {}).get("citations", []):
                    ev_id = f"evidence:{ev_id_key}"
                    if ev_id in self.nodes:
                        self._add_edge(ev_id, ver_id, "cited-in")

        return self

    def _add_node(self, node: GraphNode) -> None:
        self.nodes.setdefault(node.node_id, node)

    def _add_edge(self, src: str, dst: str, relation: str) -> None:
        edge = GraphEdge(src, dst, relation)
        self.edges.append(edge)
        self._adj[src].append(edge)
        self._radj[dst].append(edge)

    # -- traversal ------------------------------------------------------------
    def trace(self, node_id: str, direction: str, *, max_depth: int = 10) -> dict:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        adjacency = self._radj if direction == "upstream" else self._adj
        visited: dict[str, int] = {node_id: 0}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        edges: list[GraphEdge] = []
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in adjacency.get(current, []):
                nxt = edge.src if direction == "upstream" else edge.dst
                edges.append(edge)
                if nxt not in visited:
                    visited[nxt] = depth + 1
                    queue.append((nxt, depth + 1))
        return {
            "node": self.nodes[node_id].__dict__ | {"node_id": node_id, "kind": self.nodes[node_id].kind},
            "direction": direction,
            "nodes": [
                {**{"node_id": n.node_id, "kind": n.kind, "label": n.label},
                 "depth": visited[n.node_id]}
                for n in (self.nodes[nid] for nid in visited)
            ],
            "edges": [{"src": e.src, "dst": e.dst, "relation": e.relation} for e in edges],
        }

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"node_id": n.node_id, "kind": n.kind, "label": n.label,
                 "created_at": n.created_at, "detail": n.detail}
                for n in self.nodes.values()
            ],
            "edges": [{"src": e.src, "dst": e.dst, "relation": e.relation} for e in self.edges],
        }
