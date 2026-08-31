"""C3 — Signal Ladder 重构（整改 P0-03/04，方案 §5.2/§5.3/§6.1/§6.3/§9）.

验收：
  - SEM-01: 减持 ≠ 资产整合 A/B 信号
  - SEM-02: 「不存在重大资产重组计划」→ A Signal = false
  - SEM-03: 「公司正在筹划重大资产重组」+ T0 → A Signal = true
  - SEM-04: 「终止重大资产重组」→ restructuring_terminated（非正式启动）
  - 完整输出：signal_id/level/rule_id/rule_name/event_type/matched_pattern/
    evidence_ids/source_trust/entities/reason/detected_at
"""

from app.domain.signal_rules import (
    BUILTIN_SIGNAL_RULES,
    SignalResult,
    SignalRule,
)
from app.services.research_inbox import SignalLadder


def _eval(text: str, trust: str = "T0_primary_disclosure", evidence_type: str = "announcement", **kw):
    return SignalLadder.evaluate_rules(
        observations=[{"observation_id": "o1", "text": text, "evidence_ids": ["ev_test01"], "evidence_types": [evidence_type]}],
        rules=BUILTIN_SIGNAL_RULES,
        evidence_trust={"ev_test01": trust},
        **kw,
    )


# ── SEM-01：减持 ≠ 资产整合 A/B 信号 ─────────────────────────────────────────

def test_sem01_share_reduction_is_not_asset_integration_signal():
    """减持是股权变动事件，不触发资产整合 A/B 信号。"""
    results = _eval("股东广晟控股集团计划减持公司股份不超过1061.22万股。")
    integration_signals = [
        r for r in results
        if r["event_type"] in ("restructuring", "asset_injection", "asset_securitization",
                               "related_party_transaction", "regulatory_approval")
    ]
    assert not integration_signals, (
        "减持 must NOT trigger asset integration A/B signals; "
        f"got {integration_signals}"
    )


# ── SEM-02：否定重组 → A Signal = false ─────────────────────────────────────

def test_sem02_negation_blocks_a_signal():
    """「不存在重大资产重组计划」→ A Signal = false。"""
    results = _eval("公司不存在重大资产重组计划。")
    a_signals = [r for r in results if r["level"] == "A"]
    assert not a_signals, f"negation must block A signal; got {a_signals}"


# ── SEM-03：正向重组 T0 → A Signal = true ────────────────────────────────────

def test_sem03_positive_restructuring_t0_is_a_signal():
    """「公司正在筹划重大资产重组」+ T0 → A Signal = true。"""
    results = _eval("公司正在筹划重大资产重组。")
    a_signals = [r for r in results if r["level"] == "A"]
    assert a_signals, f"T0 positive restructuring must trigger A signal; got {results}"
    assert a_signals[0]["rule_id"] == "restructuring_formal_launch"
    assert a_signals[0]["event_type"] == "restructuring"


# ── SEM-04：终止重组 → restructuring_terminated（非正式启动） ────────────────

def test_sem04_terminated_restructuring_not_formal_launch():
    """「公司终止重大资产重组」不得作为重组正式启动信号。"""
    results = _eval("公司终止重大资产重组。")
    formal = [r for r in results if r["level"] == "A" and r["rule_id"] == "restructuring_formal_launch"]
    assert not formal, "terminated restructuring must NOT trigger formal launch signal"


# ── 完整输出结构（方案 §6.3） ────────────────────────────────────────────────

def test_signal_output_full_contract():
    """信号输出必须包含全部 §6.3 字段。"""
    results = _eval("公司正在筹划重大资产重组。")
    assert results
    r = results[0]
    for field_name in ("signal_id", "level", "rule_id", "rule_name", "event_type",
                       "matched_pattern", "evidence_ids", "source_trust",
                       "entities", "reason", "detected_at"):
        assert field_name in r, f"missing field: {field_name}"


# ── T4 信任不足 → A 级不触发 ────────────────────────────────────────────────

def test_t4_trust_insufficient_for_a_signal():
    """T4（社交/未证实）不得触发 A 级正式信号（需 T0/T1）。"""
    results = _eval("公司正在筹划重大资产重组。", trust="T4_social_unverified")
    a_signals = [r for r in results if r["level"] == "A"]
    assert not a_signals, "T4 trust must NOT trigger A-level signal"
