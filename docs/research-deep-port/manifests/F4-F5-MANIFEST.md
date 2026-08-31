# F4-F5-MANIFEST — Signal Production + Golden Rewrite

```text
F4 Signal Production Integration:
  - POST /signal-ladder/evaluate-evidence: production endpoint
    auto-loads evidence/trust/entities/builtin_rules
  - 旧 /signal-ladder/evaluate 保留但标记 LEGACY
  - required_evidence_types 实现于 SignalRule（不再 pass）
  - golden 改用 production API（不再自定义 keywords/level）
  status: IMPLEMENTED + VERIFIED（真机 API 返回正确空结果=语料无 A/B 证据）

F5 Golden Semantic Rewrite:
  - 减持→integration_signals=0 ✓（GOLD-SIGNAL-01）
  - 否定重组→A=false ✓（GOLD-SIGNAL-02）
  - SEM-03/04 在 test_c3_signal_rules.py 单测中 PASS
  - Thesis Diff affected_claims 2289→117（C1+影响门收紧）
  - 7b apply 在重复 golden run 时因 title UNIQUE 约束失败
    （已知限制：需在 apply 中处理幂等/去重）
  status: PARTIAL（7b 待修）
tests: 全量 backend exit 0
next: C6-C11
```
