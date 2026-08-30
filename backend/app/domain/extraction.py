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
    verdict: str  # accepted | rejected
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

    return ExtractionVerdict("accepted", "ok", "deterministic", trust.value)
