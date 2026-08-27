# A-Share Research OS 最终实施任务书

**版本：V5 Final / Canonical Repository Edition**  
**目标执行器：Claude Code / Claude Coding Agent**  
**目标：自动连续交付完整可运行系统**

---

# 0. 文档用途与正式仓库

本文档是 **A-Share Research OS** 的最终建设方案和 Claude 自动实施任务书。

它同时定义：

- 最终产品目标；
- 主工程与上游项目的边界；
- Research Core 领域模型；
- A 股数据与研究要求；
- 中英双语；
- System / Light / Dark 三态主题；
- 报告生成、问答、审查、修订和版本化；
- Timeline / Research Graph；
- 定时研究；
- Prediction / Validation / Regression；
- Quant 能力；
- UI / API / Worker / Deployment；
- 测试与最终验收；
- Claude Code 的连续执行规则。

本文件不是概念方案。

Claude 的最终任务是：

> **在正式仓库内持续编写真实代码、运行真实测试、使用真实数据验证，并最终交付可以部署和使用的完整系统。**

---

## 0.1 唯一正式仓库

本项目唯一 Canonical Repository：

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

Repository：

```text
hyperhaohao/A-Share-Research-OS
```

默认正式分支：

```text
main
```

所有最终交付物必须进入该仓库，包括：

```text
source code
frontend
backend
workers
database migrations
tests
documentation
deployment
Docker
CI configuration
```

禁止另建另一个正式产品仓库。

禁止把 TideTrading、OpenAlpha CN、觀瀾、Qlib、TradingAgents 等候选项目的 Fork 作为最终产品仓库。

---

## 0.2 上游项目工作区

Claude 可以在正式仓库之外建立临时 upstream workspace：

```text
workspace/
├── A-Share-Research-OS/       # 唯一正式仓库
│
└── upstreams/                 # 不提交进正式仓库
    ├── TideTrading/
    ├── openalpha-cn/
    ├── financial-analyst/
    ├── qlib/
    ├── RD-Agent/
    └── TradingAgents/
```

这些上游仓库仅用于：

```text
source audit
architecture comparison
license review
API/interface study
allowed code reuse
Adapter development
UI/UX reference
```

禁止：

```text
把 upstreams 整体复制进正式仓库
把完整 Git 历史嵌套进正式仓库
长期在上游 Fork 开发后再整体覆盖正式仓库
```

---

## 0.3 上游能力采用等级

M0 对每一个候选项目必须给出明确结论：

```text
ADOPT
ADAPT
REFERENCE_ONLY
REJECT
```

定义：

### ADOPT

成熟能力可以直接作为正式系统的一部分使用，并通过稳定边界与 Research Core 连接。

### ADAPT

能力有价值，但必须包装、裁剪或重构后使用。

### REFERENCE_ONLY

只借鉴设计、算法、UI、数据模型或工程思想，不直接形成运行时依赖。

### REJECT

当前不采用，并记录理由。

最终系统允许不同层分别选择最佳实现。

不要求：

> 一个项目解决全部问题。

---

## 0.4 主工程选择原则

当前首选主工程候选：

```text
TideTrading
```

原因是它在通用 A 股场景下具备较完整的：

```text
market data
finance tools
agent/swarm
quant/backtest
FastAPI
React/Vite/TypeScript
SSE
Docker
```

但这只是 **M0 的优先审计对象，不是预设结论**。

Claude 必须基于真实源码、测试、许可证和运行结果重新评分。

如果综合评估显示其他实现更优：

> 应采用客观最优方案。

如果没有任何候选适合作为整体主工程：

> 在 `hyperhaohao/A-Share-Research-OS` 内建立最小自有基线，并通过 Adapter 复用各上游的成熟能力。

---

## 0.5 正式仓库初始化规则

正式仓库从最小必要文件开始：

```text
AGENTS.md
CLAUDE.md
ROADMAP.md
docs/A-Share-Research-OS-最终实施任务书.md
```

之后目录只能随真实 Milestone 生长。

禁止 M0 一次性预创建：

```text
backend/
frontend/
services/
repositories/
agents/
quant/
workers/
几十个空模块
```

只有当前 Milestone 真正需要时才创建。

---

## 0.6 Git 开发纪律

主要 Milestone 应形成清晰的 Git 边界。

推荐：

```text
main
│
├── milestone/m0-upstream-audit
├── milestone/m1-foundation
├── milestone/m2-instrument
├── milestone/m3-source-layer
└── ...
```

如果实际执行环境更适合直接连续提交到工作分支，也允许采用等价策略。

要求：

- commit 边界清晰；
- 不覆盖用户已有修改；
- 一个主要 Milestone 的代码、测试、Migration 和文档尽量同一阶段闭环；
- Milestone 通过 DoD 后再合并/标记完成。

推荐 Commit Message：

```text
feat(instrument): add unified A-share instrument resolution
feat(source): add production market source adapter
feat(evidence): add PIT-aware evidence snapshots
feat(research): add evidence-backed claims and theses
feat(report): add versioned bilingual research reports
feat(ui): add bilingual research workspace
feat(theme): add system light and dark appearance
test(pit): block future information leakage
```

