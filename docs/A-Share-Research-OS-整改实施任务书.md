# A-Share Research OS 整改实施任务书

> 适用仓库：
>
> `https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 本文档用于 Claude Code / Coding Agent 直接执行整改。
>
> 本次整改不是推倒重来，而是：
>
> > **保留现有 Research OS Kernel，纠正“对象/接口存在 = 完成”的错误判定，补齐真实数据、真实研究、真实调度和真实端到端闭环。**

---

# 1. 执行要求

你现在不是输出建议，而是作为持续执行型工程 Agent：

> **直接修改项目、持续 Build、持续 Test、持续验证、持续修复，直到本文所有整改验收通过。**

开始前必须读取：

```text
TASK.md
AGENTS.md
CLAUDE.md
PLAN.md
STATUS.md
ROADMAP.md
README.md
docs/A-Share-Research-OS-最终实施任务书.md
```

并执行：

```bash
pwd
git status
git log --oneline -10
```

确认当前正式仓库：

```text
hyperhaohao/A-Share-Research-OS
```

除真实外部阻塞外，不要停下来等待用户逐项确认。

---

# 2. 本次整改原则

本次整改遵循：

```text
保留现有真实可用内核
>
修复错误完成判定
>
打通真实业务链
>
补齐必要能力
>
最后再优化 UI
```

禁止：

```text
重新新建一套平行系统
大规模推翻现有后端/前端
为了“架构更漂亮”重写成熟模块
继续创建未接入主流程的空对象
用 Mock / Fixture 冒充真实投研闭环
```

现有以下能力默认保留并继续演进：

```text
FastAPI
React / Vite / TypeScript
SQLAlchemy / Alembic
SourceResult / Provider Registry
Evidence
PIT
EvidenceSnapshot
Claim
Thesis
Quality Models
Valuation Library
ReportVersion
Audit / Revision Model
Timeline
Graph Model
ResearchTask
Prediction / Validation Model
i18n
System / Light / Dark Theme
Docker / Migration / Backup 基础
```

---

# 3. 当前必须承认的真实状态

当前系统已经有较完整 Research OS Kernel，但不能继续标记为完整投研系统。

以下属于当前主要缺口：

1. 正式 Source Provider 目前基本只有腾讯实时行情；
2. 缺少真实财务、公告、新闻、资金、行业、宏观/政策数据链；
3. 当前 ResearchPipeline 主链没有真正串起完整 Analyst → Claim → Thesis → Debate → Scenario → Valuation → Risk → Report；
4. MarketAnalyst 当前主要是行情事实提取；
5. Debate 当前主要是确定性拼装，不是真正 Evidence-aware AI reasoning；
6. 当前没有正式 LLM Research Provider 进入研究主流程；
7. Report Explain 当前主要依赖关键词匹配；
8. 双语报告目前部分研究内容仍是原始中文复用；
9. RunManifest 存在 placeholder 值；
10. QualityGate 存在绕过式逻辑风险；
11. Quant 主要依据 upstream 能力判定完成，但没有真正进入正式仓库主运行链；
12. Scheduler 有 tick 逻辑，但缺少真正长期后台 scheduler/worker 服务；
13. Workspace 信息架构仍不完整；
14. 当前部分所谓 E2E 实际是 API Integration E2E，并未证明真实 Research E2E。

因此：

> **不要继续使用 “M0–M29 全部完成” 作为系统真实完成结论。**

---

# 4. 整改阶段总览

本次整改采用：

```text
R0 — State & Integrity Repair
R1 — Real Research Data
R2 — Full Research Pipeline
R3 — AI / Quant / Continuous Research
R4 — Research Workspace Completion
R5 — Production Research E2E
```

每个阶段必须：

```text
Implement
→ Build
→ Unit Test
→ Integration Test
→ 必要的 Live Verification
→ Review
→ Fix
→ Re-test
→ Git Checkpoint
→ 下一阶段
```

---

# 5. R0 — State & Integrity Repair

## 5.1 目标

先修正项目状态、完成判定和几个明确的“假完成点”。

## 5.2 必做

### A. 重建真实状态

审计：

```text
TASK.md
ROADMAP.md
STATUS.md
README.md
```

逐项按真实代码和真实调用链重新标记：

```text
DONE
PARTIAL
TODO
BLOCKED
NOT_REQUIRED
```

不得因为：

```text
Schema存在
API存在
UI存在
测试文件存在
```

就判定 DONE。

建议新增：

```text
REMEDIATION.md
```

作为本次整改状态源。

旧 M0–M29 保留历史，不删除。

### B. 修 RunManifest placeholder

当前任何类似：

```text
code_commit = "0000000"
config_digest = "000000..."
random_seed = 0（若只是占位）
```

必须改为真实值。

至少记录：

```text
run_id
as_of_time
git_commit
workflow_version
config_digest
provider_versions
provider_config_digest
model_provider
model_name
model_parameters
prompt_versions
random_seed
evidence_snapshot_id
environment
started_at
finished_at
status
```

推荐真实获取：

```bash
git rev-parse HEAD
```

配置和 Prompt 使用规范化内容 SHA256。

### C. 修 QualityGate 绕过

检查所有 Gate：

```text
EvidenceQualityGate
AnalysisQualityGate
FinalReportQualityGate
```

禁止存在类似：

```python
condition = (...) or True
```

或其他无条件 PASS。

真正检查：

```text
required section exists
critical claim has evidence
citation exists
evidence belongs to snapshot
data quality evaluated
missing_data disclosed
valuation assumptions present
PIT valid
source failures visible
```

`FAIL` 必须能真正阻止正式 publish。

### D. 重新分类测试

当前使用 monkeypatch / fixture 的完整 API 流程测试，应明确归类为：

```text
API Integration E2E
```

不要继续把它当：

```text
Live Research E2E
```

保留测试，不删除。

后续新增真正 Live Research E2E。

## 5.3 R0 DoD

只有同时满足：

```text
STATUS / ROADMAP / README 状态一致
RunManifest 无 placeholder
QualityGate 无绕过
测试分类真实
Build PASS
Tests PASS
```

才允许进入 R1。

---

# 6. R1 — Real Research Data

## 6.1 目标

把 Source Layer 从“行情系统”升级为真正的“投研数据层”。

## 6.2 第一批必须补齐的能力

```text
market_data
announcements
financials
news
capital_flow
industry
macro_policy
```

## 6.3 Market Data

现有腾讯行情保留。

必须增加至少一个 fallback：

```text
Tencent
→ Eastmoney / mootdx / other stable source
```

要求：

```text
provider fallback
structured failure
health
cache
fresh bypass
source metadata
```

## 6.4 Announcements

优先：

```text
CNINFO / 巨潮
```

必要时增加交易所或其他官方/法定来源。

必须支持：

```text
code
name
aliases
date range
keywords
event-related filtering
```

生成：

```text
EvidenceRecord
```

并正确设置：

```text
authority_level
fact_status
available_time
source_url
source_document_id
```

## 6.5 Financials

必须至少获取和规范化：

```text
Income Statement
Balance Sheet
Cash Flow

