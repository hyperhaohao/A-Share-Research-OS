"""真实 Industry Graph 服务（G1，观澜语义迁移任务书 §G1）.

语义承诺：
  - 产业链与行业分类**分表分 API**：industry_chains/segments/edges 与
    行业分类字符串（industry_view_service）彻底分离；
  - Edge 可计算：9 类 relation_type、方向、时滞、强度、置信级别；
  - Edge 可引用：每条边经 IndustryEdgeEvidence 链接支撑/反对证据；
  - Edge 可 PIT：valid_from/valid_to + created_at + as_of 过滤可重放；
  - Evidence Ownership Gate：证据必须真实存在、可用时间 ≤ as_of、
    且与链上公司位置或链主题相关（跨产业证据注入被拒）；
  - 置信派生：支撑证据数（按来源独立性去重，F4 服务复用）→
    strength/confidence_level/status；删除关键证据自动降级；
  - 一家公司可位于多个产业链/环节；Peer 来自同环节共位关系。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.industry_graph import (
    EDGE_STATUSES,
    MIN_PUBLISH_EVIDENCE,
    CompanyIndustryPosition,
    IndustryChain,
    IndustryEdge,
    IndustryEdgeEvidenceLink,
    IndustryProduct,
    IndustrySegment,
    RelationType,
)
from app.storage.industry_graph_orm import (
    CompanyIndustryPositionORM,
    IndustryChainORM,
    IndustryEdgeEvidenceORM,
    IndustryEdgeORM,
    IndustryProductORM,
    IndustrySegmentORM,
)
from app.storage.orm import EvidenceORM

RELATION_TYPES = {r.value for r in RelationType}
_ROLES = {"producer", "processor", "consumer", "supplier", "recycler"}
_DIRECTIONS = {"positive", "negative"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


class IndustryGraphService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Chain / Segment / Product ───────────────────────────────────────────

    def create_chain(self, name: str, description: str = "") -> dict:
        exists = self._session.scalars(
            select(IndustryChainORM).where(IndustryChainORM.name == name)
        ).first()
        if exists is not None:
            return self._chain_dict(exists)
        row = IndustryChainORM(
            chain_id=f"chain_{uuid4().hex[:16]}", name=name[:128],
            description=description, version=1, created_at=_now(),
        )
        self._session.add(row)
        self._session.flush()
        return self._chain_dict(row)

    def create_segment(self, chain_id: str, name: str, stage_order: int = 0,
                       description: str = "") -> dict:
        chain = self._get_chain_row(chain_id)
        if chain is None:
            raise AppError("industry_graph.chain_not_found", status_code=404)
        row = IndustrySegmentORM(
            segment_id=f"seg_{uuid4().hex[:16]}", chain_id=chain_id,
            name=name[:128], stage_order=int(stage_order),
            description=description, created_at=_now(),
        )
        self._session.add(row)
        self._session.flush()
        self._bump_chain(chain)
        return self._segment_dict(row)

    def create_product(self, name: str, unit: str = "", description: str = "") -> dict:
        row = IndustryProductORM(
            product_id=f"prd_{uuid4().hex[:16]}", name=name[:128], unit=unit,
            description=description, created_at=_now(),
        )
        self._session.add(row)
        self._session.flush()
        return self._product_dict(row)

    def list_chains(self) -> list[dict]:
        rows = self._session.scalars(
            select(IndustryChainORM).order_by(IndustryChainORM.created_at.desc())
        ).all()
        return [self._chain_dict(r) for r in rows]

    # ── Edge（含 Evidence Ownership Gate） ──────────────────────────────────

    def create_edge(
        self, *,
        chain_id: str,
        source_segment_id: str,
        target_segment_id: str,
        relation_type: str,
        input_product_ids: list[str] | None = None,
        output_product_ids: list[str] | None = None,
        transmission_metric: str = "",
        direction: str = "positive",
        lag_min_days: int = 0,
        lag_max_days: int = 0,
        evidence_ids: list[str] | None = None,
        snapshot_id: str | None = None,
        as_of: datetime | None = None,
    ) -> dict:
        if relation_type not in RELATION_TYPES:
            raise AppError(
                "industry_graph.invalid_relation", status_code=422,
                detail=f"relation_type must be one of {sorted(RELATION_TYPES)}",
            ) from None
        if direction not in _DIRECTIONS:
            raise AppError("industry_graph.invalid_direction", status_code=422) from None
        chain = self._get_chain_row(chain_id)
        if chain is None:
            raise AppError("industry_graph.chain_not_found", status_code=404) from None
        src = self._get_segment_row(source_segment_id)
        tgt = self._get_segment_row(target_segment_id)
        if src is None or tgt is None or src.chain_id != chain_id or tgt.chain_id != chain_id:
            raise AppError(
                "industry_graph.segment_not_in_chain", status_code=422,
                detail="both segments must exist and belong to the chain",
            ) from None
        if source_segment_id == target_segment_id:
            raise AppError("industry_graph.self_edge", status_code=422) from None

        edge = IndustryEdgeORM(
            edge_id=f"edge_{uuid4().hex[:16]}", chain_id=chain_id,
            source_segment_id=source_segment_id, target_segment_id=target_segment_id,
            relation_type=relation_type,
            input_product_ids_json=list(input_product_ids or []),
            output_product_ids_json=list(output_product_ids or []),
            transmission_metric=transmission_metric[:200],
            direction=direction,
            lag_min_days=max(int(lag_min_days), 0),
            lag_max_days=max(int(lag_max_days), 0),
            valid_from=_now(), status="insufficient", version=1,
            snapshot_id=snapshot_id, created_at=_now(),
        )
        self._session.add(edge)
        self._session.flush()

        # Evidence Ownership Gate（§G1/G2）：证据存在 + PIT + 产业归属
        now = as_of or _now()
        for evidence_id in evidence_ids or []:
            self.attach_edge_evidence(
                edge.edge_id, evidence_id, stance="support", as_of=now,
            )
        self._recompute_edge(edge.edge_id)
        self._bump_chain(chain)
        return self.get_edge(edge.edge_id)

    def attach_edge_evidence(
        self, edge_id: str, evidence_id: str, *, stance: str = "support",
        as_of: datetime | None = None,
    ) -> dict:
        from app.domain.industry_graph import IndustryEdgeEvidenceLink

        if stance not in ("support", "contrary"):
            raise AppError("industry_graph.invalid_stance", status_code=422) from None
        edge = self._get_edge_row(edge_id)
        if edge is None:
            raise AppError("industry_graph.edge_not_found", status_code=404) from None
        ev = self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id == evidence_id)
        ).first()
        if ev is None:
            raise AppError("industry_graph.evidence_not_found", status_code=404) from None

        now = _ensure_aware(as_of) or _now()
        available = _ensure_aware(ev.available_time)
        # PIT 门：证据可用时间不得晚于归属时点
        if available is not None and available > now:
            raise AppError(
                "industry_graph.evidence_not_yet_available", status_code=422,
                detail=f"evidence available_at {available.isoformat()} > as_of {now.isoformat()}",
            ) from None

        # Ownership 门：证据须与本链相关 —— 证据标的在链上有 Company Position，
        # 或证据文本/标题含链名或任一环节名（产业级公告）。
        if not self._evidence_relates_to_chain(edge.chain_id, ev):
            raise AppError(
                "industry_graph.evidence_ownership_rejected", status_code=422,
                detail=(
                    f"evidence {evidence_id} ({ev.instrument_id}) has no relation to "
                    f"chain {edge.chain_id}: no company position on this chain and "
                    "no chain/segment mention"
                ),
            ) from None

        link = IndustryEdgeEvidenceORM(
            link_id=f"eev_{uuid4().hex[:16]}", edge_id=edge_id,
            evidence_id=evidence_id, stance=stance, added_at=_now(),
        )
        self._session.add(link)
        self._session.flush()
        self._recompute_edge(edge_id)
        return {
            "link_id": link.link_id, "edge_id": edge_id,
            "evidence_id": evidence_id, "stance": stance,
        }

    def remove_edge_evidence(self, edge_id: str, evidence_id: str,
                             *, stance: str = "support") -> dict:
        """删除边证据 → 自动重算置信；关键证据缺失自动降级（§G1 DoD）。"""
        row = self._session.scalars(
            select(IndustryEdgeEvidenceORM)
            .where(IndustryEdgeEvidenceORM.edge_id == edge_id)
            .where(IndustryEdgeEvidenceORM.evidence_id == evidence_id)
            .where(IndustryEdgeEvidenceORM.stance == stance)
        ).first()
        if row is None:
            raise AppError("industry_graph.evidence_link_not_found", status_code=404) from None
        self._session.delete(row)
        self._session.flush()
        self._recompute_edge(edge_id)
        return self.get_edge(edge_id)

    def _recompute_edge(self, edge_id: str) -> None:
        """置信派生：支撑证据（独立来源组去重）→ strength/confidence/status。

        - 支撑证据 0 → status=insufficient（不可发布）
        - 有支撑但少于发布门槛或存在未决反对 → degraded
        - 达到门槛且无未消解反对 → active
        """
        edge = self._get_edge_row(edge_id)
        if edge is None:
            return
        links = self._session.scalars(
            select(IndustryEdgeEvidenceORM)
            .where(IndustryEdgeEvidenceORM.edge_id == edge_id)
        ).all()
        support_ids = [l.evidence_id for l in links if l.stance == "support"]
        contrary_count = sum(1 for l in links if l.stance == "contrary")

        independent_groups = support_ids
        if support_ids:
            from app.services.source_independence import independent_group_count

            ev_rows = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id.in_(support_ids))
            ).all()
            independent_groups_count = independent_group_count(ev_rows)
            n_support = len(support_ids)
            n_groups = max(independent_groups_count, 1)
            # strength：独立来源组为主，同源转载不加分（F4 语义复用）
            strength = round(min(0.35 * n_groups + 0.1 * (n_support - n_groups), 0.95), 2)
            if strength >= 0.7:
                confidence = "high"
            elif strength >= 0.45:
                confidence = "medium"
            else:
                confidence = "low"
            if n_support < MIN_PUBLISH_EVIDENCE:
                status = "insufficient"
            elif contrary_count > 0:
                status = "degraded"
            elif independent_groups_count >= 2 and confidence == "high":
                status = "active"
            else:
                status = "degraded"
        else:
            strength = 0.0
            confidence = "insufficient"
            status = "insufficient"

        edge.strength = strength
        edge.confidence_level = confidence
        edge.status = status if status in EDGE_STATUSES else "insufficient"
        edge.version = edge.version + 1
        self._session.flush()

    def get_edge(self, edge_id: str) -> dict:
        row = self._get_edge_row(edge_id)
        if row is None:
            raise AppError("industry_graph.edge_not_found", status_code=404) from None
        d = self._edge_dict(row)
        d["evidence"] = self._edge_evidence(edge_id, as_of=None)
        return d

    # ── Company Industry Position ───────────────────────────────────────────

    def create_position(
        self, *,
        instrument_id: str,
        chain_id: str,
        segment_id: str,
        role: str,
        revenue_exposure_pct: float | None = None,
        profit_exposure_pct: float | None = None,
        capacity_note: str = "",
        evidence_ids: list[str] | None = None,
        snapshot_id: str | None = None,
    ) -> dict:
        if role not in _ROLES:
            raise AppError("industry_graph.invalid_role", status_code=422,
                           detail=f"role must be one of {sorted(_ROLES)}") from None
        chain = self._get_chain_row(chain_id)
        if chain is None:
            raise AppError("industry_graph.chain_not_found", status_code=404) from None
        seg = self._get_segment_row(segment_id)
        if seg is None or seg.chain_id != chain_id:
            raise AppError("industry_graph.segment_not_in_chain", status_code=422) from None
        # 证据归属：位置证据的标的必须就是该公司（公司自有披露）
        for evidence_id in evidence_ids or []:
            ev = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == evidence_id)
            ).first()
            if ev is None:
                raise AppError("industry_graph.evidence_not_found", status_code=404) from None
            if (ev.instrument_id or "") != instrument_id:
                raise AppError(
                    "industry_graph.position_evidence_ownership_rejected", status_code=422,
                    detail=(
                        f"position evidence {evidence_id} belongs to {ev.instrument_id}, "
                        f"not the positioned company {instrument_id}"
                    ),
                ) from None
        row = CompanyIndustryPositionORM(
            position_id=f"pos_{uuid4().hex[:16]}", instrument_id=instrument_id,
            chain_id=chain_id, segment_id=segment_id, role=role,
            revenue_exposure_pct=revenue_exposure_pct,
            profit_exposure_pct=profit_exposure_pct,
            capacity_note=capacity_note[:2000],
            evidence_ids_json=list(evidence_ids or []),
            valid_from=_now(), snapshot_id=snapshot_id, created_at=_now(),
        )
        self._session.add(row)
        self._session.flush()
        return self._position_dict(row)

    def company_positions(self, instrument_id: str, *,
                          as_of: datetime | None = None) -> list[dict]:
        rows = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.instrument_id == instrument_id)
            .order_by(CompanyIndustryPositionORM.created_at.desc())
        ).all()
        now = _ensure_aware(as_of) or _now()
        out = []
        for r in rows:
            valid_to = _ensure_aware(r.valid_to)
            if valid_to is not None and valid_to <= now:
                continue
            out.append(self._position_dict(r))
        return out

    def peer_companies(self, instrument_id: str, *, chain_id: str | None = None) -> list[dict]:
        """Peer = 同链同环节共位（明确关系），非关键词共现。"""
        own = self.company_positions(instrument_id)
        if chain_id:
            own = [p for p in own if p["chain_id"] == chain_id]
        segment_ids = {p["segment_id"] for p in own}
        if not segment_ids:
            return []
        rows = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.segment_id.in_(segment_ids))
            .where(CompanyIndustryPositionORM.instrument_id != instrument_id)
        ).all()
        peers: dict[str, dict] = {}
        for r in rows:
            peers.setdefault(r.instrument_id, {
                "instrument_id": r.instrument_id,
                "shared_segments": [],
                "chain_ids": [],
            })
            seg = self._get_segment_row(r.segment_id)
            peers[r.instrument_id]["shared_segments"].append(seg.name if seg else r.segment_id)
            if r.chain_id not in peers[r.instrument_id]["chain_ids"]:
                peers[r.instrument_id]["chain_ids"].append(r.chain_id)
        return list(peers.values())

    # ── Graph 读取（as_of 可重放） ──────────────────────────────────────────

    def chain_graph(self, chain_id: str, *, as_of: datetime | None = None) -> dict:
        chain = self._get_chain_row(chain_id)
        if chain is None:
            raise AppError("industry_graph.chain_not_found", status_code=404) from None
        now = _ensure_aware(as_of)
        segments = self._session.scalars(
            select(IndustrySegmentORM)
            .where(IndustrySegmentORM.chain_id == chain_id)
            .order_by(IndustrySegmentORM.stage_order.asc())
        ).all()
        edges = self._session.scalars(
            select(IndustryEdgeORM).where(IndustryEdgeORM.chain_id == chain_id)
            .order_by(IndustryEdgeORM.created_at.asc())
        ).all()
        positions = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.chain_id == chain_id)
        ).all()

        def _in_window(created: datetime | None,
                       valid_from: datetime | None, valid_to: datetime | None) -> bool:
            created = _ensure_aware(created)
            valid_from = _ensure_aware(valid_from)
            valid_to = _ensure_aware(valid_to)
            if now is not None:
                if created is not None and created > now:
                    return False  # 未来结构不进入历史 PIT
                if valid_to is not None and valid_to <= now:
                    return False
            return True

        seg_out = [self._segment_dict(s) for s in segments if _in_window(s.created_at, None, None)]
        edges_out = []
        for e in edges:
            if not _in_window(e.created_at, e.valid_from, e.valid_to):
                continue
            d = self._edge_dict(e)
            d["evidence"] = self._edge_evidence(e.edge_id, as_of=now)
            edges_out.append(d)
        pos_out = [self._position_dict(p) for p in positions
                   if _in_window(p.created_at, p.valid_from, p.valid_to)]
        return {
            "chain": self._chain_dict(chain),
            "segments": seg_out,
            "edges": edges_out,
            "positions": pos_out,
            "as_of": (now or _now()).isoformat(),
            "replayable": True,
        }

    def _edge_evidence(self, edge_id: str, *, as_of: datetime | None) -> list[dict]:
        links = self._session.scalars(
            select(IndustryEdgeEvidenceORM)
            .where(IndustryEdgeEvidenceORM.edge_id == edge_id)
        ).all()
        out = []
        for l in links:
            ev = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == l.evidence_id)
            ).first()
            available = _ensure_aware(ev.available_time) if ev else None
            if as_of is not None and available is not None and available > as_of:
                continue  # 证据在 as_of 不可见 → 不进入历史状态（PIT）
            out.append({
                "link_id": l.link_id, "evidence_id": l.evidence_id,
                "stance": l.stance, "available_time": available.isoformat() if available else None,
            })
        return out


    # ── Global Industry Position 五轴（G2，§G2.7） ──────────────────────────

    def global_position(self, chain_id: str, instrument_id: str | None = None) -> dict:
        """五轴产业定位：资源/产能/成本/技术/政策。

        每轴由图谱与证据确定性派生；无数据 → status=insufficient（显形，
        不再固定空页）。instrument_id 给定时输出该公司视角。
        """
        from app.domain.industry_graph import RelationType
        from app.storage.orm import EvidenceORM

        chain = self._get_chain_row(chain_id)
        if chain is None:
            raise AppError("industry_graph.chain_not_found", status_code=404) from None
        segments = self._session.scalars(
            select(IndustrySegmentORM).where(IndustrySegmentORM.chain_id == chain_id)
            .order_by(IndustrySegmentORM.stage_order.asc())
        ).all()
        positions = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.chain_id == chain_id)
        ).all()
        if instrument_id:
            positions = [p for p in positions if p.instrument_id == instrument_id]
        edges = self._session.scalars(
            select(IndustryEdgeORM).where(IndustryEdgeORM.chain_id == chain_id)
        ).all()
        seg_name = {s.segment_id: s.name for s in segments}

        def axis_block(axis, status, values):
            return {"axis": axis, "status": status, "values": values}

        # 资源轴：上游（stage_order 最小环节）producer 位置
        upstream = min((s.stage_order for s in segments), default=0)
        upstream_ids = {s.segment_id for s in segments if s.stage_order == upstream}
        # 资源轴为链视角（上游 producer 全量），不随 instrument 过滤 ——
        # 公司视角下资源来自链上游，链上无上游公司时才 insufficient
        all_chain_positions = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.chain_id == chain_id)
        ).all()
        resource_values = [
            {
                "instrument_id": p.instrument_id,
                "segment": seg_name.get(p.segment_id, p.segment_id),
                "role": p.role,
                "capacity": (p.capacity_note or "")[:120] or None,
            }
            for p in all_chain_positions if p.segment_id in upstream_ids
        ]
        axes = [axis_block(
            "resource", "ok" if resource_values else "insufficient", resource_values)]

        # 产能轴：带 capacity/暴露的位置
        capacity_values = [
            {
                "instrument_id": p.instrument_id,
                "segment": seg_name.get(p.segment_id, p.segment_id),
                "revenue_exposure_pct": p.revenue_exposure_pct,
                "capacity": (p.capacity_note or "")[:120] or None,
            }
            for p in positions
            if (p.capacity_note or p.revenue_exposure_pct is not None)
        ]
        axes.append(axis_block(
            "capacity", "ok" if capacity_values else "insufficient", capacity_values))

        # 成本轴：触及本公司环节的成本/价格传导边
        own_segments = {p.segment_id for p in positions}
        cost_edges = [
            e for e in edges
            if e.relation_type in (RelationType.COST_TRANSMISSION.value,
                                   RelationType.PRICE_TRANSMISSION.value)
            and (not own_segments
                 or e.source_segment_id in own_segments
                 or e.target_segment_id in own_segments)
        ]
        cost_values = [
            {
                "edge_id": e.edge_id,
                "metric": e.transmission_metric or None,
                "path": f"{seg_name.get(e.source_segment_id, '')}→{seg_name.get(e.target_segment_id, '')}",
                "direction": e.direction,
                "status": e.status,
            }
            for e in cost_edges
        ]
        axes.append(axis_block(
            "cost", "ok" if cost_values else "insufficient", cost_values))

        # 技术轴：本链 driver/transmission 语义对象（证据支撑）
        from app.application.industry_semantic import IndustrySemanticORM

        drivers = self._session.scalars(
            select(IndustrySemanticORM)
            .where(IndustrySemanticORM.chain_id == chain_id)
            .where(IndustrySemanticORM.object_type.in_(("driver", "transmission")))
        ).all()
        tech_values = [
            {"object_type": d.object_type, "title": d.title[:100],
             "direction": d.direction, "evidence_refs": len(d.evidence_refs_json or [])}
            for d in drivers
        ]
        axes.append(axis_block(
            "technology", "ok" if tech_values else "insufficient", tech_values))

        # 政策轴：policy 语义对象 或 policy_transmission 边
        policy_sem = self._session.scalars(
            select(IndustrySemanticORM)
            .where(IndustrySemanticORM.chain_id == chain_id)
            .where(IndustrySemanticORM.payload_json.contains('"axis": "policy"'))
        ).all()
        policy_edges = [e for e in edges
                        if e.relation_type == RelationType.POLICY_TRANSMISSION.value]
        policy_values = [
            {"source": "semantic", "title": d.title[:100]}
            for d in policy_sem
        ] + [
            {"source": "edge", "edge_id": e.edge_id,
             "metric": e.transmission_metric or None}
            for e in policy_edges
        ]
        axes.append(axis_block(
            "policy", "ok" if policy_values else "insufficient", policy_values))

        return {
            "chain": self._chain_dict(chain),
            "instrument_id": instrument_id,
            "axes": axes,
            "as_of": _now().isoformat(),
            "replayable": True,
        }

    def _evidence_relates_to_chain(self, chain_id: str, ev: EvidenceORM) -> bool:
        """Ownership：证据标的在链上有位置，或证据提及链名/环节名。"""
        pos = self._session.scalars(
            select(CompanyIndustryPositionORM)
            .where(CompanyIndustryPositionORM.chain_id == chain_id)
            .where(CompanyIndustryPositionORM.instrument_id == (ev.instrument_id or ""))
        ).first()
        if pos is not None:
            return True
        chain = self._get_chain_row(chain_id)
        segments = self._session.scalars(
            select(IndustrySegmentORM).where(IndustrySegmentORM.chain_id == chain_id)
        ).all()
        text = f"{ev.title or ''} {ev.summary or ''}"
        if chain and chain.name and chain.name in text:
            return True
        return any(s.name and s.name in text for s in segments)

    # ── helpers ─────────────────────────────────────────────────────────────

    def _get_chain_row(self, chain_id: str) -> IndustryChainORM | None:
        return self._session.scalars(
            select(IndustryChainORM).where(IndustryChainORM.chain_id == chain_id)
        ).first()

    def _get_segment_row(self, segment_id: str) -> IndustrySegmentORM | None:
        return self._session.scalars(
            select(IndustrySegmentORM).where(IndustrySegmentORM.segment_id == segment_id)
        ).first()

    def _get_edge_row(self, edge_id: str) -> IndustryEdgeORM | None:
        return self._session.scalars(
            select(IndustryEdgeORM).where(IndustryEdgeORM.edge_id == edge_id)
        ).first()

    def _bump_chain(self, chain: IndustryChainORM) -> None:
        chain.version = chain.version + 1
        self._session.flush()

    def _chain_dict(self, r: IndustryChainORM) -> dict:
        return {"chain_id": r.chain_id, "name": r.name,
                "description": r.description, "version": r.version}

    def _segment_dict(self, r: IndustrySegmentORM) -> dict:
        return {"segment_id": r.segment_id, "chain_id": r.chain_id,
                "name": r.name, "stage_order": r.stage_order,
                "description": r.description}

    def _product_dict(self, r: IndustryProductORM) -> dict:
        return {"product_id": r.product_id, "name": r.name,
                "unit": r.unit, "description": r.description}

    def _edge_dict(self, r: IndustryEdgeORM) -> dict:
        return {
            "edge_id": r.edge_id, "chain_id": r.chain_id,
            "source_segment_id": r.source_segment_id,
            "target_segment_id": r.target_segment_id,
            "relation_type": r.relation_type,
            "input_product_ids": list(r.input_product_ids_json or []),
            "output_product_ids": list(r.output_product_ids_json or []),
            "transmission_metric": r.transmission_metric,
            "direction": r.direction,
            "lag_min_days": r.lag_min_days, "lag_max_days": r.lag_max_days,
            "strength": r.strength, "confidence_level": r.confidence_level,
            "status": r.status, "version": r.version,
            "snapshot_id": r.snapshot_id,
            "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        }

    def _position_dict(self, r: CompanyIndustryPositionORM) -> dict:
        return {
            "position_id": r.position_id, "instrument_id": r.instrument_id,
            "chain_id": r.chain_id, "segment_id": r.segment_id,
            "role": r.role,
            "revenue_exposure_pct": r.revenue_exposure_pct,
            "profit_exposure_pct": r.profit_exposure_pct,
            "capacity_note": r.capacity_note,
            "evidence_ids": list(r.evidence_ids_json or []),
            "version": r.version, "snapshot_id": r.snapshot_id,
            "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        }


# ── 稀土 Golden Seed（确定性，显式命令 —— 不是隐式 GET 副作用） ────────────────


RARE_EARTH_SEGMENTS = [
    ("资源开采", "稀土原矿/毋液开采与选矿"),
    ("冶炼分离", "混合碳酸稀土→单一稀土氧化物（镨钕镝铽）"),
    ("金属/合金", "氧化物→稀土金属/钕铁硼速凝甩带合金"),
    ("永磁材料", "钕铁硼磁材毛坯→成品磁体"),
    ("电机/新能源应用", "永磁电机、风电、新能源车驱动"),
]

RARE_EARTH_EDGES = [
    # (src, tgt, relation, metric, direction, lag_min, lag_max)
    (0, 1, "material_flow", "稀土原矿/毋液供应量", "positive", 7, 30),
    (1, 2, "material_flow", "氧化镨钕/氧化镝价格与供应", "positive", 5, 20),
    (2, 3, "price_transmission", "稀土金属价格→磁材成本", "positive", 10, 45),
    (3, 4, "demand_transmission", "磁材订单/装机需求", "positive", 15, 60),
    (0, 2, "supply_constraint", "开采配额/环保约束→氧化物供应", "negative", 30, 90),
]


def seed_rare_earth_chain(session: Session, *, as_of: datetime | None = None) -> dict:
    """稀土产业链 Golden 种子（任务书 §G1 DoD：≥5 环节、≥4 传导边）。

    幂等：同名链已存在则直接返回。真实证据（含 PIT 归属）由调用方以
    attach_edge_evidence 补充 —— 种子只建结构，不伪造证据。
    """
    svc = IndustryGraphService(session)
    existing = session.scalars(
        select(IndustryChainORM).where(IndustryChainORM.name == "稀土产业链")
    ).first()
    if existing is not None:
        return {"chain_id": existing.chain_id, "seeded": False,
                "reason": "already exists"}

    chain = svc.create_chain("稀土产业链", "稀土资源→冶炼分离→金属合金→永磁材料→终端应用")
    seg_ids: list[str] = []
    for order, (name, desc) in enumerate(RARE_EARTH_SEGMENTS):
        seg = svc.create_segment(chain["chain_id"], name, stage_order=order, description=desc)
        seg_ids.append(seg["segment_id"])
    products = {}
    for pname in ("稀土原矿", "稀土氧化物", "稀土金属/合金", "钕铁硼磁材", "永磁电机"):
        products[pname] = svc.create_product(pname)["product_id"]

    edge_ids = []
    for src, tgt, relation, metric, direction, lag_min, lag_max in RARE_EARTH_EDGES:
        edge = svc.create_edge(
            chain_id=chain["chain_id"],
            source_segment_id=seg_ids[src],
            target_segment_id=seg_ids[tgt],
            relation_type=relation,
            transmission_metric=metric,
            direction=direction,
            lag_min_days=lag_min, lag_max_days=lag_max,
        )
        edge_ids.append(edge["edge_id"])

    # G1：图谱 Artifact 注册（任务书 §3.4 —— 注册失败显形，不吞异常）
    artifact_id = None
    provenance_complete = True
    try:
        from app.application.artifacts import ArtifactService

        artifact_id = ArtifactService(session).register(
            artifact_type="industry_graph",
            domain_type="IndustryChain",
            domain_id=chain["chain_id"],
            title=f"稀土产业链图谱 v{chain['version']}",
            instrument_ids=(),
            created_by="industry_graph_seed",
            route="/industry-map",
        )
    except Exception as exc:  # noqa: BLE001 — 显形 INCOMPLETE_PROVENANCE，不冒充成功
        provenance_complete = False
        artifact_error = f"{type(exc).__name__}: {exc}"

    out = {
        "chain_id": chain["chain_id"], "seeded": True,
        "segments": seg_ids, "edges": edge_ids,
        "products": list(products.values()),
        "artifact_id": artifact_id,
        "provenance_complete": provenance_complete,
    }
    if not provenance_complete:
        out["provenance_error"] = locals().get("artifact_error", "artifact registration failed")
    return out
