"""Source Trust 业务信任层（R2，方案 §8.2；映射既有 authority，不建平行字段）.

T0_PRIMARY_DISCLOSURE   一级披露：交易所/证监会/公司正式公告/定期报告（authority A1/A2）
T1_OFFICIAL_INSTITUTION 官方机构：国务院/部委/集团官网/官方统计（B1）
T2_PROFESSIONAL_RESEARCH 专业研究：券商研报/专业数据库/行业协会（C1）
T3_MAINSTREAM_MEDIA     主流媒体：财经媒体/正规报道（B2/C2）
T4_SOCIAL_UNVERIFIED    社交/未证实：雪球/自媒体/传闻（D）

方向永远是既有 authority → 业务层（读时派生），Evidence 存储不新增字段。
"""

from __future__ import annotations

from enum import Enum

from app.domain.evidence import AuthorityLevel


class SourceTrust(str, Enum):
    T0_PRIMARY_DISCLOSURE = "T0_primary_disclosure"
    T1_OFFICIAL_INSTITUTION = "T1_official_institution"
    T2_PROFESSIONAL_RESEARCH = "T2_professional_research"
    T3_MAINSTREAM_MEDIA = "T3_mainstream_media"
    T4_SOCIAL_UNVERIFIED = "T4_social_unverified"


_TRUST_BY_AUTHORITY: dict[str, SourceTrust] = {
    AuthorityLevel.A1.value: SourceTrust.T0_PRIMARY_DISCLOSURE,
    AuthorityLevel.A2.value: SourceTrust.T0_PRIMARY_DISCLOSURE,
    AuthorityLevel.B1.value: SourceTrust.T1_OFFICIAL_INSTITUTION,
    AuthorityLevel.C1.value: SourceTrust.T2_PROFESSIONAL_RESEARCH,
    AuthorityLevel.B2.value: SourceTrust.T3_MAINSTREAM_MEDIA,
    AuthorityLevel.C2.value: SourceTrust.T3_MAINSTREAM_MEDIA,
    AuthorityLevel.D.value: SourceTrust.T4_SOCIAL_UNVERIFIED,
}

# 可以支撑「确认事实」的信任层
FACT_SUPPORTING_TRUST = {SourceTrust.T0_PRIMARY_DISCLOSURE, SourceTrust.T1_OFFICIAL_INSTITUTION}
# 仅多源独立 T2/T3 也可支撑（须显式标注非正式披露）
CORROBORATING_TRUST = {SourceTrust.T2_PROFESSIONAL_RESEARCH, SourceTrust.T3_MAINSTREAM_MEDIA}


def trust_for_authority(authority: str | AuthorityLevel | None) -> SourceTrust:
    """authority → 业务信任层（未知值按最保守 T4 处理，不猜测升级）。"""
    if authority is None:
        return SourceTrust.T4_SOCIAL_UNVERIFIED
    key = authority.value if isinstance(authority, AuthorityLevel) else str(authority).strip()
    return _TRUST_BY_AUTHORITY.get(key, SourceTrust.T4_SOCIAL_UNVERIFIED)


def trust_for_evidence(authority: str | AuthorityLevel | None, evidence_type: str | None) -> SourceTrust:
    """带证据类型的信任层.

    行情数字（market_quote）经 A2/B2 持牌转载商分发时仍是交易所原始数据，
    按 T0 一级披露对待（方案 §8.2 T0 语义：交易所/正式行情数据）；
    政策/新闻/研报等叙述性证据不享受该升级。"""
    base = trust_for_authority(authority)
    if (
        base in (SourceTrust.T3_MAINSTREAM_MEDIA, SourceTrust.T0_PRIMARY_DISCLOSURE)
        and evidence_type == "market_quote"
        and str(authority).upper() in ("A2", "B2")
    ):
        return SourceTrust.T0_PRIMARY_DISCLOSURE
    return base


class TrustEscalationError(ValueError):
    """T4-only（或可信源不足）却试图支撑 confirmed_fact。"""


def check_fact_support(
    supporting_authorities_or_levels: list,
    *,
    min_corroborating_sources: int = 2,
) -> SourceTrust:
    """确定性校验：confirmed_fact 的证据基是否达到信任门槛（方案 §8.3）.

    入参元素可以是 authority（str/enum，自动映射）或已算好的 SourceTrust 层。
    规则：
      - 存在 ≥1 条 T0/T1 → 通过（返回该最高层）；
      - 否则 T2/T3 独立数量 ≥ min_corroborating_sources → 通过；
      - 否则 TrustEscalationError —— T4/不足证据不得自动成为 Confirmed Fact。
    """
    levels = [
        lv
        if isinstance(lv, SourceTrust)
        else trust_for_authority(lv)
        for lv in supporting_authorities_or_levels
    ]
    primary = [lv for lv in levels if lv in FACT_SUPPORTING_TRUST]
    if primary:
        return min(primary, key=lambda lv: list(SourceTrust).index(lv))
    corrob = [lv for lv in levels if lv in CORROBORATING_TRUST]
    if len(corrob) >= min_corroborating_sources:
        return min(corrob, key=lambda lv: list(SourceTrust).index(lv))
    raise TrustEscalationError(
        "confirmed_fact requires >=1 T0/T1 evidence or >=2 independent T2/T3 "
        f"evidence; got trust levels {[lv.value for lv in levels]}"
    )


def confidence_level(
    supporting_trusts: list[str],
    *,
    contrary_count: int = 0,
    missing_data: bool = False,
) -> str:
    """定性置信度等级（C9，整改 P2-01）—— 替代伪精确小数.

    规则：
      - contrary_evidence > 0 → low
      - missing_data → low
      - ≥1 T0/T1 且 contrary=0 → high
      - ≥2 独立 T2/T3 且 contrary=0 → medium
      - 其余 → low
      - 无任何证据 → insufficient
    """
    from app.domain.evidence import FactStatus  # noqa: F401 — re-export convenience

    if not supporting_trusts:
        return "insufficient"
    levels = [trust_for_authority(a) for a in supporting_trusts]
    if contrary_count > 0:
        return "low"
    has_primary = any(lv in FACT_SUPPORTING_TRUST for lv in levels)
    corrob = [lv for lv in levels if lv in CORROBORATING_TRUST]
    if has_primary:
        return "high"
    if len(corrob) >= 2:
        return "medium"
    return "low"
