"""产业研究三视图 Read Model（Guanlan Direct Port G2，方案 §7-§12/§24）.

    GET /views/industry/{instrument_id}                        → 三视图数据
    GET /views/industry/{instrument_id}/segment/{segment_id}   → 环节详情

只读投影：产业链/相关公司来自 industry_map 快照（真实证据组装），全球坐标
主题/指标来自 global_context 快照；驱动/传导/叙事/站位等 ASRO 尚无证据源
的象限返回 None/空数组并保留 disclosures —— 前端显形「暂无观点」（方案 §25
不编数），不伪造 donor 板库数据。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.research_map import GlobalContextSnapshotORM
from app.services.research_map_service import ResearchMapService
from app.services.view_service import ViewService

# 方案 §10：五条逻辑轴（内部字段名固定，显示名由前端 i18n 本地化）
GLOBAL_AXES = [
    {"key": "global_demand", "greek": "β"},
    {"key": "pricing_cycle", "greek": "Δ"},
    {"key": "domestic_substitution", "greek": "Ω"},
    {"key": "technology_route", "greek": "Θ"},
    {"key": "theme_mapping", "greek": "Ψ"},
]


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value  # repo dumps already ISO-format timestamps
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc).isoformat()


class IndustryViewService:
    """Assembles the three-view industry workspace from existing snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._maps = ResearchMapService(session)
        self._views = ViewService(session)

    # -- 三视图主视图 ---------------------------------------------------------------

    def industry_view(self, instrument_id: str) -> dict:
        identity = self._views._identity(instrument_id) or {
            "instrument_id": instrument_id,
            "name": None,
            "code": None,
        }
        industry_map = self._maps.latest_map(instrument_id)
        if industry_map is None:
            industry_map = self._maps.build_industry_map(instrument_id)
        chain = list(industry_map.get("industry_chain") or [])
        related = list(industry_map.get("related_instruments") or [])
        disclosures = dict(industry_map.get("disclosures") or {})

        segments = [
            {
                "segment_id": name,
                "name": name,
                "level": i,
                "is_current": i == len(chain) - 1,
                "definition": None,
                "momentum": None,
                "temperature": None,
                "research_count": None,
                "stars": 0,
            }
            for i, name in enumerate(chain)
        ]

        # R3（方案 §9）：真实语义对象并入视图 —— 语义条目挂在链上任一级
        # （稀土级 driver 与 有色金属级 driver 都属于本行业视图），在 Python 侧
        # 按链级集合过滤（规模 v1 可接受）。
        from app.application.industry_semantic import IndustrySemanticRepository

        sem_repo = IndustrySemanticRepository(self._session)
        chain_levels = set(chain) | {industry_map.get("industry_label") or ""}
        drivers = [
            d for d in sem_repo.latest_by_type("driver", limit=200)
            if d["industry_id"] in chain_levels
        ]
        transmissions = [
            d for d in sem_repo.latest_by_type("transmission", limit=200)
            if d["industry_id"] in chain_levels
        ]
        narratives = [
            d for d in sem_repo.latest_by_type("narrative", limit=200)
            if d["industry_id"] in chain_levels
        ]
        positions = [
            d for d in sem_repo.latest_by_type("position", limit=200)
            if d["industry_id"] in chain_levels
        ]

        context = self._maps.latest_context(instrument_id)
        if context is None:
            try:
                context = self._maps.build_global_context(instrument_id)
            except KeyError:
                context = None  # 宏观证据缺失 → 主题/指标诚实为空（§25）
        themes: list[dict] = []
        indicators: list[dict] = []
        disclosures_global: dict = {}
        if context is not None:
            themes = list(context.get("themes") or [])[:8]
            indicators = list(context.get("indicators") or [])
            disclosures_global = dict(context.get("disclosures") or {})

        return {
            "instrument": identity,
            "map_id": industry_map.get("map_id"),
            "context_snapshot_id": context.get("snapshot_id") if context else None,
            "industry_label": industry_map.get("industry_label"),
            "chain_levels": chain,
            "segments": segments,
            "related_instruments": related,
            "semantics": {
                "drivers": drivers,
                "transmissions": transmissions,
                "narratives": narratives,
                "positions": positions,
            },
            "global": {
                "axes": GLOBAL_AXES,
                "themes": themes,
                "indicators": indicators,
                # 站位（领先/并跑/追赶/短板）尚无证据源：空数组 + 披露，
                # 不伪造 donor 板库的 mrow/mcol
                "positions": [],
                "disclosures": disclosures_global,
            },
            "reports": self._recent_reports(instrument_id),
            "disclosures": disclosures,
            "as_of": _iso(industry_map.get("as_of")),
        }

    # -- 环节详情 -------------------------------------------------------------------

    def segment_view(self, instrument_id: str, segment_id: str) -> dict:
        view = self.industry_view(instrument_id)
        chain = view["chain_levels"]
        if segment_id not in chain:
            from app.core.errors import AppError

            raise AppError("industry_map.segment_not_found", status_code=404)
        segments = [s for s in view["segments"] if s["segment_id"] == segment_id]
        segment = dict(segments[0]) if segments else None
        # 环节证据：产业链/新闻证据中标题或摘要提及该环节词的行（真实共现）
        evidence = self._segment_evidence(instrument_id, segment_id)
        if segment is not None:
            segment["evidence_count"] = len(evidence)
        return {
            "instrument": view["instrument"],
            "segment": segment,
            "industry_label": view["industry_label"],
            "related_instruments": view["related_instruments"],
            "evidence": evidence,
            "reports": view["reports"],
            "disclosures": view["disclosures"],
            "as_of": view["as_of"],
        }

    # -- 内部 ----------------------------------------------------------------------

    def _recent_reports(self, instrument_id: str, limit: int = 5) -> list[dict]:
        from app.storage.report_repo import ReportORM

        rows = self._session.scalars(
            select(ReportORM)
            .where(ReportORM.instrument_id == instrument_id)
            .order_by(ReportORM.created_at.desc(), ReportORM.id.desc())
            .limit(limit)
        ).all()
        identity = self._views._identity(instrument_id) or {}
        # 报告无 title 列：业务名 = 标的名（与 report-library 视图同口径）
        return [
            {
                "report_id": r.report_id,
                "name": identity.get("name"),
                "code": identity.get("code"),
                "gate_status": r.gate_status,
                "created_at": _iso(r.created_at),
            }
            for r in rows
        ]

    def _segment_evidence(self, instrument_id: str, segment_id: str, limit: int = 8) -> list[dict]:
        from app.domain.evidence import EvidenceType
        from app.storage.repository import EvidenceRepository

        evidence = EvidenceRepository(self._session).list_for_instrument(
            instrument_id, visible_at=datetime.now(timezone.utc)
        )
        rows: list[dict] = []
        for e in evidence:
            if e.evidence_type not in (EvidenceType.INDUSTRY_DATA, EvidenceType.NEWS):
                continue
            text = f"{e.title} {e.summary or ''}"
            if segment_id and segment_id in text:
                rows.append(
                    {
                        "evidence_id": e.evidence_id,
                        "title": e.title,
                        "summary": (e.summary or "").strip()[:200],
                        "available_time": _iso(e.available_time),
                    }
                )
            if len(rows) >= limit:
                break
        return rows


    # -- 全球宏观（G8，方案 §12/§13：与产业全球坐标分离的市场级视图） -----------

    def global_macro_view(self) -> dict:
        """市场级全球宏观：取最新 global_context 快照（指标=市场级指数/商品
        真实行情数值层；主题=宏观政策证据）。无任何快照 → 各区诚实为空。"""
        from app.application.research_map import GlobalContextSnapshotORM

        row = self._session.scalars(
            select(GlobalContextSnapshotORM)
            .order_by(GlobalContextSnapshotORM.as_of.desc(), GlobalContextSnapshotORM.id.desc())
            .limit(1)
        ).first()
        if row is None:
            return {
                "indicators": [],
                "themes": [],
                "disclosures": {
                    "note": "宏观快照未采集 —— 对任一标的运行一次研究后，市场级指标与主题在此显示"
                },
                "as_of": None,
                "has_data": False,
            }
        import json as _json

        indicators = row.indicators_json if isinstance(row.indicators_json, list) else _json.loads(row.indicators_json or "[]")
        themes = row.themes_json if isinstance(row.themes_json, list) else _json.loads(row.themes_json or "[]")
        disclosures = dict(row.disclosures_json or {})
        return {
            "indicators": indicators[:12],
            "themes": themes[:10],
            "disclosures": disclosures,
            "as_of": _iso(row.as_of),
            "has_data": True,
        }
