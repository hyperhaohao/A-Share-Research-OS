# A-Share Research OS 最终产品与架构修改方案
## Research · Validation · Decision Operating System

> 目标仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 参考产品：`jesson-hh/financial-analyst`（观澜）
>
> 本方案是后续开发的**产品与架构总纲**。
>
> 它不是把观澜页面复制过来，也不是再新增一批互不相干的功能页。
>
> 最终目标：
>
> > **在现有 Evidence / PIT / Claim / Thesis / ReportVersion / ResearchTask / Prediction 内核之上，吸收观澜完整的研究生产体系，形成“研究 → 提炼 → 验证 → 筛选 → 策略 → 盯盘 → 决策 → 复盘 → 经验回灌”的 A 股 AI 投研操作系统。**

---

# 0. 最终产品定位

当前项目名称继续保持：

```text
A-Share Research OS
```

中文产品名建议：

```text
A股智能投研操作系统
```

产品副标题建议：

```text
研究 · 验证 · 决策
```

英文定位：

```text
A-Share Research, Validation & Decision OS
```

不建议改成 Trading System，因为系统核心仍然是 Research First、Evidence First 和 Decision Support，而不是券商交易终端。

---

# 1. 最重要的产品闭环

最终所有模块必须围绕下面这一条链工作：

```text
自然语言研究
        ↓
深度研报
        ↓
研究经验提炼
        ↓
经验卡
        ↓
研究工作流验证
        ↓
智能选股验证适用范围
        ↓
策略实验室装配
        ↓
策略盯盘
        ↓
观察 / 决策
        ↓
Prediction
        ↓
Validation
        ↓
复盘
        ↓
经验卡新版本
        ↓
下一轮研究
```

同时，全链必须满足：

```text
Source
→ Evidence
→ Claim
→ Thesis
→ ReportVersion
→ ExperienceCard
→ WorkflowRun
→ ScreeningRun
→ StrategyVersion
→ Observation
→ Decision
→ Prediction
→ Validation
→ Review
```

任何一步都能查看来源、查看上游、查看下游，并带上下文进入对应模块。

---

# 2. 不直接照搬观澜名称

观澜的：

```text
帷幄
河图
全球坐标
校场
席位
落子
```

具有明显的观澜品牌语言。

我们的系统应吸收功能，但重新命名成更加清晰、稳定、企业级、可扩展、第一次使用就能理解的名称。

---

# 3. 最终模块命名映射

| 观澜名称 | A-Share Research OS 正式名称 | 英文内部名 | 功能本质 |
|---|---|---|---|
| 帷幄 | **AI 研究中枢** | Research Command Center | 全局对话、计划、执行、产物总控 |
| 对话 · 研报 | **深度研究 / 研究报告** | Deep Research / Reports | 对话研究、结构化研报、版本化 |
| 河图 | **产业研究地图** | Industry Research Map | 产业链、公司、上下游、驱动关系 |
| 全球坐标 | **全球宏观视图** | Global Context | 全球市场、宏观、商品、汇率映射 |
| 经验卡 | **研究经验卡** | Experience Card | 方法论提炼、验证、沉淀 |
| AI 工作流 | **研究验证工作流** | Research Workflow | DAG 验证研究假设/因子/模型 |
| 选股 | **智能选股** | Screening | 多维条件、经验、因子、模型筛选 |
| 席位 · 校场 | **策略实验室** | Strategy Lab | 策略装配、回测、跨标验证 |
| 席位 · 盯盘 | **策略盯盘** | Strategy Monitor | 后台监控、观察、信号、决策 |
| 落子 | **研究决策** | Decision | 有依据的决策记录，不等同实盘下单 |
| 研究图谱 | **全库研究图谱** | Research Knowledge Graph | 所有研究物料溯源总览 |
| 复盘 | **研究复盘** | Research Review | 预测/决策/策略结果回顾 |
| 自选 | **关注池** | Watchlist | 用户关注标的和研究状态 |
| 调度任务 | **持续研究** | Continuous Research | 定期监测、增量研究、完整重研 |

---

# 4. 最终一级导航

不要把十几个模块横向全部铺在顶栏。

推荐：

```text
AI 研究中枢

研究
├─ 关注池
├─ 深度研究
├─ 报告库
├─ 产业研究地图
└─ 全球宏观视图

验证
├─ 研究经验卡
├─ 研究验证工作流
└─ 智能选股

策略
├─ 策略实验室
├─ 策略盯盘
└─ 预测与复盘

知识
└─ 全库研究图谱

系统
├─ 持续研究
├─ 数据源状态
└─ 设置
```