避免：

```text
update
fix
changes
complete
misc
```

---

## 0.7 Claude 的最终交付对象

Claude 的工作对象始终是：

```text
hyperhaohao/A-Share-Research-OS
```

不是：

```text
TideTrading fork
TradingAgents fork
OpenAlpha fork
觀瀾 fork
```

最终产品必须拥有自己的：

```text
Research Domain Model
Evidence/PIT contract
ResearchRun
ReportVersion
Prediction/Validation
API contract
UI information architecture
Database migrations
Tests
Deployment
Documentation
```

外部项目可以减少重复建设，但不能定义系统全部内部结构。

---

## 0.8 长时间自主执行状态体系

本项目可能持续数小时并跨多次 Claude 会话。

正式执行必须使用：

```text
TASK.md
PLAN.md
STATUS.md
ROADMAP.md
```

职责：

```text
TASK.md
= 最终不可自行降低的任务契约

PLAN.md
= 可以根据真实实施调整的执行计划

STATUS.md
= 当前执行状态、测试、问题和准确恢复点

ROADMAP.md
= 长期 Milestone 状态
```

Claude 不得依赖当前聊天上下文保存项目状态。

完整长时间执行协议：

```text
docs/01-长时间自主执行协议.md
```

上下文即将结束时必须：

```text
Update STATUS
→ Update PLAN
→ Update ROADMAP
→ Run necessary verification
→ Git Checkpoint
→ Persist Next Action
```

下一次会话从 `STATUS.md` 的 Next Action 继续，而不是重新规划整个项目。

---

# 1. 最终产品定义

建设一个面向 A 股、同时保留扩展其他市场能力的：

> **A-Share Research OS**

它不是单纯的多 Agent 报告生成器，也不是针对某一只股票或某一类事件设计的专用系统。

系统必须平衡支持：

- Fundamental Research；
- Financial Analysis；
- Valuation；
- Market / Technical；
- Capital Flow；
- News / Sentiment；
- Industry / Supply Chain；
- Macro / Policy；
- Corporate Events；
- Quant Research；
- Risk；
- Continuous Monitoring；
- Report Review；
- Prediction Validation。

系统维护的是每个研究标的持续演化的：

> **Research State**

而不是每次重新生成一份互不关联的 Markdown。

---

# 2. 三个核心闭环

## 2.1 Research Loop

```text
Source
→ Evidence
→ Claim
→ Thesis
→ Analysis
→ Debate
→ Scenario
→ Valuation
→ Risk
→ ResearchReport
```

## 2.2 Review Loop

```text
ResearchReport
→ Question / Audit
→ Evidence Refresh
→ Claim Audit
→ RevisionProposal
→ Diff
→ New ReportVersion
```

## 2.3 Learning Loop

```text
Prediction
→ Time
→ Actual Result
→ Validation
→ RegressionReview
→ ResearchExperience
```

---

# 3. 不得以单个股票塑造系统架构

任何单一标的只能作为测试样本，不能决定领域模型。

系统至少要覆盖以下典型研究风格：

```text
大消费
金融
新能源/成长
半导体/科技
周期/资源
高股息
制造业
主题/事件驱动
```

CorporateEvent 是重要研究维度之一，但不是整个 Research Core 的中心。

主领域中心必须是：

```text
Instrument
Source
Evidence
Claim
Thesis
ResearchRun
ResearchReport
Prediction
Validation
```

---

# 4. 候选项目的客观定位

Claude 必须在 M0 源码审计后做最终采用决定。

## 4.1 TideTrading — 首选主工程候选

当前优先评估作为主工程基线，因为其目标与本系统最接近：

- A 股 / 港股原生；
- Python；
- FastAPI；
- React + Vite + TypeScript；
- 多 Agent / Swarm；
- Finance Skills；
- 数据 Loader / Registry / fallback；
- 回测；
- Session；
- SSE / Web；
- Docker；
- 已存在 i18n 和双主题基础。

如果源码审计通过：

> 直接在现有真实工程上增量建设，不再重新建立另一套 frontend/backend 空架构。

如果审计不通过：

> 使用其通过审计的数据/Agent/量化模块，通过 Adapter 接入最小自有 Research Core。

---

## 4.2 OpenAlpha CN — Evidence/PIT 参考

重点吸收：

- Evidence；
- 四时钟 PIT；
- EvidenceSnapshot；
- RunManifest；
- Replay；
- 可追溯；
- 可复现；
- 明确失败语义。

不要求整个项目成为主工程。

---

## 4.3 觀瀾 — UI/UX 第一参考

重点参考：

- 中文投研工作台的信息密度；
- 总控 Copilot；
- 对话研报；
- Evidence citation；
- 产业链视图；
- Research Graph；
- 经验卡；
- 缺失数据显式显示。

不把 browser local state 或个人数据目录作为服务器事实源。

---

## 4.4 Qlib — 专业 QuantEngine

如果主工程现有量化不足，再接 Qlib。

用于：

