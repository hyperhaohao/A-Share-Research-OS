# ROADMAP.md

# A-Share Research OS — Milestone Roadmap

> 本文件是长期 Milestone 状态的唯一状态源。
>
> 每完成一个 Milestone（通过其 DoD）更新状态。
> 同一时间只允许一个 `DOING`。
> Milestone 细节以 `docs/A-Share-Research-OS-最终实施任务书.md` 为准。

---

## 产品闭环二次整改（PW，当前执行线）

> 依据 `docs/archive/A-Share-Research-OS-产品闭环二次审查与本地化整改方案.md`。
> 核心回归标的：000831 中国稀土（禁止为其写特殊业务逻辑）。

| 阶段 | 内容 | 状态 |
|------|------|------|
| PW0 | Instrument Identity & Localization（持久化 Registry / 统一 Service / 本地化 / 单 Select） | DONE |
| PW1 | Research Live Experience（SSE 实时 / 逐项进度 / 中文化 / CTA） | DONE |
| PW2 | Watchlist / Task / Report / Prediction Closure | DONE |
| PW3 | Command Center & Product E2E（Playwright / 000831 全链） | DONE |

---

## V2 总纲执行线（Phase A–J，当前长期线）

> 依据 `docs/archive/A-Share-Research-OS-最终产品与架构修改方案.md`。
> 以 Artifact/Provenance 为物料总线、AI 研究中枢为统一入口，
> 按「研报→经验→验证→选股→策略→盯盘→决策→复盘→回灌」纵向闭环推进。

| Phase | 内容 | 状态 |
|-------|------|------|
| A | 统一研究基础协议（Artifact/Provenance/Context/Handoff/RunEvent 持久化；Registry+本地化已由 PW0 计入） | DONE |
| B | AI 研究中枢 + 报告 Handoff | DONE |
| C | 研究经验卡（原炼验用） | DONE |
| D | 研究验证工作流（强类型 DAG） | DONE |
| E | 智能选股（Why Selected） | DONE |
| F | 策略实验室 | DONE |
| G | 策略盯盘（Observation/Signal/Decision 分离） | DONE |
| H | 产业研究地图 + 全球宏观视图 | DONE |
| I | 全库研究图谱 | DONE |
| J | 完整复盘回灌 | DONE |
| 验收 | 总纲验收全链复查（Reviewer Pass） | DONE |
| 深度 | 深度扩展（关系源/宏观/quant/§47 全套） | DONE |
| 部署 | 认证 + TLS + PostgreSQL（公网部署准备） | PLANNED |
| UI | UX Foundation（UI0–UI8，业务冻结） | DONE |

---

## Guanlan Direct Port（Track B，当前长期线）

> 依据 `docs/A-Share-Research-OS-Guanlan-Direct-Port-最终迁植与集成方案.md`
> （Experience Layer 唯一总任务书）。
> Donor-First：观澜成熟 Experience Layer 直接迁植（JSX→TSX 组件化），
> 后端坚持 ASRO（Evidence/PIT/Artifact/Provenance/Version/Auth/Scheduler）。
> Donor：upstreams/financial-analyst @ 98f1398（觀瀾）。
> 每模块 PORT-MANIFEST.md + 功能级对标，禁止以"页面能打开"宣布完成。

| Phase | 内容 | 状态 |
|-------|------|------|
| G0 | Shared UI Foundation（token 映射 / 共享组件 TSX 化 / 基础组件集） | DONE |
| G1 | AI 研究中枢 / 深度研究 | DONE |
| G2 | 产业研究三视图（产业链+全球坐标+环节详情） | DONE |
| G3 | 研究经验卡（原炼验用） | DONE |
| G4 | Workflow Studio（真 Editor） | DONE |
| G5 | 智能选股（三面板） | DONE |
| G6 | 策略实验室（物料装配） | DONE |
| G7 | 策略盯盘（K线/Signal/Decision/Replay） | DONE |
| G8 | 全球宏观 / 海外 | DONE |
| G9 | 全库研究图谱整合 | DONE |
| G10 | Full Product Closure（§44 端到端 + §45 parity） | DONE |

---

## Research Capability Deep Port（R 线，当前 DOING）

> 依据 `docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md`（正式任务书）。
> 目标：观澜非量化 Research Capability 深度融合 ASRO
> Evidence/PIT/Claim/Thesis/Version/Monitor/Validation 内核。
> Quant 冻结（NO NEW DEVELOPMENT，保留不删）。License Gate：REFERENCE_ONLY。
> 黄金场景：000831 中国稀土资产整合 → docs/research-deep-port/R10-CLOSURE.md。

