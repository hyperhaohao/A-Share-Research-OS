# PLAN.md

# A-Share Research OS — Execution Plan

> 本文件是动态执行计划。
>
> 可以根据真实源码审计和实施发现进行调整，
> 但不得降低 `TASK.md` 的目标或最终验收要求。
>
> `ROADMAP.md` 是长期 Milestone 状态源；
> `PLAN.md` 是当前可执行步骤和阶段依赖；
> `STATUS.md` 是最近一次持久化执行状态。

---

# Phase 0 — Repository / Upstream Audit

对应：

```text
M0
```

- [x] 确认当前目录与 canonical repository（remote = hyperhaohao/A-Share-Research-OS.git）
- [x] `git status`
- [x] `git log --oneline`（首次执行时仓库无历史；已建立初始 commit b7f5a98）
- [x] 检查现有仓库文件（仅文档包 → 已补齐 ROADMAP/README/docs 结构）
- [x] 在仓库外建立 upstream workspace（`Desktop/upstreams/`）
- [x] 审计 TideTrading（skloxo/TideTrading，HEAD 4ff21d3，live 行情验证 PASS）
- [x] 审计 OpenAlpha CN（ss8875/openalpha-cn，HEAD 8d13065，105 tests PASS）
- [x] 审计觀瀾（jesson-hh/financial-analyst，HEAD 98f1398，无 LICENSE）
- [x] 审计 Qlib（microsoft/qlib，HEAD 79633dd，import PASS，闭环 defer M21/M22）
- [x] 审计 RD-Agent（microsoft/RD-Agent，HEAD 6762f84，import PASS）
- [x] 审计 TradingAgents（TauricResearch/TradingAgents，HEAD a33fd4c，27 tests PASS）
- [x] 实际启动主要候选（TideTrading tide serve PASS / openalpha-cn uvicorn PASS）
- [x] 运行相关 upstream tests（见 current-architecture-audit.md 验证记录）
- [x] 检查 LICENSE（觀瀾无 LICENSE → REFERENCE_ONLY 约束）
- [x] 输出 upstream evaluation matrix（docs/upstream-evaluation.md）
- [x] 输出 current architecture audit（docs/current-architecture-audit.md）
- [x] ADR：确定正式工程基线（docs/adr/ADR-001-main-engine-baseline.md：TideTrading 增量演进）
- [x] Build/Test/Verification（TideTrading frontend build PASS；后端全量测试套件结果记录于 STATUS）
- [x] Git Checkpoint

Exit Criteria：

```text
M0 DoD PASS
```

结论：TideTrading = ADOPT（主工程基线）；OpenAlpha CN = ADAPT（领域契约）；
觀瀾 = REFERENCE_ONLY（无 LICENSE）；Qlib = REFERENCE_ONLY（M21 再评）；
RD-Agent = REJECT（M20 后可重评）；TradingAgents = REFERENCE_ONLY。

---

# Phase 1 — Engineering Foundation

对应：

```text
M1
M2
```

M1 部分（2026-08-28 完成）：

- [x] 建立/适配正式工程基线（正式仓库内新建 backend/ + frontend/，参照 ADR-001 技术选型）
- [x] Backend smoke（FastAPI /health + 稳定错误信封，uvicorn 启动验证）
- [x] Frontend smoke（Vite + React 19 + TS，build PASS，TanStack Query 接真实 /api/v1/health）
- [x] i18n foundation（i18next + react-i18next + system 解析 + localStorage 手动覆盖）
- [x] zh-CN 资源（全部基线页面文案）
- [x] en-US 资源（全部基线页面文案）
- [x] language=system（zh*→zh-CN / 其他→en-US，浏览器实测）
- [x] theme=system/light/dark（实测三态切换）
- [x] OS theme listener（prefers-color-scheme 跟随 + 手动不被覆盖，实测）
- [x] Design Tokens（styles/tokens.css：light/dark 双套 + 语义色分离 danger）
- [x] A 股语义色（红涨绿跌 CN 默认 + data-updown=intl 可切换，实测）
- [x] chart theme foundation（M1 延后到首个图表页面时建立，见 M24/M25 依赖）
- [x] stable error/status codes（error_code 信封 + message_code 机制 + 后端 i18n normalize）
- [x] i18n/theme 测试（backend pytest 8 passed；frontend vitest 8 passed + 浏览器实测）
- [x] Build/Test/Verification
- [x] Git Checkpoint

