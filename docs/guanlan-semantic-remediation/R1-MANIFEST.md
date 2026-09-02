# R1-MANIFEST — 统一权威生产模型

> 观澜研究能力语义迁移第二轮整改任务书 §R1（P0）| 日期：2026-09-02

## 交付

### 1. 权威生产 Facade（app/services/research_production.py）
- `ResearchProductionFacade.create_strategy_from_screen_run`：
  **ScreenRun → StrategyDefinitionVersion 唯一生产路径**；
- ScreenRun 必须存在且来源 ScreenDefinition **已发布**（否则 404/422）；
- universe = ScreenRun 真实候选（rank/score 透传）；
- **input_digest**（源 ID+规则规范化 sha256）、**idempotency_key**
  （strategy:{run_id}:{def_version}）—— 同源重复提交返回既有版本（幂等）；
- **source_version_ids_json** 因果链：[card_id, card_version, def_id,
  def_version, run_id]；
- confirmation_id 预留（发布确认链）。

### 2. 权威字段落库（迁移 c7b8c9d0e1f4）
- strategy_versions 增：source_screen_definition_id / source_screen_run_id /
  input_digest / source_version_ids_json / confirmation_id / idempotency_key。

### 3. 生产路径收敛
- `POST /strategies/from-screen-run`：REST 入口走 Facade（幂等）；
- Replay 回退路径改造：不再调用旧 `create_from_screening` —— 直接克隆
  旧版本行（append-only，规则不变）+ 注册 strategy_version Artifact；
  rule_error 分支同样注册 Artifact；
- 旧 `create_from_screening` 保留只读兼容，不再被 Replay/Golden 调用；
- Golden B（test_g13_golden.py）改为权威路径：ScreenRun → from-screen-run
  （幂等断言）→ backtest-v2；**删除手工 StrategyVersionORM 种入**。

## 测试

- Golden B（test_g13_golden.py）：ScreenRun → 策略（幂等 + 因果链）→
  backtest-v2 全链 **PASS**；
- 全量 backend：528+ collected / 0 FAILED（live 排除）。

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
R2（Experience 验证与审批治理）依赖本路径的 confirmation_id 钩子。