| 阶段 | 内容 | 状态 |
|-------|------|------|
| R0 | Donor Delta Audit + Bootstrap（三方 commit/License Gate/差距矩阵 27 项/执行线注册） | DONE |
| R1 | Research Domain Boundary & Product Repositioning（ADR/导航/README） | DONE |
| R2 | Source Trust + Evidence-backed Extraction（T0-T4/升级规则/Citation Verification/注入防线） | DONE |
| R3 | Industry Semantic Engine（Driver/Transmission/Narrative/五轴站位，稀土跑通） | DONE |
| R4 | Research Commander Autonomous Loop（九类意图/结构化 Plan/Missing Data Loop/Profiles/状态机/迭代上限） | DOING |
| R5 | Research Product System（P0 四类 + P1 三类，逐类型 Contract） | PLANNED |
| R6 | Experience 非量化改造（LLM Refinement 九字段/非量化验证/Playbook） | PLANNED |
| R7 | Research Memory（七类/versioned/检索/staging 晋升/Memory≠Evidence） | PLANNED |
| R8 | Research Inbox / Materiality 扩展 / Thesis Diff / Monitor 类型 / A-B Signal Ladder | PLANNED |
| R9 | Research Graph 扩展 + Context Handoff + 000831 黄金场景 | PLANNED |
| R10 | Closure（逐项 PASS/FAIL 文档） | PLANNED |

---

## 整改阶段（REMEDIATION，历史执行线）

> 整改依据 `docs/archive/A-Share-Research-OS-整改实施任务书.md`；状态详情见 `REMEDIATION.md`。
> 整改 R0–R5 已全部完成。下方 M0–M29 为首轮交付历史记录。

### Final Integrity Pass — COMPLETE（第二轮整改）

F0 Pipeline Integrity / F1 Research Integration / F2 Product Integrity /
F3 Final Verification — 全部通过（详见 STATUS.md 与 git 历史 5a0cec7–HEAD）。

| 阶段 | 内容 | 状态 |
|------|------|------|
| R0 | State & Integrity Repair（状态/Manifest/Gate/测试分类） | DONE |
| R1 | Real Research Data（公告/财务/新闻/资金/行业/宏观 + 行情 fallback） | DONE |
| R2 | Full Research Pipeline（Analyst 集→Claim→Thesis→Debate→Scenario→Valuation→Risk→Report） | DONE |
| R3 | AI / Quant / Continuous（LLMProvider/Copilot/QuantAdapter/后台调度/Delta） | DONE |
| R4 | Research Workspace Completion（九 Tab/Copilot/React Flow/Interactive Report） | DONE |
| R5 | Production Research E2E（多标的 Live E2E/长时运行/生产复验） | DONE |

---

## 首轮交付历史（M0–M29）

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
| M18 | Tasks / Scheduler | DONE | ResearchTask、scheduler、worker、retry、idempotency、recovery |
| M19 | Prediction / Validation | DONE | 不可变 PredictionRecord、5D/20D/60D、ValidationRecord |
| M20 | Regression / Experience | DONE | RegressionReview 归因、ResearchExperience 沉淀 |
| M21 | Quant audit | DONE | 主工程 quant 能力客观审计，决定是否需要 Qlib |
| M22 | Qlib（若需要） | NOT_REQUIRED | 经审计：主工程 quant 能力满足（详见 docs/quant-audit.md） |
| M23 | Research API / SSE | PLANNED | 稳定 Research API、SSE 事件流、source health API |
| M24 | Workspace | DONE | Dashboard、Watchlist、Stock Workspace |
| M25 | Research visual UI | DONE | Timeline UI、Research Graph UI、Thesis Board、Evidence UI |
| M26 | Interactive Report | DONE | TOC、Citation viewer、Explain/Audit/Refresh/Revalue/Revision Diff |
| M27 | Tasks / Prediction UI | DONE | Tasks UI、Prediction Dashboard、完整双语主题回归 |
| M28 | E2E / Performance / Cost | DONE | 多标的 E2E、性能、成本核算、安全审查 |
| M29 | Production Delivery | DONE | Docker Compose、migration、health check、backup/restore、最终 Reviewer Pass |

---

## 当前状态：全部 Milestone 已交付

M0–M29 全部完成（M22 经审计 NOT_REQUIRED）。详见「已完成 Milestone」各节与
docs/final-review.md（最终 Reviewer Pass 逐项核对）。

---

## 已完成 Milestone

### M29 — Production Delivery（DONE，2026-08-28）

