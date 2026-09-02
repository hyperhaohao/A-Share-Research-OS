# G3-MANIFEST — Experience 原—炼—验—用

> 观澜研究能力语义迁移任务书 §G3（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §3

## 交付

### 1. Approval 语义收紧（§G3.3）
- approve 需 **≥1 项明确 PASS** 的有效验证（case/historical/cross-company
  = inconclusive 不再满足）；
- **关键 FAIL 未解决禁止批准**（counterexample 命中反例 → verdict=fail →
  422，错误含未解决 FAIL 数）；
- 验证结论落库：validations.verdict（pass/fail/inconclusive）——
  counterexample_search：0 命中=pass、命中=fail；case/historical/
  cross_company：inconclusive（方向预测记录由 G8 接入后升级）；
- 旧测试按新契约更新（phase C/R6/R7 批准前补反例搜索）。

### 2. 审计事件（§G3.4）
- approve/reject 落 RunEvent（experience_approved/experience_rejected，
  run_id=audit_exp_*），测试断言事件存在。

### 3. 规则组件（§G3.5）
- `GET /experience-cards/{id}/rule-component`：APPROVED 卡 → 机器可消费
  结构（kind/component_version/preconditions/invalidators/signals/scope/
  usage_guidance/counterexamples/mechanism_terms/instrument_scope/
  compiled_at）；非 APPROVED → 422 experience.not_approved；
- G5 ScreenDefinition 编译将直接消费该组件。

### 4. 结构化经验字段（§G3.1）
- 迁移 c1d2e3f4a6b7：cards/versions 增 signals_json/scope_json/
  usage_guidance/counterexamples_json/validation_method；versions 同步携带
  （append-only 版本快照）。

### 5. 版本 Diff（§G3.6）
- `GET /experience-cards/{id}/versions/diff?v1=&v2=`：字段级 changed_fields
  + diff；缺失版本 404。

### 6. 非量化指标（§G3.7）
- `GET /experience-cards/{id}/metrics`：真实 case 记录聚合 —— n_cases/
  span_days/前向收益分布（mean/min/max/positive_rate）；
- **样本 <3 → status=INSUFFICIENT（不造数值）**；
- directional_ic：honest INSUFFICIENT（预测方向记录由 G8 因果链接入）。

### 7. F7 审批门整合（§G3.4）
- 注册高风险工具 approve_experience_card / reject_experience_card
  （15 工具）：批准/否决必须经 Confirmation Gate（digest 绑定/一次性消费/
  审计事件）。

## 测试（tests/test_g3_experience.py，10 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | case-only（inconclusive）→ 禁止批准 | PASS |
| 2 | FAIL 未解决 → 禁止批准（即使另有 pass） | PASS |
| 3 | counterexample pass → 批准 OK + 审计事件 | PASS |
| 4 | reject 落审计事件 | PASS |
| 5 | 规则组件未批准 422 | PASS |
| 6 | 规则组件结构化输出（preconditions/invalidators/mechanism_terms） | PASS |
| 7 | 版本 Diff 字段级（v1↔v2；缺失版本 404） | PASS |
| 8 | 指标 <3 样本 → INSUFFICIENT | PASS |
| 9 | 指标 3 样本 → 真实 n/span/分布（positive_rate 2/3）+ IC INSUFFICIENT | PASS |
| 10 | F7 工具批准（确认门全链）+ reject 工具同样需确认 | PASS |
（旧测试 phase C/R6/R7 按 §G3.3 新契约更新；全量 backend 481 collected / 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G4：Typed Dataflow Workflow（端口/schema/data_contract/节点 I/O 持久化）。
