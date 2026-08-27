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
| M0 | 上游/底座源码审计 | DOING | upstream audit workspace、评估矩阵、架构审计、ADR-001 |
| M1 | 工程基线 + i18n + theme | PLANNED | 可运行的 backend/frontend 基线、zh-CN/en-US、system/light/dark |
| M2 | Instrument | PLANNED | InstrumentProfile、A 股代码/名称解析、四板回归 |
| M3 | Source Layer | PLANNED | capability-based Provider、fallback、SourceResult、source health |
| M4 | Evidence | PLANNED | EvidenceRecord、authority/fact_status、dedup、SourceManifest |
| M5 | PIT / Snapshot | PLANNED | 四时钟、available_time <= as_of 强制、不可变 EvidenceSnapshot |
| M6 | Research Domain | PLANNED | CorporateEvent、Claim、InvestmentThesis |
| M7 | Quality | PLANNED | EvidenceQualityGate、AnalysisQualityGate、FinalReportQualityGate |
| M8 | Structured Agents | PLANNED | AnalystBrief、missing_data → ResearchRequest 闭环 |
| M9 | Debate / Scenario / Risk | PLANNED | Thesis-based Bull/Bear、Bear/Base/Bull Scenario、Risk trigger |
| M10 | Valuation | PLANNED | 确定性估值引擎（PE/PB/PS/EV/EBITDA/DCF/DDM/SOTP/NAV/percentile/comps） |
| M11 | ResearchReport bilingual | PLANNED | 结构化报告、zh/en renderer、共享 Research State |
| M12 | Manifest / Versions | PLANNED | ResearchRun、RunManifest、不可变 ReportVersion |
| M13 | Report Q&A | PLANNED | Explain（无新数据）与 Refresh（允许新数据）严格区分 |
| M14 | Audit / Revision | PLANNED | sentence/claim/thesis audit、RevisionProposal、Diff、Accept |
| M15 | Delta / Materiality | PLANNED | Monitor、Evidence delta、MaterialityJudge 三分支 |
| M16 | Timeline | PLANNED | 统一事件时间线 |
| M17 | Research Graph | PLANNED | 溯源图、upstream/downstream 遍历 |
| M18 | Tasks / Scheduler | PLANNED | ResearchTask、scheduler、worker、retry、idempotency、recovery |
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

## 当前 DOING：M0 — 上游/底座源码审计

### 范围

在正式仓库之外建立 `upstreams/` workspace，对以下候选做源码级审计（不得只读 README）：

```text
TideTrading
OpenAlpha CN
觀瀾
Qlib
RD-Agent
TradingAgents
```

### 每个候选必须记录

```text
repository URL
branch / HEAD commit / 最后提交时间
LICENSE（文件级检查）
关键源码定位（data / agent / api / frontend / quant）
实际运行结果（backend 启动 / import / CLI）
测试运行结果
维护活跃度
评估结论：ADOPT / ADAPT / REFERENCE_ONLY / REJECT
```

### 评估维度

```text
A-share data coverage / engineering completeness / maintainability / license
tests / backend+API / frontend / i18n / theme / agent orchestration
quant+backtest / PIT / evidence provenance / task scheduling / deployment / migration cost
```

### M0 DoD

```text
[ ] upstreams/ 建立在正式仓库之外
[ ] 六个候选全部完成源码级审计并记录 branch/commit/license
[ ] 主要候选实际启动
[ ] 相关测试实际运行
[ ] docs/current-architecture-audit.md 输出
[ ] docs/upstream-evaluation.md 输出（含 ADOPT/ADAPT/REFERENCE_ONLY/REJECT 矩阵）
[ ] docs/adr/ADR-001-main-engine-baseline.md 输出（主工程基线决策）
[ ] PLAN/STATUS/ROADMAP 更新
[ ] Git checkpoint
```

M0 通过后自动进入 M1。

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
