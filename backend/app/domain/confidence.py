"""可解释置信度模型（F4，第三轮整改任务书 §7.1 P1-A）.

目标：生产 Claim 路径不再产生任何无解释的固定置信度
（0.6 / 0.95 / 0.9 / 0.55 / 0.99 全部移除）。

推荐模型（任务书 §7.1）：
    confidence_level = high | medium | low | insufficient
    confidence_basis = {source_trust, corroboration, directness,
                        semantic_consistency, freshness}

数值仅用于排序：
  - 数值不是概率（文档级红线）；
  - 由下列可解释因素计算，映射随 CONFIDENCE_MODEL_VERSION 可追溯；
  - 不允许使用固定默认值掩盖缺失。

因素 → 数值映射（v1）：
    base            = 最好支撑证据的信任层分数（T0 0.85 / T1 0.75 / T2 0.65 /
                      T3 0.50 / T4 0.30）
    corroboration   = +0.04 × min(max(独立来源组数 − 1, 0), 3)
    directness      = direct_quote +0.05 / derived 0 / inference −0.05
    semantic        = passed 0 / uncertain −0.10
    freshness       = ≤7 天 +0.02 / ≤90 天 0 / ≤365 天 −0.05 / 更旧 −0.10
    contrary        = −0.15 × 反向证据条数
    clamp [0.05, 0.95]
等级：≥0.75 high / ≥0.55 medium / ≥0.35 low / 否则 insufficient。
"""

from __future__ import annotations

from dataclasses import dataclass, field

CONFIDENCE_MODEL_VERSION = "claim_confidence_v1"

_TRUST_SCORE: dict[str, float] = {
    "T0_primary_disclosure": 0.85,
    "T1_official_institution": 0.75,
    "T2_professional_research": 0.65,
    "T3_mainstream_media": 0.50,
    "T4_social_unverified": 0.30,
}

_DIRECTNESS_ADJUST = {
    "direct_quote": 0.05,
    "derived": 0.0,
    "inference": -0.05,
}

_CONTRARY_PENALTY = 0.15
_CORROBORATION_BONUS = 0.04
_CORROBORATION_MAX_BONUS_STEPS = 3

_LEVELS = ("high", "medium", "low", "insufficient")


def level_for_value(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.55:
        return "medium"
    if value >= 0.35:
        return "low"
    return "insufficient"


@dataclass
class ConfidenceOutcome:
    """compute_claim_confidence 的结构化结果（可直接落库/透出）。"""

    value: float
    level: str
    basis: dict = field(default_factory=dict)
    model_version: str = CONFIDENCE_MODEL_VERSION

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "level": self.level,
            "basis": dict(self.basis),
            "model_version": self.model_version,
        }


def compute_claim_confidence(
    *,
    supporting_trusts: list[str],
    contrary_count: int = 0,
    corroboration_groups: int | None = None,
    directness: str = "derived",
    semantic_consistency: str = "passed",
    evidence_age_days: float | None = None,
    missing_data: bool = False,
) -> ConfidenceOutcome:
    """由可解释因素计算 Claim 置信度（数值非概率；版本可追溯）。

    supporting_trusts: 支撑证据的信任层值列表（T0_primary_disclosure…）；
    corroboration_groups: 独立来源组数（来源独立性服务计算；None → 取 len）；
    directness: direct_quote | derived | inference；
    semantic_consistency: passed | uncertain；
    evidence_age_days: 支撑证据可用时间距今天数（新鲜度）。
    """
    if not supporting_trusts:
        # 无支撑 = 无可信度依据 → insufficient（显式披露，不用默认值掩盖）
        return ConfidenceOutcome(
            0.05,
            "insufficient",
            basis={
                "model_version": CONFIDENCE_MODEL_VERSION,
                "source_trust": None,
                "corroboration": 0,
                "directness": directness,
                "semantic_consistency": semantic_consistency,
                "freshness": None,
                "notes": ["no_supporting_evidence"],
            },
        )

    best = max(supporting_trusts, key=lambda t: _TRUST_SCORE.get(t, 0.30))
    base = _TRUST_SCORE.get(best, 0.30)  # 未知信任层按最保守 T4 处理
    groups = corroboration_groups if corroboration_groups is not None else len(set(supporting_trusts))
    bonus = _CORROBORATION_BONUS * min(max(groups - 1, 0), _CORROBORATION_MAX_BONUS_STEPS)
    direct_adj = _DIRECTNESS_ADJUST.get(directness, 0.0)
    semantic_adj = -0.10 if semantic_consistency == "uncertain" else 0.0

    if evidence_age_days is None:
        fresh_adj, fresh_bucket = 0.0, None
    elif evidence_age_days <= 7:
        fresh_adj, fresh_bucket = 0.02, "fresh_<=7d"
    elif evidence_age_days <= 90:
        fresh_adj, fresh_bucket = 0.0, "recent_<=90d"
    elif evidence_age_days <= 365:
        fresh_adj, fresh_bucket = -0.05, "stale_<=365d"
    else:
        fresh_adj, fresh_bucket = -0.10, "very_stale_>365d"

    contrary_adj = -_CONTRARY_PENALTY * max(contrary_count, 0)

    value = base + bonus + direct_adj + semantic_adj + fresh_adj + contrary_adj
    value = round(min(max(value, 0.05), 0.95), 4)
    level = level_for_value(value)
    if missing_data:
        level = "insufficient"

    basis = {
        "model_version": CONFIDENCE_MODEL_VERSION,
        "source_trust": best,
        "source_trust_score": base,
        "corroboration": {
            "independent_groups": groups,
            "bonus": round(bonus, 4),
        },
        "directness": directness,
        "directness_adjust": direct_adj,
        "semantic_consistency": semantic_consistency,
        "freshness": fresh_bucket,
        "freshness_adjust": fresh_adj,
        "contrary_count": max(contrary_count, 0),
        "contrary_adjust": contrary_adj,
        "notes": ["missing_data"] if missing_data else [],
    }
    return ConfidenceOutcome(value, level, basis)
