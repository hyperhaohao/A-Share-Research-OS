# G8-MANIFEST — Causal Replay

> 观澜研究能力语义迁移任务书 §G8（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §8（因果链不成立 → FAIL）

## 交付

### 1. 因果引用（§G8.1）
- 迁移 c5b6c7d8e9f1：predictions.decision_id（索引）；
- 新端点 `POST /predictions/from-decision`：由 Decision 因果派生 Prediction
  （decision_id 链接落库；方向/区间由研究者显式锚定）；
- **Replay 严格因果过滤**：candidate 只取 `decision_id == 本 Decision` 的
  预测 —— 无关 Prediction（即使同 universe、已验证）不得进入 Replay
  （ReplayRefusal 显形，任务书 DoD）。

### 2. Attribution 七类补全（§G8.3）
- 新增 RULE_ERROR（方向错误且回撤显著 ≥3% → 止损/入场规则问题，确定性）、
  EXECUTION_ERROR、INSUFFICIENT_DATA（缺收益数据时显形）；
- 既有 evidence/claim/timing/market_regime 归因保留。

### 3. 规则反馈改变可执行定义（§G8.5）
- rule_error 归因 → 新策略版本 v(n+1) 直接克隆旧版本行 +
  **exit_rules 追加 stop_loss{pct = max(3, 不利波动×1.2)}**（确定性、
  可解释；origin 注明 replay rule_error 与不利波动幅度）；
- 旧版本不可变：旧版本 exit_rules 不被改写（测试锁定）；
- 反馈路径不依赖 screening run 存在（直接克隆；缺失诚实跳过 v2）。

### 4. 修复
- 旧 phase J 测试按新因果契约更新（预测带 decision_id —— G8 因果语义）。

## 测试（tests/test_g8_causal_replay.py，3 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 无因果链接的成熟预测 → Replay 拒绝（409/422 + 缺环显形） | PASS |
| 2 | 因果链接 → Replay 成功（review.prediction_id/validation_id 全可见） | PASS |
| 3 | 方向错误+显著回撤 → rule_error 归因 → 新版本 stop_loss 规则可执行修改 + 旧版本不可变 | PASS |
（全量 backend 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G9：Research Products Artifact/Version/PIT/Provenance + 页面。