- 因子；
- Dataset；
- ML model；
- Prediction；
- Backtest；
- Benchmark；
- Portfolio；
- 中国市场量化研究。

不把 Qlib 当 Research Workspace。

---

## 4.5 RD-Agent — 后期可选

仅用于成熟后的：

```text
Hypothesis
→ Experiment
→ Evaluation
→ Feedback
```

禁止基础系统还没稳定就优先接入。

---

## 4.6 TradingAgents — 可选 ResearchEngine

不再是主底座。

后期若其分析师/辩论能力有增量价值，通过 Adapter 接入。

---

# 5. 最终技术原则

默认：

## Backend

```text
Python 3.11+
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
```

若主工程已有成熟等价实现，优先复用。

## Persistence

生产默认：

```text
PostgreSQL
```

任务/缓存按实际规模：

```text
Redis
```

轻量开发允许 SQLite。

## Async Jobs

先复用主工程已有机制。

只有现有机制不能满足时，再选择：

```text
RQ / Dramatiq / Celery
```

不要同时维护两套 Job Queue。

## Scheduler

调度器只负责“什么时候执行”。

业务逻辑必须是可独立测试的函数。

## Frontend

优先在通过 M0 审计的 TideTrading React 工程上演进：

```text
React
TypeScript
Vite
```

状态：

```text
TanStack Query：Server State
Zustand：UI/客户端临时状态
```

不得用 Zustand/localStorage 当研究事实数据库。

图表优先：

```text
ECharts
```

Research Graph：

```text
React Flow
```

组件体系优先复用现有，如需要统一企业组件再评估 Ant Design。

禁止为了“重新架构”同时引入多套 UI 框架。

---

# 6. 中英双语是一级能力

系统从 M1 起必须原生支持：

```text
zh-CN
en-US
```

不是项目完成后再补翻译。

---

# 7. UI i18n

推荐使用主工程已有 i18n 方案；若没有成熟实现，使用：

```text
i18next
react-i18next
```

所有用户可见字符串必须进入语言资源。

禁止：

```tsx
<Button>开始研究</Button>
```

长期硬编码。

应该：

```text
t("research.start")
```

---

# 8. 语言选择

支持：

```text
system
zh-CN
en-US
```

其中语言默认可以跟随浏览器/系统语言：

- `zh*` → `zh-CN`
- 其他 → `en-US`

允许用户手动覆盖。

手动选择可以存入 localStorage，因为它是 UI Preference，不是研究事实。

---

# 9. 后端与 i18n

后端核心状态不要把中文字符串作为协议。

例如不要只返回：

```json
{"status": "研究完成"}
```

应该：

```json
{
  "status": "completed",
  "message_code": "research.completed"
}
```

前端本地化。

真正需要后端生成的人类文本，例如 ResearchReport，可以通过：

```text
language = zh-CN | en-US
```

控制。

---

# 10. 双语报告

ResearchReport 必须支持：

```text
中文报告
英文报告
```

可以基于同一个结构化 Research State 生成两种语言。

不能分别独立运行两次研究后产生事实不一致。

正确方式：

```text
同一个 EvidenceSnapshot
同一个 Claim/Thesis/Valuation
        ↓
Chinese Renderer
English Renderer
```

数字、日期、估值等结构化事实共享。

---

# 11. Evidence 翻译原则

证据必须保留：

```text
original_title
original_excerpt
original_language
```

可选：

```text
translated_title
translated_excerpt
```

但：

> 原始 Evidence 永远不能被翻译文本覆盖。

报告引用弹窗必须可以查看原文。

对中文公告生成英文报告时：

- 英文报告可以使用翻译后的摘要；
- Citation 必须仍指向中文原文；
- 明确标记 `Translated summary`。

---

# 12. Light / Dark / System 三态主题

必须支持：

```text
system
light
dark
```

默认：

```text
system
```

---

# 13. System Theme 行为

必须监听：

```css
prefers-color-scheme
```

当 preference = `system`：

- Windows/macOS/Linux 系统主题变化后；
- UI 无刷新或最小更新自动切换。

当用户选择 light/dark：

- 覆盖系统；
- 持久化用户 UI Preference。

---

# 14. Design Tokens

颜色不能散落硬编码。

至少建立：

```text
--color-bg
--color-bg-elevated
--color-surface
--color-border
--color-text
--color-text-secondary
--color-positive
--color-negative
--color-warning
--color-info
--color-accent
--shadow
```

Light / Dark 各自定义 token。

---

# 15. A 股红绿语义

颜色语义必须与视觉主题解耦。

A 股默认：

```text
上涨 = 红
下跌 = 绿
```

但需要支持可配置：

```text
CN convention
International convention
```

第一版可以默认 CN。

不得把“红色”同时承担：

```text
上涨
错误
危险
删除
```

所有语义。

---

# 16. 图表主题

ECharts 等必须根据 Theme Context 重新应用：

```text
background
axis
grid
tooltip
legend
positive/negative
highlight
```

不得出现：

> 页面变黑了，但图表还是白底黑字。

---

# 17. PDF / Export Theme

Web 报告支持当前主题。

PDF 默认：

```text
light
```

