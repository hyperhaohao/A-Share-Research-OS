"""R5 — Research Product 契约（方案 §11）.

验收：
  - 7 类产品契约齐全（P0 四类 + P1 三类），每契约含 required_sections/
    intent/missing_data_behavior；
  - EVENT_INVESTIGATION 缺 corporate_events section → 契约校验显形缺失
    （不阻断——阻断由 FinalReportQualityGate 决定）；
  - pipeline 按焦点映射落 product_type（event 焦点 → EVENT_INVESTIGATION）。
"""

from app.domain.research_products import (
    ALL_PRODUCT_TYPES,
    CONTRACTS,
    ProductContract,
    ProductType,
    get_contract,
    validate_product,
)
from types import SimpleNamespace


def test_seven_contracts_cover_p0_and_p1():
    assert set(ALL_PRODUCT_TYPES) == set(CONTRACTS.keys())
    for t in ("COMPANY_DEEP_DIVE", "INDUSTRY_DEEP_DIVE", "EVENT_INVESTIGATION",
              "THESIS_REVIEW", "MAINLINE_RADAR", "OVERSEAS_MAPPING",
              "DAILY_RESEARCH_BRIEF"):
        c = CONTRACTS[t]
        assert isinstance(c, ProductContract)
        assert c.required_sections, t
        assert c.missing_data_behavior == "disclose"  # §4.4


def test_unknown_type_falls_back_to_company_deep_dive():
    c = get_contract("NOT_A_TYPE")
    assert c.product_type == ProductType.COMPANY_DEEP_DIVE


def _sections_with(items_map):
    return {
        k: SimpleNamespace(items=items)
        for k, items in items_map.items()
    }


def test_event_investigation_contract_flags_missing_sections():
    contract = get_contract("EVENT_INVESTIGATION")
    assert contract.intent == "event"
    # 事件调查必须含 corporate_events —— 缺失显形
    sections = _sections_with({
        "executive_summary": [{}],
        "key_theses": [{}],
        "risks": [{}],
    })
    missing = validate_product(contract, sections)
    assert "corporate_events" in missing

    # 齐备 → 无缺失
    sections["corporate_events"] = SimpleNamespace(items=[{}])
    assert validate_product(contract, sections) == []


def test_market_wide_products_flagged():
    for t in ("MAINLINE_RADAR", "OVERSEAS_MAPPING", "DAILY_RESEARCH_BRIEF"):
        assert CONTRACTS[t].market_wide is True
    for t in ("COMPANY_DEEP_DIVE", "EVENT_INVESTIGATION"):
        assert CONTRACTS[t].market_wide is False
