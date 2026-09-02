# G4-MANIFEST — Typed Dataflow Workflow

> 观澜研究能力语义迁移任务书 §G4（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §4（Edge 不传数据 → FAIL）

## 交付

### 1. 节点类型规格（15 类最低清单 + output）
- `NODE_TYPE_SPECS`：每类声明 input_ports/output_ports（name+type）、
  parameters_schema（参数名→(类型,默认值)）、execution_policy
  （pure/side_effect/blocking）；
- 覆盖 §G4 全部最低类型：evidence/quote/industry/transform/filter/rule/
  screening/backtest/validation/prediction/thesis_impact/experience_output/
  memory_output/notification/human_confirmation（+output 终端）；
- 端口类型系统：instrument_ref/evidence_set/quote_series/series/table/
  rule_result/metrics/graph/diff/text/any。

### 2. 图校验 v2（发布门槛）
- v1 规则保留（环/重复 key/未知 kind）+ 新增：
  **端口类型不匹配 → 422 不能发布**；重复 output 端口名；
  孤立节点（无输入且非输入型 kind）；output 不可达（从输入型节点 BFS）；
- 修复过程登记：reachability 种子初版误用 node key 与 kind 混比 → 修正为
  按 kind 判定（自测捕获）。

### 3. 真实数据流执行器（§G4 核心）
- **Edge 承担数据传输**：下游 `_collect_inputs` 仅从显式边指定的
  source_port 取上游输出 → target_port；分支各边独立取数，互不覆盖；
- **节点 I/O 不可变账本**（workflow_node_io，迁移 c2e3f4a5b6c8）：
  每 attempt 追加一行（input_json/output_json/status/error/时间）；
- 失败传播：节点异常 → 下游 skipped + run failed（错误落 run.error）；
- **恢复语义**：retry 时 pure 节点复用既有输出、失败节点重跑 attempt+1；
- 控制面：pause/resume/cancel/retry（非法状态转换 422）；
- 执行器真实消费上游：quote 节点产出真实日线序列（collect_daily_bars）、
  backtest 消费 quote_series 调 forward_returns、thesis_impact 调真实
  Thesis Diff、screening 走真实 ScreeningService、experience/memory/
  notification 落真实对象。

### 4. API（/workflows-typed/*）
definitions（发布校验）/ runs（创建+执行）/ runs/{id}（含 node_io 账本）/
runs/{id}/control（pause/resume/cancel/retry）。

## 测试（tests/test_g4_workflow_typed.py，6 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 端口类型不匹配 → 422 不能发布 | PASS |
| 2 | 孤立节点 + 不可达 output → 422 | PASS |
| 3 | 真实数据流（evidence→transform→output）+ 节点 I/O 账本（下游输入=上游输出） | PASS |
| 4 | 分支隔离（同源两分支不同参数 → 输出互不覆盖） | PASS |
| 5 | 失败传播（screening 卡缺失 → failed + 下游 skipped）+ retry（attempt 2 落账本） | PASS |
| 6 | 控制面（succeeded 后 pause/cancel 422；未知 action 422） | PASS |
（全量 backend 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G5：Screening 消费 G3 规则组件（Experience-driven Definition 编译）。