保证打印、存档与审阅稳定。

允许高级选项：

```text
light / dark
```

但导出主题不能改变报告内容和 EvidenceSnapshot。

---

# 18. Research Core

无论底座选择如何，最终领域模型必须稳定。

---

# 19. InstrumentProfile

至少：

```text
instrument_id
market
code
exchange
name
aliases
currency
industry
sector
concept_tags
listed_status
market_cap
data_availability
created_at
updated_at
```

接口必须能通过代码或名称解析。

不得依赖 UI Session 保存股票名字。

---

# 20. Source Layer

统一 Source Adapter。

至少按能力提供：

```text
instrument
market_data
announcements
financials
news
capital_flow
industry
macro
research
corporate_actions
```

不要强迫每个 Provider 实现所有能力。

采用 capability-based adapter。

---

# 21. SourceResult

所有 Source 调用必须明确：

```text
source
capability
status
data
as_of
attempted_at
error_type
retryable
metadata
```

区分：

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

禁止失败伪装为空成功。

---

# 22. EvidenceRecord

至少：

```text
evidence_id
instrument_id

evidence_type
title
summary
excerpt

source
source_type
source_url
source_document_id

authority_level
fact_status

event_time
available_time
ingested_time
revision_time

confidence

content_hash
metadata
```

---

# 23. Point-in-Time 四时钟

必须：

```text
event_time
available_time
ingested_time
revision_time
```

历史研究强制：

```text
available_time <= ResearchRun.as_of_time
```

任何违反 PIT 的数据不能进入 EvidenceSnapshot。

---

# 24. EvidenceSnapshot

正式研究冻结不可变 Snapshot：

```text
snapshot_id
instrument_id
as_of_time
evidence_ids
content_hash
created_at
```

历史快照不能因为后来数据修订而变化。

---

# 25. authority_level

统一枚举，不以具体股票事件为中心。

建议：

```text
A1 primary_regulatory_or_company_disclosure
A2 statutory_disclosure_platform
B1 official_company_or_government
B2 major_financial_media
C1 professional_research
C2 secondary_media
D  rumor_or_unverified
```

---

# 26. fact_status

至少：

```text
confirmed_fact
official_disclosure
regulatory_document
management_statement
media_report
market_expectation
analyst_inference
rumor
```

---

# 27. Research Domain

## CorporateEvent

只是通用研究对象之一。

支持但不限于：

```text
earnings
guidance
dividend
buyback
shareholding_change
financing
M&A
restructuring
contract
litigation
regulation
governance
product
capacity
industry_event
corporate_action
```

不要让某一类事件决定整个数据模型。

---

# 28. Claim

```text
claim_id
statement
claim_type
supporting_evidence_refs
opposing_evidence_refs
fact_status
confidence
status
```

---

# 29. InvestmentThesis

```text
thesis_id
title
description
supporting_claims
opposing_claims
confidence
catalysts
risks
trigger_conditions
invalidate_conditions
status
```

---

# 30. AnalystBrief

统一约束 Agent：

```text
analyst_type
conclusions
claim_refs
evidence_refs
missing_data
confidence
key_questions
risks
```

Agent 默认从 EvidenceSnapshot 获取事实。

缺失：

```text
missing_data
→ ResearchRequest
→ EvidenceCollector
```

不得让不同 Agent 私自形成彼此冲突的事实库。

---

# 31. Quality Gates

必须是真正业务 Gate，不是字数检查。

## EvidenceQualityGate

- PIT；
- 来源；
- 新鲜度；
- 关键数据覆盖；
- 冲突；
- Source failures。

## AnalysisQualityGate

- Claim 是否有证据；
- 是否事实越界；
- 是否事实/预测混用；
- conflicting evidence 是否说明；
- missing_data 是否披露。

## FinalReportQualityGate

- 无效 Citation；
- 不存在 Evidence；
- Unsupported Claim；
- 估值无假设；
- 风险缺失；
- 数据质量未披露；
- Disclaimer 缺失。

FAIL 不得发布正式报告。

---

# 32. Fundamental Research

至少覆盖：

```text
business model
revenue/profit structure
growth
margin
cash flow
balance sheet
ROE/ROIC
earnings quality
capital expenditure
shareholder return
industry position
competitive advantage
management/governance
```

---

# 33. Market / Capital Research

至少覆盖可用数据中的：

```text
price/volume
trend
volatility
turnover
capital flow
northbound/other available flows
margin financing
block trades
share unlocks
major holders
technical state
```

没有数据必须显示无数据，而不是推测。

---

# 34. Industry / Macro

至少支持：

```text
industry classification
industry relative performance
supply chain
peer comparison
policy
rates
FX
commodities
macro factors
```

具体能力按 Source availability 分级。

---

# 35. Debate

Bull/Bear 围绕 Thesis 和已存在 Claim。

不能：

> Bull 为了说服 Bear 自己创造一条新新闻。

新事实必须先回 EvidenceCollector。

---

# 36. Deterministic Valuation

估值数字必须由可测试代码计算。

支持按适用性：

