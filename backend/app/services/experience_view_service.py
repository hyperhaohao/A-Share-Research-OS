"""研究经验卡 Workbench Read Model（Guanlan Direct Port G3，方案 §14/§24/§34）.

    GET /views/experience/{card_id} → 原炼验用工作台一次装配

只读投影：原（来源报告 + 主张原文 + 证据摘要，主张按卡引用序给 cite 序号）/
炼（机制/适用/失效/表达式）/ 验（验证记录；量化指标无则诚实空）/ 用（已批准
卡片知识库）。不迁 donor markdown 三桶库（方案 §14 禁止）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.application.experience import ExperienceCardORM
from app.storage.orm import EvidenceORM
from app.storage.research_orm import ClaimORM
from app.services.experience_service import ExperienceService


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc).isoformat()


class ExperienceViewService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def experience_view(self, card_id: str) -> dict:
        card = self._session.scalars(
            select(ExperienceCardORM).where(ExperienceCardORM.card_id == card_id)
        ).first()
        if card is None:
            raise AppError("experience.not_found", status_code=404)

        detail = ExperienceService(self._session).get_card_detail(card_id)
        claims = self._card_claims(card)
        evidence = self._card_evidence(card)

        return {
            "card": detail,
            "source": {
                "report_id": card.source_report_id,
                "report_version_id": getattr(card, "source_report_version_id", None),
                "claims": claims,
                "evidence": evidence,
            },
            "kb": self._approved_cards(exclude=card_id),
        }

    # -- 原：卡引用的主张与证据（真实原文，donor cite 标记等价物） ----------------

    def _card_claims(self, card: ExperienceCardORM) -> list[dict]:
        ids = list(card.source_claim_ids_json or [])
        if not ids:
            return []
        rows = self._session.scalars(
            select(ClaimORM).where(ClaimORM.claim_id.in_(ids))
        ).all()
        by_id = {r.claim_id: r for r in rows}
        out: list[dict] = []
        for i, cid in enumerate(ids):
            r = by_id.get(cid)
            if r is None:
                continue
            out.append(
                {
                    "claim_id": cid,
                    "cite": i + 1,
                    "statement": r.statement,
                    "claim_type": r.claim_type,
                    "fact_status": r.fact_status,
                    "confidence": r.confidence,
                    "evidence_refs": list(r.supporting_evidence_refs_json or []),
                }
            )
        return out

    def _card_evidence(self, card: ExperienceCardORM) -> list[dict]:
        ids = list(card.source_evidence_ids_json or [])
        if not ids:
            return []
        rows = self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id.in_(ids))
        ).all()
        out: list[dict] = []
        for r in rows:
            out.append(
                {
                    "evidence_id": r.evidence_id,
                    # §27：主界面不泄漏技术串——展示真实摘要，缺失显形 —
                    "summary": (r.summary or "").strip()[:200] or "—",
                    "source": r.source,
                    "authority_level": r.authority_level,
                    "fact_status": r.fact_status,
                    "available_time": _iso(r.available_time),
                }
            )
        return out

    # -- 用：知识库 = 已批准卡片（donor KB 等价物，真实批准门槛） -------------------

    def _approved_cards(self, exclude: str, limit: int = 8) -> list[dict]:
        rows = self._session.scalars(
            select(ExperienceCardORM)
            .where(ExperienceCardORM.status == "APPROVED")
            .order_by(ExperienceCardORM.updated_at.desc())
            .limit(limit + 1)
        ).all()
        out: list[dict] = []
        for r in rows:
            if r.card_id == exclude:
                continue
            out.append(
                {
                    "card_id": r.card_id,
                    "title": r.title,
                    "category": r.category,
                    "confidence": r.confidence,
                    "verdict": r.verdict,
                    "quant_expression": getattr(r, "quant_expression", None),
                    "updated_at": _iso(r.updated_at),
                }
            )
            if len(out) >= limit:
                break
        return out