`Instrument Workspace` 不作为一级导航，它是 Search、Watchlist、Report、Screening、Strategy、Graph 进入具体股票后的统一上下文工作台。

---

# 5. 整体架构必须分成 5 层

```text
┌───────────────────────────────────────────┐
│  1. Experience Layer                     │
│  React UI / Command Center / Workspaces  │
├───────────────────────────────────────────┤
│  2. Application Layer                    │
│  Orchestration / Handoff / Workflow      │
├───────────────────────────────────────────┤
│  3. Domain Layer                         │
│  Research / Experience / Screen / Strategy│
├───────────────────────────────────────────┤
│  4. Research Foundation                  │
│  Instrument / Evidence / PIT / Artifact  │
├───────────────────────────────────────────┤
│  5. Infrastructure                       │
│  Source / LLM / DB / Scheduler / SSE     │
└───────────────────────────────────────────┘
```

---

# 6. Experience Layer

职责只负责展示、交互、导航、上下文和状态投影，不得把核心业务规则放到 JSX。

主要页面：

```text
ResearchCommandCenterPage
WatchlistPage
InstrumentWorkspacePage
ReportsPage
IndustryMapPage
GlobalContextPage
ExperienceCardsPage
WorkflowStudioPage
ScreeningPage
StrategyLabPage
StrategyMonitorPage
PredictionReviewPage
ResearchGraphPage
ContinuousResearchPage
SettingsPage
```

---

# 7. Application Layer

这是未来最重要的新增层。

不要让页面直接拼各种 Repository。

建立：

```text
ResearchCommandService
ResearchRunService
ArtifactService
HandoffService
ExperienceCardService
WorkflowExecutionService
ScreeningService
StrategyService
MonitoringService
ReviewService
```

负责编排多个领域对象、执行跨模块动作、生成 Artifact、发布事件、维护上下文。

---

# 8. Domain Layer

分成八个明确域：

```text
Research Domain
Industry & Macro Domain
Experience Domain
Workflow Domain
Screening Domain
Strategy Domain
Prediction & Review Domain
Knowledge Graph Domain
```

不能全部塞进 `services/`。

---

# 9. Research Domain —— 保留现有核心

继续以现有对象为真数据：

```text
Instrument
Source
Evidence
EvidenceSnapshot
CorporateEvent
Claim
Thesis
AnalystBrief
Debate
Scenario
Valuation
Risk
ResearchRun
ResearchReport
ReportVersion
RevisionProposal
```

原则：Research Domain 不因为观澜功能扩展而重写。

---

# 10. Industry & Macro Domain

## 产业研究地图

回答：

```text
公司在产业体系中的位置是什么？
谁影响谁？
哪些驱动正在变化？
```

核心对象：

```text
IndustryMap
IndustryMapVersion
IndustryNode
IndustryEdge
IndustryDriver
IndustryNarrative
IndustrySnapshot
```

Node Type：

```text
company
business
product
material
technology
customer
supplier
competitor
commodity
policy
region
theme
```

Edge：

```text
supplies
purchases
competes_with
owns
controls
benefits_from
depends_on
substitutes
price_transmission
policy_impacts
```

所有 LLM 抽取关系必须带 Evidence refs。未确认关系标记 `inferred`，不能写成 confirmed。

---

# 11. 全球宏观视图

回答：

```text
这只股票当前处于怎样的全球市场环境？
```

核心对象：

```text
GlobalContextSnapshot
MacroIndicator
MacroTheme
MacroRelation
```

包含：

```text
利率
汇率
美元指数
国债
全球指数
商品
能源
贵金属
工业金属
产业关键原料
风险偏好
政策周期
```

关键约束：`GlobalContextSnapshot.as_of` 必须进入 PIT。报告历史回放不能读取当前宏观值。

---

# 12. Experience Domain —— 研究经验卡

经验卡不是笔记。

定义：

```text
ExperienceCard
ExperienceCardVersion
ExperienceValidation
ExperienceCase
```

核心字段：

```text
card_id
version
title
category
statement
mechanism
applicable_conditions
invalid_conditions
source_report_ids
source_claim_ids
source_evidence_ids
source_review_ids
quant_expression
workflow_id
confidence
verdict
success_cases
failure_cases
created_at
updated_at
```

状态：

```text
DRAFT
REFINED
VALIDATING
APPROVED
DOUBTFUL
REJECTED
SUPERSEDED
```

---

# 13. 经验卡标准流程

