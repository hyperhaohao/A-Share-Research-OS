"""Evidence-backed Extraction 契约 + CitationVerifier（R2，方案 §8.4/§8.5）.

观澜 donor 概念（研报观点批量抽取/原文引用）的 ASRO 化：任何
「从 Evidence 抽出的观点/事实/驱动/叙事」必须通过 引用反查 才能进入
正式 Research State：

    Extract → Locate Support → Verify Entailment → Accept / Reject

确定性裁决内核（无 LLM 也可运行、可审计）：
  1. support_span 必须能在 source evidence 原文中找到（归一化包含）；
  2. statement 中的数字必须都能在原文中找到（防编造数字）；
  3. 信任升级防线：T4 证据上的抽取不得声明 confirmed_fact。
LLM entailment 为可选增强（配置 KEY 后可加），裁决基线诚实标注
verdict_basis=deterministic。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.source_trust import SourceTrust, check_fact_support, trust_for_authority

# 归一化剔除字符：空白 + ASCII 标点 + CJK 标点。
# 全部以码点（chr）构建，零字符串转义依赖。
_PUNCT_CODES = [
    32, 9, 10, 13, 46, 44, 58, 59, 33, 63, 40, 41, 91, 93, 123, 125,
    39, 34, 96, 126, 64, 35, 36, 37, 94, 38, 42, 43, 45, 95, 47, 92,
    124, 60, 62, 61,
    0x3000, 0xFF0C, 0x3002, 0x3001, 0xFF1B, 0xFF1A, 0xFF1F, 0xFF01,
    0x201C, 0x201D, 0x2018, 0x2019, 0xFF08, 0xFF09, 0x3010, 0x3011,
    0x300A, 0x300B, 0x00B7, 0x2026, 0x2014, 0x2013,
]
_PUNCT_CHARS = "".join(chr(c) for c in _PUNCT_CODES)
_NORMALIZE_RE = re.compile("[" + re.escape(_PUNCT_CHARS) + "]+")
_NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")

MAX_STATEMENT_LEN = 500
MAX_SPAN_LEN = 2000


def normalize_text(text: str) -> str:
    return _NORMALIZE_RE.sub("", (text or "").lower())


VALID_CLAIM_TYPES = (
    "fundamental_fact", "earnings_quality", "growth_outlook",
    "competitive_position", "valuation_assessment", "capital_allocation",
    "governance_quality", "industry_trend", "risk_factor", "catalyst",
)


@dataclass(frozen=True)
class ExtractionInput:
    source_evidence_id: str
    statement: str
    support_span: str
    fact_status: str = "analyst_inference"
    confidence_basis: str = ""
    extractor: str = "deterministic"
    prompt_version: str = "v0"
    claim_type: str = "fundamental_fact"


@dataclass(frozen=True)
class ExtractionVerdict:
    verdict: str  # accepted | rejected | uncertain（uncertain 走人工审查，不进正式 Research State）
    reason: str
    verdict_basis: str  # deterministic（LLM entailment 接入后扩展）
    trust_level: str  # 源证据的业务信任层


def verify_extraction(
    item: ExtractionInput,
    *,
    evidence_text: str,
    evidence_authority: str | None,
) -> ExtractionVerdict:
    """确定性引用反查。任何 check 失败 → rejected（不进正式 Research State）。"""
    trust = trust_for_authority(evidence_authority)
    statement = (item.statement or "").strip()
    span = (item.support_span or "").strip()

    if len(statement) > MAX_STATEMENT_LEN:
        return ExtractionVerdict(
            "rejected", "statement_too_long", "deterministic", trust.value
        )
    if len(span) > MAX_SPAN_LEN:
        return ExtractionVerdict(
            "rejected", "support_span_too_long", "deterministic", trust.value
        )

    # 1) 原文定位：support_span 必须出现在 evidence 原文（归一化包含）
    norm_ev = normalize_text(evidence_text)
    norm_span = normalize_text(span)
    if not norm_span or norm_span not in norm_ev:
        return ExtractionVerdict(
            "rejected", "support_span_not_found", "deterministic", trust.value
        )

    # 2) 数字一致性：statement 中的每个数字必须存在于原文（防编造数字）
    ev_numbers = set(_NUMBER_RE.findall(evidence_text or ""))
    for num in _NUMBER_RE.findall(statement):
        if num not in ev_numbers:
            return ExtractionVerdict(
                "rejected", "number_not_in_source", "deterministic", trust.value
            )

    # 3) 信任升级防线：confirmed_fact 需要源证据达到信任门槛（T4 直接拒绝）
    if item.fact_status == "confirmed_fact":
        try:
            check_fact_support([evidence_authority])
        except Exception:  # TrustEscalationError
            return ExtractionVerdict(
                "rejected", "trust_escalation", "deterministic", trust.value
            )

    # 4) Semantic Entailment（C4，整改 P0-05）：方向/主体/时间一致性
    ent_verdict, ent_reason = _semantic_entailment(statement, evidence_text)
    if ent_verdict == "rejected":
        return ExtractionVerdict("rejected", ent_reason, "deterministic", trust.value)
    if ent_verdict == "uncertain":
        return ExtractionVerdict("uncertain", ent_reason, "deterministic", trust.value)

    return ExtractionVerdict("accepted", "ok", "deterministic", trust.value)


# ── Semantic Entailment（C4，整改 P0-05 §7.4） ────────────────────────────────

_AFFIRM_NEGATE_PAIRS = [
    ("筹划", "不存在"), ("筹划", "否认"), ("筹划", "终止"),
    ("注入", "否认"), ("注入", "不存在"), ("注入", "终止"),
    ("减持", "增持"), ("增持", "减持"),
    ("上涨", "下跌"), ("下跌", "上涨"),
    ("通过", "否决"), ("批准", "拒绝"),
]

_MODALITY_PAIRS = [
    ("正在", "已经"), ("计划", "已完成"), ("拟", "已实施"),
]


def _semantic_entailment(statement: str, evidence_text: str) -> tuple[str, str]:
    """确定性语义一致性检查（无 LLM）。

    检查维度（方案 §7.4）：
      1. 方向一致性：statement 含正向标记但 evidence 含对应否定标记 → rejected
      2. 计划/完成一致性：statement 含「计划」但 evidence 含「已完成」→ uncertain
      3. 主体偷换：statement 引入 evidence 中不存在的新主体 → uncertain
    目前 only rejected-level conflicts block; uncertain 走人工审查。

    Returns: (verdict, reason) — verdict is "ok" or "rejected" or "uncertain"
    """
    stmt = statement or ""
    txt = evidence_text or ""

    # 1) 方向冲突：A→¬A 或 ¬A→A
    for pos, neg in _AFFIRM_NEGATE_PAIRS:
        if pos in stmt and neg in txt:
            return "rejected", f"semantic_direction_conflict: statement has '{pos}' but evidence has '{neg}'"
        if neg in stmt and pos in txt:
            return "rejected", f"semantic_direction_conflict: statement has '{neg}' but evidence has '{pos}'"

    # 2) 计划/完成混淆
    for plan, done in _MODALITY_PAIRS:
        if plan in stmt and done in txt and plan not in txt:
            return "rejected", f"modality_conflict: statement says '{plan}' but evidence says '{done}'"

    # 3) 范围扩大：statement 含「全部/所有/必然」但 evidence 用「部分/可能/或」
    for absolute, qualified in (("全部", "部分"), ("所有", "可能"), ("必然", "或")):
        if absolute in stmt and qualified in txt and absolute not in txt:
            return "rejected", "scope_inflation: statement uses absolute but evidence is qualified"

    # 4) 主体偷换（F4，任务书 §7.3）：Entity Dictionary 确定性检测。
    #    「中国稀土集团 ≠ 中国稀土股份」——不得仅因词面重叠而通过。
    #    保守触发（仅词典实体混淆对），避免第一阶段误报回潮（§22.1）。
    from app.domain.entity_dictionary import subject_swap_verdict

    swap_verdict, swap_reason = subject_swap_verdict(statement, txt)
    if swap_verdict == "uncertain":
        return "uncertain", swap_reason

    return "ok", ""
