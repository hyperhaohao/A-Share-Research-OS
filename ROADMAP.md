# ROADMAP.md

# A-Share Research OS — Milestone Roadmap

> 本文件是长期 Milestone 状态的唯一状态源。
>
> 每完成一个 Milestone（通过其 DoD）更新状态。
> 同一时间只允许一个 `DOING`。
> Milestone 细节以 `docs/A-Share-Research-OS-最终实施任务书.md` 为准。

---

## 状态图例

```text
PLANNED   未开始
DOING     进行中（当前只能有一个）
DONE      已通过 DoD
BLOCKED   真实外部阻塞（需在 STATUS.md 记录 blocker）
NOT_REQUIRED   经审计后证明不需要（仅 M22 允许）
```

---

## Milestones

| # | Milestone | 状态 | 交付核心 |
|---|-----------|------|----------|
| M0 | 上游/底座源码审计 | DONE | upstream audit workspace、评估矩阵、架构审计、ADR-001 |
| M1 | 工程基线 + i18n + theme | DONE | 可运行的 backend/frontend 基线、zh-CN/en-US、system/light/dark |
| M2 | Instrument | DONE | InstrumentProfile、A 股代码/名称解析、四板回归 |
| M3 | Source Layer | DONE | capability-based Provider、fallback、SourceResult、source health |
| M4 | Evidence | DONE | EvidenceRecord、authority/fact_status、dedup、SourceManifest |
| M5 | PIT / Snapshot | DONE | 四时钟、available_time <= as_of 强制、不可变 EvidenceSnapshot |
| M6 | Research Domain | DONE | CorporateEvent、Claim、InvestmentThesis |
| M7 | Quality | DONE | EvidenceQualityGate、AnalysisQualityGate、FinalReportQualityGate |
| M8 | Structured Agents | DONE | AnalystBrief、missing_data → ResearchRequest 闭环 |
| M9 | Debate / Scenario / Risk | DONE | Thesis-based Bull/Bear、Bear/Base/Bull Scenario、Risk trigger |
| M10 | Valuation | DONE | 确定性估值引擎（PE/PB/PS/EV/EBITDA/DCF/DDM/SOTP/NAV/percentile/comps） |
| M11 | ResearchReport bilingual | DONE | 结构化报告、zh/en renderer、共享 Research State |
| M12 | Manifest / Versions | DONE | ResearchRun、RunManifest、不可变 ReportVersion |
| M13 | Report Q&A | DONE | Explain（无新数据）与 Refresh（允许新数据）严格区分 |
| M14 | Audit / Revision | DONE | sentence/claim/thesis audit、RevisionProposal、Diff、Accept |
| M15 | Delta / Materiality | DONE | Monitor、Evidence delta、MaterialityJudge 三分支 |
| M16 | Timeline | DONE | 统一事件时间线 |
| M17 | Research Graph | DONE | 溯源图、upstream/downstream 遍历 |
| M18 | Tasks / Scheduler | DOING | ResearchTask、scheduler、worker、retry、idempotency、recovery |
| M19 | Prediction / Validation | PLANNED | 不可变 PredictionRecord、5D/20D/60D、ValidationRecord |
| M20 | Regression / Experience | PLANNED | RegressionReview 归因、ResearchExperience 沉淀 |
| M21 | Quant audit | PLANNED | 主工程 quant 能力客观审计，决定是否需要 Qlib |
| M22 | Qlib（若需要） | PLANNED | 若需要：真实 A 股 Data→Factor→Model→Backtest→Metrics 闭环；否则 NOT_REQUIRED |
| M23 | Research API / SSE | PLANNED | 稳定 Research API、SSE 事件流、source health API |
| M24 | Workspace | PLANNED | Dashboard、Watchlist、Stock Workspace |
| M25 | Research visual UI | PLANNED | Timeline UI、Research Graph UI、Thesis Board、Evidence UI |
| M26 | Interactive Report | PLANNED | TOC、Citation viewer、Explain/Audit/Refresh/Revalue/Revision Diff |
| M27 | Tasks / Prediction UI | PLANNED | Tasks UI、Prediction Dashboard、完整双语主题回归 |
| M28 | E2E / Performance / Cost | PLANNED | 多标的 E2E、性能、成本核算、安全审查 |
| M29 | Production Delivery | PLANNED | Docker Compose、migration、health check、backup/restore、最终 Reviewer Pass |

---

## 当前 DOING：M18 — Tasks / Scheduler

### 范围（任务书 §48/§49）

- ResearchTask（§48 字段全集）：task_id/instrument_id/task_type/schedule/
  research_level/filters/enabled/last_run_at/next_run_at/status