Revenue
Net Profit
Operating Profit
Gross Margin
ROE
ROIC
EPS
BVPS
FCF
Dividend
Shares Outstanding
Net Debt
EBITDA
```

必须保留来源和 period/as_of。

不能把解析失败当作 no_data。

## 6.6 News

至少一个真实财经新闻源。

必须：

```text
按 code / name / alias 搜索
去重
来源标记
发布时间
正文/摘要
fact_status
authority_level
```

媒体新闻默认不能与正式公告同等级。

## 6.7 Capital Flow

至少覆盖可稳定获得的：

```text
turnover
volume
main capital flow
margin financing（如可用）
block trade（如可用）
shareholder / unlock（如可用）
```

缺失时显式 unavailable。

## 6.8 Industry

至少形成：

```text
industry
sub_industry
concepts
peers
upstream
downstream
```

第一版允许结构化基础行业链，不要求一步做到复杂传播模型。

## 6.9 Macro / Policy

第一版重点官方源：

```text
央行
统计局
发改委
工信部
财政部
证监会
国务院
行业主管部门
```

至少支持按：

```text
industry
topic
keyword
date range
```

获取并形成 Evidence。

## 6.10 Source Layer 不变量

所有 Provider 必须统一：

```text
success
no_data
partial
network_error
rate_limit
parse_error
auth_error
source_unavailable
```

禁止：

```text
异常 → []
```

禁止：

```text
请求失败 → no_data
```

## 6.11 R1 DoD

至少选 3～5 个不同类型真实 A 股验证：

```text
market
announcement
financial
news
```

均能形成真实 Evidence。

要求：

```text
Source → Evidence → SourceManifest
```

可追溯。

---

# 7. R2 — Full Research Pipeline

## 7.1 目标

把当前研究流程改造成真正完整 Research Pipeline。

最终主链：

```text
InstrumentResolver
↓
EvidenceCollector
↓
EvidenceSnapshot
↓
EvidenceQualityGate
↓
Analyst Orchestrator
↓
AnalystBrief[]
↓
ClaimCompiler
↓
AnalysisQualityGate
↓
ThesisBuilder
↓
Bull / Bear
↓
ScenarioEngine
↓
ValuationEngine
↓
RiskManager
↓
ResearchManager
↓
ReportCompiler
↓
FinalReportQualityGate
↓
ReportVersion
```

---

# 8. Analyst Set

不要一次创建一堆空 Analyst。

按真实数据能力逐个闭环实现：

```text
FinancialAnalyst
Announcement / CorporateEventAnalyst
NewsAnalyst
IndustryAnalyst
MacroPolicyAnalyst
CapitalFlowAnalyst
MarketAnalyst
RiskAnalyst
```

每新增一个 Analyst 必须满足：

```text
真实 Source
→ EvidenceSnapshot
→ AnalystBrief
→ Claim
→ Report
```

---

# 9. Claim / Thesis 自动化

当前测试中手工 POST 创建 Claim/Thesis 的方式不能作为最终 Research E2E。

必须增加：

```text
AnalystBrief[]
↓
ClaimCompiler
↓
Claim[]
↓
ThesisBuilder
↓
InvestmentThesis[]
```

要求：

```text
Claim 必须引用 Evidence
Thesis 必须引用 Claim
```

无引用不得进入正式报告。

---

# 10. Debate

保留当前 deterministic debate 作为 fallback / baseline。

但正式研究应增加 Evidence-aware reasoning。

流程：

```text
Thesis
↓
Supporting Claims
Opposing Claims
↓
Bull Reasoning
Bear Reasoning
↓
Research Manager Synthesis
```

要求：

- Debate 不允许创造新事实；
- 新事实必须先进入 EvidenceCollector；
- 输出必须引用现有 Claim / Evidence；
- 必须能表达冲突证据和不确定性。

---

# 11. Scenario

至少：

```text
Bear
Base
Bull
```

每个 Scenario：

```text
probability
assumptions
catalysts
risks
trigger_conditions
invalidate_conditions
valuation_result
```

概率总和 100%。

---

# 12. Deterministic Valuation 进入真实主链

现有 Valuation Engine 保留。

新增：

```text
Financial Evidence
↓
Normalized FinancialMetrics
↓
ValuationInputBuilder
↓
ValuationEngine
↓
ValuationResult
↓
Report
```

估值输入必须能追溯到 Evidence。

例如：

```text
EPS TTM
BVPS
Revenue per Share
EBITDA
Net Debt
FCF
Dividend
Shares Outstanding
```

不得依赖用户手工 POST 输入才算正式闭环。

---

# 13. RiskManager

至少形成结构化：

```text
risk_type
description
supporting_claims
supporting_evidence
likelihood
impact
trigger
invalidate_condition
```

不能只输出通用风险模板。

---

# 14. R2 DoD

至少一个真实股票执行：

```text
Source
→ Evidence
→ Snapshot
→ Analysts
→ Claims
→ Thesis
→ Debate
→ Scenario
→ Valuation
→ Risk
→ ResearchReport
```

不能手工 POST Claim/Thesis 补链。

---

# 15. R3 — AI / Quant / Continuous Research

## 15.1 LLMProvider

增加统一：

```text
LLMProvider
```

能力至少：

```text
generate_structured()
generate_text()
stream()
model_info()
usage()
```

优先实现：

```text
OpenAI-compatible
```

从而兼容：

```text
NewAPI
OpenAI
DeepSeek
GLM
Qwen
Doubao
Claude-compatible gateway
```

不要把业务代码绑定单一厂商 SDK。

---

# 16. LLM 使用边界

LLM 可以：

```text
Evidence synthesis
Claim drafting
Thesis construction
Counterargument
Scenario reasoning
Risk reasoning
Narrative report
Report Q&A
Report audit
```

LLM 不可以：

```text
invent financial numbers
invent announcements
invent policy
invent corporate event
invent prices
invent source URL
```

原则：

```text
Evidence First
LLM Reasoning Second
```

---

# 17. Research Copilot

## Explain

```text
Question
↓
ReportVersion
EvidenceSnapshot
Claim
Thesis
Valuation
↓
LLM
↓
Answer + citations
```

禁止新 Source 调用。

## Refresh

```text
Question
↓
ResearchRequest
↓
Fresh Source
↓
New Evidence
↓
New Snapshot
↓
Impact Analysis
```

Explain 和 Refresh 必须继续严格分离。

---

# 18. 双语整改

当前英文报告不能仅复用中文 Thesis / Claim 文本。

正确方式：

```text
Structured Research State
↓
Narrative Layer
├─ zh-CN
└─ en-US
```

两种语言必须共享：

```text
Evidence IDs
Claim IDs
Thesis IDs
Valuation
Numbers
Snapshot
Run
```

Evidence 原文永久保留。

英文报告可以生成英文 narrative，但 citation 仍指向原 Evidence。

---

# 19. Quant 整改

当前不得因为 upstream TideTrading 有 Quant 就认为正式系统已有 Quant。

必须二选一。

## 方案 A — 推荐

实际接入：

```text
QuantEngine
↓
TideQuantAdapter
```

至少打通：

```text
Instrument
→ Historical Data
→ Factor / Feature
→ Model / Score
→ Backtest
→ Metrics
→ QuantBrief
→ Research State
```

如果完成，则 Qlib 可以继续：

```text
NOT_REQUIRED
```

## 方案 B

如果不接 TideTrading Quant：

```text
M22 / Quant = TODO
```

重新评估 Qlib Adapter。

---

# 20. Scheduler / Worker

当前手动：

```text
POST /tasks/scheduler/tick
```

不能算自动持续研究。

必须增加真实后台进程。

第一版允许：

```text
backend
frontend
scheduler
```

scheduler：

```text
periodic tick
↓
DB task claim
↓
run business function
↓
complete / retry
```

量大后再引入 Redis + Celery/RQ/Dramatiq。

不要提前增加多套队列。

---

# 21. Continuous Research

必须真正接入主 Pipeline。

## Monitor

```text
collect new Evidence
```

## Materiality

```text
new Evidence
↓
MaterialityJudge
├─ NO_MATERIAL_CHANGE
├─ DELTA_RESEARCH
└─ FULL_RESEARCH
```

## Delta

```text
Changed Evidence
↓
Affected Claims
↓
Affected Thesis
↓
Affected Analysts
↓
Revaluation if needed
↓
New ReportVersion
```

## Full

调用完整 ResearchPipeline。

---

# 22. R3 DoD

必须真实证明：

```text
LLMProvider works
Research Copilot works
Quant actually runs in formal system
Scheduler automatically runs
Monitor / Delta / Full works
```

---

# 23. R4 — Research Workspace Completion

## 23.1 Stock Workspace

至少补齐：

```text
Overview
Timeline
Research Graph
Thesis
Financials
Valuation
Evidence
Reports
Predictions
```

右侧：

```text
Research Copilot
```

---

# 24. Thesis UI

展示：

```text
title
status
confidence
supporting claims
opposing claims
catalysts
risks
trigger conditions
invalidate conditions
first created
last updated
```

---

# 25. Financial UI

至少：

```text
Revenue
Profit
Margins
ROE / ROIC
Cash Flow
Balance Sheet
Growth
Per-share metrics
```

支持趋势图。

---

# 26. Valuation UI

展示：

```text
method
bear/base/bull
assumptions
peer set
historical percentile
confidence
missing data
input evidence
```

---

# 27. Research Graph

当前列式 Graph 可保留作为 fallback。

正式 Graph 推荐使用：

```text
React Flow
```

或其他成熟关系图组件。

节点：

```text
Source
Evidence
Event
Claim
Thesis
Report
Prediction
Validation
```

要求：

```text
zoom
pan
filter
upstream
downstream
node detail
theme
i18n
```

---

# 28. Interactive Report

现有：

```text
Explain
Audit
Refresh
Citation Viewer
```

继续补：

```text
Counter Evidence
Revalue
Propose Revision
Revision Diff
Accept
Reject
Version History
Research More
```

最重要的是：

```text
selected paragraph
↓
related Claim
↓
related Evidence
↓
Audit / Refresh / Revision
```

---

# 29. UI 技术要求

继续保持：

```text
zh-CN
en-US