```text
原
↓
从 Report / Review / Conversation 提取原始经验

炼
↓
LLM 结构化为机制、适用条件、失效条件

验
↓
Workflow / Historical Case / Quant Backtest

用
↓
批准后进入筛选、策略实验室、AI研究
```

即：

```text
原 → 炼 → 验 → 用
```

但增加版本、Evidence、PIT 和 Validation。

---

# 14. 经验卡不强制全部量化

经验分：

```text
Quantifiable
Semi-Quantifiable
Qualitative
```

例如：

```text
量价突破
→ 可以直接因子回测

央企资产整合
→ 事件分类 + case study

管理层资本配置改善
→ 定性 + 财务后验验证
```

禁止为了“能回测”强行编造 DSL。

---

# 15. Workflow Domain —— 研究验证工作流

不要设计成纯 Quant 页面。

正式定位：**验证任何研究假设的可视化 DAG。**

核心：

```text
WorkflowDefinition
WorkflowVersion
WorkflowNode
WorkflowEdge
WorkflowRun
WorkflowNodeRun
WorkflowOutput
```

---

# 16. Workflow Node 分六类

## 数据节点

```text
MarketData
FinancialData
Announcement
News
CapitalFlow
Industry
Macro
Universe
EvidenceQuery
```

## Research 节点

```text
EvidenceFilter
EventClassifier
ClaimSelector
ThesisSelector
ExperienceCard
LLMReasoning
```

## Quant 节点

```text
Formula
Factor
FeatureEngineering
PCA
Model
FactorCompose
Portfolio
```

## Validation 节点

```text
IC
Backtest
CaseStudy
PredictionValidation
Sensitivity
ScenarioTest
```

## Selection 节点

```text
UniverseFilter
Score
Rank
TopN
Constraint
```

## 输出节点

```text
ReportArtifact
ExperienceCardArtifact
ScreeningArtifact
StrategyArtifact
PredictionArtifact
```

---

# 17. Workflow 必须是强类型 DAG

不要：

```text
任意 JSON → 任意 JSON
```

每个 NodeSpec 定义：

```text
input_types
output_types
config_schema
executor
deterministic
pit_requirement
```

Workflow Build 阶段就检查类型兼容。

---

# 18. WorkflowRun 必须固定 Research Context

每次 Run 固定：

```text
as_of_time
instrument/universe
snapshot ids
workflow_version
code_commit
config_hash
random_seed
model info
```

保证历史 WorkflowRun 可解释和可复现。

---

# 19. Screening Domain —— 智能选股

选股不是单纯条件过滤器。

核心对象：

```text
ScreenDefinition
ScreenVersion
ScreeningRun
ScreeningCandidate
ScreeningExplanation
```

可使用：

```text
Financial Metrics
Valuation
Factors
Experience Cards
Events
Industry
Macro
Capital Flow
Thesis
Model Score
```

---

# 20. 每个候选必须 Why Selected

`ScreeningCandidate`：

```text
instrument_id
rank
score
factor_scores
matched_rules
experience_card_refs
event_refs
claim_refs
evidence_refs
explanation
risks
```

用户必须看到为什么选中、为什么没选中，而不是只有 Score。

---

# 21. Strategy Domain —— 策略实验室

不使用观澜“席位 / 校场”作为正式名称。

正式：

```text
策略实验室
```

核心对象：

```text
StrategyDefinition
StrategyVersion
StrategyComponent
StrategyBacktestRun
StrategyValidation
```

Strategy 包含：

```text
name
philosophy
universe
experience_cards
workflow_refs
screen_refs
entry_policy
exit_policy
risk_policy
position_policy
monitor_policy
decision_policy
```

---

# 22. 策略实验室用途

允许用户把经验卡、选股逻辑、因子、事件规则、风险规则组成一个可版本化策略，然后跨股票、跨时间、跨市场状态验证。

必须真实显示失败，例如收益 -5.8% 就显示 -5.8%。

---

# 23. 策略盯盘

正式名称：

```text
策略盯盘
```

不是简单行情看板。

核心对象：

```text
MonitorDefinition
MonitorRun
Observation
Signal
DecisionRecord
```

后台由 Scheduler Worker 运行，不是页面打开才工作。

---

# 24. Observation 与 Decision 必须分开

```text
Observation
= 系统观察到什么

Signal
= 策略规则产生什么信号

Decision
= 最终研究决策是什么
```

例如：

```text
Observation:
新集团公告

Signal:
资产整合条件增强

Decision:
继续观察
```

不能把技术指标直接冒充 AI Decision。

---

# 25. 当前不接真实券商下单

正式定义：

```text
Decision Support
Paper Decision
Research Decision
```

