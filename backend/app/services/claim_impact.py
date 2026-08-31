"""Claim Impact Analysis（R8-C1，整改 P0-01）.

替代原「旧证据 ∉ 新证据 = stale」错误算法。
确定性关系判定（不依赖 LLM，可审计）：

    New Evidence
        ↓
    Event Classification（事件类型匹配）
        ↓
    Entity / Keyword Overlap（实体/关键词重叠）
        ↓
    Candidate Claims
        ↓
    Relation Determination
        ├─ supports      新证据为 Claim 提供独立新支撑
        ├─ strengthens   新证据与 Claim 已有证据同事件同向，加固
        ├─ weakens       新证据引入削弱信号（同事件反向/条件变化）
        ├─ contradicts   新证据含否定/否认标记，与 Claim 方向冲突
        ├─ supersedes    新证据声明取代/更正 Claim 已有证据
        ├─ updates       新证据已被 Claim 直接引用
        └─ irrelevant    实体与事件均无交集（不进入 affected）

红线：irrelevant 的 Claim 不进入 affected_claims；
      possibly_stale 概念废除（旧证据存在≠过期）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.orm import EvidenceORM
from app.storage.research_orm import ClaimORM, ThesisORM


# ── 事件类型分类（确定性关键词规则，方案 P0-01 §3.4 Event Match） ──────────────

EVENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "share_reduction": ("减持", "减持计划", "预披露"),
    "restructuring": ("重组", "资产注入", "发行股份购买资产", "筹划重大资产重组"),
    "equity_change": ("股权变更", "无偿划转", "股权转让", "股权划转"),
    "earnings": ("财报", "业绩", "营收", "净利", "季报", "年报", "中报"),
    "policy": ("政策", "部委", "发改委", "工信部", "证监会"),
    "price": ("价格", "上涨", "下跌", "涨幅", "跌幅", "氧化", "稀土价格"),
    "capital_flow": ("资金流", "主力", "净流入", "净流出"),
    "capacity": ("产能", "配额", "开采", "冶炼分离"),
}

# 否定/反向标记（C4 Semantic Entailment 亦复用）
NEGATION_MARKERS = ("不存在", "未筹划", "没有", "否认", "终止", "未考虑", "澄清")
SUPERSEDE_MARKERS = ("更正", "修订", "补充公告", "取代", " supersede")

_STOPWORDS = frozenset(
    "的 了 在 是 与 及 和 对 从 被 将 已 有 无 不 等 中 为 上 下 这 那 其 该 本 也 又 才 只 更 最 很 都 都"
    "公司 中国 股份 有限 集团 上市 关于 进行 相关 情况 披露 公告 报告 影响 研究 目前 以下 以上 内容 具体".split()
)


def _tokens(text: str) -> set[str]:
    """确定性分词：去停用词后按 2-gram + 标点/空白切分，够用于实体重叠判断。"""
    text = (text or "").strip()
    if not text:
        return set()
    chunks = re.split(r"[，。、；：！？\s（）()\[\]【】《》\-—/\\|,.;:!?\[\]{}]+", text)
    out: set[str] = set()
    for c in chunks:
        c = c.strip()
        if len(c) >= 2 and c not in _STOPWORDS:
            out.add(c)
        # CJK 2-gram for overlap recall
        for i in range(len(c) - 1):
            bg = c[i : i + 2]
            if bg not in _STOPWORDS:
                out.add(bg)
    return out


def _overlap(a: set[str], b: set[str]) -> float:
    """Jaccard-ish containment：较小集合在较大集合中的覆盖率。"""
    if not a or not b:
        return 0.0
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    return len(smaller & larger) / len(smaller)


def _events(text: str) -> set[str]:
    return {name for name, patterns in EVENT_PATTERNS.items() if any(p in text for p in patterns)}


@dataclass
class ClaimImpact:
    """结构化影响判定（方案 P0-01 §3.3最低要求）。"""

    impact_id: str
    claim_id: str
    new_evidence_id: str
    relation: str  # supports|strengthens|weakens|contradicts|supersedes|updates|irrelevant
    reason: str
    matched_events: list[str] = field(default_factory=list)
    matched_entities: list[str] = field(default_factory=list)
    confidence_basis: str = "deterministic_entity_event_overlap"
    verdict_basis: str = "deterministic"
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "impact_id": self.impact_id,
            "claim_id": self.claim_id,
            "new_evidence_id": self.new_evidence_id,
            "relation": self.relation,
            "reason": self.reason,
            "matched_events": self.matched_events,
            "matched_entities": list(self.matched_entities)[:6],
            "confidence_basis": self.confidence_basis,
            "verdict_basis": self.verdict_basis,
            "created_at": self.created_at,
        }


class ClaimImpactService:
    """确定性 Claim Impact 分析（无 LLM，可审计）。"""

    ENTITY_OVERLAP_THRESHOLD = 0.20
    ENTITY_MIN_SHARED = 2  # 至少 2 个重叠 token（防单个数字 2-gram 误匹配）
    EVENT_OVERLAP_MIN = 1  # 至少命中 1 个事件类型

    def __init__(self, session: Session) -> None:
        self._session = session

    def analyze(self, instrument_id: str, new_evidence_view: list[dict]) -> dict:
        """对 instrument 全部 claims 做影响分析；只返回非 irrelevant 的。

        new_evidence_view: [{evidence_id, kind, title, summary, at}]
        """
        claims = self._session.scalars(
            select(ClaimORM).where(ClaimORM.instrument_id == instrument_id)
        ).all()
        if not claims or not new_evidence_view:
            return self._empty(new_evidence_view)

        # 预加载新证据的原文（实体/事件分类用完整 summary）
        new_ids = {ev["evidence_id"] for ev in new_evidence_view}
        ev_rows = self._session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id.in_(new_ids))
        ).all()
        ev_text_by_id = {r.evidence_id: (r.summary or "") for r in ev_rows}

        # 证据全量（claim 已有证据的 event/entity 计算）
        all_ev_ids: set[str] = set()
        for c in claims:
            all_ev_ids.update(c.supporting_evidence_refs_json or [])
            all_ev_ids.update(c.opposing_evidence_refs_json or [])
        if all_ev_ids:
            ev_rows_all = self._session.scalars(
                select(EvidenceORM).where(EvidenceORM.evidence_id.in_(all_ev_ids))
            ).all()
            ev_text_by_id.update({r.evidence_id: (r.summary or "") for r in ev_rows_all})

        impacts: list[ClaimImpact] = []
        irrelevant_count = 0

        for c in claims:
            claim_refs = list(c.supporting_evidence_refs_json or [])
            claim_opp_refs = list(c.opposing_evidence_refs_json or [])
            claim_text = f"{c.statement} " + " ".join(
                ev_text_by_id.get(r, "") for r in claim_refs
            )
            claim_entities = _tokens(claim_text)
            claim_events = _events(claim_text)
            # evidence text cache for relation determination
            self._ev_text_cache = dict(ev_text_by_id)

            for ev in new_evidence_view:
                ev_id = ev["evidence_id"]
                ev_text = ev_text_by_id.get(ev_id, ev.get("summary", ""))
                ev_entities = _tokens(ev_text)
                ev_events = _events(ev_text)

                # ── Gate 1: 实体重叠 ──
                entity_overlap = _overlap(claim_entities, ev_entities)
                shared_entities = claim_entities & ev_entities

                # ── Gate 2: 事件类型重叠 ──
                shared_events = set(claim_events) & set(ev_events)

                if not shared_events and (
                    entity_overlap < self.ENTITY_OVERLAP_THRESHOLD
                    or len(shared_entities) < self.ENTITY_MIN_SHARED
                ):
                    irrelevant_count += 1
                    continue

                relation, reason = self._determine_relation(
                    claim_stmt=c.statement,
                    claim_refs=claim_refs,
                    claim_opp_refs=claim_opp_refs,
                    ev_id=ev_id,
                    ev_text=ev_text,
                    shared_events=shared_events,
                    shared_entities=shared_entities,
                    entity_overlap=entity_overlap,
                )
                if relation == "irrelevant":
                    irrelevant_count += 1
                    continue

                impacts.append(
                    ClaimImpact(
                        impact_id=f"imp_{uuid4().hex[:12]}",
                        claim_id=c.claim_id,
                        new_evidence_id=ev_id,
                        relation=relation,
                        reason=reason,
                        matched_events=sorted(shared_events),
                        matched_entities=sorted(shared_entities),
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

        affected_claim_ids = {i.claim_id for i in impacts}
        affected_claims = [
            {
                "claim_id": cid,
                "impacts": [i.to_dict() for i in impacts if i.claim_id == cid],
                "relations": sorted({i.relation for i in impacts if i.claim_id == cid}),
            }
            for cid in sorted(affected_claim_ids)
        ]

        theses = self._session.scalars(
            select(ThesisORM).where(ThesisORM.instrument_id == instrument_id)
        ).all()
        affected_theses = []
        for t in theses:
            sup = set(t.supporting_claims_json or [])
            opp = set(t.opposing_claims_json or [])
            hit = [cid for cid in affected_claim_ids if cid in sup or cid in opp]
            if hit:
                affected_theses.append(
                    {
                        "thesis_id": t.thesis_id,
                        "title": t.title,
                        "affected_claims": hit,
                        "relations": sorted(
                            {i.relation for i in impacts if i.claim_id in hit}
                        ),
                    }
                )

        return {
            "impacts": [i.to_dict() for i in impacts],
            "affected_claims": affected_claims,
            "affected_theses": affected_theses,
            "irrelevant_count": irrelevant_count,
        }

    @staticmethod
    def _empty(new_evidence_view: list[dict]) -> dict:
        return {
            "impacts": [],
            "affected_claims": [],
            "affected_theses": [],
            "irrelevant_count": 0,
        }



    def _determine_relation(
        self,
        *,
        claim_stmt: str,
        claim_refs: list[str],
        claim_opp_refs: list[str],
        ev_id: str,
        ev_text: str,
        shared_events: set[str],
        shared_entities: set[str],
        entity_overlap: float,
    ) -> tuple[str, str]:
        """确定性关系判定（方案 §3.4：Candidate ≠ Impact，须过 relation 判断）。"""
        # updates: claim 直接引用了该新证据
        if ev_id in claim_refs or ev_id in claim_opp_refs:
            return "updates", "claim 已直接引用该证据"

        ev_neg = any(m in ev_text for m in NEGATION_MARKERS)
        claim_neg = any(m in claim_stmt for m in NEGATION_MARKERS)
        ev_supersedes = any(m in ev_text for m in SUPERSEDE_MARKERS)

        if ev_supersedes:
            return "supersedes", "证据含更正/修订/补充标记"

        # 语义冲突：新证据含否定标记而 claim 无否定（或反向）
        if ev_neg and not claim_neg:
            return "contradicts", "新证据含否定/否认标记，与 Claim 方向冲突"

        if not ev_neg and claim_neg:
            return "weakens", "Claim 含否定语义，新证据为正向"

        # 同事件同向
        if shared_events:
            already = False
            for r in claim_refs:
                r_text = self._ev_text_cache.get(r, "")
                if _events(r_text) & shared_events:
                    already = True
                    break
            if already:
                return "strengthens", (
                    f"同事件类型 {sorted(shared_events)} 已有证据，新证据加固支撑"
                )
            return "supports", (
                f"新证据提供独立支撑（事件类型 {sorted(shared_events)}，"
                f"实体重叠 {entity_overlap:.0%}）"
            )

        # 事件不重叠 → irrelevant（实体重叠 alone 不足以构成研究影响）
        return "irrelevant", "实体与事件均无有效交集"
