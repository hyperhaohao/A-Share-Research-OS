# STATUS.md

# Current Execution Status

> 本文件是长时间自主任务的持久状态。
>
> Claude 在每一个可验证 checkpoint 后、上下文即将压缩前、会话结束前必须更新。
>
> 不得只依赖当前对话上下文。

---

## Repository

```text
Canonical:
https://github.com/hyperhaohao/A-Share-Research-OS.git

Branch:
main

Current Commit:
（见 git log；M0 审计 checkpoint 后为 audit commit）
```

---

## 当前阶段

```text
Phase 1 — Engineering Foundation
Milestone M2（Instrument）
Status: DOING
```

M0（2026-08-28）、M1（2026-08-28）已完成并通过各自 DoD（见 ROADMAP.md）。

---

## 已完成（M0 + M1）

M0（2026-08-28）：

- 正式仓库文档结构补齐，初始 commit b7f5a98。
- `Desktop/upstreams/` 建立六上游工作区；六候选源码级审计 + 运行/测试/Live 验证。
- 关键验证：TideTrading `tide serve` PASS + 102 端点 + **真实 A 股行情 live PASS**（000001 五档盘口）
  + frontend build PASS + 定向测试切片 78 passed；OpenAlpha CN 105 tests PASS + API 25 端点；
  觀瀾 engine import PASS（**无 LICENSE**）；Qlib/RD-Agent import PASS；TradingAgents 27 tests PASS。
- 三份 M0 输出 + ADR-001：**主工程基线 = TideTrading 增量演进；领域契约蓝本 = OpenAlpha CN（MIT）**。
- commit 70a6632。

M1（2026-08-28）：

- 正式仓库内新建最小工程基线（未搬迁 TideTrading）：
  - `backend/` FastAPI + Pydantic v2：`/api/v1/health`、稳定 error_code 错误信封、
    message_code + Accept-Language normalize；pytest 8 passed；uvicorn 启动实测 PASS。
  - `frontend/` Vite + React 19 + TS + TanStack Query + zustand：react-i18next 双语资源 +
    system 解析 + 手动覆盖；三态主题 + prefers-color-scheme 跟随 + 手动不被覆盖；
    Design Tokens（light/dark 双套、语义色分离、A股红涨绿跌 CN 默认 + intl 可切换）；
    vitest 8 passed；build PASS（1.14s）。
- 浏览器真实验证（Chrome DevTools 实测，见 ROADMAP M1 节）：
  后端连通 / 三态主题 / OS 跟随 / 手动覆盖 / 语言切换 / 涨跌语义色 全部 PASS。

---

## 正在进行

```text
M2 — Instrument（正式仓库内）
```

---

## 下一步（Next Action）

1. `backend/app/domain/instrument.py`：InstrumentProfile（任务书 §19 字段全集）。
2. A 股代码规范化与板块识别：`code_norm`（6 位数字 → SSE/SZSE 主板、创业板 300/301、
   科创板 688/689；支持 600519 / 000001 / 300750 / 688981 / sh600519 / 600519.SH 等输入）。
3. 名称解析：先建静态 seed 数据（四板代表性标的：沪主板大市值、深主板、创业板成长、
   科创板科技），M3 Source Layer 接入后再由 provider 动态补全名称/行业。
4. API：`GET /api/v1/instruments?query=600519|茅台`（code+name 双路解析，缺数据显示缺失）。
5. 四板回归测试（task书 §72：code/name/exchange/market 全部断言）+ API 测试。
6. 前端：Header 搜索框接解析 API（最小可用），双语 key 补齐。
7. Build/Test → 更新 PLAN/STATUS/ROADMAP → Git checkpoint。

M2 完成后进入 M3（Source Layer）。

---

## 已验证

```text
M1 Build:
  backend:  uv sync PASS；pytest 8 passed；uvicorn /api/v1/health 实测 {"status":"ok","version":"0.1.0"}
  frontend: npm install PASS；vitest 8 passed；vite build PASS（1.14s）
M1 Live（浏览器实测）:
  前端→后端真实调用 PASS（health ok · v0.1.0）
  三态主题 + OS 跟随 + 手动覆盖: PASS（§77 两语义均验证）
  语言 system/zh-CN/en-US 切换: PASS
  涨跌语义色（CN 默认红涨绿跌 + intl 翻转）: PASS
```

---

## 当前问题

```text
None blocking.
环境备注：
- 本机对 github.com 直连克隆不稳定（API tarball + ghfast 镜像可用，已记录）。
- 沙箱进程缺 HOME 会致 TideTrading 大套件 pathlib.expanduser 报错（环境性，已定位记录）。
```

---

## 关键设计决策

### Decision 1 — Canonical Repository
唯一正式仓库 `hyperhaohao/A-Share-Research-OS`；upstreams 在仓库外。

### Decision 2 — ADR-001 主工程基线（2026-08-28）
TideTrading = ADOPT（增量演进）；OpenAlpha CN = ADAPT（领域契约移植）；
觀瀾 = REFERENCE_ONLY（无 LICENSE）；Qlib = REFERENCE_ONLY（M21 再评）；
RD-Agent = REJECT（M20 后可重评）；TradingAgents = REFERENCE_ONLY。

### Decision 3 — Persistent Long-Running Execution
TASK / PLAN / STATUS / ROADMAP 四文件职责分工（见 AGENTS.md §5）。

---

## 最近修改文件

```text
M1 checkpoint:
backend/pyproject.toml, app/{__init__,config,main}.py,
        app/api/{__init__,health}.py, app/core/{__init__,errors,i18n}.py,
        tests/{__init__,test_health,test_error_envelope,test_i18n}.py
frontend/package.json, vite.config.ts, tsconfig.json, index.html,
        src/main.tsx, src/App.tsx, src/i18n/{index.ts,LanguageProvider.tsx},
        src/i18n/locales/{zh-CN,en-US}.json,
        src/theme/{theme.ts,ThemeProvider.tsx},
        src/components/{AppHeader,AppearanceControls}.tsx, src/pages/HomePage.tsx,
        src/styles/{tokens.css,global.css}, tests/{i18n-theme.test.ts,app.test.tsx}
.claude/launch.json（dev server 配置）
ROADMAP.md / PLAN.md / STATUS.md
```

---

## Blockers

```text
None
```

---

## Recovery Metadata

```text
Last Safe Checkpoint:
M1 engineering foundation（backend/frontend/i18n/theme + 浏览器实测，git commit）

Last Verified Milestone:
M0, M1

Resume From:
M2 / Phase 1 / Instrument 领域模型与解析服务（见 Next Action 步骤 1）
```

---

## Context Handoff

如果本次会话上下文即将结束：

1. 更新本文件所有字段；
2. 更新 `PLAN.md` checkbox；
3. 更新 `ROADMAP.md`；
4. 记录当前 branch / commit；
5. 记录 Build/Test 命令及结果；
6. Git checkpoint；
7. 下一会话重新读取 TASK / AGENTS / PLAN / STATUS 后继续。

不得重新从头规划整个项目。
