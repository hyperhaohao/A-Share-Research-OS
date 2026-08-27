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

- [ ] 确认当前目录与 canonical repository
- [ ] `git status`
- [ ] `git log --oneline`
- [ ] 检查现有仓库文件
- [ ] 在仓库外建立 upstream workspace
- [ ] 审计 TideTrading
- [ ] 审计 OpenAlpha CN
- [ ] 审计觀瀾
- [ ] 审计 Qlib
- [ ] 审计 RD-Agent
- [ ] 审计 TradingAgents
- [ ] 实际启动主要候选
- [ ] 运行相关 upstream tests
- [ ] 检查 LICENSE
- [ ] 输出 upstream evaluation matrix
- [ ] 输出 current architecture audit
- [ ] ADR：确定正式工程基线
- [ ] Build/Test/Verification
- [ ] Git Checkpoint

Exit Criteria：

```text
M0 DoD PASS
```

---

# Phase 1 — Engineering Foundation

对应：

```text
M1
M2
```

- [ ] 建立/适配正式工程基线
- [ ] Backend smoke
- [ ] Frontend smoke
- [ ] i18n foundation
- [ ] zh-CN
- [ ] en-US
- [ ] language=system
- [ ] theme=system/light/dark
- [ ] OS theme listener
- [ ] Design Tokens
- [ ] chart theme foundation
- [ ] stable error/status codes
- [ ] Instrument model
- [ ] A-share code/name resolution
- [ ] SSE/SZSE/STAR/ChiNext regression
- [ ] Build/Test/Verification
- [ ] Git Checkpoint

Exit Criteria：

```text
M1 + M2 PASS
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

- [ ] capability-based Source Layer
- [ ] Provider fallback
- [ ] structured failures
- [ ] cache semantics
- [ ] source health
- [ ] EvidenceRecord
- [ ] SourceManifest
- [ ] source dedup
- [ ] authority_level
- [ ] fact_status
- [ ] PIT four clocks
- [ ] historical future-data blocking
- [ ] immutable EvidenceSnapshot
- [ ] CorporateEvent
- [ ] Claim
- [ ] InvestmentThesis
- [ ] EvidenceQualityGate
- [ ] AnalysisQualityGate
- [ ] FinalReportQualityGate skeleton only when used by real flow
- [ ] live-source validation
- [ ] PIT tests
- [ ] traceability tests
- [ ] Git Checkpoints by verified slice

Exit Criteria：

```text
M3–M7 PASS
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
