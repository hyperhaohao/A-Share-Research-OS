"""Research map service (V2 Phase H, 总纲 §11/§52/§77).

产业研究地图 + 全球宏观视图 —— 由真实证据层组装的 Research Inputs：
  - 产业链来自 eastmoney_industry 证据（industry_chain/main_business）；
  - 相关公司由证据文本与注册表名称共现推导（真实、可溯源）；
  - 全球坐标来自 macro_policy 证据（政策资讯 + 官方机构提及），显式披露
    「官方宏观数值源未接入」；
  - as_of 取 PIT 证据时间，注册为 Artifact（generated_from 报告）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.artifacts import ArtifactService, RelationType
from app.application.research_map import (
    GlobalContextSnapshotORM,
    IndustryMapSnapshotORM,
    ResearchMapRepository,
)
from app.domain.evidence import EvidenceType
from app.storage.instrument_repo import InstrumentRegistryORM
from app.storage.repository import EvidenceRepository


class ResearchMapService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ResearchMapRepository(session)

    # -- 产业研究地图 ----------------------------------------------------------------

    def build_industry_map(self, instrument_id: str) -> dict:
        evidence_repo = EvidenceRepository(self._session)
        evidence = evidence_repo.list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )
        profile = next(
            (
                e
                for e in reversed(evidence)
                if e.evidence_type is EvidenceType.INDUSTRY_DATA
                and (e.metadata or {}).get("industry_chain")
            ),
            None,
        )
        if profile is None:
            raise KeyError("industry profile not collected for this instrument")

        chain = list(profile.metadata.get("industry_chain") or [])
        industry_label = chain[0] if chain else ""
        as_of = max(
            (e.available_time for e in evidence if e.evidence_type is EvidenceType.INDUSTRY_DATA),
            default=datetime.now(timezone.utc),
        )

        # 相关公司：注册表名称在本标的产业/新闻证据文本中共现（真实共现，
        # 非编造关系）；关系源未接入前这就是可溯源的最强信号。
        texts: list[str] = []
        evidence_ids: list[str] = []
        for e in evidence:
            if e.evidence_type in (EvidenceType.INDUSTRY_DATA, EvidenceType.NEWS):
                texts.append(f"{e.title} {e.summary}")
                evidence_ids.append(e.evidence_id)
        corpus = " ".join(texts)
        related: list[dict] = []
        for row in self._session.scalars(select(InstrumentRegistryORM)).all():
            name = (row.name or "").strip()
            if (
                row.instrument_id != instrument_id
                and len(name) >= 3
                and name in corpus
            ):
                related.append(
                    {
                        "instrument_id": row.instrument_id,
                        "name": name,
                        "code": row.code,
                        "basis": "产业/新闻证据文本共现",
                    }
                )
            if len(related) >= 12:
                break

        now = datetime.now(timezone.utc)
        row = IndustryMapSnapshotORM(
            map_id=f"imap_{_short_hex()}",
            instrument_id=instrument_id,
            industry_label=industry_label,
            as_of=as_of,
            industry_chain_json=chain,
            main_business=(profile.metadata.get("main_business") or None),
            related_instruments_json=related,
            evidence_ids_json=evidence_ids[:200],
            disclosures_json={
                "peers": "pending_relationship_source",
                "note": "上下游/同业关系源未接入：相关公司由证据文本共现推导（真实共现，非既有关系）",
            },
            created_at=now,
        )
        snapshot = self._repo.add_map(row)
        self._register_map_artifact(snapshot)
        return snapshot

    # -- 全球宏观视图 ------------------------------------------------------------------

    def build_global_context(self, instrument_id: str, topic: str | None = None) -> dict:
        evidence_repo = EvidenceRepository(self._session)
        evidence = evidence_repo.list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )
        macro_items = [
            e for e in evidence if e.evidence_type is EvidenceType.MACRO_INDICATOR
        ]
        if not macro_items:
            raise KeyError("macro evidence not collected for this instrument")

        as_of = max(e.available_time for e in macro_items)
        themes: list[dict] = []
        for e in macro_items:
            themes.append(
                {
                    "title": e.title,
                    "topic": (e.metadata or {}).get("topic"),
                    "mentions_official_body": bool(
                        (e.metadata or {}).get("mentions_official_body")
                    ),
                    "official_bodies": list((e.metadata or {}).get("official_bodies") or []),
                    "summary": e.summary[:500],
                    "available_time": e.available_time.isoformat(),
                    "evidence_id": e.evidence_id,
                }
            )
        now = datetime.now(timezone.utc)
        row = GlobalContextSnapshotORM(
            snapshot_id=f"gctx_{_short_hex()}",
            instrument_id=instrument_id,
            topic=topic or "macro_policy",
            as_of=as_of,
            themes_json=themes[:50],
            evidence_ids_json=[e.evidence_id for e in macro_items][:200],
            disclosures_json={
                "official_macro_source": "not_connected",
                "note": (
                    "官方宏观数值源未接入：当前为政策/宏观资讯层（真实资讯，"
                    "含官方机构提及标注）；利率/汇率等数值待官方源接入后补齐"
                ),
            },
            created_at=now,
        )
        snapshot = self._repo.add_context(row)
        self._register_context_artifact(snapshot)
        return snapshot

    # -- reads ----------------------------------------------------------------------

    def latest_map(self, instrument_id: str) -> dict | None:
        return self._repo.latest_map(instrument_id)

    def latest_context(self, instrument_id: str) -> dict | None:
        return self._repo.latest_context(instrument_id)

    # -- artifact ---------------------------------------------------------------------

    def _register_map_artifact(self, snapshot: dict) -> str:
        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="industry_map",
            domain_type="IndustryMapSnapshot",
            domain_id=snapshot["map_id"],
            title=f"产业研究地图：{snapshot['industry_label']}",
            summary=" → ".join(snapshot["industry_chain"]) or None,
            instrument_ids=(snapshot["instrument_id"],),
            as_of_time=None,
            created_by="research_map",
            route="/industry-map",
        )
        self._link_to_report(artifact_id, snapshot["instrument_id"], service)
        return artifact_id

    def _register_context_artifact(self, snapshot: dict) -> str:
        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="global_context",
            domain_type="GlobalContextSnapshot",
            domain_id=snapshot["snapshot_id"],
            title=f"全球宏观坐标：{snapshot['instrument_id']}（{snapshot['topic']}）",
            summary=f"{len(snapshot['themes'])} 条宏观/政策主题",
            instrument_ids=(snapshot["instrument_id"],),
            as_of_time=None,
            created_by="research_map",
            route="/global-context",
        )
        self._link_to_report(artifact_id, snapshot["instrument_id"], service)
        return artifact_id

    def _link_to_report(self, artifact_id: str, instrument_id: str, service: ArtifactService) -> None:
        from app.storage.report_repo import ReportORM

        report_row = self._session.scalars(
            select(ReportORM)
            .where(ReportORM.instrument_id == instrument_id)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
        ).first()
        if report_row is not None:
            report_artifact = service.by_domain("Report", report_row.report_id)
            if report_artifact is not None:
                service.link(
                    from_artifact_id=artifact_id,
                    to_artifact_id=report_artifact["artifact_id"],
                    relation=RelationType.GENERATED_FROM,
                )


def _short_hex() -> str:
    return uuid4().hex[:12]