```text
PE
PB
PS
EV/EBITDA
DCF
DDM
SOTP
NAV
historical percentile
peer comps
```

不是所有公司强行全做。

LLM 负责：

```text
解释
比较
风险说明
```

不负责：

```text
偷偷在自然语言里计算并生成无来源目标价
```

---

# 37. Scenario

至少：

```text
Bear
Base
Bull
```

每个：

```text
probability
assumptions
catalysts
risks
trigger_conditions
valuation
```

概率总和 100%。

---

# 38. ResearchReport

结构化对象至少包含：

```text
metadata
executive_summary
company_overview
business_and_industry
financial_quality
market_and_capital
key_theses
corporate_events
valuation
scenarios
bull_bear
risks
invalidate_conditions
prediction
data_quality
source_manifest
disclaimer
```

---

# 39. ReportCompiler

单一结构化 ResearchReport：

```text
→ Web
→ Markdown
→ HTML
→ PDF
```

中文和英文都来自同一 ResearchReport 数据。

---

# 40. ResearchRun / RunManifest

ResearchRun：

```text
run_id
instrument_id
as_of_time
run_type
language
status
evidence_snapshot_id
started_at
finished_at
cost
```

RunManifest：

```text
code_commit
workflow_version
config_hash
provider_versions
model
model_parameters
prompt_versions
random_seed
evidence_snapshot_id
environment
```

---

# 41. ReportVersion

禁止覆盖：

```text
report_id
version
parent_version
research_run_id
created_at
change_reason
changed_sections
research_report
```

同一个 ReportVersion 可拥有不同 language rendering，但不能变成两套不同研究事实。

---

# 42. Report Q&A

## Explain

问题：

> 为什么当前报告有这个判断？

只使用当前：

```text
ReportVersion
EvidenceSnapshot
Claim
Thesis
SourceManifest
```

## Refresh

问题：

> 用最新数据重新检查。

允许执行：

```text
Source Layer
→ New Evidence
→ New Snapshot
→ Impact Analysis
```

两种行为必须在 UI 清晰区分。

---

# 43. Report Audit

可选中：

```text
sentence
paragraph
section
claim
thesis
full report
```

检查：

```text
unsupported
outdated
conflicting
missing evidence
logical leap
numeric inconsistency
```

---

# 44. RevisionProposal

禁止 LLM 直接覆盖 Markdown。

必须：

```text
original
proposed
reason
added_evidence
invalidated_evidence
affected_claims
affected_theses
confidence_change
```

用户接受后创建新 ReportVersion。

---

# 45. Continuous Research

## Monitor

低成本更新事实。

## Delta Research

只重跑受影响内容。

## Full Research

首次、重大变化、定期完整研究、人工触发。

MaterialityJudge：

```text
NO_MATERIAL_CHANGE
DELTA_RESEARCH
FULL_RESEARCH
```

---

# 46. Timeline

统一：

```text
market_event
announcement
financial_release
evidence_added
claim_changed
thesis_changed
research_run
report_version
prediction
validation
```

回答：

> 何时发生了什么？

---

# 47. Research Graph

```text
Source
→ Evidence
→ Event
→ Claim
→ Thesis
→ Report
→ Prediction
→ Validation
```

任意节点支持：

```text
upstream
downstream
```

回答：

> 为什么形成这个结论、它影响了什么、最后是否兑现？

---

# 48. ResearchTask

至少：

```text
task_id
instrument_id
task_type
schedule
research_level
filters
enabled
last_run_at
next_run_at
status
```

支持：

```text
monitor
periodic_full_research
event_trigger
prediction_validation
```

---

# 49. Worker / Scheduler

核心业务函数必须可单独运行：

```text
run_monitor
run_delta_research
run_full_research
validate_prediction
```

Scheduler 不能包含研究实现。

必须支持：

```text
retry
idempotency
restart recovery
concurrency control
failure visibility
```

---

# 50. Prediction

```text
prediction_id
instrument_id
research_run_id
as_of_time
horizon
benchmark
expected_direction
expected_return_range
expected_excess_return_range
confidence
supporting_thesis
trigger_conditions
invalidate_conditions
```

第一版：

```text
5D
20D
60D
```

创建后不可修改。

---

# 51. Validation

至少：

```text
instrument_return
benchmark_return
excess_return
direction_correct
range_hit
```

长期：

```text
Direction Accuracy
Average Excess Return
Interval Hit Rate
MAE
Brier Score
Calibration
```

---

# 52. RegressionReview

错误归因至少判断：

```text
evidence
claim
thesis
valuation
catalyst
risk
timing
market regime
```

不能只输出“市场环境变化”。

---

# 53. ResearchExperience

验证后形成经验：

```text
experience_id
context
lesson
related_research_type
confidence
supporting_validations
```

第一版只沉淀。

禁止系统自动修改 Prompt。

---

# 54. Quant Strategy

先审计主工程已有：

```text
alpha
factor
backtest
model
optimizer
```

如果足够：

> 不接 Qlib，避免双轨。

如果明确缺少：

> 通过 Qlib Adapter 补齐。

必须有实际业务需求后才创建 Adapter。

---

# 55. Research Workspace UI

