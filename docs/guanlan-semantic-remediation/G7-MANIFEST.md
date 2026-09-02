# G7-MANIFEST — Strategy-aware Monitor

> 观澜研究能力语义迁移任务书 §G7（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §7（通用行情/新闻监控 → FAIL）

## 交付

### 1. 执行所引用策略版本规则（§G7.2）
- run_monitor 每次运行对 universe 标的**执行所引用策略版本的真实规则**
  （复用 G6 事件引擎：entry quote_move 规则 + max_hold_days 出场，
  Cursor 窗口内增量）；
- 策略规则信号（strategy_entry_exit）与通用观察信号分离落库并计数披露
  （strategy_signals）。

### 2. 状态机（§G7.3/§G7.4）
- 状态机：**ACTIVE ↔ PAUSED → RETIRED**（非法转换 422 monitor.bad_transition；
  决定落 monitor_status_changed 审计事件）；
- PAUSED 不运行（run → 显式拒绝）；
- **VALIDATED 版本亦可监控**（§G7.4 不再排除 Validated）。

### 3. Cursor + 幂等（§G7.6/DoD1）
- quote_cursor / evidence_cursor 落库（迁移 c4a5b6c7d8e0）；
- 信号 **idempotency_key**（monitor:instrument:entry:exit）——同批输入
  重复运行零新增信号（测试锁定）；
- Cursor 推进：行情 Cursor = 运行时间（下次只看增量）。

### 4. 方向与可解释性（§G7.10 + F4 衔接）
- 信号方向字段（direction=long/exit）落库并透出（正负方向保留）；
- 决策 rationale 携 F4 置信度 basis（可解释，无固定启发式）。

### 5. 失败持久化（§G7.12）
- 策略执行异常 → last_error 落 monitor 行（不静默退出）。

## 测试（tests/test_g7_monitor.py，4 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 执行策略规则（strategy_signals≥1，G6 引擎对真实日线）+ 方向保留 + Cursor 幂等（二跑零新增） | PASS |
| 2 | VALIDATED 版本可监控 | PASS |
| 3 | 状态机：PAUSED 不运行；ACTIVE↔PAUSED；RETIRED 终态非法回转 422 | PASS |
| 4 | 决策 rationale 携可解释置信度 basis | PASS |
（全量 backend 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