system
light
dark
```

图表、Graph、Markdown、Dialog、Tooltip、Table 全部验证。

行情金融图表建议：

```text
ECharts
```

Graph 建议：

```text
React Flow
```

---

# 30. R4 DoD

至少完成真实：

```text
Stock Workspace
Thesis UI
Financial UI
Valuation UI
Evidence UI
Research Graph
Interactive Report
Research Copilot
```

全部接真实 API。

禁止业务 Mock。

---

# 31. R5 — Production Research E2E

## 31.1 重新定义 E2E

保留：

```text
API Integration E2E
```

新增：

```text
Live Research E2E
```

---

# 32. Live Research E2E

至少选择 4～6 个不同类型真实 A 股：

```text
消费
银行/金融
新能源/成长
半导体/科技
周期/资源
制造
```

要求自动执行：

```text
真实股票
↓
Instrument Resolve
↓
Market
Announcements
Financials
News
Capital Flow
Industry
Macro/Policy
↓
Evidence
↓
EvidenceSnapshot
↓
AnalystBrief[]
↓
Claims
↓
Theses
↓
Bull / Bear
↓
Scenario
↓
Valuation
↓
Risk
↓
Bilingual ResearchReport
↓
Citation
↓
Report Audit
↓
Revision
↓
ReportVersion
↓
Scheduled Monitor
↓
New Evidence
↓
Delta Research
↓
Prediction
↓
Validation
```

不能在测试中手工创建 Claim / Thesis / Valuation 来补链。

---

# 33. 多股票回归

至少覆盖：

```text
SSE Main Board
SZSE Main Board
ChiNext
STAR Market
```

并覆盖不同研究风格。

测试的是系统通用性，不是特定股票观点。

---

# 34. 长时间运行测试

至少验证：

```text
scheduler continuous execution
task retry
restart recovery
idempotency
duplicate prevention
source failure recovery
partial source degradation
```

---

# 35. Production

最终再次验证：

```text
Docker Compose
Migration
Health Checks
Backend
Frontend
Scheduler
Database
Backup
Restore
```

实际进行一次 restore drill。

---

# 36. Final Reviewer Pass

整改结束后必须重新以 Reviewer 身份全仓审查。

重点：

```text
TODO / FIXME / placeholder
RunManifest
QualityGate bypass
swallowed exception
Source failure semantics
PIT violation
broken citation
orphan Claim / Thesis
LLM hallucinated fact
double architecture
API mismatch
i18n missing
theme missing
XSS
unsafe HTML
scheduler recovery
prediction mutability
quant not actually connected
```

发现问题直接修复。

不要只输出 Review Report。

---

# 37. 最终完成条件

只有以下全部满足才允许重新写：

```text
TASK COMPLETE
```

必须：

```text
R0 PASS
R1 PASS
R2 PASS
R3 PASS
R4 PASS
R5 PASS