不定义 `TradeExecution`，除非以后单独立项。

---

# 26. Prediction & Review Domain

继续使用：

```text
Prediction
Validation
RegressionReview
```

新增关系：

```text
Decision → Prediction
ExperienceCard → Prediction
StrategyVersion → Prediction
```

最终：

```text
Prediction
→ FinalValidation
→ RegressionReview
→ ExperienceCardVersion
```

---

# 27. 最关键的新基础设施：Artifact Registry

这是整合观澜功能的核心。

但必须明确：**Artifact 不是替代所有领域表的万能 JSON。**

现有 Evidence、Claim、Thesis、ReportVersion、Prediction 继续保持强类型。

新增 `ArtifactRegistry` 只负责：

```text
跨领域索引
跨模块导航
全库溯源
统一搜索
统一 Handoff
```

---

# 28. ArtifactRecord

```text
artifact_id
artifact_type
domain_type
domain_id
title
summary
instrument_ids
as_of_time
version
status
created_by
created_at
route
metadata
```

Artifact Type：

```text
evidence
event
claim
thesis
report
report_version
industry_map
global_context
experience_card
workflow
workflow_run
screen
screening_run
strategy
strategy_version
strategy_backtest
observation
signal
decision
prediction
validation
review
```

---

# 29. ProvenanceEdge

统一关系表：

```text
ProvenanceEdge
```

字段：

```text
edge_id
from_artifact_id
to_artifact_id
relation_type
created_at
metadata
```

关系：

```text
derived_from
supported_by
contradicted_by
validated_by
generated_from
used_by
produced
supersedes
triggered_by
selected_by
monitored_by
decided_from
predicted_from
reviewed_by
```

---

# 30. 研究图谱不允许前端手工拼关系

全库研究图谱的数据来源必须是：

```text
ArtifactRegistry + ProvenanceEdge
```

不能由 frontend 根据 type 手工猜关系。

---

# 31. 全库研究图谱

正式名称：

```text
全库研究图谱
```

目标是 Research Asset Provenance Explorer，不是传统企业知识图谱。

---

# 32. 图谱必须支持 Scope

```text
全库
单股票
单 Report
单 Experience Card
单 Workflow
单 Strategy
单 Prediction
```

例如点击一个经验卡：

```text
ExperienceCard v2
        ↑
RegressionReview
        ↑
Validation
        ↑
Prediction
        ↑
Decision
        ↑
StrategyVersion
        ↑
WorkflowRun
        ↑
ExperienceCard v1
        ↑
ReportVersion
        ↑
Thesis
        ↑
Claim
        ↑
Evidence
        ↑
Source
```

---

# 33. 图谱节点必须支持 Handoff

点击节点：

```text
报告 → 报告模块
经验卡 → 经验卡
WorkflowRun → 工作流运行结果
Strategy → 策略实验室
Decision → 策略盯盘历史
```

并保留当前股票、当前 as_of 和当前上游物料。

---

# 34. 第二个关键基础设施：Research Context

统一：

```text
ResearchContext
```

字段：

```text
instrument_ids
primary_instrument_id
as_of_time
snapshot_id
research_run_id
report_version_id
selected_artifact_ids
workflow_run_id
screening_run_id
strategy_version_id
locale
```

Context 只描述当前研究上下文，不是业务真数据。

---

# 35. 第三个关键基础设施：Handoff

定义：

```text
HandoffEnvelope
```

字段：

```text
handoff_id
source_module
target_module
action
artifact_ids
context
message
created_at
```

典型：

```text
Research Report → Experience Card
Experience Card → Workflow Studio
Workflow Run → Screening
Screening Result → Strategy Lab
Strategy → Strategy Monitor
Decision → Prediction
Validation → Research Review
```

---

# 36. 不使用 localStorage 作为跨模块真相

可以保存 theme、language、temporary UI preference。

不能保存真实 Experience Card、真实 Strategy、真实 Provenance。

所有真实物料必须后端持久化。

---

# 37. 第四个关键基础设施：统一 Research Run Event

升级现有 SSE 为：

```text
ResearchEvent
```

字段：

```text
event_id
run_id
stage
event_type
status
progress
title
summary
artifact_ids
created_at
metadata
```

统一 Stage：

```text
PLANNING
COLLECTING
ANALYZING
SYNTHESIZING
VALIDATING
SCREENING
BACKTESTING
MONITORING
REPORTING
COMPLETED
FAILED
```

Event 必须实时 SSE，同时持久化为 RunEvent，用于任务历史、研究回放和失败分析。

---

# 38. AI 研究中枢

正式名称：

```text
AI 研究中枢
```