- task_type：monitor / periodic_full_research / event_trigger / prediction_validation
- Scheduler 只负责「何时执行」；业务逻辑是可独立测试的函数（run_monitor/
  run_full_research/validate_prediction）
- retry / idempotency / restart recovery / concurrency control（§49）
- SSE 进度推送预留（M23 正式 API）

### M18 DoD

```text
[ ] ResearchTask 模型 + 持久化 + CRUD API
[ ] Scheduler 循环（due → claim → run → retry/backoff）
[ ] idempotency（同 task 同周期不重复执行）
[ ] restart recovery（中断任务恢复）
[ ] 并发控制（同 instrument 互斥）
[ ] Git checkpoint
```

---

## 已完成 Milestone

### M17 — Research Graph（DONE，2026-08-28）

```text
backend/app/services/research_graph.py
                                  派生图：source→evidence→snapshot→claim→thesis→
                                  report_version + research_run 节点/边全从现有对象构建；
                                  BFS upstream/downstream 遍历（max_depth）
backend/app/api/graph.py          GET /graph?instrument= + GET /graph/trace?instrument=&node_id=&direction=
验证: backend pytest 199 passed
      §95 测试：thesis 上游追溯达 source/evidence；evidence 下游达 thesis/report_version
```

## 已完成 Milestone

### M16 — Timeline（DONE，2026-08-28）

```text
backend/app/services/timeline.py  派生读模型：从 evidence/claims/theses/corporate
                                  events/research runs/report versions/snapshots
                                  聚合排序（不建重复存储），kind 过滤 + 分页
backend/app/api/timeline.py       GET /api/v1/timeline?instrument=&kinds=&limit=&offset=
验证: backend pytest 195 passed —— 聚合/排序/过滤/分页/404
```

### M15 — Delta / Materiality（DONE，2026-08-28）

```text
backend/app/services/monitor.py  MonitorService：fresh 采集 → 新快照 → 与前一快照
                                 的证据差集 + 价格变动 → MaterialityJudge；
                                 MaterialityJudge 确定性规则：
                                 首扫→FULL；无变化→NO；纯行情重观测价格未动→NO；
                                 价格变动 <5% → DELTA；≥5% → FULL；
                                 非行情类新增（公告/财报/新闻）→ DELTA（阈值可配）
backend/app/api/monitor.py       POST /monitor/run + GET /monitor/decisions
backend/alembic                  m15 迁移（materiality_decisions 表）
验证: backend pytest 191 passed —— 三分支全部触发
      调试记录：测试曾未打补丁导致真实行情进入（1292.3）→ 30% 跳变 → FULL 判定
      正确，证明判定器对真实数据的鲁棒性
```

### M14 — Audit / Revision（DONE，2026-08-28）

```text
backend/app/domain/audit.py      audit_claim 确定性规则：unsupported（引用不可解析）/
                                 outdated（证据过期）/ conflicting（反证未解释）/
                                 numeric_inconsistency（陈述数字不可追溯到证据载荷）
backend/app/domain + storage     RevisionProposal（§44 字段全集：original/proposed/
                                 reason/added+invalidated evidence/affected claims/
                                 confidence_change；original≠proposed 强制）
backend/app/services + api       accept → 新 ReportVersion（parent+reason+changed_sections）
                                 reject → 记录；旧版本保留（§78 回归复用）
backend/alembic                  m14 迁移（revision_proposals 表）
验证: backend pytest 182 passed
      accept 双重执行 → 422；假证据修订 → 422；reject 后无新版本
```

### M13 — Report Q&A（DONE，2026-08-28）

```text
backend/app/services/report_qa.py  Explain（冻结态回答：关键词路由 claims/theses、
                                   引用 evidence 链、零新数据 —— 测试断言证据/manifest
                                   计数前后不变）vs Refresh（fresh=True 旁路 TTL 缓存 →
                                   采集 → 新快照 → 影响差集：新增/移除证据、受影响 claims）
backend/app/api/report_qa.py       POST /reports/{id}/ask {question, mode}
backend/app/storage + alembic      report_asks 审计日志
验证: backend pytest 177 passed
      explain 零采集断言；refresh 新报价 → 新内容寻址证据 → 新快照
      缓存旁路设计：refresh 语义要求绕过 TTL 缓存（已记录）
```

### M12 — Manifest / Versions（DONE，2026-08-28）

