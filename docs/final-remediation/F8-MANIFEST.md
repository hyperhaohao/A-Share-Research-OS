# F8-MANIFEST — Weiwo Dynamic Workbench

> 阶段：F8（第三轮整改任务书 §11 F8 / §8.7 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 页面注册表 + 受控 Handoff（§8.7：禁任意 URL 注入）
- 新表 `command_workbench_tabs`（迁移 f6a7b8c9d0e1）+ 服务
  `app/services/workbench.py`；
- **PAGE_REGISTRY 20 页白名单**（instrument-workspace / thesis-center /
  research-report / experience-card / workflow-run / screening-result /
  strategy-lab / strategy-monitor / industry-map / global-macro /
  research-graph / daily-brief 等 §8.7 最低页面集全覆盖）；
- **ARTIFACT_PAGE_MAP**：19 类 Artifact → 页面映射（report→research-report、
  thesis→thesis-center、screening_run→screening-result、workflow_run→
  workflow-run、strategy_version→strategy-lab、strategy_monitor→
  strategy-monitor 等）；
- Handoff 契约：`{page, route, title, payload, artifact_ids,
  open_mode: "workbench_tab"}`；payload 携 domain id（report_id/thesis_id/
  card_id/run_id/version_id/monitor_id）+ instrument_ids —— 页面收到后
  加载真实数据复算（route 即真实产品路由，衔接 §44 Handoff）。

### 2. 每会话独立 Tab 状态（服务端持久化 → 刷新恢复）
- open（artifact 自动映射 / 显式 page）：同 artifact 复用已开 Tab（唯一约束 +
  查重），单激活模型；close（关闭激活 Tab → 次新自动激活）；activate；
- `GET/POST/DELETE /command/sessions/{sid}/workbench…` 全套端点；
- workbench_open_requested 事件入会话事件流（§8.3 贯通）；
- **Artifact 自动打开**：commander 计划步骤产出 Artifact 与工具执行产出
  Artifact → open_for_artifacts 自动开 Tab（§8.7：自动打开而非仅链接）；
  未映射类型诚实跳过。

### 3. 前端：右栏动态 Tab Workbench（不再固定 Artifact List）
- `features/command-center/workbench.ts`：API client +
  resolveTabRoute（payload 占位符替换 + artifact/instrument 溯源参数）；
- `CommandCenterWorkbench.tsx` 新增 WorkbenchTabs：Tab 条（激活高亮、关闭 ×、
  切换）、激活 Tab 真实数据面（page 标识 + 标题 + instrument 元数据 +
  「在完整页面打开」CTA —— 不丢上下文）、5s 轮询恢复（刷新后 Tab 复原）、
  会话内隔离；i18n cc.workbench*（zh/en）；CSS cc-wb-*。

## 测试

### 后端（tests/test_f8_workbench.py，4 用例）
| # | 场景 | 结果 |
|---|---|---|
| 1 | Handoff 契约（report→research-report+payload.report_id）+ 同 artifact 复用 + 单激活 + 关闭次新激活 | PASS |
| 2 | 白名单外 page 422 + 未映射 artifact 422 显形 | PASS |
| 3 | 会话隔离（B 不见 A）+ 刷新恢复 | PASS |
| 4 | 真实计划执行产出 report → Workbench 自动出现报告 Tab + workbench_open_requested 事件 | PASS |
backend 全量：exit 0，0 FAILED（448 collected）

### 前端（tests/workbench.test.tsx，3 用例）
| # | 场景 | 结果 |
|---|---|---|
| 1 | resolveTabRoute 占位符替换 + artifact/instrument 溯源参数 | PASS |
| 2 | 无匹配占位符回退纯路由 | PASS |
| 3 | 服务端状态渲染 Tab 条 + 激活数据面 + 完整页面 CTA | PASS |
frontend：vitest 33/33（7 files）+ tsc PASS + vite build PASS

## 状态

IMPLEMENTED / INTEGRATED / TESTED（后端 live 全链 + 前端组件测试）。
浏览器端到端核验在 F10（UI 集成）/F13（全量回归）执行。
