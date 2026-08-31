"""Signal Rule Contract + 内置规则库（R8-C3，整改 P0-03/04）.

方案 §6.1 SignalRule：
  rule_id / level / event_type / positive_patterns / negative_patterns /
  required_entities / required_source_trust / required_evidence_types /
  exclusions / state_transition / label / description

方案 §6.3 Signal 输出：
  signal_id / level / rule_id / rule_name / event_type / matched_pattern /
  evidence_ids / source_trust / entities / reason / detected_at

语义红线（§5.3 Negative Rules + §9 SEM-01…04）：
  - 减持 ≠ 资产整合 A/B 信号（除非显式 event_type=ownership_structure_change）
  - 否定标记文本（不存在/未筹划/否认/终止）不得触发射向 A 级
  - 终止重组 → restructuring_terminated（非正式启动）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class SignalRule:
    rule_id: str
    level: str  # "A" | "B"
    event_type: str
    positive_patterns: tuple[str, ...]
    negative_patterns: tuple[str, ...] = ()
    required_entities: tuple[str, ...] = ()
    required_source_trust: tuple[str, ...] = ()  # T0/T1/T2/T3/T4
    required_evidence_types: tuple[str, ...] = ()
    label: str = ""
    description: str = ""
    state_transition: str = ""


# ── 内置规则库（稀土资产整合 A/B 信号，方案 §5.2/§5.3） ─────────────────────────

BUILTIN_SIGNAL_RULES: list[SignalRule] = [
    # ── A 级正式信号 ──
    SignalRule(
        rule_id="restructuring_formal_launch",
        level="A",
        event_type="restructuring",
        positive_patterns=(
            "筹划重大资产重组", "重大资产重组预案", "重组报告书",
            "发行股份购买资产", "重大资产重组方案",
        ),
        negative_patterns=("不存在", "未筹划", "没有", "否认", "终止", "未考虑", "暂未"),
        required_source_trust=("T0_primary_disclosure",),
        required_evidence_types=("announcement",),
        label="重组正式启动",
        description="T0 级公告明确披露资产重组方案/预案/报告书",
        state_transition="B → A",
    ),
    SignalRule(
        rule_id="asset_injection_explicit",
        level="A",
        event_type="asset_injection",
        positive_patterns=(
            "明确资产注入方案", "标的资产明确", "注入上市公司",
            "资产注入预案", "收购资产",
        ),
        negative_patterns=("不存在", "没有", "否认", "暂未", "终止"),
        required_source_trust=("T0_primary_disclosure", "T1_official_institution"),
        label="资产注入方案明确",
        description="T0/T1 级披露明确资产注入方案",
        state_transition="B → A",
    ),
    SignalRule(
        rule_id="regulatory_approval_progress",
        level="A",
        event_type="regulatory_approval",
        positive_patterns=(
            "证监会核准", "国资委批准", "国资审批", "监管审批通过",
            "获得批复", "审核通过",
        ),
        negative_patterns=("未获得", "尚未", "被否决", "终止审核"),
        required_source_trust=("T0_primary_disclosure", "T1_official_institution"),
        label="监管审批明确推进",
        description="监管机构明确批准/核准资产重组事项",
        state_transition="B → A",
    ),
    # ── B 级前置信号 ──
    SignalRule(
        rule_id="assets_securitization_upgrade",
        level="B",
        event_type="asset_securitization",
        positive_patterns=(
            "资产证券化", "证券化率", "上市平台", "资本运作",
            "资产整合", "归集",
        ),
        negative_patterns=("不存在", "否认", "暂未考虑", "没有", "终止"),
        required_source_trust=("T0_primary_disclosure", "T1_official_institution", "T2_professional_research"),
        label="资产证券化措辞升级",
        description="集团/国资资产证券化措辞由原则性转为具体方案",
        state_transition="无 → B",
    ),
    SignalRule(
        rule_id="related_party_boundary_change",
        level="B",
        event_type="related_party_transaction",
        positive_patterns=(
            "同业竞争解决方案", "解决同业竞争", "业务边界调整",
            "托管协议", "资产租赁",
        ),
        negative_patterns=("不存在", "否认"),
        required_source_trust=("T0_primary_disclosure", "T1_official_institution"),
        label="同业竞争/业务边界变化",
        description="同业竞争解决由原则性转为具体方案；托管/租赁/关联交易结构变化",
        state_transition="无 → B",
    ),
    SignalRule(
        rule_id="ownership_structure_change",
        level="B",
        event_type="ownership_structure_change",
        positive_patterns=(
            "无偿划转", "股权划转", "股权变更", "控制权变化",
            "控股股东变更", "实际控制人变更",
        ),
        negative_patterns=("否认", "不存在"),
        required_source_trust=("T0_primary_disclosure", "T1_official_institution"),
        label="所有权结构变化",
        description="股权/控制权结构变化（方案 §5.2：地方国资划转/央地合作）",
        state_transition="无 → B",
    ),
]

# ── 事件类型映射（方案 P0-01 §3.4 Event Match 扩展） ─────────────────────────

EVENT_TYPE_LABELS = {
    "restructuring": "资产重组",
    "asset_injection": "资产注入",
    "share_reduction": "股东减持",
    "equity_change": "股权变更",
    "regulatory_approval": "监管审批",
    "asset_securitization": "资产证券化",
    "related_party_transaction": "关联交易/同业竞争",
    "ownership_structure_change": "所有权结构变化",
    "earnings": "业绩/财报",
    "policy": "政策/监管",
    "price": "价格/涨跌",
    "capital_flow": "资金流",
    "capacity": "产能/配额",
}


@dataclass
class SignalResult:
    """方案 §6.3 完整信号输出。"""

    signal_id: str
    level: str
    rule_id: str
    rule_name: str
    event_type: str
    matched_pattern: str
    evidence_ids: list[str]
    source_trust: str
    entities: list[str]
    reason: str
    detected_at: str

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "level": self.level,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "event_type": self.event_type,
            "matched_pattern": self.matched_pattern,
            "evidence_ids": list(self.evidence_ids),
            "source_trust": self.source_trust,
            "entities": list(self.entities),
            "reason": self.reason,
            "detected_at": self.detected_at,
        }
