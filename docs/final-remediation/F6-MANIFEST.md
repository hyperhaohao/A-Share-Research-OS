# F6-MANIFEST — Weiwo Tool Orchestration

> 阶段：F6（第三轮整改任务书 §11 F6 / §8.5 P0-WEIWO）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. Tool Registry（白名单，无 eval / 任意函数名）
- 新模块 `app/services/tool_registry.py`：ToolSpec 声明 **§8.5 全字段**：
  name / description / input_schema / output_schema / risk_level(read|write|high) /
  requires_confirmation / timeout_s / idempotency_policy(idempotent|at_most_once|merge) /
  artifact_contract / executor；manifest() 对外不暴露执行体；
- 依赖内置 JSON-Schema 子集校验器（required/type/enum/minLength/maxLength/
  minimum/maximum/array items），无第三方依赖。

### 2. 首批跨模块工具（13 个，复用既有服务，不建第二套业务）
search_evidence / build_pit_snapshot / open_current_thesis / analyze_thesis_diff /
**submit_thesis_revision（high）** / create_experience_card / start_validation_workflow /
run_screening / assemble_strategy / **create_strategy_monitor（high）** /
generate_market_product（mainline_radar/overseas_mapping/daily_brief）/ memory_search /
open_page（页面白名单 13 项，禁任意 URL）。

### 3. 执行内核（结构化结果 + 失败显形 + 事件）
- `execute_tool`：schema 校验（422 tool.arguments_invalid）→ 确认门 →
  executor → 结构化 Result（不使用自然语言「已完成」替代真实结果）；
  异常 → tool.execution_failed + tool_error 事件（失败显形）；
- 确认门执行面（与 F7 审批门衔接）：
  requires_confirmation=True 无 token → 422 tool.confirmation_required +
  arguments_digest；token 由 issue_confirmation 签发（lease 有效期、
  **一次性消费**、digest 与参数绑定）→ 复用/过期/参数替换 →
  tool.confirmation_invalid（防 TOCTOU，§15）；
- 执行可选挂帷幄会话：tool_call / tool_result / artifact_created 事件
  （correlation_id 关联，复用 F5 协议）。

### 4. API
- `GET /command/tools`：注册表清单；
- `POST /command/tools/{name}/execute`：执行（unknown → 404）。

## 测试（tests/test_f6_tool_registry.py，7 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 清单声明字段齐全（13 工具）+ 不暴露 executor | PASS |
| 2 | 白名单外工具 404 | PASS |
| 3 | schema 校验（缺 required / 类型错 / enum 外页面）→ 422 | PASS |
| 4 | 只读工具真实执行（search_evidence 结构化结果 / open_page） | PASS |
| 5 | 确认门全链：required + digest → token 放行执行修订 → 复用 invalid → 参数替换 invalid | PASS |
| 6 | tool_call/tool_result 事件落会话（correlation 关联） | PASS |
| 7 | 失败显形（不存在报告 → tool.execution_failed 结构化错误） | PASS |

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（441 collected）
```

## 新增/修改文件

- 新增：app/services/tool_registry.py、tests/test_f6_tool_registry.py
- 修改：app/api/command.py（tools 清单/执行端点）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
create_strategy_monitor / run_screening 等后台长执行在 F9 Background Runway
承接（timeout 声明 + at_most_once 已定）；F7 提供审批 UI 状态机。