AND

Backend Build PASS
Frontend Build PASS
Unit Tests PASS
Integration Tests PASS
API Integration E2E PASS
Live Research E2E PASS
PIT PASS
Traceability PASS
i18n PASS
Theme PASS
Report Review PASS
Report Version PASS
Scheduler PASS
Restart Recovery PASS
Quant Real Integration PASS
Prediction Validation PASS
Docker PASS
Backup Restore PASS
Final Reviewer PASS
```

---

# 38. 整改期间状态规则

不要继续简单 append `STATUS.md` 历史内容。

`STATUS.md` 必须始终只描述：

```text
Current Phase
Current Milestone
Completed
In Progress
Next Action
Tests
Live Verification
Open Issues
Branch
Commit
```

历史记录放：

```text
docs/milestones/
```

不要让 STATUS 同时出现：

```text
“全部完成”
+
“正在进行 M6”
```

这种矛盾状态。

---

# 39. Git Checkpoint

每完成一个真实整改闭环做 checkpoint。

示例：

```text
fix(integrity): restore truthful roadmap and run manifest

feat(source): add cninfo announcements provider

feat(source): add financial statements provider

feat(research): wire analyst briefs into claim and thesis pipeline

feat(ai): add evidence-grounded llm provider

feat(scheduler): add continuous task runner

