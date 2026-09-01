# F7-MANIFEST — Weiwo Approval Governance

> 阶段：F7（第三轮整改任务书 §11 F7 / §8.6 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 持久化审批确认状态机（§8.6）
- 新表 `command_confirmations`（迁移 f5a6b7c8d9e0）+ 服务
  `app/services/confirmation_gate.py`；
- 状态机：**pending → approved | rejected | expired | revoked → consumed**
  （approved 未消费可 revoked；rejected/expired/consumed 终态）；
- **参数摘要绑定**：digest = sha256(规范化 tool+arguments)；批准后参数不可
  被替换（执行时 digest 复核，替换 → invalid，防 TOCTOU §15）；
- **lease/timeout**：pending 超过 expires_at → expired（读取/决定/执行时
  惰性判定）；过期不可批准；
- **重复点击幂等**：终态重复决定返回当前状态（无错误、无副作用、
  不重复发事件）；
- **拒绝无副作用**：rejected/expired/revoked/consumed 一律不可执行；
- **一次性消费**：执行成功即 consumed；复用 confirmation_id → invalid；
- **审计**：全部决定落库（decided_at/decided_by）+ confirmation_requested /
  confirmation_decided 事件进帷幄事件流（F5 协议）。

### 2. 与 Tool Registry（F6）集成
- `execute_tool` 新增 `confirmation_id` 路径：approved + digest 匹配 +
  未过期未消费 → 消费并执行；否则 tool.confirmation_invalid /
  tool.confirmation_required（含创建确认的操作指引）；
- 非高风险工具创建确认 → 422 confirmation.not_applicable。

### 3. API
- `POST /command/confirmations`（创建 pending；requested 事件）
- `GET /command/confirmations?status=`（左栏未处理确认数据面）
- `GET /command/confirmations/{id}`
- `POST /command/confirmations/{id}/decide`（approved/rejected/revoked）

## 测试（tests/test_f7_confirmations.py，8 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 全流程：创建（pending+digest+requested 事件）→ 批准 → 执行（修订成功）→ consumed → decided 事件 | PASS |
| 2 | 拒绝 → 执行 invalid；无副作用（Thesis 数不变） | PASS |
| 3 | 重复决定幂等（approve×2、approved 后 reject 不改状态） | PASS |
| 4 | 批准后参数替换 → digest 不匹配 → invalid | PASS |
| 5 | 非高风险工具创建确认 → 422 | PASS |
| 6 | approved → revoked → 执行 invalid | PASS |
| 7 | lease 过期 → expired（不可批准） | PASS |
| 8 | 按状态列举未处理确认（左栏数据面） | PASS |

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（448 collected）
```

## 新增/修改文件

- 新增：app/services/confirmation_gate.py、app/application/confirmations_orm.py、
  alembic/versions/f5a6b7c8d9e0_f7_command_confirmations.py、
  tests/test_f7_confirmations.py
- 修改：app/services/tool_registry.py（confirmation_id 消费路径）、
  app/api/command.py（confirmations 端点 + execute 入参）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。F10 提供确认卡片 UI（服务端状态真源）。
