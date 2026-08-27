"""A-share code normalization and board classification (task书 §72)."""

import pytest

from app.domain.code_norm import InvalidInstrumentCode, normalize_code


@pytest.mark.parametrize(
    ("raw", "code", "exchange", "board"),
    [
        # 沪市主板
        ("600519", "600519", "SSE", "main_board"),
        ("600519.SH", "600519", "SSE", "main_board"),
        ("SH600519", "600519", "SSE", "main_board"),
        ("sh 600519", "600519", "SSE", "main_board"),
        ("601398", "601398", "SSE", "main_board"),
        # 科创板
        ("688981", "688981", "SSE", "star_market"),
        ("SH688111", "688111", "SSE", "star_market"),
        ("689009", "689009", "SSE", "star_market"),
        # 深市主板
        ("000001", "000001", "SZSE", "main_board"),
        ("000001.SZ", "000001", "SZSE", "main_board"),
        ("SZ000858", "000858", "SZSE", "main_board"),
        ("002594", "002594", "SZSE", "main_board"),
        ("003816", "003816", "SZSE", "main_board"),
        # 创业板
        ("300750", "300750", "SZSE", "chinext"),
        ("300750.SZ", "300750", "SZSE", "chinext"),
        ("SZ301269", "301269", "SZSE", "chinext"),
        # 北交所
        ("430047", "430047", "BSE", "bse"),
        ("831799.BJ", "831799", "BSE", "bse"),
    ],
)
def test_normalize_valid_forms(raw, code, exchange, board):
    got_code, got_exchange, got_board = normalize_code(raw)
    assert got_code == code
    assert got_exchange.value == exchange
    assert got_board.value == board


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "abc123",
        "12345",
        "1234567",
        "999999",  # unknown prefix
        "600519.XX",  # unknown suffix
        "400001",  # unknown prefix
    ],
)
def test_reject_invalid_forms(raw):
    with pytest.raises(InvalidInstrumentCode):
        normalize_code(raw)


def test_contradictory_hint_rejected():
    # 300750 is ChiNext (SZSE); a .SH suffix contradicts the code itself.
    with pytest.raises(InvalidInstrumentCode):
        normalize_code("300750.SH")
