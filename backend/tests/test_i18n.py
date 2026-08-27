"""Language normalization for backend message resolution."""

from app.core.i18n import normalize_language, resolve_message


def test_zh_variants_map_to_zh_cn():
    assert normalize_language("zh-CN,zh;q=0.9") == "zh-CN"
    assert normalize_language("zh-TW") == "zh-CN"
    assert normalize_language("zh") == "zh-CN"


def test_other_languages_map_to_en_us():
    assert normalize_language("en-US,en;q=0.9") == "en-US"
    assert normalize_language(None) == "en-US"
    assert normalize_language("ja-JP") == "en-US"


def test_unknown_code_resolves_to_none_not_crash():
    assert resolve_message("no.such.code", "zh-CN") is None
