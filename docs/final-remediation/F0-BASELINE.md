# F0-BASELINE — 第三轮整改基线冻结

> 阶段：F0 Reopen 与基线冻结（docs/A-Share-Research-OS-第三轮验收整改任务书 §11 F0）
> 冻结时间：2026-09-01 23:59 (+08:00)
> 本文件为第三轮整改的基线事实记录。后续所有阶段以本基线为准，
> 不得在整改过程中切换 donor 版本后继续声称同一基线对等（任务书 §2.1）。

---

## 1. 固定版本

| 项 | 值 |
|---|---|
| ASRO commit（整改开始时 HEAD） | `4c2e506c92fc7c2eef08bcca2050e132428374cc` |
| donor（观澜 financial-analyst）固定 commit | `98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28`（GitHub HEAD，2026-08-21，license=None） |
| Python | 3.11.15（backend/.venv） |
| Node | v24.16.0 |
| uv | 0.11.26 |
| 数据库 | SQLite（backend/asro_dev.db，dev 栈）；compose 栈同一数据卷 |
| Worktree | 干净（仅本基线文件为新增未跟踪文件） |

## 2. 基线测试原始结果（整改开始时的真实状态）

### 2.1 backend pytest（全量）

- 命令：`cd backend && .venv/Scripts/python.exe -m pytest -q`
- 结果：**404 collected / 403 passed / 1 FAILED，exit 1**
- 失败项：`tests/test_r8_inbox.py::test_thesis_diff_detects_and_applies`
  - 异常：`app.storage.research_repo.CrossSnapshotError: snapshot snap_0630a9c4a3ddf592827280e9 not found`
  - 位置：`app/storage/research_repo.py:288`（thesis-diff/apply 路径）
- 原始输出：[baseline/F0-backend-pytest-raw.txt](baseline/F0-backend-pytest-raw.txt)
- 判定：真实回归失败（F2 Research State 修复范围），基线如实记录。

### 2.2 frontend vitest

- 命令：`cd frontend && npx vitest run`
- 结果：**6 files / 30 tests passed，exit 0**

### 2.3 TypeScript / Vite build

- 命令：`cd frontend && npx tsc -b && npx vite build`
- 结果：**PASS，exit 0**

### 2.4 Playwright（产品 E2E + 视觉）

- 本基线阶段：**NOT RUN**（不冒充已验证；F13/F14 全量回归阶段执行）
- compose 栈状态：backend :8000 healthy / frontend :8080 healthy / scheduler up

### 2.5 Golden E2E（backend/tests/test_r10_golden.py，live-API 脚本）

- R10-EVIDENCE-V2.md 记录（上一轮）：**24/25 PASS，6b Production Signal API FAIL（status=500）**
- 本轮基线复测（2026-09-01，compose 栈实测）：
  - `POST /api/v1/research-inbox/signal-ladder/evaluate-evidence?instrument_id=SZSE%3A000831`
  - 实测 **HTTP 500**，`{"status":"error","error_code":"common.internal_error"}` → **6b FAIL 仍然复现**
  - 容器日志根因：`AttributeError: 'InstrumentProfile' object has no attribute 'get'`
    —— `backend/app/api/research_inbox_api.py:556` 将 pydantic `InstrumentProfile`
    当 dict 使用（`profile.get("name")`）。该缺陷在 HEAD 源码中同样存在（F3 修复范围）。
- 其余 24 步：未在本基线逐项复测（compose 栈为运行中旧镜像 + 真实数据持续累积，
  部分计数型断言会随数据漂移）；以 R10-EVIDENCE-V2.md 记录 + 本轮 6b 复现为准。

## 3. 外部数据源 / API Key 可用性

| 项 | 状态 |
|---|---|
| 搜索/行情聚合源 | 可用（watchlist/quote/宏观数值层正常） |
| 东方财富 kline 日线端点 | **断连**（本机网络 TLS 指纹拦截，宿主机与容器一致；已知问题 STATUS Open Issues #1） |
| 腾讯宏观数值源 | 可用（6 指标） |
| ASRO_LLM_API_KEY | **缺失**（LLM 精炼 422 显形，BLOCKED_EXTERNAL 维持） |

## 4. 已知阻塞（整改开始时）

1. Golden 6b Production Signal API 500（本轮 F3 修复）。
2. backend 1 个真实测试失败（r8 thesis-diff apply CrossSnapshotError，F2 修复）。
3. 生产 Claim 路径仍有固定 `confidence=0.6`（F4 移除）。
4. Source Independence 缺 origin_url/publisher/source_group/content_hash 等事实字段（F4）。
5. Subject Swap Detection 缺 Entity Dictionary（F4）。
6. 帷幄核心（Commander Orchestration / Event Protocol / Approval Gate /
   Dynamic Workbench / Background Runway / Memory）全部 FAIL（F5–F10）。
7. kline 源断连（外部网络限制，影响回测/工作流完成路径的真机验证；
   后端确定性路径有测试覆盖；按任务书 §13.3 记 BLOCKED_ENVIRONMENT，不计 PASS）。

## 5. 整改阶段登记

F0–F15 已登记于 PLAN.md「第三轮整改 — Correctness & Product Closure Remediation」；
每阶段完成必须产出 `Fxx-MANIFEST.md`（本目录）+ 单一主题 commit（任务书 §16）。