```text
backend/app/domain/manifest.py    RunManifest（§40 契约全集：code_commit/config_digest/
                                  provider digests/model+prompt versions/random_seed/
                                  environment/checkpoints；终态须 finished_at）、
                                  ReportVersion（append-only，V>1 须 parent+reason）
backend/app/storage/manifest_repo.py  两仓储 + (report_id, version_no) 唯一
backend/app/api/manifest.py       POST /run-manifests、GET /run-manifests?run_id=
                                  POST /reports/{id}/versions（无链时从已存报告播种 V1）
                                  GET 版本链/单版本
backend/alembic                   m12 迁移
验证: backend pytest 173 passed
      §78 测试：V1 播种 → V1.1（parent+reason）→ V1.0 仍存在且内容未变
      终态缺 finished_at → 422；修订缺 change_reason → 422
```

### M11 — ResearchReport bilingual（DONE，2026-08-28）

```text
backend/app/domain/report.py     StructuredReport（§38 字段集映射到 sections）+
                                 ReportRenderer（markdown/html × zh-CN/en-US，
                                 HTML 全量 escape 防 XSS）
backend/app/core/report_i18n.py  服务端双语渲染目录（仅本地化脚手架文案；
                                 数字/claims/引用为共享数据）
backend/app/services/report_compiler.py
                                 从 snapshot 证据/claims/theses/debates/scenarios/
                                 valuations 编译；缺失 section 显式「暂无数据」；
                                 FinalReportQualityGate 接入发布路径（FAIL 阻断）
backend/app/api/reports.py       POST /reports/compile（publish 需过门）+ GET
backend/alembic                  m11 迁移（reports 表）
验证: backend pytest 168 passed
      §90 一致性：zh/en 报告数字相同（1648/100/25 等）、claim 原文逐字保留、
      citation 集合相同；缺失数据在 data_quality 显式披露
      不安全报告 blocked=true 且 published=false
```

### M10 — Valuation（DONE，2026-08-28）

```text
backend/app/domain/valuation.py   八种确定性方法：PE/PB/PS/EV-EBITDA/DCF(两阶段+
                                  Gordon 终值)/DDM(Gordon)/历史分位(百分位排名)/
                                  可比公司(中位数倍数)；MissingInput 语义 ——
                                  缺输入 → 显式 not computable，绝不猜测
backend/app/storage/valuation_repo.py  持久化（含 scenario/thesis 绑定列）
backend/app/api/valuation.py      POST /valuations/compute + GET 列表
backend/alembic                   m10 迁移
验证: backend pytest 164 passed —— 固定数值单测（DCF 手算终值/分位排名 30%/
      同业中位数 19x/DDM 102 元等）；缺失输入显式落库
```

### M9 — Debate / Scenario / Risk（DONE，2026-08-28）

```text
backend/app/domain/debate.py      Scenario（§37）/ ScenarioSet（概率总和=100 强制、
                                  kind 唯一）/ DebateRound（bull/bear claims）
backend/app/storage/debate 持久化（scenarios + debate_rounds 表）
backend/app/services/debate_engine.py
                                  确定性辩论：bull/bear 论点 = analyst_inference
                                  claims，只引用论点自身证据基（无新事实可引入，
                                  引用完整性拒绝）；最多 3 轮；多轮递增轮次
backend/app/api/debate.py         POST /scenarios、/debates/run + GET 两个列表
backend/alembic                   m9 迁移
验证: backend pytest 144 passed
      概率非 100 拒绝；bull/bear claims 可追溯到证据；3 轮耗尽拒绝
      风险建模：Thesis/Scenario 内嵌 risks+trigger+invalidate（§29/§37，不设重复 Risk 表）
```

### M8 — Structured Agents（DONE，2026-08-28）

```text
backend/app/domain/agents.py      AnalystBrief（§30 统一输出契约，结构化结论支持
                                  双语渲染）、MissingData、ResearchRequest
backend/app/storage/agent_repo.py briefs + requests 持久化
backend/app/services/market_analyst.py
                                  确定性 market analyst：仅引用快照内证据；
                                  产出价格/涨跌幅/市值结论 + 机械事实 Claim（0.99 置信、
                                  全引用、无预测语言）；financials/announcements 缺失
                                  显式披露 → ResearchRequest → 采集器补采
backend/app/api/analysts.py       POST /analysts/market/run + GET briefs/research-requests
backend/alembic                   m8 迁移
验证: backend pytest 139 passed
      跨 run 闭环测试：空快照(2020) → missing disclosed → 采集器跑 → 新快照含
      真实行情 → 后续 run 产出带引用 brief
      PIT 正确性：数据不在快照 → agent 不能引用（即使库中已有）
```

### M7 — Quality（DONE，2026-08-28）

