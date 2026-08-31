# C3-MANIFEST — Signal Ladder 重构（整改 P0-03/04）

```text
problem:  旧 SignalLadder 用 `keyword in text = hit`，无否定规则/无信任门/
          无实体校验 → 减持被误判为资产整合 B 信号
fix:
  - app/domain/signal_rules.py：SignalRule 契约（rule_id/level/event_type/
    positive_patterns/negative_patterns/required_entities/required_source_trust/
    required_evidence_types/state_transition/label/description）
  - 6 条内置规则（3 A + 3 B）：A=重组正式启动/资产注入明确/监管审批推进；
    B=资产证券化升级/同业竞争边界/所有权结构变化
  - SignalLadder.evaluate_rules：正向命中→负 pattern 排除→source trust gate→
    entity gate→SignalResult（§6.3 全字段输出）
  - 否定标记（不存在/未筹划/否认/终止）命中→该规则不触发
  - T4 信任不足→A 级不触发（required_source_trust 含 T0/T1）
  - 旧 keyword-only ladder API 兼容保留
tests:    tests/test_c3_signal_rules.py 6/6（SEM-01…04 + 完整输出 + T4 信任门）
next:     C4 Citation Semantic Entailment
```