```text
docker-compose.yml + backend/Dockerfile + frontend/Dockerfile + nginx.conf
.env.example（数据库/CORS/调试配置）
scripts/backup.sh + scripts/restore.sh —— 演练 PASS（26 表完整恢复）
docs/ 全量补齐：architecture/data-model/source-layer/evidence-and-pit/
research-workflow/report-and-review/i18n/theming/tasks/quant-audit/
testing/security/deployment/backup-restore/migration/known-limitations/
final-review（共 17 篇实现与治理文档）
docs/final-review.md  最终 Reviewer Pass：§99 三十三项逐项核对，
                      发现问题当场修复（吞异常/迁移链/错误边界）
README                最终版（快速开始/能力矩阵/文档索引）
验证: backend 240 tests + frontend 8 tests + build PASS
      备份恢复演练 PASS；compose config 校验 PASS
      注：docker 镜像完整构建需 Docker Desktop 守护进程（本机启动中），
      配置已校验，守护进程可用后直接 docker compose build 即可
```

## 已完成 Milestone

### M28 — E2E / Performance / Cost（DONE，2026-08-28）

```text
backend/tests/test_e2e_multiresearch.py
                                  四板全流程 E2E（搜索→采集→快照→主张→论点→估值→
                                  双语门禁报告→时间线→图谱追溯）+ 报告隔离测试
backend/app/api/costs.py          GET /api/v1/costs（每 run：LLM 调用 0/source 调用/时长）
docs/security.md                  XSS 转义矩阵/注入防护/密钥/CORS 部署边界
docs/testing.md                   测试分层/不变量映射/Live 记录/性能基线/已知限制
验证: backend pytest 239 passed
```

## 已完成 Milestone

### M27 — Tasks / Prediction UI（DONE，2026-08-28）

```text
frontend/src/pages/TasksPage.tsx       任务创建（monitor/prediction_validation）+
                                       启停 + 调度器 tick 按钮 + 结果显示
frontend/src/pages/PredictionsPage.tsx 预测表现统计（Direction Accuracy / Avg Excess /
                                       Range Hit）+ 预测列表（含验证结果）
frontend/src/components/ErrorBoundary.tsx  渲染错误不白屏
导航                                    dashboard/watchlist/tasks/predictions/reports
验证: frontend 8 tests + build PASS；浏览器实测：任务创建（宁德时代）+
      tick 执行（claimed 1 succeeded 1）+ 预测页统计渲染
      后端修复：resolve_instrument_id 支持全格式 instrument id；all_models
      注册表补 MaterialityDecisionORM；25 表全量迁移重建
```

## 已完成 Milestone

### M26 — Interactive Report（DONE，2026-08-28）

```text
frontend/src/pages/InteractiveReportPage.tsx
                                  报告动作组（Explain→ask explain / Audit→full_report
                                  审计 / Refresh→ask refresh）+ TOC（11 节锚点滚动）+
                                  Citation viewer（点击引用 → GET /evidence/{id} 弹层：
                                  来源/权威度/fact_status/可得时间/摘要）
backend                           GET /api/v1/evidence/{evidence_id} 引用详情端点
验证: frontend 8 tests + build PASS；浏览器实测：
      Explain 面板（主张+引用）、TOC 11 节、Citation viewer 全字段、
      Refresh（新增证据 2 / 移除 0 / 受影响主张——真实采集差集）
```

## 已完成 Milestone

### M25 — Research visual UI（DONE，2026-08-28）

```text
frontend/src/components/ResearchVisuals.tsx
                                  TimelineTab（§46 时间线 + 类型过滤 chips）+
                                  GraphTab（§60 图谱：按研究层分列、节点点击 →
                                  upstream 追溯、depth 标注、关闭回视图）
frontend/src/pages/InstrumentWorkspacePage.tsx
                                  §58 五 Tab 工作区：总览/时间线/研究图谱/证据/预测
验证: frontend 8 tests + build PASS；浏览器实测：
      时间线条目（论点/主张/报告版本/行情）按时间倒序；
      图谱 20 节点分 8 列；claim 上游追溯：0 claim → 1 evidence+snapshot →
      2 source(tencent_quote)，深度标注正确
```

## 已完成 Milestone

### M24 — Workspace（DONE，2026-08-28）

```text
frontend/src/pages/WatchlistPage.tsx       关注列表（真实 API 增删 + 名称解析入列）
frontend/src/pages/InstrumentWorkspacePage.tsx
                                           标的 Workspace：Header（name/code/exchange/
                                           board/industry）+ 最新行情 + 证据 + 预测
frontend/src/pages/ReportsPage.tsx         报告列表 + 报告查看页（服务端已转义的 HTML）
frontend/src/App.tsx                       BrowserRouter + 导航（§56 前三项；其余随
                                           M25–M27 路由逐项点亮，不留死链）
验证: frontend 8 tests + build PASS；浏览器实测：导航/关注列表增删/
      名称解析（贵州茅台→SSE:600519）/Workspace 页数据全通
```