它不是另一个聊天机器人，而是整个系统的自然语言 Application Orchestrator。

推荐布局：

```text
┌──────────────┬─────────────────────────┬─────────────────────┐
│ 左：任务/计划 │ 中：对话 + 执行过程      │ 右：当前研究产物      │
│              │                         │                     │
│ 当前计划      │ 用户输入                 │ Report              │
│ 正在运行      │ AI 计划                  │ Experience Card      │
│ 后台任务      │ Tool / Stage Progress   │ Screening            │
│ 最近研究      │ 研究总结                 │ Strategy             │
└──────────────┴─────────────────────────┴─────────────────────┘
```

---

# 39. AI 研究中枢不能是万能 Agent

设计：

```text
ResearchCommander
        ↓
Tool / Domain Registry
        ↓
Application Services
```

工具按域：

```text
Research Tools
Experience Tools
Workflow Tools
Screening Tools
Strategy Tools
Monitoring Tools
Graph Tools
```

不要一个 Agent 直接拿所有 Repository 权限。

---

# 40. AI 计划对象

定义：

```text
ResearchPlan
ResearchPlanStep
```

每一步：

```text
step_id
title
action
status
artifact_ids
started_at
completed_at
```

中枢左栏直接渲染这个。

---

# 41. 对话不是聊天记录堆积

Conversation：

```text
ConversationSession
ConversationTurn
```

重要产物必须 Artifact 化，不能只存在聊天历史。

---

# 42. 从对话生成研报

```text
研究中国稀土最近是否有资产重组迹象
↓
Resolve Instrument
↓
Create ResearchPlan
↓
Run ResearchPipeline
↓
ReportVersion
↓
Artifact
↓
右侧自动打开报告
```

---

# 43. 从报告炼成经验卡

```text
把“央企资产整合预期”炼成经验卡
↓
ReportVersion
↓
选择 Claim / Evidence
↓
ExperienceCard DRAFT
↓
LLM refine
↓
REFINED
```

必须保留 report_version_id、claim_ids、evidence_ids。

---

# 44. 从经验卡进入工作流验证

```text
验证过去 5 年这种逻辑是否有效
↓
ExperienceCard
↓
Create Workflow Draft
↓
User chooses Universe / Period
↓
WorkflowRun
↓
ExperienceValidation
```

若无法量化，走 CaseStudy Validation，而不是假装 Factor Backtest。

---

# 45. 工作流验证后进入智能选股

```text
按这个经验卡把现在 A 股筛一遍
↓
ExperienceCard APPROVED + WorkflowVersion
↓
ScreenDefinition
↓
ScreeningRun
↓
Candidate List
```

---

# 46. 选股进入策略实验室

```text
把这些候选做成“央企资产整合策略”
↓
ScreenDefinition
ExperienceCards
Workflow
↓
StrategyDefinition
```

---

# 47. 策略实验室验证

```text
Cross Instrument Backtest
Regime Split
Sensitivity
Failure Cases
```

输出 StrategyValidation。

未通过不可进入正式 Monitor，或标记 `EXPERIMENTAL`。

---

# 48. 策略盯盘

批准 StrategyVersion 后：

```text
StrategyVersion
↓
MonitorDefinition
↓
Scheduler Worker
```

后台检查：

```text
新公告
新新闻
行情变化
资金变化
宏观变化
经验条件
风险条件
```

---

# 49. 盯盘产物

```text
Observation
↓
Signal
↓
DecisionRecord
```

DecisionRecord 必须记录：

```text
decision
confidence
rationale
strategy_version_id
observation_ids
signal_ids
evidence_ids
as_of
```

---

# 50. Decision 进入 Prediction

Decision 不等于 Prediction。

Prediction 必须有：

```text
horizon
expected_direction
expected_range
benchmark
due_at
```

---

# 51. 复盘回灌

到期：

```text
Prediction
↓
Validation
↓
RegressionReview
```

Review 判断哪些 Evidence、Thesis、ExperienceCard、Strategy Rule 有问题。

最终生成：

```text
ExperienceCard v2
StrategyVersion v2
```

而不是覆盖旧版本。

---

# 52. 产业研究地图、全球宏观与 Research Domain 的关系

它们不是孤立 Dashboard，而是 Research Inputs：

```text
IndustryMapSnapshot → IndustryAnalyst → Claim
GlobalContextSnapshot → MacroAnalyst → Claim
```

Report、ExperienceCard、Strategy 都可以引用这些 Artifact。

---

# 53. UI 统一用户语言层

后端继续使用稳定英文 Enum，前端不能直接显示。

