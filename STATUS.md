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
Milestone M4（Evidence）
Status: DOING
```

M0–M3（均于 2026-08-28）已完成并通过各自 DoD（见 ROADMAP.md）。

---

## 已完成（M0 + M1 + M2 + M3）

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
M4 — Evidence（EvidenceRecord / authority/fact_status / dedup / SourceManifest / 持久化）
```

---

## 下一步（Next Action）

1. 持久化基线：`backend/` 引入 SQLAlchemy 2 + Alembic（开发 SQLite，目标 PostgreSQL），
   建初始迁移并真实运行。
2. `backend/app/domain/evidence.py`：EvidenceRecord（任务书 §22 字段全集）、
   EvidenceType、authority_level（§25 A1–D）、fact_status（§26 八态）、四时钟字段、
   content_hash 内容寻址 evidence_id（蓝本 OpenAlpha CN domain/evidence.py，MIT）。
3. dedup：同一 (instrument, source, content_hash) 幂等入库测试。
4. SourceManifest：每次采集生成来源台账（providers used、statuses、attempted_at）。
5. 采集服务：market_data quote → Evidence（authority/fact_status 映射）→ 入库。
6. API：GET /api/v1/evidence?instrument_id=（含缺失数据显式语义）。
7. 真实采集回归：live quote → Evidence 落库 → 查询断言（含 dedup 幂等）。
8. Build/Test → 更新状态 → Git checkpoint。M4 后进入 M5（PIT 强制 + Snapshot）。

---

## 已验证

```text
M3 Backend Tests:
  uv run pytest → 83 passed
  （SourceResult 契约不变量 13 项 / fallback 链 6 场景 / health 状态机 /
   TTL 缓存 / 腾讯报文解析（真实字段布局）/ API 集成 / live 测试）
M3 Live（真实网络）:
  GET /api/v1/market-data/quote?instrument=600519
    → SSE:600519 贵州茅台 1292.30 -0.81% 总市值 1.615万亿
      event_time 2026-08-27T16:14:55 source=tencent_quote
  GET /api/v1/market-data/quote?instrument=平安银行
    → SZSE:000001 平安银行 11.59（名称→解析→行情全链）
  GET /api/v1/source-health → tencent_quote available=true
M2（延续）:
  backend 49 passed；frontend 8 passed + build PASS；浏览器实测四场景 PASS
M1（延续）:
  主题/语言/涨跌语义色浏览器实测 PASS
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
M3 checkpoint:
backend/app/sources/{__init__,base,provider,registry,health,cache,runtime}.py
backend/app/sources/providers/{__init__,tencent_quote}.py
backend/app/api/{market_data,source_health}.py
backend/tests/{test_source_contract,test_source_registry,test_tencent_quote,test_market_data_api}.py
backend/app/main.py（路由挂载）
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
M3 source layer（真实行情采集链 + 83 tests，git commit）

Last Verified Milestone:
M0, M1, M2, M3

Resume From:
M4 / Phase 2 / SQLAlchemy 持久化基线 + EvidenceRecord（见 Next Action 步骤 1）
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