UI 第一原则：

> 研究对象优先，Agent 名称其次。

不要把主页面做成多个 Agent Markdown 面板。

---

# 56. 一级导航

至少：

```text
Dashboard
Watchlist
Research
Tasks
Reports
Predictions
Evidence
Settings
```

zh-CN 和 en-US 均完整。

---

# 57. Dashboard

至少：

```text
material changes
watchlist alerts
running research
failed jobs
recent reports
pending reviews
prediction validations
cost
source health
```

---

# 58. Stock Workspace

Header：

```text
name/code
market
industry
price
latest research
research confidence
data quality
```

Tabs：

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

# 59. Overview

优先：

```text
Research Summary
Top Thesis
Top Catalysts
Top Risks
Latest Material Changes
Financial Snapshot
Valuation State
Latest Prediction
Data Quality
```

---

# 60. Research Graph UI

参考觀瀾交互，但领域节点使用本系统模型。

至少：

- zoom/pan；
- node detail；
- upstream/downstream；
- filter by type；
- click → entity detail；
- dark/light 完整适配；
- zh/en labels。

---

# 61. Interactive Report

布局：

```text
左：目录
中：正文
右：Copilot / Audit
```

文本动作：

```text
Explain
Evidence
Audit
Counter Evidence
Refresh
Revalue
Propose Revision
```

双语模式下动作与 UI 全部本地化。

---

# 62. Evidence Citation

点击 Citation：

```text
source
authority
fact status
available time
original title
original excerpt
translated summary if present
URL
related claims
```

不得只显示一个 URL。

---

# 63. Theme UX

Settings：

```text
Appearance:
  System
  Light
  Dark

Language:
  System
  简体中文
  English
```

顶部可提供快捷切换，但 Settings 是完整配置入口。

---

# 64. Responsive

主要目标桌面。

同时：

- 1366×768 可用；
- 1920×1080 良好；
- 超宽屏不无限拉伸正文；
- Tablet 至少可查看；
- 手机提供阅读/监控基本能力，不强求完整 Research Graph 编辑体验。

---

# 65. Accessibility

至少：

- keyboard focus；
- 不仅依靠红/绿区分；
- dark/light 对比度；
- Tooltip 可访问；
- `aria-label`；
- i18n 后按钮宽度不过度截断。

---

# 66. API

最终至少表达以下能力：

```text
instruments
research runs
timeline
research graph
evidence
claims
theses
reports
report ask
report review
report revision
tasks
predictions
validation performance
source health
settings
```

实际 URL 遵循项目现有风格即可。

---

# 67. SSE

研究执行至少推送：

```text
run_started
source_progress
evidence_ready
quality_gate
analyst_progress
valuation_ready
report_ready
run_completed
run_failed
```

前端不得依赖整页轮询刷新。

---

# 68. 数据存储

结构化研究事实进入正式数据库。

原始公告、PDF、HTML 等大对象：

```text
Filesystem / S3-compatible adapter
```

数据库保存：

```text
hash
metadata
location
```

---

# 69. 缓存

不同数据不同 TTL。

例如：

```text
instrument metadata: long
financial statements: long/period-aware
announcement index: medium
news: short
market quote: very short
```

缓存不能破坏 PIT。

---

# 70. 成本

每次 ResearchRun 记录：

```text
LLM calls
input tokens
output tokens
estimated cost
source calls
duration
```

Dashboard 支持查看：

```text
per run
per instrument
monitor vs delta vs full
model
```

---

# 71. 测试矩阵不得依赖单只股票

至少选取多个不同类型 A 股做回归。

建议动态选择当前正常上市且数据可用的：

```text
沪市主板大市值
深市/创业板成长
科创板科技
金融
消费
周期/资源
```

可以维护固定代码 Fixture，但不要让某一个股票的特殊事件进入核心架构假设。

---

# 72. Instrument 回归

至少：

- 上交所主板；
- 深交所主板；
- 创业板；
- 科创板。

验证：

```text
code
name
exchange
market
```

---

# 73. Evidence 回归

测试：

```text
primary source
secondary source
dedup
failure semantics
authority
fact status
```

---

# 74. PIT 强制测试

构造：

```text
available_time > ResearchRun.as_of_time
```

必须保证该 Evidence 不可见。

---

# 75. Traceability Test

随机正式报告关键事实：

```text
Report
→ Thesis
→ Claim
→ Evidence
→ Source
```

必须全链存在。

---

# 76. i18n Test

必须自动检查：

- zh-CN 页面；
- en-US 页面；
- missing key；
- 禁止 key 直接显示；
- 主要页面无硬编码业务文本；
- 中文/英文切换不丢状态；
- Report 两种语言共享同一 Research State。

---

# 77. Theme Test

至少：

```text
light
dark
system-light
system-dark
```

主要页面截图/E2E。

系统主题切换时：

- preference=system 应自动变化；
- manual light/dark 不应被系统变化覆盖。

---

# 78. Revision Test

```text
V1.0
→ review
→ accept
→ V1.1
```

V1.0 仍然存在。

---

# 79. Task Test

至少：