统一 Presentation Layer：

```text
SSE          → 上交所
SZSE         → 深交所
BSE          → 北交所
main_board   → 主板
chinext      → 创业板
star_market  → 科创板
monitor      → 持续研究
PASS         → 通过
```

技术 ID 放“技术详情”折叠区。

---

# 54. 外观与语言设置

继续按用户要求：

```text
外观
[ 跟随系统 ▾ ]

界面语言
[ 简体中文 ▾ ]
```

不要三按钮。

---

# 55. 关注池正式定位

关注池不是代码列表。

每张卡显示：

```text
中国稀土
000831 · 深交所 · 主板
实时行情
最新研究判断
最新 Report
持续研究状态
待验证 Prediction
最新变化
```

Actions：

```text
打开工作台
立即研究
查看报告
持续研究
策略盯盘
```

---

# 56. Instrument Workspace

继续保留：

```text
总览
时间线
研究图谱
Thesis
财务
估值
Evidence
报告
预测
```

新增：

```text
经验
策略
```

其中 Workspace Research Graph 是当前股票 scoped graph，一级“全库研究图谱”是全系统，两者共用同一个 Graph Backend。

---

# 57. 总览必须成为“当前研究状态”

```text
核心观点
研究置信度
估值
关键催化
主要风险
数据质量
最新变化
持续研究状态
Prediction
Strategy Monitor
```

---

# 58. 持续研究

不再独立保留“研究任务”开发者页面。

正式名称：

```text
持续研究
```

用户看到：

```text
股票
策略
频率
上次运行
本次变化
最新报告
下次运行
```

不是 claimed、succeeded、task_id。

支持：

```text
立即运行
暂停
删除
查看历史
```

删除只删除未来调度，历史 Run / Report 保留。

---

# 59. 后端目录建议

不要立即大迁移，但新增域建议：

```text
backend/app/
├─ application/
│  ├─ research_command/
│  ├─ handoff/
│  └─ artifacts/
│
├─ domain/
│  ├─ research/
│  ├─ industry/
│  ├─ macro/
│  ├─ experience/
│  ├─ workflow/
│  ├─ screening/
│  ├─ strategy/
│  ├─ prediction/
│  └─ knowledge_graph/
│
├─ services/
├─ sources/
├─ storage/
└─ api/
```

不要一次把旧代码全部移动，新代码进入新边界，旧代码渐进迁移。

---

# 60. Frontend 目录建议

```text
frontend/src/
├─ app/
├─ pages/
├─ features/
│  ├─ command-center/
│  ├─ instrument/
│  ├─ reports/
│  ├─ industry-map/
│  ├─ global-context/
│  ├─ experience/
│  ├─ workflow/
│  ├─ screening/
│  ├─ strategy-lab/
│  ├─ strategy-monitor/
│  ├─ predictions/
│  └─ research-graph/
│
├─ entities/
├─ presentation/
├─ i18n/
└─ shared/
```

---

# 61. API 设计原则

统一资源化：

```text
POST /research-runs
GET  /research-runs/{id}
GET  /research-runs/{id}/events

POST /experience-cards
POST /experience-cards/{id}/refine
POST /experience-cards/{id}/validate

POST /workflow-runs
GET  /workflow-runs/{id}

POST /screening-runs
GET  /screening-runs/{id}

POST /strategies
POST /strategies/{id}/backtests

POST /monitors
GET  /monitors/{id}/observations

GET /artifacts/{id}
GET /artifacts/{id}/lineage
```

---

# 62. Artifact / Graph API

```text
GET /artifacts
GET /artifacts/{artifact_id}
GET /artifacts/{artifact_id}/upstream
GET /artifacts/{artifact_id}/downstream
GET /artifacts/{artifact_id}/lineage
```

Graph：

```text
GET /research-graph
```

参数：

```text
scope=global|instrument|artifact
instrument_id
artifact_id
depth
relation_types
```

---

# 63. 版本策略

以下必须 immutable version：

```text
ReportVersion
ExperienceCardVersion
WorkflowVersion
ScreenVersion
StrategyVersion
IndustryMapVersion
```

运行结果：

```text
WorkflowRun
ScreeningRun
BacktestRun
ResearchRun
```

永远不可覆盖。

---

# 64. PIT 边界

所有会影响历史研究结论的 Run：

```text
ResearchRun
WorkflowRun
ScreeningRun
StrategyBacktestRun
Decision
```

必须有 `as_of_time`。

历史 Run 只能使用：

```text
available_time <= as_of_time
```

的数据。

---

# 65. LLM 正式边界