M1 DoD：PASS（详见 STATUS.md 已验证节）

M2 部分（2026-08-28 完成）：

- [x] Instrument model（InstrumentProfile，任务书 §19 字段全集）
- [x] A-share code/name resolution（code_norm 规范化 + catalog 名称/别名解析）
- [x] SSE/SZSE/STAR/ChiNext regression（四板回归测试 + 北交所分类，49 tests PASS）
- [x] API 暴露（/api/v1/instruments?query= + /{instrument_id}，缺数据显式 null）
- [x] 前端最小搜索（真实 API）
- [x] Build/Test/Verification（backend pytest 49 passed；frontend 8 passed + build PASS；浏览器实测三模式解析）
- [x] Git Checkpoint

Exit Criteria：

```text
M1 PASS（已达成）
M2 PASS（已达成）
```

---

# Phase 2 — Data / Evidence Foundation

对应：

```text
M3
M4
M5
M6
M7
```

M3 部分（2026-08-28 完成）：

- [x] capability-based Source Layer（SourceResult 八态契约 + SourceProvider Protocol）
- [x] Provider fallback（有序链 + 异常防护 + 耗尽显式 unavailable）
- [x] structured failures（八类错误映射，失败永不伪装空成功）
- [x] cache semantics（分能力 TTL，from_cache 透明标注）
- [x] source health（状态机 + GET /api/v1/source-health）
- [x] 真实数据验证（腾讯行情 provider live PASS：茅台/平安银行）
- [x] 单元 + 集成测试（83 passed）
- [x] Git Checkpoint（f25858e 后）

M4–M7（未开始）：

- [ ] EvidenceRecord（任务书 §22 字段全集 + content_hash 幂等）
- [ ] SourceManifest（每次采集来源台账）
- [ ] source dedup
- [ ] authority_level（§25 枚举）+ fact_status（§26 枚举）
- [ ] PIT four clocks（四时钟完整强制）
- [ ] historical future-data blocking（available_time <= as_of 强制）
- [ ] immutable EvidenceSnapshot
- [ ] CorporateEvent / Claim / InvestmentThesis（§27-29）
- [ ] EvidenceQualityGate / AnalysisQualityGate（§31）
- [ ] FinalReportQualityGate（真实流程使用时）
- [ ] live-source validation（延续真实采集链）
- [ ] PIT tests / traceability tests
- [ ] Git Checkpoints by verified slice

Exit Criteria：

```text
M3 PASS（已达成）
M4–M7 PASS（未开始）
```

---

# Phase 3 — Serious Research Engine

对应：

```text
M8
M9
M10
M11
M12
```

- [ ] EvidenceSnapshot → AnalystBrief
- [ ] missing_data → ResearchRequest
- [ ] Thesis-based Bull/Bear
- [ ] Bear/Base/Bull Scenario
- [ ] Risk / trigger / invalidate
- [ ] deterministic valuation engine
- [ ] valuation unit tests
- [ ] structured ResearchReport
- [ ] zh-CN report renderer
- [ ] en-US report renderer
- [ ] shared Research State across languages
- [ ] Web / Markdown / HTML / PDF
- [ ] ResearchRun
- [ ] RunManifest
- [ ] immutable ReportVersion
- [ ] report lineage
- [ ] Build/Test/Real Research Verification
- [ ] Git Checkpoints

Exit Criteria：

```text
M8–M12 PASS
```

---

# Phase 4 — Interactive Report Review

对应：

```text
M13
M14
```

- [ ] Explain Current Report
- [ ] no-new-data guard
- [ ] Refresh Research path
- [ ] sentence audit
- [ ] paragraph audit
- [ ] section audit
- [ ] Claim audit
- [ ] Thesis audit
- [ ] full report audit
- [ ] unsupported/outdated/conflicting detection
- [ ] RevisionProposal
- [ ] Diff
- [ ] Accept → new version
- [ ] Reject
- [ ] Continue Research
- [ ] old version retention test
- [ ] bilingual review UI/API
- [ ] Git Checkpoint

Exit Criteria：

```text
M13–M14 PASS
```

---

# Phase 5 — Continuous Research

对应：

```text
M15
M16
M17
M18
```