feat(ui): complete research workspace

test(e2e): add live multi-instrument research flow
```

---

# 40. Claude 直接执行指令

现在开始：

1. 读取现有 `TASK.md / AGENTS.md / CLAUDE.md / PLAN.md / STATUS.md / ROADMAP.md`；
2. 检查当前真实代码；
3. 将本整改任务纳入 PLAN / STATUS；
4. 从 `R0 — State & Integrity Repair` 开始；
5. 不要重新输出新的整改建议；
6. 不要等待用户逐项确认；
7. 不要提前做 R4 UI 美化；
8. 普通错误自行修复；
9. 每阶段 Build/Test/Live Verify；
10. 通过 DoD 后继续下一阶段；
11. 上下文即将结束时更新 STATUS / PLAN / Git checkpoint；
12. 下一次会话从 STATUS Next Action 继续；
13. 只有 R0～R5 和全部最终验收通过后，才允许重新声明项目完成。

最重要的整改目标：

> **把现有“Research OS Kernel”升级成真正能持续进行 A 股真实投研的完整系统。**

最终判断标准不是：

```text
对象有没有
API 有没有
页面有没有
```

而是：

```text
真实数据
→ 真实研究
→ 真实报告
→ 真实审查
→ 真实定时任务
→ 真实增量研究
→ 真实预测验证
```

完整跑通。
