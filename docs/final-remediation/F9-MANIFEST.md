# F9-MANIFEST — Weiwo Background Runway / Session Governance / Memory

> 阶段：F9（第三轮整改任务书 §11 F9 / §8.8-§8.9 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 后台任务跑道（§8.8）—— 持久化，不依赖 daemon thread
- 新表 `command_background_tasks`（迁移 a8b9c0d1e2f5）+ 服务
  `app/services/background_runway.py`；
- **Confirm → Background Task → Progress Events → 用户继续对话 →
  Complete/Fail/Retry → 事件通知 → Artifact Auto-open** 全链；
- 提交：工具白名单校验（404）+ 合并策略（queued/running 同 digest 复用）+
  **高风险工具需已消费的审批确认**（confirmation_id 消费后入队）；
- 执行泵：**Scheduler.tick 驱动 run_one**（compose scheduler 容器/独立
  worker 进程皆可；非页面打开才工作，§23 一致）；
- **lease 恢复**：worker 崩溃 → lease 过期 running 被下一 worker 认领重试；
- **失败自动重试**（attempts<max → 重新入队）→ 最终 failed 显形
  last_error + task_failed 事件；手动 **retry 恢复入口**（failed/cancelled →
  queued）；
- **安全取消**：queued/running → cancelled，泵校验状态后跳过；
- 进度/耗时真实落库（progress/current_step/started/finished/elapsed_ms/
  attempts）；
- 会话级 + 全局任务列表 API；
- 完成 → task_completed 事件 + Artifact 自动打开 Workbench（F8 衔接）。

### 2. 会话治理（§8.9）
- command_sessions 增 status(active|archived) + last_activity_at；
- PATCH /command/sessions/{sid}（重命名/归档/恢复）；默认列表不含 archived；
- `GET /command/sessions/{sid}/overview`：状态 + 关联
  Instrument/Thesis/Plan/Workbench Tabs/Background Tasks。

### 3. 双层记忆（§8.9）
- **Session Memory**（command_session_memory）：goal / confirmed_params /
  key_conclusions / open_questions；GET/PUT 端点；
- Research Memory：既有 /memories（R7 candidate→active→retired）不变 —— 双层
  结构（会话层 vs 治理层）分离。

### 4. 长对话压缩（§8.9）
- `maybe_compact`：达到轮次阈值（默认 50）→ **确定性**结构化摘要
  （user_requests / plans / artifacts / key_conclusions / open_questions /
  instruments）；阈值内不压缩并显形原因；
- 摘要版本可追溯（summary_version 单调 + compacted_at）；
- **原始事件不动**（append-only 仍可审计）；
- 压缩显形为 memory_compacted 事件（披露注入，§8.9）。

## 测试（tests/test_f9_background_session_memory.py，7 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 提交（queued+合并）→ 泵执行 → succeeded+progress100+结果 → task_started/completed 事件 → 任务期间对话照常 | PASS |
| 2 | 失败重试至 max → failed+last_error → 手动 retry 恢复 | PASS |
| 3 | 高风险工具无确认 → 422 | PASS |
| 4 | 未知工具 404 + 提交后取消 → 泵跳过 | PASS |
| 5 | 会话治理：重命名 + 概览关联对象 + 归档后默认列表不含 | PASS |
| 6 | Session Memory PUT/GET（goal/params/conclusions/questions） | PASS |
| 7 | 压缩：force → summary_version 1 + memory_compacted 事件 + 原始事件保留 + 回读 | PASS |
backend 全量：exit 0，0 FAILED（459 collected）

## 新增/修改文件

- 新增：app/services/background_runway.py、app/services/session_memory.py、
  app/application/background_orm.py、
  alembic/versions/a8b9c0d1e2f5_f9_background_session_memory.py、
  tests/test_f9_background_session_memory.py
- 修改：app/application/conversation.py（会话治理字段 + 列表过滤）、
  app/scheduler/scheduler.py（后台任务泵 hook）、app/api/command.py
  （tasks/sessions/memory 端点 + ORM 注册）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
已知边界：单 worker 串行泵（有界 5/ tick）；多 worker 并发认领在
PostgreSQL 行锁下安全，SQLite 测试栈串行（与部署现实一致）。