```text
create
enable
disable
execute
retry
idempotency
restart recovery
```

---

# 80. Prediction Test

固定行情 Fixture：

```text
return
benchmark return
excess return
direction
range hit
```

确定性正确。

---

# 81. UI E2E

至少：

```text
切换中文/英文
切换system/light/dark
搜索股票
打开Workspace
查看Evidence
查看Research Graph
打开Report
Ask
Audit
接受Revision
创建Monitor Task
查看Timeline
查看Prediction
```

全部使用真实 API 或稳定测试后端，不允许业务 Mock 冒充 E2E。

---

# 82. Production Deployment

最终至少交付：

```text
docker-compose.yml
.env.example
migration
health checks
frontend
api
worker
scheduler if separate
database
redis if used
```

---

# 83. Backup / Restore

必须写明：

```text
database backup
object/document backup
configuration backup
restore procedure
version compatibility
```

并至少实际演练一次测试环境恢复。

---

# 84. Observability

至少：

```text
structured logs
run_id
instrument_id
task_id
source
node
duration
error code
```

Source health 和 failed jobs 在 UI 可见。

---

# 85. Security

第一版：

- 不连接真实券商自动交易；
- API Key 不入库明文；
- 不在日志打印 secrets；
- 对管理设置有权限边界；
- 公网部署必须显式配置 auth/CORS/trusted hosts；
- Markdown/HTML 输出防 XSS；
- 外部新闻/研报文本按不可信输入处理。

---

# 86. Milestone 总执行顺序

以 `ROADMAP.md` 为唯一状态源。

```text
M0  上游/底座源码审计
M1  工程基线 + i18n + theme
M2  Instrument
M3  Source Layer
M4  Evidence
M5  PIT/Snapshot
M6  Research Domain
M7  Quality
M8  Structured Agents
M9  Debate/Scenario/Risk
M10 Valuation
M11 ResearchReport bilingual
M12 Manifest/Versions
M13 Report Q&A
M14 Audit/Revision
M15 Delta/Materiality
M16 Timeline
M17 Research Graph
M18 Tasks/Scheduler
M19 Prediction/Validation
M20 Regression/Experience
M21 Quant audit
M22 Qlib if needed
M23 Research API/SSE
M24 Workspace
M25 Research visual UI
M26 Interactive Report
M27 Tasks/Prediction UI
M28 E2E/Performance/Cost
M29 Production Delivery
```

---

# 87. Claude 自动连续执行要求

Claude 不得把此任务理解为：

> 一次会话必须胡乱完成所有代码。

正确行为：

1. 从 M0 开始；
2. 完成真实代码；
3. 运行测试；
4. 完成真实验证；
5. 修复失败；
6. 更新 ROADMAP；
7. 自动进入下一阶段；
8. 上下文不足时准确持久化进度；
9. 下一会话从当前 DOING 继续；
10. 直到 M29 全部通过。

---

# 88. M0 的最终选择规则

M0 首先确认当前工作目录确实对应唯一正式仓库：

```text
hyperhaohao/A-Share-Research-OS
```

然后在正式仓库之外获取并审计候选上游。

不是预先认定 TideTrading 一定最好，也不是选择“应该 Fork 谁”。

真正要回答的是：

> **A-Share Research OS 的每一层应该采用、适配或参考哪个成熟实现。**

Claude 必须基于真实源码、实际运行、测试和许可证给出：

```text
ADOPT
ADAPT
REFERENCE_ONLY
REJECT
```

评估指标：

```text
A-share data coverage
engineering completeness
maintainability
license
tests
backend/API
frontend
i18n
theme
agent orchestration
quant/backtest
PIT
evidence provenance
task scheduling
deployment
migration cost
```

如果 TideTrading 综合最优：

> 使用 TideTrading 作为主工程，增量演进。

如果不是：

> 选择综合最优基线，不得因为本任务书的偏好硬选 TideTrading。

---

# 89. 最终验收场景：Research

从 UI 搜索任意正常 A 股标的。

系统：

```text
Instrument
→ Sources
→ EvidenceSnapshot
→ Claims
→ Theses
→ Analysts
→ Scenario
→ Valuation
→ ResearchReport
```

报告有真实 Citation。

---

# 90. 最终验收场景：双语

同一个 ResearchRun：

```text
中文报告
英文报告
```

必须：

- 数字一致；
- Claims/Theses一致；
- Citation 指向同一 Evidence；
- 原始 Evidence 不因翻译改变。

---

# 91. 最终验收场景：主题

用户：

```text
Appearance = System
```

系统 OS 从浅色切到深色：

- Workspace 自动切换；
- Report 自动切换；
- Graph 自动切换；
- Charts 自动切换；
- Dialog/Tooltip/Markdown 自动切换；
- 无明显白块/黑字不可读。

---

# 92. 最终验收场景：报告解释

用户：

> 为什么这份报告认为某项 Thesis 成立？

只能基于当前版本证据解释。

---

# 93. 最终验收场景：重新审查

用户：

> 用最新数据重新审查这一段。

系统：

```text
New Evidence
→ Impact Audit
→ RevisionProposal
→ Diff
```