LLM 可以：

```text
提炼
解释
归纳
反证
分类
规划
生成结构化推理
```

LLM 不可以：

```text
创造行情
创造公告
创造财务数字
创造回测结果
创造事件事实
```

---

# 66. 统一 Trust / Fact Status

继续沿用：

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

新模块不能重新发明另一套。

---

# 67. 观澜值得完整吸收的产品原则

必须吸收：

```text
1. 一个总控入口
2. 对话即操作
3. 研究计划显形
4. 研究过程显形
5. 真实产物自动 Handoff
6. Experience Card 原炼验用
7. 可视化 DAG
8. Screening 与研究物料连接
9. Strategy 真实失败不隐藏
10. Monitoring 与研究结合
11. 全库物料关系图
12. 点任意物料带上下文跳模块
13. 降级状态必须显形
14. Mock 与真实必须显式区分
```

---

# 68. 不应该照搬观澜的部分

不要复制：

```text
品牌名称
中式命名体系
iframe 页面嵌入
localStorage 作为业务数据库
no-build React 架构
固定 24 Agent
440+ 因子宣传口径
页面驱动盯盘
模块自建一套状态
```

我们的优势必须保留：

```text
FastAPI
React/Vite
PostgreSQL
Evidence/PIT
强类型 Domain
ReportVersion
Prediction Validation
Scheduler Worker
真实 Source Layer
```

---

# 69. 实施顺序不能按页面数量推进

禁止：

```text
10 个模块
→ 10 个菜单
→ 10 个空页面
```

必须按闭环纵向切片。

---

# 70. Phase A —— 统一研究基础协议

先实现：

```text
ArtifactRegistry
ProvenanceEdge
ResearchContext
HandoffEnvelope
Persistent RunEvent
Instrument Registry
Presentation Localization
```

这是后续所有模块的地基。

没有这一层，禁止同时开发大量新模块。

---

# 71. Phase B —— AI 研究中枢 + 报告 Handoff

实现：

```text
ResearchCommandCenter
ResearchPlan
ConversationSession
ResearchRun Progress
Report Artifact
```

闭环：

```text
对话
→ ResearchRun
→ ReportVersion
→ Artifact
→ 右栏报告
```

---

# 72. Phase C —— 研究经验卡

闭环：

```text
ReportVersion
→ ExperienceCard Draft
→ Refine
→ Validate
→ Approve
```

先支持 Case validation 和简单 Quant validation，不要一次复制观澜全部指标库。

---

# 73. Phase D —— 研究验证工作流

先实现最小强类型 DAG：

```text
Data
→ Factor/Rule
→ Validation
→ Output
```

随后增加 Feature、ML、Backtest、Screening。

---

# 74. Phase E —— 智能选股

```text
ExperienceCard + Workflow + Universe
→ ScreeningRun
→ Candidate Artifact
```

每个 Candidate 必须解释原因。

---

# 75. Phase F —— 策略实验室

```text
Screening
ExperienceCard
Workflow
→ StrategyVersion
→ Backtest
→ Validation
```

---

# 76. Phase G —— 策略盯盘

```text
StrategyVersion
→ Monitor
→ Observation
→ Signal
→ Decision
```

必须后台运行。

---

# 77. Phase H —— 产业研究地图 + 全球宏观视图

接入 Industry Analyst、Macro Analyst、Report、Strategy，不做孤立 Dashboard。

---

# 78. Phase I —— 全库研究图谱

Artifact/Edge 从 Phase A 就开始积累。

此阶段主要做 Global Graph UI、Lineage Explorer、Cross-module Handoff。

---

# 79. Phase J —— 完整复盘回灌

最终跑通：

```text
Decision
→ Prediction
→ Validation
→ RegressionReview
→ ExperienceCard v2
→ StrategyVersion v2
```

---

# 80. 最终产品 E2E

必须以真实股票，例如：

```text
000831 中国稀土
```

完成：

```text
AI 研究中枢
↓
“研究中国稀土近期是否存在资产整合信号”
↓
真实 Source / Evidence
↓
ResearchRun
↓
深度研报 v1
↓
提炼“央企资产整合预期”研究经验卡
↓
研究验证工作流
↓
历史验证
↓
智能选股
↓
候选列表
↓
策略实验室
↓
央企资产整合策略 v1
↓
策略盯盘
↓
新公告 Observation
↓
Decision
↓
Prediction
↓
Final Validation
↓
Research Review
↓
ExperienceCard v2
```

---

# 81. 图谱最终验收

从 ExperienceCard v2 必须可以一路点回：

