# F5-REVIEW-MANIFEST — Golden 真正重写（整改 P0-C）

```text
problem:  上次 commit 声称 golden 已重写但实际没有修改 test_r10_golden.py
fix:      真正替换了 golden 中的 signal-ladder 调用：
  - 旧：POST /signal-ladder/evaluate + 自定义 ladder[{level,keywords,label}]
  - 新：POST /signal-ladder/evaluate-evidence?instrument_id=…（BUILTIN_RULES）
  - 删除了旧的自定义 keywords/level/label 代码块
  - GOLD-SIGNAL-01: 减持→integration_hits=0（PASS）
  - Production Signal API count=0（语料无 A/B 整合证据 = 正确结果）
  - affected_claims 从 2289→122（C1+实体门收紧）
status:   24/25 PASS（7b apply 因 (snapshot_id,title) UNIQUE 约束在
  重复 golden run 时失败 —— 已知限制，需幂等处理）
tests:    backend 全量 exit 0
next:     F6-F12（F6 Semantic Entailment 完成/C4；F7-F9 UI 部分完成/C8；
  F10 回归已在每步运行；F11-F12 待 7b 修复后最终执行）
```
