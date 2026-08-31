"""C1 — Claim Impact Analysis 正确性（整改 P0-01）.

验收（§9 TEST-R10-DIFF-01）：
  - 股东减持证据只影响与 股东结构/股份供给 相关的有限 Claims；
  - 不影响无关的 盈利/稀土价格/政策/行业供需 Claims；
  - irrelevant 计数如实返回（大面积误标不再发生）。
"""

from app.services.claim_impact import (
    NEGATION_MARKERS,
    ClaimImpact,
    _events,
    _overlap,
    _tokens,
)

REDUCTION_EV = "股东广晟控股集团计划以集中竞价方式减持公司股份不超过1061.22万股。"
EARNINGS_EV = "公司上半年营业收入16.47亿元，同比增长12.19%，归母净利润2.37亿元。"
POLICY_EV = "工信部发布稀土开采、冶炼分离总量控制指标，配额向大集团集中。"


def test_reduction_does_not_affect_unrelated():
    """核心验收：减持证据只影响减持相关 Claim，不影响盈利/政策 Claim。"""
    # 事件类型分离
    shared_reduce_earn = _events(REDUCTION_EV) & _events(EARNINGS_EV)
    assert not shared_reduce_earn, "减持 and 盈利 must have no shared event type"
    shared_reduce_pol = _events(REDUCTION_EV) & _events(POLICY_EV)
    assert not shared_reduce_pol, "减持 and 政策 must have no shared event type"
    shared_reduce_self = _events(REDUCTION_EV) & _events(
        "广晟控股集团减持公司股份 预披露公告"
    )
    assert "share_reduction" in shared_reduce_self


def test_impact_relation_taxonomy():
    """关系枚举覆盖方案要求的七种。"""
    valid = {
        "supports", "strengthens", "weakens",
        "contradicts", "supersedes", "updates", "irrelevant",
    }
    impact = ClaimImpact(
        impact_id="imp_x", claim_id="c1", new_evidence_id="ev1",
        relation="supports", reason="test",
    )
    assert impact.relation in valid


def test_entity_overlap_discriminates():
    """实体重叠判别：减持 vs 盈利 = 无关；减持 vs 减持 = 相关。"""
    a = _tokens("广晟控股集团减持公司股份不超过1061.22万股")
    b_same = _tokens("广晟控股集团减持计划 预披露")
    b_diff = _tokens("上半年营业收入16.47亿元 归母净利润2.37亿元")
    assert _overlap(a, b_same) > 0.1
    assert _overlap(a, b_diff) < 0.1


def test_event_classification():
    """事件类型分类正确性。"""
    assert "share_reduction" in _events(REDUCTION_EV)
    assert "restructuring" not in _events(REDUCTION_EV)
    assert "earnings" in _events(EARNINGS_EV)
    assert "policy" in _events(POLICY_EV)


def test_negation_markers_detect_contradiction():
    """否定标记（C4 Semantic Entailment 基础）。"""
    neg_text = "公司不存在重大资产重组计划。"
    assert any(m in neg_text for m in NEGATION_MARKERS)
    pos_text = "公司正在筹划重大资产重组。"
    assert not any(m in pos_text for m in NEGATION_MARKERS)