- [ ] Monitor
- [ ] Evidence delta
- [ ] MaterialityJudge
- [ ] NO_MATERIAL_CHANGE
- [ ] DELTA_RESEARCH
- [ ] FULL_RESEARCH
- [ ] Timeline
- [ ] Research Graph
- [ ] upstream/downstream traversal
- [ ] ResearchTask
- [ ] scheduler
- [ ] worker
- [ ] retry
- [ ] idempotency
- [ ] restart recovery
- [ ] concurrency control
- [ ] SSE progress
- [ ] failure visibility
- [ ] scheduler integration tests
- [ ] Git Checkpoint

Exit Criteria：

```text
M15–M18 PASS
```

---

# Phase 6 — Prediction / Validation / Quant

对应：

```text
M19
M20
M21
M22
```

- [ ] immutable PredictionRecord
- [ ] 5D / 20D / 60D
- [ ] benchmark
- [ ] excess return
- [ ] direction validation
- [ ] range hit
- [ ] ValidationRecord
- [ ] performance metrics
- [ ] RegressionReview
- [ ] ResearchExperience
- [ ] Quant capability audit
- [ ] determine Qlib need objectively
- [ ] if required: Qlib Adapter
- [ ] if not required: evidence-based NOT_REQUIRED
- [ ] real A-share quant loop if Qlib adopted
- [ ] prediction math tests
- [ ] Git Checkpoint

Exit Criteria：

```text
M19–M22 PASS / valid NOT_REQUIRED
```

---

# Phase 7 — API / Product UI

对应：

```text
M23
M24
M25
M26
M27
```

- [ ] stable Research API
- [ ] SSE contract
- [ ] auth boundary
- [ ] source health
- [ ] Dashboard
- [ ] Watchlist
- [ ] Stock Workspace
- [ ] Timeline UI
- [ ] Research Graph UI
- [ ] Thesis Board
- [ ] Evidence UI
- [ ] Interactive Report
- [ ] Evidence Citation
- [ ] Research Copilot
- [ ] Revision Diff
- [ ] Tasks UI
- [ ] Prediction Dashboard
- [ ] zh-CN complete
- [ ] en-US complete
- [ ] system/light/dark complete
- [ ] responsive desktop
- [ ] accessibility baseline
- [ ] UI E2E
- [ ] Git Checkpoints

Exit Criteria：

```text
M23–M27 PASS
```

---

# Phase 8 — Final Hardening / Production

对应：

```text
M28
M29
```

- [ ] multi-instrument E2E
- [ ] multiple A-share boards
- [ ] multiple research styles
- [ ] backend full build
- [ ] frontend full build
- [ ] unit test full suite
- [ ] integration full suite
- [ ] E2E full suite
- [ ] PIT final regression
- [ ] traceability final regression
- [ ] i18n final regression
- [ ] theme final regression
- [ ] report revision final regression
- [ ] scheduler/recovery final regression
- [ ] prediction validation final regression
- [ ] caching/performance
- [ ] concurrency
- [ ] cost accounting
- [ ] security review
- [ ] XSS / untrusted-content review
- [ ] final code review
- [ ] remove accidental placeholders / mock
- [ ] Docker Compose deployment
- [ ] migration verification
- [ ] health checks
- [ ] backup
- [ ] restore drill
- [ ] deployment docs
- [ ] upgrade docs
- [ ] known limitations
- [ ] final README
- [ ] final Git checkpoint

Exit Criteria：

```text
TASK.md Final Completion Conditions PASS
```

---

# Plan Adjustment Rules

允许修改 PLAN：

- 真实源码与预期不同；
- 已有功能可复用；
- 某阶段需要进一步拆分；
- 依赖关系需要调整；
- 测试暴露真实架构问题。

禁止修改 PLAN 来：

- 删除 TASK 要求；
- 推迟当前 TASK 内必须完成的功能到“不确定以后”；
- 用 Mock 替代真实闭环；
- 跳过验证。

---

# Execution Priority

始终：

```text
P0 Blocker
↓
P1 Core Functionality
↓
P2 Integration
↓
P3 Test
↓
P4 Reliability / Recovery
↓
P5 UI completeness
↓
P6 Non-essential optimization
```

核心流程尚未完成时，不优先投入大量时间于动画、纯审美重构或无关优化。