```text
backend/app/domain/quality.py      GateResult/GateFinding + 三类 Gate：
                                   Evidence（empty/PIT 违规/权威度不足/过期/来源失败）、
                                   Analysis（悬空引用/事实-预测混用/冲突未解释/薄证据高置信）、
                                   FinalReport（无效 citation/未支撑主张/估值无假设/
                                   风险缺失/数据质量未披露/disclaimer 缺失）
backend/app/services/quality_service.py   快照级评估 + 结果持久化
backend/app/api/quality.py         POST /quality-gates/run + /final-report + GET history
backend/alembic                    m7 迁移（quality_gate_results 表）
验证: backend pytest 135 passed —— 每个 FAIL 场景都真实拦截（blocked=true）
      FinalReport 门为 M11 真实报告预留结构化输入契约（ReportGateInput），已测试
```

### M6 — Research Domain（DONE，2026-08-28）

```text
backend/app/domain/research.py    CorporateEvent（§27 事件类型全集/announce>=occur 校验）、
                                  Claim（§28 字段全集 + 至少一条证据引用的域约束）、
                                  InvestmentThesis（§29 字段全集 + 至少一条主张引用）
backend/app/storage/research_orm.py + research_repo.py
                                  ORM/仓储 + 写时引用完整性（引用不存在的
                                  evidence/claim → ReferenceNotFoundError 拒绝）
backend/app/api/research.py       POST/GET claims、theses、corporate-events
backend/alembic                   m6 迁移（三表真实建表）
验证: backend pytest 121 passed
      追溯链测试：Thesis → Claim → Evidence → source 全链存在
      假引用 422（claim.evidence_not_found / thesis.claims_not_found）
```

### M5 — PIT / Snapshot（DONE，2026-08-28）

```text
backend/app/domain/snapshot.py     EvidenceSnapshot（frozen 语义、内容寻址 snapshot_id、
                                   §24 字段全集）、SnapshotItem、ResearchRun 最小骨架
backend/app/storage/snapshot_repo.py
                                   build = PIT gate（available_time <= as_of 双重强制）+
                                   get-or-create 幂等（同 (instrument, as_of) 永不改写历史）
backend/app/api/snapshots.py       POST /snapshots + GET /snapshots/{id} + POST /research-runs
backend/alembic                    m5 迁移（evidence_snapshots + research_runs 真实建表）
验证: backend pytest 112 passed
      §74 强制测试：未来证据不可见（> as_of）、边界 == as_of 可见、
      幂等重建同快照、后续新数据不改历史快照、不同 as_of 产生新快照
      LIVE: collect(1) → snapshot snap_c5d14844(1 item) → run 绑定 PASS
```

### M4 — Evidence（DONE，2026-08-28）

```text
backend/app/domain/evidence.py     EvidenceRecord（§22 字段全集 + 内容寻址 evidence_id +
                                   content_hash）、AuthorityLevel（§25 A1-D）、
                                   FactStatus（§26 八态）、EvidenceType、SourceManifest
backend/app/storage/orm.py         SQLAlchemy 2 ORM（evidence_records + source_manifests，
                                   唯一约束 (source, content_hash) 实现去重）
backend/app/storage/repository.py  幂等 save（同源同内容 → created=False）、
                                   PIT 可见性过滤 list、manifest 台账
backend/app/services/evidence_collector.py
                                   SourceResult → Evidence 采集服务（失败记录 manifest，
                                   不伪造数据）
backend/app/api/evidence.py        POST /api/v1/evidence/collect + GET /api/v1/evidence
backend/alembic/                   初始迁移（真实建表 asro_dev.db，autogenerate 生成）
验证: backend pytest 100 passed（含 live 采集入库回归）
      失败采集 → manifest 记录 network_error、evidence 为空（不伪装）
```

---

### M3 — Source Layer（DONE，2026-08-28）

```text
backend/app/sources/base.py          SourceResult 契约（八态 status、错误分类、retryable、
                                     as_of/attempted_at；成功必须带记录、no_data 必须带原因；
                                     契约蓝本 OpenAlpha CN providers/base.py，MIT 已注明）
backend/app/sources/provider.py      BaseProvider 显式结果构造器
backend/app/sources/registry.py      capability registry + 有序 fallback（异常防护，
                                     耗尽后合成 SOURCE_UNAVAILABLE，永不静默空返回）
backend/app/sources/health.py        source health 状态机（连续失败→unavailable）
backend/app/sources/cache.py         分能力 TTL 缓存（market_data 5s … instrument 24h）
backend/app/sources/runtime.py       进程级 runtime（resolve_cached）
backend/app/sources/providers/tencent_quote.py
                                     腾讯实时行情 provider（GBK 报文解析、真实字段布局）
backend/app/api/market_data.py       GET /api/v1/market-data/quote?instrument=…
backend/app/api/source_health.py     GET /api/v1/source-health
验证: backend pytest 83 passed（契约不变量/fallback/health/缓存/mock 报文/live）
      LIVE: 茅台 1292.30(-0.81%) 总市值 1.615万亿 event_time 2026-08-27T16:14:55
            平安银行 11.59 按名称解析 → SZSE:000001；health available=true
```

