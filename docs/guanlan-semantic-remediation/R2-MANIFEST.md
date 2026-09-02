# R2-MANIFEST — Experience 验证与审批治理

> 观澜研究能力语义迁移第二轮整改任务书 §R2（P0）| 日期：2026-09-02

## 交付

### 1. Fail-closed 验证结论（§R2.1）
- counterexample_search verdict 三态：空语料 → `inconclusive`；
  有语料无命中 → `no_counterexample_found`（不再单独视为 PASS）；
  命中反例 → `fail`；
- case verdict 由真实前向收益符号确定性判定（≥0 → pass，<0 → fail）。

### 2. Approval 治理（§R2.2）
- **approve/reject 必须持有效持久 Confirmation**（无 confirmation_id → 422）；
- digest 绑定 `card_id + card_version` —— 内容修改后旧确认失效（digest 不匹配 → 422）；
- 一次性消费（consume → 后续 approve 不可复用）；
- `ToolSpec.confirmation_consumed_by_executor` 标志：
  approve_experience_card/reject_experience_card 工具的审批消费由 executor
  内部执行（execute_tool 仅校验 approved 状态），避免双重消费；
- approval 决策写入审计事件（含 confirmation_id）。

### 3. 审批策略（§R2.2.4）
- approve 验证策略：≥1 明确 PASS + 0 未解决 FAIL
  （no_counterexample_found / inconclusive 不构成 PASS）；
- 配置化：验证策略由 approve 方法内 policy 检查实现，可扩展为外部配置。

### 4. 测试更新
- G3/G5/G13/phase C/R6/R7 测试全部改为 confirmation-gated approve 流程；
- verdict 断言更新（no_counterexample_found 等 fail-closed 语义）。

## 全量回归

```text
backend：0 FAILED（519 collected，live 默认排除）
```

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