接受：

```text
V1.0 → V1.1
```

---

# 94. 最终验收场景：Continuous Research

定时 Monitor：

无重大变化：

```text
NO_MATERIAL_CHANGE
```

不运行完整研究。

重大变化：

```text
DELTA_RESEARCH
```

必要时：

```text
FULL_RESEARCH
```

---

# 95. 最终验收场景：Timeline + Graph

Timeline 能回答：

> 什么时候发生了什么？

Research Graph 能回答：

> 这条结论来自哪里，后来影响了什么？

---

# 96. 最终验收场景：Prediction

ResearchRun 创建预测。

到期：

```text
Validation
```

系统长期统计准确性，不允许事后改预测。

---

# 97. 最终验收场景：Quant

如果 M21 判断需要 Qlib：

至少一个真实 A 股数据集完成：

```text
Factor/Feature
→ Model
→ Backtest
→ Metrics
```

结果可在 Workspace 查看。

如果现有量化已经满足：

M22 可以经审计后标记：

```text
NOT_REQUIRED
```

并写明理由，不能为了 checklist 强行引入 Qlib。

---

# 98. 最终交付内容

最终交付必须全部存在于唯一正式仓库：

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

最终仓库必须包含真实可用：

```text
README.md
AGENTS.md
CLAUDE.md
ROADMAP.md
.env.example
docker-compose.yml

docs/
  architecture.md
  data-model.md
  upstream-evaluation.md
  source-layer.md
  research-workflow.md
  evidence-and-pit.md
  report-and-review.md
  i18n.md
  theming.md
  tasks.md
  quant.md
  testing.md
  deployment.md
  backup-restore.md
  migration.md
  known-limitations.md
```

文档必须描述实际系统。

---

# 99. 最终完成判定

全部满足后才能宣布交付：

- [ ] 主工程选择经过源码审计，而非主观预设
- [ ] A 股多类型标的可解析
- [ ] Source fallback 可用
- [ ] Evidence 可追溯
- [ ] PIT 强制执行
- [ ] EvidenceSnapshot 不可变
- [ ] Claim / Thesis 可追溯
- [ ] QualityGate 真正拦截
- [ ] Agent 受 Evidence 约束
- [ ] Valuation 数字由确定性代码计算
- [ ] 中文 UI 完整
- [ ] 英文 UI 完整
- [ ] 中文报告可用
- [ ] 英文报告可用
- [ ] system/light/dark 完整
- [ ] 系统主题实时跟随
- [ ] Report Q&A 可用
- [ ] Audit / Revision / Version 可用
- [ ] Delta Research 可用
- [ ] Timeline 可用
- [ ] Research Graph 可用
- [ ] Scheduler/Worker 可用
- [ ] Prediction/Validation 可用
- [ ] Quant 能力经过客观评估
- [ ] UI 全部使用真实业务数据
- [ ] PDF/Markdown/HTML 可用
- [ ] 自动测试通过
- [ ] 多标的 E2E 通过
- [ ] Docker Compose 可部署
- [ ] 备份恢复实际演练
- [ ] 无业务 Mock 冒充实现
- [ ] 无大量未来空架构
- [ ] 文档与实现一致

---

# 100. Claude 启动指令

实际开始开发时，Claude 必须按以下顺序执行：

```text
1. 确认当前正式仓库：
   https://github.com/hyperhaohao/A-Share-Research-OS.git

2. 阅读：
   AGENTS.md
   CLAUDE.md
   ROADMAP.md
   docs/A-Share-Research-OS-最终实施任务书.md

3. 从 ROADMAP 当前 DOING 的 M0 开始。

4. 在正式仓库之外获取候选 upstream：
   TideTrading
   OpenAlpha CN
   觀瀾
   Qlib
   RD-Agent
   TradingAgents

5. 实际源码审计、运行、测试并检查 LICENSE。

6. 为每个候选给出：
   ADOPT / ADAPT / REFERENCE_ONLY / REJECT

7. 客观确定 A-Share Research OS 各层实现。
```

必须遵守：

```text
不要重新生成方案。
不要先创建未来空架构。
不要把任一上游 Fork 直接视为最终产品。
不要因为任务书提到 TideTrading 就跳过 M0。
不要使用 Mock 宣称业务完成。
```

每个 Milestone：

```text
理解真实现状
→ 最小设计
→ 编码
→ 自动测试
→ 真实数据验证
→ 修复
→ 更新文档
→ 更新 ROADMAP
→ 继续下一 Milestone
```

除明确 `BLOCKED` 外连续推进。

如果 Claude 单次上下文不足：

```text
先准确更新 ROADMAP
记录当前 commit / branch
记录已完成能力
记录测试命令与结果
记录真实验证结果
记录未解决问题
设置准确的下一步
```

下一次 Claude 会话重新读取：

```text
AGENTS.md
CLAUDE.md
ROADMAP.md
```

并从当前 `DOING` 继续。

最终只有在 M0～M29 以及本文全部最终验收条件通过后，才允许声明：

> **A-Share Research OS 已完成最终交付。**
