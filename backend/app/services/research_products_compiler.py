"""Research Product Compilers（R8-C7，方案 §11.4/§11.5/§11.6）.

三类市场级研究产品编译器：从 Inbox/语义对象/证据语料聚合真实数据。
不走管线（非 instrument-scoped），而是市场级只读投影 + 编译。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.research_products import get_contract
from app.storage.orm import EvidenceORM
from app.storage.agent_repo import AgentRepository
from app.domain.agents import ResearchRequestStatus


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class MarketProductCompiler:
    """市场级研究产品编译器（非 instrument-scoped）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _recent_evidence(self, hours: int = 48, limit: int = 50) -> list:
        cutoff = _utc() - timedelta(hours=hours)
        return self._session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.available_time >= cutoff)
            .order_by(EvidenceORM.available_time.desc())
            .limit(limit)
        ).all()

    def compile_mainline_radar(self) -> dict:
        """主线雷达（方案 §11.4）：叙事 → 证据 → 驱动 → 产业映射 → 反方。"""
        from app.application.industry_semantic import IndustrySemanticRepository

        sem_repo = IndustrySemanticRepository(self._session)
        drivers = sem_repo.latest_by_type("driver", limit=20)
        narratives = sem_repo.latest_by_type("narrative", limit=20)
        recent = self._recent_evidence(48, 30)

        # 产业映射：driver/narrative 的 industry_id → 相关标的
        lines = []
        for d in drivers:
            lines.append({
                "kind": "driver",
                "industry": d["industry_id"],
                "title": d["title"],
                "direction": d.get("direction") or "uncertain",
                "evidence_count": len(d.get("evidence_refs") or []),
            })
        for n in narratives:
            lines.append({
                "kind": "narrative",
                "industry": n["industry_id"],
                "title": n["title"],
                "status": n.get("status") or "emerging",
                "evidence_count": len(n.get("evidence_refs") or []),
            })
        for e in recent[:10]:
            if "稀土" in (e.summary or "") or "有色" in (e.summary or ""):
                lines.append({
                    "kind": "evidence",
                    "industry": "有色",
                    "title": (e.summary or "")[:120],
                    "direction": None,
                    "evidence_count": 1,
                })

        return {
            "product_type": "MAINLINE_RADAR",
            "compiled_at": _utc().isoformat(),
            "items": lines,
            "count": len(lines),
            "note": "主线雷达 = 叙事/驱动/证据 聚合（非涨幅榜）",
        }

    def compile_overseas_mapping(self) -> dict:
        """海外映射（方案 §11.5）：海外事件 → 影响 → 中国映射（每条挂证据）。"""
        overseas_kw = ("海外", "美股", "美联储", "美国", "欧洲", "欧盟", "美元", "关税", "出口")
        recent = self._recent_evidence(72, 100)
        overseas_ev = [
            e for e in recent
            if any(kw in (e.summary or "") for kw in overseas_kw)
        ]
        items = []
        for e in overseas_ev[:15]:
            items.append({
                "evidence_id": e.evidence_id,
                "title": (e.summary or "")[:160],
                "at": e.available_time.isoformat() if e.available_time else None,
                "kind": e.evidence_type,
            })
        return {
            "product_type": "OVERSEAS_MAPPING",
            "compiled_at": _utc().isoformat(),
            "items": items,
            "count": len(items),
            "note": "海外事件 → 中国映射（每条必须挂证据，禁止无证据荐股）",
        }

    def compile_daily_brief(self) -> dict:
        """每日研究简报（方案 §11.6）：Inbox + Thesis 变化 + 信号 + 请求聚合。"""
        from app.services.research_inbox import ResearchInboxService

        inbox = ResearchInboxService(self._session).inbox(window_hours=24, limit_per=10)
        sections = []

        if inbox["new_evidence"]:
            sections.append({
                "title": "新证据",
                "items": [
                    {"text": f"{e['instrument_id']} {e['title'][:80]}", "at": e.get("at")}
                    for e in inbox["new_evidence"][:5]
                ],
            })
        if inbox["materiality_alerts"]:
            sections.append({
                "title": "重要性预警",
                "items": [
                    {"text": f"{m['instrument_id']} {m['decision']}", "at": m.get("at")}
                    for m in inbox["materiality_alerts"][:5]
                ],
            })
        if inbox["open_research_requests"]:
            sections.append({
                "title": "待补研究请求",
                "items": [
                    {"text": f"{r['instrument_id']} {r['capability']} {r['reason'][:60]}", "at": None}
                    for r in inbox["open_research_requests"][:5]
                ],
            })
        if inbox["failed_collections"]:
            sections.append({
                "title": "采集失败",
                "items": [
                    {"text": f"{f['instrument_id']} {f['capability']} {f['status']}", "at": None}
                    for f in inbox["failed_collections"][:5]
                ],
            })

        return {
            "product_type": "DAILY_RESEARCH_BRIEF",
            "compiled_at": _utc().isoformat(),
            "sections": sections,
            "section_count": len(sections),
            "note": "研究简报 = Inbox/Thesis/信号 聚合（非行情播报）",
        }
