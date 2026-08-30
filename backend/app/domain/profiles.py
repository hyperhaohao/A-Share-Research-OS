"""Agent Profiles（R4，方案 §10.4）：研究职责/工具边界白名单.

每个 profile 声明该类研究运行允许采集的 capabilities 与允许执行的 analysts。
管线按 profile 过滤（未指明 = general 全量，向后兼容）；不得让研究 agent
获得超出其职责的数据面（donor profile_tool_names 语义的 ASRO 化）。
"""

from __future__ import annotations

from typing import Any

ALL_CAPABILITIES = (
    "market_data",
    "announcements",
    "financials",
    "news",
    "capital_flow",
    "industry",
    "historical_data",
)

ALL_ANALYSTS = (
    "industry",
    "financial",
    "event",
    "news",
    "capital_flow",
    "macro_policy",
    "market",
)

PROFILES: dict[str, dict] = {
    # 研究通用（默认）：全量采集 + 全量分析师
    "general": {
        "capabilities": ALL_CAPABILITIES,
        "analysts": ALL_ANALYSTS,
    },
    # 公司研究：全维度
    "company": {
        "capabilities": ALL_CAPABILITIES,
        "analysts": ALL_ANALYSTS,
    },
    # 产业研究：产业链/政策/市场面
    "industry": {
        "capabilities": ("market_data", "news", "industry", "macro_policy"),
        "analysts": ("industry", "macro_policy", "market"),
    },
    # 事件研究：公告/新闻/资金面
    "event": {
        "capabilities": ("market_data", "announcements", "news", "capital_flow"),
        "analysts": ("event", "news", "capital_flow", "market"),
    },
    # 财报研究：财务/公告/新闻
    "earnings": {
        "capabilities": ("market_data", "financials", "announcements", "news"),
        "analysts": ("financial", "news"),
    },
    # 政策研究：宏观政策/新闻
    "policy": {
        "capabilities": ("market_data", "macro_policy", "news"),
        "analysts": ("macro_policy", "news", "market"),
    },
    # 主线雷达 / 海外映射 / Thesis 复核 / 对比：v1 退回 general（全量证据面）
    "mainline": {"capabilities": ALL_CAPABILITIES, "analysts": ALL_ANALYSTS},
    "overseas_mapping": {"capabilities": ALL_CAPABILITIES, "analysts": ALL_ANALYSTS},
    "thesis_review": {"capabilities": ALL_CAPABILITIES, "analysts": ALL_ANALYSTS},
    "comparison": {"capabilities": ALL_CAPABILITIES, "analysts": ALL_ANALYSTS},
}


def get_profile(name: str | None) -> dict:
    """未知 profile → general（不猜、不漂移）。"""
    return PROFILES.get(name or "general") or PROFILES["general"]


def filter_capabilities(capabilities: list[str], profile_name: str | None) -> list[str]:
    allowed = set(get_profile(profile_name)["capabilities"])
    return [c for c in capabilities if c in allowed]


def filter_analysts(analysts: list[tuple[str, Any]], profile_name: str | None) -> list[tuple[str, Any]]:
    allowed = set(get_profile(profile_name)["analysts"])
    return [(key, a) for key, a in analysts if key in allowed]

