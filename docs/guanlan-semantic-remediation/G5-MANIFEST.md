# G5-MANIFEST — Experience-driven Smart Screening

> 观澜研究能力语义迁移任务书 §G5（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §5（DEFAULT_RULES 常量，经验内容不进规则 → FAIL）

## 交付

### 1. ScreenDefinition Vn（新域模型，迁移 c3f4a5b6c8d9）
- 表 `screen_definitions`：source_card_id/source_card_version、universe、
  rules、ranking（formula_version+weights）、missing_data_policy、
  as_of_policy、status(draft/published/retired)、version、compiled payload；
- 表 `screen_definition_runs`：完整 universe + candidates + exclusions +
  artifact_id 落档。

### 2. 编译器（§G5.2，确定性）
- **仅 Approved Experience 可编译**（G3 规则组件；未批准 → 422
  `screen.source_not_approved`，§G5.1）；
- preconditions/invalidators/signals 按模式映射为可检查规则
  （holding_reduction{min_pct}/no_hedge/earnings_positive/has_share_reduction/
  invalidator_keyword/signal_rule）；无法映射的自由文本进 uncompiled 显形；
  invalidators 编译为排除规则；
- **修复过程登记**：初版 `_map_text` 未校验匹配即返回 kind（第一个非持有
  模式恒胜出）→ 修正为「匹配才返回」+ 特定模式先于泛化
  （holding_reduction 先于「减持」）。

### 3. 发布门（§G5.3）
- draft → published 需人工确认（confirm=False → 422
  `screen.publish_needs_confirmation`）；发布幂等；draft 运行 → 422。

### 4. PIT 执行（§G5.4/§G5.5）
- **Current Thesis Selector**（get_current_thesis）参与 thesis 因子；
- 证据可见性 PIT：所有规则求值以 `available_time ≤ as_of` 过滤；
- Universe = 产业链共位公司（G1 明确关系，非关键词）。

### 5. 候选/排除解释（§G5.6-8）
- 候选：逐通过规则解释 + 因子值（evidence_freshness/thesis_aligned）+
  score + **rank** + ranking_formula_version（screen_rank_v1 权重表）；
- 排除：按 instrument 去重、保留多条原因（rule/source/detail）；
- ScreenRun Artifact 注册（universe+结果完整落档；失败 →
  INCOMPLETE_PROVENANCE 显形）。

## 测试（tests/test_g5_screening.py，6 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 未批准 Experience 编译 → 422 | PASS |
| 2 | 两张机制不同的卡 → 规则集不同（holding_reduction vs earnings_positive） | PASS |
| 3 | 发布门（未确认 422 / draft 运行 422 / 确认后 published） | PASS |
| 4 | PIT 执行：000831 候选（rank/因子/解释/公式版本）+ 600259 排除原因 + Artifact | PASS |
| 5 | Memory/验证等旧流兼容 | PASS |
| 6 | precondition 变化（≥0.3% vs ≥1%）→ 候选可解释变化 | PASS |
（全量 backend 0 FAILED —— f5 order-flake 单测复跑通过，已登记）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G6：Strategy Lab 可执行回测（entry/exit/risk 真实交易路径）。