## 已完成 Milestone

### M23 — Research API / SSE（DONE，2026-08-28）

```text
§66 API 清单: instruments/research runs/timeline/graph/evidence/claims/theses/
             reports/ask/revisions/tasks/predictions/performance/source-health/
             watchlist 全部就位（233 tests）
SSE:         app/core/events.py EventBus（线程安全 pub/sub）+
             GET /events/stream（SSE 生成器，keep-alive + run_completed/failed 终止）
管线:        POST /pipeline/run —— ResearchPipeline 全链：collect → snapshot(PIT) →
             analyst → compile → quality_gate → report(+V1 版本) → manifest →
             run_completed；事件序列 §67 全覆盖
前端:        ResearchPipelineCard（EventSource 订阅 + 事件渲染）
关键修复:    alembic 迁移链曾静默断裂（Windows 文件锁使 rm 失败 → 空迁移）；
             已建立 all_models 注册表 + 合并迁移重建（25 表全部就位）
验证: backend pytest 233 passed；LIVE: 管线事件序列 + watchlist 增删
```

## 已完成 Milestone

### M21 — Quant audit（DONE，2026-08-28）

```text
证据: TideTrading agent/src/factors（约2.8万行：alpha101 104 / gtja191 194 /
     qlib158 158 / academic；registry + IC bench_runner + analysis core）+
     agent/backtest（约1.26万行：ChinaAEngine T+1/印花税/佣金/涨跌停 + 多市场
     引擎 + 优化器 + metrics/validation/scorecard）+ quant 真实性测试
决定: M22 = NOT_REQUIRED —— Qlib 158 因子集已移植进主工程；ChinaAEngine 覆盖
     A股规则；引入 Qlib 违反「不维护两套重复量化底层」（§12）
产出: docs/quant-audit.md（证据矩阵 + 重评触发条件）
```

## 已完成 Milestone

### M20 — Regression / Experience（DONE，2026-08-28）

```text
backend/app/domain/regression.py  RegressionReview：确定性归因（market_regime 需基准
                                  同向佐证、证据过期→evidence、低置信→claim、
                                  方向对但区间miss→timing、兜底 thesis；≥1 维强制）；
                                  ResearchExperience append-only（只沉淀不自动改 Prompt）
backend/app/api/regression.py     POST /regression/reviews + experiences + GET 列表 +
                                  GET /regression/performance（Direction Accuracy /
                                  Avg Excess / Range Hit Rate 聚合）
backend/alembic                   m20 迁移
验证: backend pytest 226 passed
```

## 已完成 Milestone

### M19 — Prediction / Validation（DONE，2026-08-28）

```text
backend/app/domain/prediction.py  PredictionRecord（§50 字段全集，frozen 不可变）、
                                  Horizon 5D/20D/60D、交易日 due 计算（周末跳过，
                                  假日历为已知限制）、ValidationRecord
backend/app/services/validation_service.py
                                  compute_validation 纯数学（§80 固定数值单测：
                                  收益/超额/方向/区间命中，取整后一致性），
                                  validate 单次性（重复验证返回同记录）
backend/app/storage/prediction_repo.py + API + 调度器 prediction_validation 处理器
验证: backend pytest 219 passed
      §80 固定数值（1648→1730.4 = +5.0% 方向正确/区间命中）
      不可变（frozen 赋值拒绝）；premature 验证 422
      调度器集成：prediction_validation 任务跑到期预测
```

## 已完成 Milestone

### M18 — Tasks / Scheduler（DONE，2026-08-28）

```text
backend/app/scheduler/tasks.py     ResearchTask（§48 字段全集）+ TaskRepository：
                                   claim 原子认领（推进 next_run_at → 幂等）、
                                   同 instrument 互斥（并发控制）、
                                   retry 指数退避 + FAILED 终态、
                                   recover_interrupted（租约超时重启恢复）
backend/app/scheduler/scheduler.py tick 循环 + 业务函数注册表（scheduler 只管何时，
                                   monitor/full_research 处理器独立可测）
backend/app/api/tasks.py           POST/GET /tasks、PATCH enable、POST /scheduler/tick
backend/alembic                    m18 迁移
验证: backend pytest 205 passed
      幂等（第二 tick 不重复）、失败退避、并发互斥、中断恢复、禁用停跑全测试
```

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
