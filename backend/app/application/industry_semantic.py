"""产业语义对象仓储与服务（R3，方案 §9）.

核心规则：
  1. 引用反查强制：创建/更新必须挂 evidence_refs，且支撑句必须在对应证据
     原文中可定位（复用 R2 CitationVerifier 归一化包含）；失败 → 拒绝。
  2. Append-only：同一 object_key 的更新产生新版本行，旧行永久保留（§4.3）。
  3. 单一 Domain：industry_id 对齐既有 industry_chain 标签；不建第二套产业存储。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.domain.extraction import normalize_text
from app.domain.industry_semantic import (
    VALID_AXES,
    VALID_DIRECTIONS,
    VALID_NARRATIVE_STATUSES,
    VALID_TRANSMISSION_DIRECTIONS,
)
from app.storage.orm import Base, EvidenceORM
from app.storage.industry_graph_orm import IndustryEdgeORM


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class IndustrySemanticORM(Base):
    __tablename__ = "industry_semantic_objects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String(16), index=True)
    object_key: Mapped[str] = mapped_column(String(48), index=True)
    instrument_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    industry_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    mechanism: Mapped[str] = mapped_column(String(2000), default="")
    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # G2：图谱链接 + 反对证据（任务书 §G2.1）
    chain_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    segment_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    edge_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    contrary_evidence_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)


class IndustrySemanticRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def latest_version(self, object_type: str, object_key: str) -> int:
        row = self._session.scalars(
            select(IndustrySemanticORM)
            .where(
                IndustrySemanticORM.object_type == object_type,
                IndustrySemanticORM.object_key == object_key,
            )
            .order_by(IndustrySemanticORM.version.desc())
            .limit(1)
        ).first()
        return row.version if row else 0

    def add(self, row: IndustrySemanticORM) -> dict:
        self._session.add(row)
        self._session.flush()
        return self._to_dict(row)

    def latest_by_type(
        self,
        object_type: str,
        *,
        industry_id: str | None = None,
        instrument_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """每个 object_key 取最新版本。"""
        rows = self._session.scalars(
            select(IndustrySemanticORM)
            .where(IndustrySemanticORM.object_type == object_type)
            .order_by(IndustrySemanticORM.object_key, IndustrySemanticORM.version.desc())
        ).all()
        latest: dict[str, IndustrySemanticORM] = {}
        for r in rows:
            if industry_id and r.industry_id != industry_id:
                continue
            if instrument_id and r.instrument_id != instrument_id:
                continue
            latest.setdefault(r.object_key, r)
        return [self._to_dict(r) for r in list(latest.values())[:limit]]

    def get_versions(self, object_type: str, object_key: str) -> list[dict]:
        rows = self._session.scalars(
            select(IndustrySemanticORM)
            .where(
                IndustrySemanticORM.object_type == object_type,
                IndustrySemanticORM.object_key == object_key,
            )
            .order_by(IndustrySemanticORM.version)
        ).all()
        return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(r: IndustrySemanticORM) -> dict:
        return {
            "object_type": r.object_type,
            "object_key": r.object_key,
            "instrument_id": r.instrument_id,
            "industry_id": r.industry_id,
            "version": r.version,
            "status": r.status,
            "direction": r.direction,
            "title": r.title,
            "mechanism": r.mechanism,
            "evidence_refs": list(r.evidence_refs_json or []),
            "chain_id": r.chain_id,
            "segment_id": r.segment_id,
            "edge_id": r.edge_id,
            "contrary_evidence_refs": list(r.contrary_evidence_refs_json or []),
            "payload": dict(r.payload_json or {}),
            "as_of": r.as_of.isoformat() if r.as_of else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }


class IndustrySemanticService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = IndustrySemanticRepository(session)

    # -- 引用反查（复用 R2 内核） ------------------------------------------------------

    def _verify_citations(self, claims: list[dict]) -> None:
        """每条 claim 的 support_span 必须能在其证据原文中定位。

        claims: [{evidence_id, support_span, observed_at?}]
        无引用 / 反查失败 → ValueError（API 层转 422 citation_failed）。
        """
        if not claims:
            raise ValueError("at least one evidence_ref with support_span is required")
        for c in claims:
            evidence_id = str(c.get("evidence_id") or "").strip()
            span = str(c.get("support_span") or "").strip()
            if not evidence_id or not span:
                raise ValueError("evidence_ref missing evidence_id or support_span")
            row = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == evidence_id)
            ).first()
            if row is None:
                raise ValueError(f"evidence not found: {evidence_id}")
            text = " ".join(p for p in [row.summary or "", row.excerpt or ""] if p)
            if normalize_text(span) not in normalize_text(text):
                raise ValueError(
                    "citation_failed: support_span not found in evidence " + evidence_id
                )

    # -- 通用创建/更新（append-only） -----------------------------------------------

    def get_versions(self, object_type: str, object_key: str) -> list[dict]:
        return self._repo.get_versions(object_type, object_key)

    def latest_by_type(
        self,
        object_type: str,
        *,
        industry_id: str | None = None,
        instrument_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        return self._repo.latest_by_type(
            object_type, industry_id=industry_id, instrument_id=instrument_id, limit=limit
        )

    def upsert(
        self,
        object_type: str,
        *,
        object_key: str,
        industry_id: str,
        title: str,
        mechanism: str = "",
        status: str,
        direction: str | None = None,
        evidence_claims: list[dict],
        instrument_id: str | None = None,
        as_of: datetime | None = None,
        extra_payload: dict | None = None,
        chain_id: str | None = None,
        segment_id: str | None = None,
        edge_id: str | None = None,
        contrary_evidence_claims: list[dict] | None = None,
    ) -> dict:
        if object_type == "driver":
            self._require(direction in VALID_DIRECTIONS, f"invalid direction: {direction}")
        if object_type == "transmission":
            self._require(
                direction in VALID_TRANSMISSION_DIRECTIONS, f"invalid direction: {direction}"
            )
        if object_type == "narrative":
            self._require(status in VALID_NARRATIVE_STATUSES, f"invalid status: {status}")
        if object_type == "position":
            self._require(
                bool(extra_payload) and extra_payload.get("axis") in VALID_AXES,
                "invalid axis",
            )
        self._verify_citations(evidence_claims)
        if contrary_evidence_claims:
            self._verify_citations(contrary_evidence_claims)

        # G2（§G2.1/§G2.2）：Evidence Ownership Gate —— 证据存在 + PIT
        # （available_time ≤ as_of）+ 产业归属（链上位置或产业/环节名提及）。
        from app.services.industry_graph_service import IndustryGraphService

        gate = IndustryGraphService(self._session)
        as_of_eff = as_of or _utc()
        graph_links = {"chain_id": chain_id, "segment_id": segment_id, "edge_id": edge_id}
        if any(graph_links.values()):
            # 显式链接时校验目标存在且属于同一链
            if edge_id:
                edge_row = self._session.scalars(
                    select(IndustryEdgeORM).where(IndustryEdgeORM.edge_id == edge_id)
                ).first()
                if edge_row is None:
                    raise ValueError(f"edge not found: {edge_id}")
                graph_links["chain_id"] = graph_links["chain_id"] or edge_row.chain_id
            if chain_id and gate._get_chain_row(chain_id) is None:
                raise ValueError(f"chain not found: {chain_id}")
            if segment_id and gate._get_segment_row(segment_id) is None:
                raise ValueError(f"segment not found: {segment_id}")
        # 链回填（edge→chain）落到落库参数
        if chain_id is None and any(graph_links.values()):
            chain_id = graph_links.get("chain_id")
        industry_name = None
        for c in list(evidence_claims) + list(contrary_evidence_claims or []):
            ev_row = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == str(c.get("evidence_id")))
            ).first()
            if ev_row is None:
                continue
            available = ev_row.available_time
            if available is not None and available.tzinfo is None:
                available = available.replace(tzinfo=timezone.utc)
            if available is not None and available > as_of_eff:
                raise ValueError(
                    f"evidence {c.get('evidence_id')} available_at "
                    f"{available.isoformat()} > as_of {as_of_eff.isoformat()}"
                )
            # 产业归属：链名/环节名提及 或 标的在含该产业名的链上有位置
            if industry_name is None:
                from app.storage.industry_graph_orm import IndustryChainORM as _C

                chain_row = self._session.scalars(
                    select(_C).where(_C.name.contains(industry_id))
                ).first() if industry_id else None
                industry_name = chain_row.name if chain_row else industry_id
            related = self._evidence_relates_to_industry(industry_name, ev_row)
            if not related:
                raise ValueError(
                    f"evidence {c.get('evidence_id')} ({ev_row.instrument_id}) "
                    f"has no relation to industry {industry_id}"
                )

        version = self._repo.latest_version(object_type, object_key) + 1
        row = IndustrySemanticORM(
            object_type=object_type,
            object_key=object_key,
            instrument_id=instrument_id,
            industry_id=industry_id,
            version=version,
            status=status,
            direction=direction,
            title=title[:200],
            mechanism=mechanism[:2000],
            evidence_refs_json=evidence_claims,
            chain_id=chain_id,
            segment_id=segment_id,
            edge_id=edge_id,
            contrary_evidence_refs_json=list(contrary_evidence_claims or []) or None,
            payload_json=extra_payload or {},
            created_at=_utc(),
            as_of=as_of or _utc(),
        )
        saved = self._repo.add(row)
        # R9（方案 §15.1）：语义对象注册为 Artifact —— 进入全库图谱。
        # 幂等：按 domain 查已有 artifact 则只更新 title/version（append-only
        # 版本在 artifact 内以 version 字段递进，不重复建行）。
        from app.application.artifacts import ArtifactService

        try:
            svc = ArtifactService(self._session)
            domain_id = f"{object_type}:{object_key}"
            # register 幂等 per (domain_type, domain_id)：已有行刷新
            # title/version，不重复建行
            svc.register(
                artifact_type=f"industry_{object_type}",
                domain_type="IndustrySemantic",
                domain_id=domain_id,
                title=title[:200],
                summary=mechanism[:300] or None,
                instrument_ids=(instrument_id,) if instrument_id else (),
                as_of_time=as_of or _utc(),
                version=version,
                created_by="industry_semantic",
                route="/industry-map",
                metadata={"industry_id": industry_id, "status": status},
            )
        except Exception as exc:  # noqa: BLE001 — 不阻断研究状态，但显形 INCOMPLETE_PROVENANCE
            saved["provenance_status"] = "INCOMPLETE_PROVENANCE"
            saved["provenance_error"] = f"{type(exc).__name__}: {exc}"[:300]
        else:
            saved["provenance_status"] = "complete"
        return saved

    @staticmethod
    def _require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    def narrative_temperature(self, object_key: str, *, now: datetime | None = None) -> dict:
        """可复算温度（G2，§G2.3）：**服务端**从证据表读取
        ``available_time``（禁止客户端提交时间集合），且只统计
        已验证信任层（T0/T1）的证据为有效观察；T2/T3 单独披露不计入。

        观察点总量不足（<3）→ insufficient（不展示数字温度，不造数值）。
        """
        from app.domain.source_trust import trust_for_evidence

        now = now or _utc()
        rows = self._repo.get_versions("narrative", object_key)
        if not rows:
            return {"temperature": "insufficient", "recent_obs": 0, "prior_obs": 0,
                    "basis": "server_evidence_table"}
        latest = max(rows, key=lambda r: r["version"])
        ev_ids = [str(c.get("evidence_id") or "")
                  for c in (latest["evidence_refs"] or [])]
        ev_ids = [e for e in ev_ids if e]
        stamps: list[float] = []
        lower_trust = 0
        for evidence_id in ev_ids:
            row = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id == evidence_id)
            ).first()
            if row is None:
                continue
            trust = trust_for_evidence(row.authority_level, row.evidence_type)
            available = row.available_time
            if available is not None and available.tzinfo is None:
                available = available.replace(tzinfo=timezone.utc)
            if available is None:
                continue
            if trust.value.startswith(("T0", "T1")):
                stamps.append(available.timestamp())
            else:
                lower_trust += 1
        if len(stamps) < 3:
            return {"temperature": "insufficient", "recent_obs": 0, "prior_obs": 0,
                    "validated_obs": len(stamps), "lower_trust_obs": lower_trust,
                    "basis": "server_evidence_table"}
        recent_cut = now.timestamp() - 14 * 86400
        prior_cut = now.timestamp() - 28 * 86400
        recent = sum(1 for t in stamps if t >= recent_cut)
        prior = sum(1 for t in stamps if prior_cut <= t < recent_cut)
        if recent > prior:
            temperature = "warming"
        elif recent < prior:
            temperature = "cooling"
        else:
            temperature = "stable"
        return {"temperature": temperature, "recent_obs": recent, "prior_obs": prior,
                "validated_obs": len(stamps), "lower_trust_obs": lower_trust,
                "basis": "server_evidence_table"}

    def _evidence_relates_to_industry(self, industry_name: str, ev) -> bool:
        """G2 产业归属：证据文本提及产业/环节名，或标的相关链上有位置。"""
        text = f"{ev.title or ''} {ev.summary or ''}"
        if industry_name and industry_name in text:
            return True
        from app.storage.industry_graph_orm import (
            CompanyIndustryPositionORM as _Pos,
            IndustryChainORM as _Chain,
        )

        chains = self._session.scalars(
            select(_Chain).where(_Chain.name.contains((industry_name or "")[:100]))
        ).all() if industry_name else []
        for chain in chains:
            pos = self._session.scalars(
                select(_Pos)
                .where(_Pos.chain_id == chain.chain_id)
                .where(_Pos.instrument_id == (ev.instrument_id or ""))
            ).first()
            if pos is not None:
                return True
            from app.storage.industry_graph_orm import IndustrySegmentORM as _Seg

            segments = self._session.scalars(
                select(_Seg).where(_Seg.chain_id == chain.chain_id)
            ).all()
            if any(s.name and s.name in text for s in segments):
                return True
        return False
