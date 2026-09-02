# G12-MANIFEST — 长任务/并发/失败恢复

> 观澜研究能力语义迁移任务书 §G12（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §12

## 交付

### 1. 状态扩展（§G12.3）
- 后台任务状态补全：QUEUED/RUNNING/PAUSED/SUCCEEDED/FAILED/CANCELLED
  （+ dead_letter 标记）；**paused 不被泵认领**；
- 迁移 c6b7c8d9e0f3：heartbeat_at + dead_letter 列。

### 2. Heartbeat（§G12.4）
- claim 时记录 heartbeat_at（worker 存活信号；与 lease 恢复互补）；
- dead_letter：超过 max_attempts 的失败任务标记（可经 retry 恢复或人工处理）。

### 3. 控制端点补全（§G12.4）
- `POST /command/tasks/{id}/pause`（queued → paused）；
- `POST /command/tasks/{id}/resume`（paused → queued，恢复执行）；
- 既有：cancel/retry/merge/lease 恢复（F9）。

### 4. 版本锁（§G12.6）
- Current Thesis：claims (snapshot,statement) 唯一约束 + demote 修复（F2）；
- Definition Publish：published 状态转换门（G5）；
- Monitor State：状态机转换门（G7）；
- 并发唯一 Current：F2 测试 9 锁定。

## 测试（tests/test_g12_recovery.py，3 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | pause → 泵跳过 → resume → queued → succeeded | PASS |
| 2 | 重试耗尽 → dead_letter 标记 + attempts=max | PASS |
| 3 | claim 记录 heartbeat（worker 存活） | PASS |
（全量 backend 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G13：语义否定测试 + Golden A/B/C 收口。
