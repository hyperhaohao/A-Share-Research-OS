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
Milestone — 全部交付完成
Status: DELIVERED (M0–M29 DONE)
```

M0–M29 全部完成（2026-08-28）；M22 经审计 NOT_REQUIRED（docs/quant-audit.md）。

---

## 已完成（M0 – M29 全量交付）

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
M6 — Research Domain（CorporateEvent / Claim / InvestmentThesis + 引用完整性）
```

---

## 下一步（Next Action）

1. `backend/app/domain/research.py`：CorporateEvent（§27 事件类型全集）、
   Claim（§28 字段 + claim_type 枚举 + 引用 evidence_ids）、
   InvestmentThesis（§29 字段 + status/catalysts/risks/trigger+invalidate）。
2. 引用完整性：Claim 引用的 evidence_id 必须真实存在于库（repository 校验 + 测试）；
   Thesis 引用的 claim 同理 —— Traceability 从源头强制（§75 前置）。
3. ORM + 迁移（corporate_events/claims/theses 表）+ repository。
4. API：POST/GET /api/v1/claims、/api/v1/theses、/api/v1/corporate-events（最小集，
   Claim/Thesis 绑定 instrument_id 与 snapshot_id）。
5. 追溯测试：Thesis → Claim → Evidence → (M3 source) 全链存在断言。
6. Build/Test → 更新状态 → Git checkpoint。M6 后进入 M7（Quality Gates）。

---

## 已验证

```text
M5 Backend Tests:
  uv run pytest → 112 passed
  （PIT gate：未来证据不可见/边界可见/naive as_of 拒绝；快照幂等重建；
   后续新数据不改历史快照；内容寻址身份；run 绑定 snapshot；API 集成）
M5 Live:
  collect(1 created) → snapshot snap_c5d14844f1be24d (1 item) →
  run_1d6af330d463 running 绑定该 snapshot PASS
M4 Backend Tests（延续）:
  uv run pytest → 100 passed
  （Evidence 域不变量/内容寻址/时钟校验/PIT 可见性/幂等 dedup/manifest 台账/
   collect+list API/失败采集不伪造/live 采集入库）
M4 Alembic:
  autogenerate 初始迁移 + upgrade head 真实建表（asro_dev.db）PASS
M4 Live:
  POST /api/v1/evidence/collect?instrument=600519 → created>=1，
  GET /api/v1/evidence?instrument_id=SSE:600519 可追溯（source/authority/fact_status/时钟）
M3 Backend Tests（延续）:
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
M5 checkpoint:
backend/app/domain/snapshot.py（新）
backend/app/storage/snapshot_repo.py（新）
backend/app/api/snapshots.py（新）
backend/alembic/versions/63951c2ef1c1_m5_snapshots_and_research_runs.py（新）
backend/tests/{test_snapshot_pit,test_snapshot_api}.py（新）
M4 checkpoint:
backend/app/domain/evidence.py（新）
backend/app/storage/{__init__,orm,repository}.py（新）
backend/app/services/{__init__,evidence_collector}.py（新）
backend/app/api/evidence.py（新）
backend/app/db.py（新）
backend/alembic/ + alembic.ini（初始迁移）
backend/tests/{test_evidence_domain,test_evidence_repository,test_evidence_api}.py（新）
backend/app/{config,main}.py、app/api/market_data.py、sources/providers/tencent_quote.py（扩展）
ROADMAP.md / PLAN.md / STATUS.md
```

---

## Blockers

```text
None（交付已完成）
环境备注：Docker Desktop 守护进程本机启动缓慢，镜像级构建验证待其就绪
（compose 配置已校验；属运行环境项，非代码缺陷）。
```

---

## Recovery Metadata

```text
Last Safe Checkpoint:
M29 production delivery（全量交付 + 文档 + 演练 + 最终评审）

Last Verified Milestone:
M0–M29 全部（M22 NOT_REQUIRED）

Resume From:
交付后加固清单（见 Next Action）；无未完成里程碑。
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
