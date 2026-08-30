"""Research Product 契约（R5，方案 §11/§5-§11.2）.

每个研究产品类型一份显式契约（Intent/Required Sections/Evidence 规则/
Missing Data 行为/Quality Gate/Output Artifacts/Monitor 行为）——
不得仅靠 Prompt 模板隐式约定（方案 §11.2）。

复用既有 Report/Artifact/Version 基座（方案 §11：不建平行报告系统）：
product_type 只是 reports 表的类型字段 + 本契约的编译期校验。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ProductType:
    COMPANY_DEEP_DIVE = "COMPANY_DEEP_DIVE"
    INDUSTRY_DEEP_DIVE = "INDUSTRY_DEEP_DIVE"
    EVENT_INVESTIGATION = "EVENT_INVESTIGATION"
    THESIS_REVIEW = "THESIS_REVIEW"
    MAINLINE_RADAR = "MAINLINE_RADAR"
    OVERSEAS_MAPPING = "OVERSEAS_MAPPING"
    DAILY_RESEARCH_BRIEF = "DAILY_RESEARCH_BRIEF"


ALL_PRODUCT_TYPES = (
    ProductType.COMPANY_DEEP_DIVE,
    ProductType.INDUSTRY_DEEP_DIVE,
    ProductType.EVENT_INVESTIGATION,
    ProductType.THESIS_REVIEW,
    ProductType.MAINLINE_RADAR,
    ProductType.OVERSEAS_MAPPING,
    ProductType.DAILY_RESEARCH_BRIEF,
)


@dataclass(frozen=True)
class ProductContract:
    product_type: str
    title_zh: str
    intent: str                      # commander focus 映射（§10.1）
    required_sections: tuple[str, ...]
    optional_sections: tuple[str, ...] = ()
    required_evidence_rule: str = "citation_verified"   # 全部 Claim 引用可反查（R2）
    quality_gate: str = "final_report_gate"
    missing_data_behavior: str = "disclose"             # §4.4：缺失显形
    monitor_behavior: str = "none"                      # none | register
    market_wide: bool = False        # 市场级产品（不绑定单一 instrument）
    notes: tuple[str, ...] = field(default=())


CONTRACTS: dict[str, ProductContract] = {
    ProductType.COMPANY_DEEP_DIVE: ProductContract(
        product_type=ProductType.COMPANY_DEEP_DIVE,
        title_zh="公司深度研究",
        intent="company",
        required_sections=("executive_summary", "market_and_capital", "key_theses", "risks"),
        optional_sections=("corporate_events", "valuation", "scenarios"),
        monitor_behavior="register",
    ),
    ProductType.INDUSTRY_DEEP_DIVE: ProductContract(
        product_type=ProductType.INDUSTRY_DEEP_DIVE,
        title_zh="产业深度研究",
        intent="industry",
        required_sections=("executive_summary", "key_theses", "risks"),
        optional_sections=("corporate_events",),
        monitor_behavior="register",
    ),
    ProductType.EVENT_INVESTIGATION: ProductContract(
        product_type=ProductType.EVENT_INVESTIGATION,
        title_zh="事件调查",
        intent="event",
        # §11.3：事件事实/时间线/相关主体/阶段/影响路径/反方/Invalidator/监控清单
        required_sections=("executive_summary", "corporate_events", "key_theses", "risks"),
        optional_sections=("market_and_capital", "valuation"),
        monitor_behavior="register",
        notes=(
            "事件事实与时间线必须 ≥1 条 T0/T1 证据支撑（A/B 信号分级在 R8 接入）",
            "当前阶段/下一关键节点由 CorporateEvent 时间线显形",
        ),
    ),
    ProductType.THESIS_REVIEW: ProductContract(
        product_type=ProductType.THESIS_REVIEW,
        title_zh="Thesis 复核",
        intent="thesis_review",
        required_sections=("executive_summary", "key_theses", "risks"),
        optional_sections=("scenarios",),
        notes=("支撑/反对 Claim 结构 + Invalidator 状态必须显形（§16.5）",),
    ),
    ProductType.MAINLINE_RADAR: ProductContract(
        product_type=ProductType.MAINLINE_RADAR,
        title_zh="主线雷达",
        intent="mainline",
        required_sections=("executive_summary",),
        optional_sections=("key_theses",),
        market_wide=True,
        notes=("表达：叙事 → 证据 → 驱动 → 产业映射（非涨幅榜，方案 §11.4）",),
    ),
    ProductType.OVERSEAS_MAPPING: ProductContract(
        product_type=ProductType.OVERSEAS_MAPPING,
        title_zh="海外映射",
        intent="overseas_mapping",
        required_sections=("executive_summary",),
        optional_sections=("key_theses",),
        market_wide=True,
        notes=("海外事件 → 全球产业 → A 股映射，每条映射必须挂证据（方案 §11.5）",),
    ),
    ProductType.DAILY_RESEARCH_BRIEF: ProductContract(
        product_type=ProductType.DAILY_RESEARCH_BRIEF,
        title_zh="每日研究简报",
        intent="general",
        required_sections=("executive_summary",),
        market_wide=True,
        notes=("新重大证据/Thesis 实质变化/事件信号/研究请求聚合（非行情播报，§11.6）",),
    ),
}


def get_contract(product_type: str | None) -> ProductContract:
    """未知类型 → COMPANY_DEEP_DIVE（默认），不猜。"""
    return CONTRACTS.get(product_type or "", CONTRACTS[ProductType.COMPANY_DEEP_DIVE])


def validate_product(
    contract: ProductContract,
    sections: dict[str, Any],
) -> list[str]:
    """编译期契约校验：缺 Required Section → 返回缺失清单（诚实显形，
    不阻断发布——由既有 FinalReportQualityGate 决定阻断）。"""
    missing = []
    for key in contract.required_sections:
        section = sections.get(key)
        items = list(getattr(section, "items", None) or [])
        if section is None or len(items) == 0:
            missing.append(key)
    return missing