```text
RegressionReview
← Validation
← Prediction
← Decision
← StrategyVersion
← ScreeningRun
← WorkflowRun
← ExperienceCard v1
← ReportVersion
← Thesis
← Claim
← Evidence
← Source
```

再从任意节点带 Context 跳回原模块。

---

# 82. 产品 UI 最终判断标准

普通用户不需要理解：

```text
artifact_id
run_id
snapshot_id
SZSE
main_board
workflow_node_type
claimed
succeeded
```

这些放“技术详情”。

主界面只显示：

```text
中国稀土
000831 · 深交所 · 主板
研究完成
发现重要变化
报告 v3
经验卡已验证
策略正在盯盘
预测待验证
```

---

# 83. 最重要的架构红线

```text
红线 1：不建第二套 Research Core
红线 2：Artifact 不取代强类型 Domain
红线 3：所有历史计算遵守 PIT
红线 4：业务物料不靠 localStorage 持久化
红线 5：跨模块必须通过 Artifact + Context + Handoff
红线 6：运行过程必须事件化且可回放
红线 7：LLM 不创造事实
红线 8：失败 / 无数据 / 降级必须显形
红线 9：策略失败结果不能隐藏
红线 10：任何“完成”必须有产品级 E2E
```

---

# 84. Claude 开工前必须做的事情

Claude 不应立即创建页面。

第一步基于当前代码输出：

```text
ARCHITECTURE-V2.md
DOMAIN-MAP.md
ARTIFACT-PROTOCOL.md
HANDOFF-PROTOCOL.md
```

这四份文档必须严格遵循本方案，只做代码映射和接口细化，不能重新改变顶层方向。

---

# 85. 推荐第一批代码

第一批只允许：

```text
ArtifactRecord
ProvenanceEdge
ArtifactRepository
ArtifactService
ResearchContext
HandoffEnvelope
RunEvent Persistence
Instrument Registry 持久化
```

然后把现有：

```text
ReportVersion
Prediction
ResearchRun
```

注册成 Artifact，验证跨模块基础设施。

---

# 86. 第一批禁止直接做

```text
Experience Card Page
Workflow Canvas
Strategy Monitor
Industry Map
```

如果 Artifact / Provenance / Context / Handoff 地基没完成，这些页面暂时不要建。

否则又会重复“页面存在，但互相没有关系”。

---

# 87. 第二批

完成 AI 研究中枢。

先只控制现有：

```text
Search
ResearchPipeline
Report
Continuous Research
Prediction
```

证明一个入口可以真正控制现有系统。

---

# 88. 第三批以后

才依次：

```text
Experience Card
Research Workflow
Screening
Strategy
Industry/Macro
Global Graph
Review Feedback Loop
```

---

# 89. 最终完成定义

系统最终不是：

```text
“观澜功能我也有”
```

而是：

> **观澜的研究生产闭环，被重新建模进 A-Share Research OS 的强类型、PIT、可追溯架构中。**

最终核心价值：

```text
事实可信
研究可解释
经验可沉淀
方法可验证
标的可筛选
策略可试验
运行可监控
预测可验证
错误可复盘
知识可回灌
全链可溯源
```

---

# 90. Claude 最终执行指令

1. 将本文作为产品与架构总纲；
2. 不复制观澜品牌命名；
3. 使用本文正式模块名称；
4. 保留现有 Research Core；
5. 先设计并实现 Artifact / Provenance / Context / Handoff 地基；
6. 不允许创建平行 Domain；
7. 不允许万能 JSON Artifact 取代强类型对象；
8. 所有新 Run 必须 PIT；
9. 所有模块必须生成真实 Artifact；
10. 所有 Artifact 必须有 Provenance；
11. 所有跨模块动作必须 Handoff；
12. 所有长期业务数据必须后端持久化；
13. 所有 UI Enum 必须本地化；
14. 外观和语言使用单 Select；
15. 技术 ID 放技术详情；
16. 开发按纵向闭环推进，不按页面数量推进；
17. 000831 作为核心产品回归标的，但禁止特殊化；
18. 每阶段 Build + Unit + Integration + Product E2E；
19. 每次上下文结束前更新 PLAN / STATUS；
20. 未通过对应 E2E 不得宣布模块完成。

---

# 91. 一句话总纲

> **以 Evidence/PIT 为事实底座，以 Artifact/Provenance 为研究物料总线，以 AI 研究中枢为统一入口，以“研报 → 经验 → 验证 → 选股 → 策略 → 盯盘 → 决策 → 复盘 → 回灌”为主闭环，构建真正可长期演进的 A 股智能投研操作系统。**
