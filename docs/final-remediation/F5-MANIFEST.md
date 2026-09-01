# F5-MANIFEST — Weiwo Event Foundation

> 阶段：F5（第三轮整改任务书 §11 F5 / §8.3-§8.4 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. Commander Event Protocol（§8.3）
- 新表 `command_events`（迁移 e4f5a6b7c8d9）+ ORM + 事件协议模块
  `app/application/command_events.py`；
- Envelope 全键：event_id / session_id / sequence / event_type / created_at /
  correlation_id / plan_id / task_id / status / payload / artifact_ids /
  provenance；
- **sequence 每 Session 单调递增**：max+1 + UniqueConstraint(session_id,
  sequence) + 有界重试（并发安全）；
- **append-only**：无更新/删除端点（行为面测试断言 PUT/DELETE → 405）；
  事件类型白名单（§8.3 最低 21 类 + session_created）；
- Tool Call ↔ Tool Result 经 correlation_id 关联（corr_<plan>_<step>）；
- artifact_ids 落事件 → Artifact 可反查产生它的事件
  （events_for_artifact）；
- payload 版本化（schema_version=v1）；敏感键递归脱敏
  （api_key/password/token/secret/authorization/cookie → [redacted]）。

### 2. 执行链事件化（真实发射点）
- POST /command/sessions → session_created；
- POST /command/sessions/{sid}/turns → user_message / assistant_message
  （含显式拒绝）/ plan_created（含计划步骤）；
- ResearchCommander.execute（worker 线程，全程）→ step_started /
  tool_call / tool_result（含 detail + artifact_ids）/ tool_error /
  step_updated / artifact_created / run_completed / run_failed。

### 3. Snapshot → Replay → Live SSE（§8.4）
- `GET /command/sessions/{sid}/events?after_sequence=N`：断点回放（纯读，
  重放不重复执行副作用）；
- `GET /command/sessions/{sid}/snapshot`：会话 + turns + plans +
  latest_sequence（刷新恢复数据源；未知会话 404）；
- `GET /command/sessions/{sid}/stream?after_sequence=N`：**真实 SSE**
  （text/event-stream；retry/id/event/data 帧）：
  Connect → Replay(after_sequence) → Live Events（0.6s 短会话轮询）→
  Heartbeat（保活帧）→ 达时上限 stream_end 注释帧；
  每轮回放有界（500）构成背压；慢客户端/断线以 last sequence 重连，
  sequence 单调 → 不丢不重。

## 测试（tests/test_f5_command_events.py，6 用例，真实 API + mocked 源数据）

| # | 场景 | 结果 |
|---|---|---|
| 1 | Envelope 全键 + sequence 单调无重复 + 执行链事件（session→user→plan→step/tool→run_completed）+ tool_call↔result correlation + artifact_ids | PASS |
| 2 | Replay after_sequence 断点续传 | PASS |
| 3 | Live SSE：text/event-stream、id/event/data 帧、heartbeat、断线重连不重放旧事件 | PASS |
| 4 | 敏感键脱敏 + Session 隔离（B 会话不见 A 会话事件） | PASS |
| 5 | append-only：PUT/DELETE 405；未知 event_type 拒绝 | PASS |
| 6 | Snapshot（turns/plans/latest_sequence；未知会话 404） | PASS |

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（434 collected）
```

## 修改/新增文件

- 新增：app/application/command_events.py、command_events_orm.py、
  alembic/versions/e4f5a6b7c8d9_f5_command_events.py、
  tests/test_f5_command_events.py
- 修改：app/api/command.py（事件发射 + events/snapshot/stream 端点）、
  app/services/commander.py（执行链全程事件化）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
F6–F9 将在此协议上叠加 Tool Registry / Approval / Workbench / Background；
F10 前端消费 SSE。