### M2 — Instrument（DONE，2026-08-28）

```text
backend/app/domain/instrument.py   InstrumentProfile（任务书 §19 字段全集）
backend/app/domain/code_norm.py    A 股代码规范化 + 板块分类
                                   （沪主板60/科创板688-689/深主板000-003/创业板300-302/北交所43-92）
backend/app/domain/catalog.py      seed 目录（12 只真实标的，覆盖四板 + 五大研究风格）
backend/app/api/instruments.py     GET /api/v1/instruments?query= / GET /instruments/{id}
frontend                           标的搜索卡片（真实 API 调用）
验证: backend pytest 49 passed（四板回归/前缀变体/矛盾提示拒绝/名称别名/缺数据契约）
      浏览器实测: 600519→按代码 / 茅台→按名称 / CATL→按别名 / 未知→空
```

### M1 — 工程基线 + i18n + theme（DONE，2026-08-28）

正式仓库内建立（非搬迁 TideTrading，见 ADR-001 D1/D4）：

```text
backend/   FastAPI + Pydantic v2；/api/v1/health；稳定 error_code 信封
           （common.not_found/validation_error/internal_error…）；
           message_code + Accept-Language normalize（zh*→zh-CN）
frontend/  Vite + React 19 + TS；TanStack Query 接真实后端；react-i18next
           （zh-CN/en-US 资源、system 解析、手动覆盖持久化）；三态主题
           （data-theme + prefers-color-scheme 跟随 + 手动覆盖）；
           Design Tokens（tokens.css light/dark 双套，语义色与主题解耦，
           A股红涨绿跌 CN 默认 + data-updown=intl 可配置）
```

真实验证（浏览器实测）：

```text
后端连通 PASS（/api/v1/health → ok · v0.1.0）
三态主题切换 PASS；OS 深浅跟随 PASS；手动覆盖不被系统覆盖 PASS
语言三态（system/zh-CN/en-US）切换 PASS（h1/lang 属性/localStorage）
涨跌语义色实测：light up=#c23a2f(红) down=#2e7d54(绿)；dark 同语义提亮；intl 惯例翻转 PASS
frontend build PASS（vite）
```

### M0 — 上游/底座源码审计（DONE，2026-08-28）

六个候选完成源码级审计（结构/运行/测试/许可证）：

```text
TideTrading    ADOPT  主工程基线（live A股行情验证 PASS，102 端点，frontend build PASS）
OpenAlpha CN   ADAPT  领域契约蓝本（105 tests PASS，25 端点验证）
觀瀾            REFERENCE_ONLY（无 LICENSE，仅 UX 参考）
Qlib           REFERENCE_ONLY（import PASS，闭环验证 defer M21/M22）
RD-Agent       REJECT（import PASS，M20 后可重评）
TradingAgents  REFERENCE_ONLY（27 tests PASS，无 A 股数据层）
```

产出：`docs/current-architecture-audit.md`、`docs/upstream-evaluation.md`、
`docs/adr/ADR-001-main-engine-baseline.md`。

---

## Milestone 依赖关系

```text
M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12
M12 → M13 → M14
M12 → M15 → M16 → M17 → M18
M18 → M19 → M20
M18 → M21 → (M22 | NOT_REQUIRED)
M12 → M23 → M24 → M25 → M26 → M27
M27 + M20 + M22 → M28 → M29
```

M13/M14 与 M15–M18 可交错推进，但各自 DoD 独立成立。

---

## 长期不变量（所有 Milestone 必须遵守）

- 所有正式交付物只进入 `hyperhaohao/A-Share-Research-OS`；
- 不允许伪完成（TODO/placeholder/mock 冒充真实业务）；
- i18n（zh-CN/en-US/system）与 theme（system/light/dark）从 M1 起是一级能力；
- PIT 与 Traceability 约束从 M4 起强制；
- Prediction 一旦创建不可修改；
- ReportVersion 永不覆盖旧版本；
- 每个 Milestone 的代码、测试、migration、文档同一阶段闭环。
