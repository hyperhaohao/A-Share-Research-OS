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
Phase 2 — Data / Evidence Foundation
Milestone M3（Source Layer）
Status: DOING
```

M0（2026-08-28）、M1（2026-08-28）、M2（2026-08-28）已完成并通过各自 DoD（见 ROADMAP.md）。

---

## 已完成（M0 + M1 + M2）

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

M2（2026-08-28）：

- `backend/app/domain/instrument.py`：InstrumentProfile（任务书 §19 字段全集）。
- `backend/app/domain/code_norm.py`：A 股代码规范化 + 板块分类
  （沪主板/科创板/深主板/创业板/北交所；前缀变体 SH600519、000001.SZ 等；
  矛盾提示拒绝；未知前缀抛 InvalidInstrumentCode）。
- `backend/app/domain/catalog.py`：seed 目录（12 只真实标的：四板 × 金融/消费/科技/新能源/周期/制造）。
- `backend/app/api/instruments.py`：GET /api/v1/instruments?query=（code/name/alias 三路解析）
  + GET /{instrument_id}；缺失分析字段显式 null。
- 前端 InstrumentSearch 卡片接真实 API。
- 验证：backend pytest 49 passed（四板回归/前缀变体/名称别名/缺数据契约）；
  frontend 8 passed + build PASS；浏览器实测 600519/茅台/CATL/未知 四场景全 PASS。

---

## 正在进行

```text
M3 — Source Layer（SourceResult 语义 / capability provider / fallback / source health）
```

---

## 下一步（Next Action）

1. `backend/app/sources/base.py`：SourceResult 契约（status: success/no_data/partial/
   network_error/rate_limit/parse_error/auth_error/source_unavailable + error_type/retryable/
   attempted_at/as_of/metadata）与 SourceProvider Protocol（capability-based，注明 OpenAlpha CN
   MIT 契约蓝本出处）。
2. capability registry + fallback 链（同能力多 provider 依序 fallback，结构化失败不伪装空成功）。
3. source health 记录 + GET /api/v1/source-health。
4. 第一个真实 provider：instrument profile 补全（接入上游验证过的真实 A 股行情源读取器，
   或静态 seed 扩展 —— 以能真实运行为准）。
5. 缓存语义骨架（分 TTL）+ dedup 预留。
6. 单元 + 集成测试（fallback 顺序、失败分类、no_data 语义、health 状态机）。
7. Build/Test → 更新状态 → Git checkpoint。M3 后进入 M4（Evidence）。

---

## 已验证

```text
M2 Backend Tests:
  uv run pytest → 49 passed
  （含四板回归、前缀变体、矛盾提示拒绝、名称/别名解析、缺数据显式 null、错误信封）
M2 Frontend:
  vitest 8 passed；vite build PASS
M2 Live（浏览器实测，真实 API）:
  600519 → 贵州茅台 SSE 按代码 PASS
  茅台   → 贵州茅台 按名称 PASS
  CATL   → 宁德时代 按别名 PASS
  zzz999 → 空结果（不编造）PASS
M1（延续）:
  后端连通 / 三态主题 / OS 跟随 / 手动覆盖 / 语言切换 / 涨跌语义色 PASS
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
M2 checkpoint:
backend/app/domain/{__init__,instrument,code_norm,catalog}.py
backend/app/api/instruments.py
backend/tests/{test_code_norm,test_instrument_resolution,test_instruments_api}.py
frontend/src/components/InstrumentSearch.tsx（新增）
frontend/src/pages/HomePage.tsx、src/i18n/locales/*.json（搜索接入）
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
M2 instrument resolution（四板回归 + 三模式解析实测，git commit）

Last Verified Milestone:
M0, M1, M2

Resume From:
M3 / Phase 2 / SourceResult 契约与 capability provider（见 Next Action 步骤 1）
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
