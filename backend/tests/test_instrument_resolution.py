"""Four-board instrument resolution regression (task书 §71/§72).

Identity facts are static public reference data (code/name/exchange/board).
"""

import pytest

from app.domain.catalog import default_catalog


FOUR_BOARD_SAMPLES = [
    # (query, code, name, exchange, board, market)
    ("600519", "600519", "贵州茅台", "SSE", "main_board", "CN"),  # 沪市主板
    ("000001", "000001", "平安银行", "SZSE", "main_board", "CN"),  # 深市主板
    ("300750", "300750", "宁德时代", "SZSE", "chinext", "CN"),  # 创业板
    ("688981", "688981", "中芯国际", "SSE", "star_market", "CN"),  # 科创板
]


@pytest.mark.parametrize(("query", "code", "name", "exchange", "board", "market"), FOUR_BOARD_SAMPLES)
def test_four_board_code_resolution(query, code, name, exchange, board, market):
    results = default_catalog().resolve(query)
    assert len(results) == 1
    instrument = results[0].instrument
    assert instrument.code == code
    assert instrument.name == name
    assert instrument.exchange.value == exchange
    assert instrument.board.value == board
    assert instrument.market == market
    assert instrument.currency == "CNY"
    assert results[0].matched_by == "code"


def test_resolution_prefixed_forms():
    catalog = default_catalog()
    for raw in ("600519.SH", "SH600519", "000001.SZ", "SZ300750", "688981"):
        results = catalog.resolve(raw)
        assert len(results) == 1, raw
        assert results[0].matched_by == "code"


def test_name_and_alias_resolution():
    catalog = default_catalog()
    by_name = catalog.resolve("贵州茅台")
    assert by_name and by_name[0].instrument.code == "600519"

    by_partial = catalog.resolve("茅台")
    assert any(r.instrument.code == "600519" for r in by_partial)

    by_alias = catalog.resolve("CATL")
    assert by_alias and by_alias[0].instrument.code == "300750"
    assert by_alias[0].matched_by == "alias"

    by_en_name = catalog.resolve("ping an")
    assert any(r.instrument.code == "000001" for r in by_en_name)


def test_unresolvable_query_returns_empty_not_error():
    assert default_catalog().resolve("不存在的股票XYZ") == []
    assert default_catalog().resolve("") == []


def test_seed_catalog_covers_required_research_styles():
    """§71: sectors represented across the catalog, and all four boards present."""
    catalog = default_catalog()
    boards = {p.board for p in catalog.all()}
    assert boards == {"main_board", "chinext", "star_market"}
    assert all(p.exchange.value in ("SSE", "SZSE") for p in catalog.all())
    sectors = {p.sector for p in catalog.all()}
    assert {"financial", "consumer", "technology", "industrial", "materials"} <= sectors


def test_seed_static_fields_and_missing_data_contract():
    """Static reference facts are present; market data stays explicitly missing."""
    profile = default_catalog().resolve("600519")[0].instrument
    assert profile.data_availability == ("identity", "static_profile")
    assert profile.industry is not None  # static classification, source-backed later
    assert profile.market_cap is None  # market data must come from sources
    assert profile.listed_status.value == "listed"
