# F10-MANIFEST — Weiwo Product Cards & UI

> 阶段：F10（第三轮整改任务书 §11 F10 / §8.10 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 中栏事件线程卡片（§8.10）
- 新组件 `features/command-center/EventThread.tsx`：由 F5 事件协议驱动的
  卡片流（append-only 回放 + **真实 EventSource SSE** live 消费，
  polling 兜底；sequence/event_id 双重去重 → 断线重连不丢不重）；
- 卡片类型：PlanCard / ToolCallCard / ToolResultCard / ToolErrorCard（失败
  显形红色）/ **ConfirmationCard（批准/拒绝动作直接走 F7 状态机）** /
  TaskCard（进度）/ RunResultCard / ArtifactCard（工作台已自动打开披露）/
  MemoryCard（压缩版本 + 可审计说明）；user/assistant 气泡由既有 turns
  渲染（线程内去重不重复展示）；role=status + aria-label（a11y 基础）。

### 2. 左栏状态（§8.10）
- **未处理确认**面板：GET confirmations?status=pending（5s 轮询）+
  批准/拒绝动作（服务端状态真源；批准后立即从 pending 消失）；
- **后台任务**面板：GET tasks（状态着色 + 进度% + failed/cancelled 的
  「重试」恢复入口）；
- 既有：当前计划墨痕 / 正在运行 / 最近计划 / 会话切换（多会话）。

### 3. 右栏动态 Workbench（F8 已建，此处集成验证）
- compose 栈重建后实测：前端 bundle 含 workbench/event-thread 代码；
  后端 events / snapshot / workbench / confirmations / tasks / memory /
  tools(13) 端点全部 live；F5–F9 迁移在真实数据卷自动应用。

## 测试

### 前端（tests/event-thread.test.tsx，2 用例）
| # | 场景 | 结果 |
|---|---|---|
| 1 | 事件流 → Tool Call/Result/Error + Task + Run Failed 卡片渲染；失败文本显形 | PASS |
| 2 | 确认卡片「批准」→ 创建确认 + decide(approved) 服务端调用 | PASS |
frontend 全量：vitest 35/35（8 files）+ tsc PASS + build PASS

### Live Verify（compose 栈重建实测）
```text
docker compose build backend frontend && up -d
迁移：e4f5a6b7c8d9 → f5a6b7c8d9e0 → f6a7b8c9d0e1 → a8b9c0d1e2f5（真实数据卷自动应用）
POST /command/sessions → session_created 事件入流（count=1）
GET /command/sessions/{sid}/{events,workbench,memory,snapshot} + /command/confirmations + /command/tools(13) 全通
前端 bundle：cc-event-thread / workbench 代码在内（:8080）
```

## 新增/修改文件

- 新增：frontend/src/features/command-center/EventThread.tsx、
  frontend/tests/event-thread.test.tsx、.claude/launch.json
- 修改：CommandCenterTranscript.tsx（线程集成）、CommandCenterLeft.tsx
  （确认/任务面板）、CommandCenterWorkbench.tsx、i18n locales（zh/en）、
  command-center.css

## 状态

IMPLEMENTED / INTEGRATED / TESTED / REAL_VERIFIED（live 栈端点 + bundle）。
浏览器视觉回归与 Playwright E2E 在 F13/F14 执行。
