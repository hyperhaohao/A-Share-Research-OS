# A-Share Research OS 全产品 UI / 信息架构重构任务说明书
## UI Information Architecture Rebuild — Final Product Task Book

> 仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 审查基线：
> - 当前 HEAD：`360b532a3503a192ac2576d6cf1a737cab715b6f`
> - 最近核心实现提交：`4b9ebcc5f468c67f343ef4be63b4c1a2bef456fa`
> - 相比产品整改基线 `13f734660db7a35077c274a1ec3246a22ea9ab78` 已前进约 48 个提交
>
> 本文档是后续 Claude Code / Coding Agent 的完整 UI/产品体验整改总纲。
>
> **本轮不再扩展新的研究业务能力，不推倒 Research Core。**
>
> 最终目标：
>
> > **把已经具备 V2 研究/验证/决策能力的系统，从“功能很多但界面数据混乱”重构为专业、清晰、可长期使用的 A 股智能投研操作系统。**

---

# 1. 当前总体判断

当前仓库已经实际具备：

```text
Instrument Registry
Evidence / PIT Snapshot
Claim / Thesis
ResearchPipeline
Report / ReportVersion
Prediction / Validation

Artifact Registry
Provenance Edge
Research Context
Handoff
Persistent RunEvent

AI 研究中枢
研究经验卡
研究验证工作流
智能选股
策略实验室
策略盯盘
产业研究地图
全球宏观视图
全库研究图谱
研究复盘 / 经验回灌
```

并且以下产品问题已经有实际修复：

```text
外观：单 Select
语言：单 Select
研究任务：支持调度、立即运行、暂停、删除
关注池：升级为研究卡
Pipeline：支持 SSE + RunEvent Replay
预测：已有生成入口与方向/区间冲突披露
```

所以当前最大的短板不是 Domain，而是：

```text
Experience Layer
Information Architecture
Read Model
Visual Hierarchy
Semantic Components
Data Aggregation
```

---

# 2. 为什么当前 UI 会显得“数据很乱”

当前系统仍大量复用最早期的：

```text
.page
.card
.result-row
.task-grid
.header-controls
.watch-list
```

然后把越来越复杂的：

```text
Watchlist
Report
Task
Prediction
Experience
Workflow
Screening
Strategy
Monitoring
Graph
```

全部塞进同一套视觉结构。

结果是：

```text
功能越来越多
→ 所有页面越来越像
→ 所有字段权重一样
→ 结论/依据/状态/技术信息混在一起
```

这是当前 UI 混乱的根因。

---

# 3. 第一红线：冻结业务功能扩张

UI Foundation 完成前：

```text
禁止新增新的一级业务模块
禁止为了展示新能力快速增加空页面
禁止继续给旧页面堆更多字段
```

允许修：

```text
真实数据
PIT
安全
部署
严重业务 bug
```

但新增产品能力暂时冻结。

---

# 4. 正式模块名称

继续使用适配后的 A-Share Research OS 名称：

| 功能语义 | 正式名称 |
|---|---|
| 帷幄 | AI 研究中枢 |
| 对话出研报 | 深度研究 / 研究报告 |
| 河图 | 产业研究地图 |
| 全球坐标 | 全球宏观视图 |
| 经验卡 | 研究经验卡 |
| AI 工作流 | 研究验证工作流 |
| 选股 | 智能选股 |
| 席位 · 校场 | 策略实验室 |
| 席位 · 盯盘 | 策略盯盘 |
| 落子 | 研究决策 |
| 研究图谱 | 全库研究图谱 |
| 复盘 | 研究复盘 |
| 自选 | 关注池 |
| 研究任务 | 持续研究 |

禁止重新把“帷幄/河图/席位/校场”作为正式产品名称。


---

# 5. P0-UI-01：导航必须重构

当前顶部横向导航已经有约 10 个入口，继续加 Workflow/产业/宏观/设置后必然失控。

必须改为左侧分组 Sidebar：

```text
AI 研究中枢

研究
├─ 关注池
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

Sidebar：
- 展开宽度约 220px；
- 收起宽度约 64px；
- 分组可折叠；
- 当前模块明显；
- 设置/外观/语言可放底部。

---

# 6. P0-UI-02：建立正式 Layout System

当前全局 `.page max-width:1080px` 不适合复杂投研工作台。

新增：

```text
ReadingLayout
WorkspaceLayout
CommandCenterLayout
CanvasLayout
```

### ReadingLayout
用于 Interactive Report：

```text
max-width: 1040px
```

### WorkspaceLayout
用于：
- Instrument Workspace
- Experience Detail
- Screening Detail
- Strategy Detail

```text
max-width: 1480px
```

### CommandCenterLayout
用于 AI 研究中枢：

```text
max-width: 1680px
Left   250px
Center min 680px / flexible
Right  340px
```

### CanvasLayout
用于：
- Workflow Studio
- Industry Map
- Research Graph
- Strategy Monitor

```text
width: 100%
max-width: none
height: calc(100vh - shell)
```

响应式：

```text
>=1440   完整三栏
1200-1439 右栏变可折叠 Drawer
960-1199 左右辅助栏均可折叠
<960     单栏
```

不要再简单 `<1100 → 全部纵向堆叠`。

---

# 7. P0-UI-03：修复 Design Token 漂移

正式 Token 目前是：

```text
--color-border
--color-text
--color-bg-elevated
--color-surface
```

但新 CSS 已出现：

```text
--border
--text
--text-secondary
--bg-card
```

必须统一。

只保留：

```text
--color-bg
--color-bg-elevated
--color-surface
--color-surface-subtle

--color-border
--color-border-strong

--color-text
--color-text-secondary
--color-text-tertiary

--color-accent
--color-info
--color-warning
--color-danger
--color-positive
--color-negative
```

新增：

```text
--space-1 4px
--space-2 8px
--space-3 12px
--space-4 16px
--space-5 24px
--space-6 32px

--radius-sm
--radius-md
--radius-lg

--font-xs
--font-sm
--font-md
--font-lg
--font-xl

--shadow-sm
--shadow-md
```

禁止继续出现未定义 alias。

同时移除散落硬编码色，例如：

```text
#b8860b
#ddd
#fff
#eef2ff
#f8fafc
```

A 股语义继续保持：

```text
上涨 = positive
下跌 = negative
错误 = danger
```


---

# 8. P0-UI-04：建立 Semantic Component System

新增：

```text
frontend/src/ui/
├─ layout/
├─ navigation/
├─ data-display/
├─ feedback/
├─ actions/
└─ research/
```

必须逐步建立：

```text
AppShell
Sidebar
TopContextBar
PageHeader
SectionHeader

Panel
Toolbar
Drawer
Tabs
SegmentedTabs

DataTable
Metric
MetricGrid
KeyValueList

Badge
StatusBadge
DirectionBadge
QualityBadge
AuthorityBadge
ConfidenceBadge
MaterialityBadge

EmptyState
LoadingSkeleton
ErrorState
DegradedState

ActionMenu
PrimaryAction
SecondaryAction
DangerAction

TechnicalDetails
Disclosure
```

研究语义组件：

```text
InstrumentIdentity
InstrumentHeader

ResearchStance
ResearchConfidence
ResearchSummary
ResearchChangeSummary

ThesisSummary
CatalystList
RiskList

ValuationSummary
ScenarioBand

EvidenceRow
EvidenceAuthority

ReportSummary
PredictionSummary
ValidationSummary

ExperienceLifecycle
WorkflowRunSummary

ScreeningCandidate
StrategyValidationSummary

ObservationCard
SignalCard
DecisionCard

ArtifactChip
LineageBreadcrumb
```

---

# 9. Action 规则

任何列表/卡片：

```text
Primary Action 最多 1 个
Secondary Action 最多 1–2 个
其余进入 [更多 ▾]
```

例如关注池：

```text
[打开工作台] [···]

···
立即研究
查看报告
创建持续研究
移除关注
```

禁止再出现一张卡 5–6 个并列按钮。

---

# 10. P0-UI-05：必须增加 UI Read Model / Query Layer

当前大量页面自己调用多个底层 API，再自己拼结果。

必须新增：

```text
backend/app/application/views/
```

建议：

```text
command_center_view.py
watchlist_view.py
instrument_overview_view.py
report_library_view.py
continuous_research_view.py
prediction_review_view.py
experience_view.py
workflow_view.py
screening_view.py
strategy_view.py
monitor_view.py
research_graph_view.py
```

View Model：
- 只做读侧聚合；
- 不复制 Domain；
- 不成为新业务真相；
- 不新增重复业务表。

建议 API：

```text
GET /api/v1/views/command-center
GET /api/v1/views/watchlist
GET /api/v1/views/instruments/{id}/overview
GET /api/v1/views/reports
GET /api/v1/views/continuous-research
GET /api/v1/views/predictions
GET /api/v1/views/experience-cards
GET /api/v1/views/screening-runs/{id}
GET /api/v1/views/strategies/{id}
GET /api/v1/views/monitors/{id}
```

所有 View Model 带：

```text
generated_at
as_of
data_status
degraded_sections
```

---

# 11. N+1 必须消除

目前 Watchlist 单股票可能分别请求：

```text
Instrument
Quote
Report
```

Report Card 又会请求：

```text
Instrument Name
Thesis Judgment
```

Task Card 又会请求：

```text
Instrument
Latest Report
```

必须改为页面级聚合。

请求预算：

```text
Command Center 首屏 <= 3 个业务请求
Watchlist 5只/50只都 <= 3 个业务请求
Reports 不随报告数线性增长
Tasks 不随任务数线性增长
```

禁止：

```text
N Cards → 2N / 3N requests
```

---

# 12. Research Stance 必须只有一个来源

前端不得再通过：

```text
supporting_claims.length > opposing_claims.length
```

计算看多/看空。

建立：

```text
ResearchStanceView
```

字段：

```text
direction
confidence
basis
source_thesis_id
source_report_id
valuation_consistency
prediction_consistency
updated_at
```

前端只展示。

---

# 13. 所有页面统一三级信息结构

## L1 — 结论
用户 3 秒内知道：

```text
当前是什么？
发生了什么？
结论是什么？
```

## L2 — 关键依据

```text
为什么？
关键催化？
主要风险？
最新变化？
```

## L3 — 技术详情

```text
run_id
artifact_id
snapshot_id
provider
raw enum
raw JSON
```

L3 默认折叠。

---

# 14. 中文 UI 禁止裸露技术信息

主界面不得主要出现：

```text
SZSE:000831
SSE:
run_xxx
rpt_xxx
artifact_xxx
snapshot_xxx

market_data
main_board
monitor
succeeded
APPROVED
DELTA_RESEARCH
```

技术 ID 统一进入：

```text
技术详情 ▾
```

Presentation Layer 扩展到：

```text
Artifact Type
Relation
Workflow Node
Workflow Status
Experience Status
Strategy Status
Monitor Status
Signal Type
Decision Type
Prediction Horizon
Consistency
Validation Verdict
Failure Reason
```


---

# 15. AI 研究中枢重构

三栏理念保留，但重新组织。

最终布局：

```text
┌──────────┬────────────────────────────┬──────────────┐
│ 计划      │ 当前研究                    │ 产物 / 上下文 │
│          │                            │              │
│ 当前计划  │ 当前标的 Context Bar        │ 最新报告      │
│ 最近计划  │                            │ 最新经验卡    │
│ 后台运行  │ 对话                        │ 最新筛选      │
│          │ 实时研究过程                 │ 策略/预测      │
│          │ 最终研究结论                 │              │
└──────────┴────────────────────────────┴──────────────┘
```

中栏顶部：

```text
中国稀土
000831 · 深交所 · 主板

当前研究：资产整合信号

[切换标的]
```

InstrumentSearch 改为 Context Picker / Command Palette，不再长期占一张卡。

Conversation 成为主操作面。

手工：
```text
完整研究
刷新数据
```
作为快捷动作。

当前 Plan 逻辑必须改：

```text
currentPlan = 仅 running
recentPlans = 排除 current
```

避免最近已完成 Plan 被同时当“当前计划”和“最近计划”。

待验证预测排序：

```text
冲突优先
到期优先
置信度优先
```

---

# 16. Instrument Workspace 重构

这是第二核心页面。

Header：

```text
中国稀土
000831 · 深交所 · 主板 · 稀土

¥60.18   +2.31%

中性偏多 · 72%
数据质量：良好
更新：今天 18:32

[立即研究] [查看最新报告] [···]
```

更多菜单：

```text
创建持续研究
生成预测
产业研究地图
全球宏观视图
策略盯盘
```

Overview 使用 `InstrumentOverviewView`：

```text
┌─────────────────────┬─────────────────────┐
│ 核心观点             │ 估值                 │
│ 中性偏多 · 72%       │ Base ¥31.20          │
│                     │ 与当前价冲突 ⚠       │
├─────────────────────┼─────────────────────┤
│ 关键催化             │ 主要风险             │
│ 资产整合             │ 注入时间不确定       │
├─────────────────────┼─────────────────────┤
│ 最新变化             │ 数据质量             │
│ 新 Evidence 3 条     │ 7/8 能力可用         │
└─────────────────────┴─────────────────────┘
```

下方：

```text
最新报告
持续研究
Prediction
经验卡
策略盯盘
```

---

# 17. Workspace Tab 收敛

不要继续平铺十几个按钮。

一级：

```text
总览
研究
基本面
证据
产物
```

二级：

### 研究
```text
Thesis
Timeline
研究图谱
```

### 基本面
```text
财务
估值
产业
宏观
```

### 证据
```text
Evidence
Source
```

### 产物
```text
报告
预测
经验卡
策略
```

Copilot 变为可折叠 Context Inspector。

---

# 18. 关注池

桌面优先表格，移动端卡片。

| 标的 | 价格 | 涨跌 | 研究判断 | 最新变化 | 报告 | 持续研究 | 预测 | 更新时间 |
|---|---:|---:|---|---|---|---|---|---|

示例：

```text
中国稀土 000831
¥60.18
+2.31%
中性偏多 72%
新公告 3条
v4
每天08:30
20D看多
18:32
```

Action：

```text
打开
···
```

必须由一个 `/views/watchlist` 一次返回完整 Row。

---

# 19. 报告库

顶部过滤：

```text
股票
时间
研究判断
质量
语言
```

Row/Card：

```text
中国稀土
完整研究报告 v4

中性偏多 · 72%
2026-08-29 18:32
质量：通过

[打开] [···]
```

更多：

```text
生成预测
炼成经验卡
查看溯源
```

Lineage 默认折叠，不允许每个列表项默认请求完整链路。

Interactive Report 使用 ReadingLayout。

Header：

```text
中国稀土 · 完整研究报告 v4
中性偏多 · 72%
数据质量 良好
as_of ...
```

---

# 20. Evidence

每条：

```text
[官方公告] [A2]
2026-08-29

关于……

巨潮资讯

支持 3 条研究主张

[查看原文] [查看被谁引用]
```

必须显示 Authority/Fact Status，技术 ID 折叠。

---

# 21. Thesis

不要字段全展开。

首屏：

```text
核心 Thesis

集团资产整合是主要估值催化

置信度 72%
状态：有效

支持 5
反向 2
```

然后：

```text
催化剂
风险
失效条件
```

Claim 详情用 Drawer / Disclosure。

---

# 22. 财务

上层优先：

```text
营收
净利润
ROE
毛利率
现金流
```

重点展示变化趋势。

不要以 MetricRow 列表为主界面。

---

# 23. 估值

必须明确：

```text
当前价
熊市
基准
牛市
```

再显示：

```text
PE
PS
PB
```

方法细节。

如果方向与估值冲突：

```text
⚠ 研究方向与基本面估值区间存在冲突
```

解释：

```text
方向来自 Thesis
区间来自确定性估值锚
```


---

# 24. 预测与复盘

顶部 KPI：

```text
方向准确率
区间命中率
平均超额收益
已验证数量
```

Tab：

```text
待验证
已验证
方向/区间冲突
复盘
```

Prediction Row：

```text
中国稀土

20个交易日
方向：看多
区间：-20% ~ -5% ⚠

当前：+1.2%
到期：09-20

来源：研究报告 v4
```

---

# 25. 研究经验卡

Library：

| 经验 | 状态 | 置信度 | 验证 | 来源 | 更新时间 |
|---|---|---:|---|---|---|

Detail Header：

```text
央企资产整合预期

已批准
置信度 76%
v2

原 → 炼 → 验 → 用
✓   ✓   ✓   当前
```

主体：

```text
经验结论
作用机制
适用条件
失效条件
```

次级：

```text
验证
来源
版本
```

---

# 26. 研究验证工作流必须成为独立模块

当前 Workflow 主要嵌在 Experience Card。

必须补：

```text
/workflows
/workflows/:workflowId
```

Workflow Studio：

```text
┌──────────┬──────────────────────────┬──────────────┐
│ Node库    │ Canvas                   │ Inspector    │
│ 数据      │ [Data]→[Rule]→[Validate]│ 节点配置      │
│ 研究      │                          │              │
│ Quant    │                          │              │
│ 验证      │                          │              │
│ 输出      │                          │              │
└──────────┴──────────────────────────┴──────────────┘

Bottom:
Run Console / Metrics / Error
```

使用现有 React Flow。

支持：

```text
typed port
valid connection
node status
run overlay
failed node
artifact output
```

---

# 27. 智能选股

历史筛选页：

```text
历史筛选
运行中
最近结果
```

Detail 顶部：

```text
Universe
规则
经验卡
工作流
候选数
排除数
```

候选用表格：

| 排名 | 股票 | Score | 命中规则 | 风险 | 关键原因 |
|---:|---|---:|---|---|---|

点击打开 Candidate Inspector：

```text
为什么选中
Factor Contribution
Matched Rules
Experience
Evidence
Risk
```

“为什么没选中”作为独立分析：

```text
估值不满足       812
证据不足         631
行业不匹配       412
```

---

# 28. 策略实验室

分三层：

```text
策略定义
验证结果
失败案例
```

Header：

```text
央企资产整合策略
v3
EXPERIMENTAL

Universe 23
经验卡 2
工作流 1
```

Validation：

```text
组合收益
最大回撤
命中率
样本数

Regime Split
Sensitivity
```

失败案例必须永远显示。

---

# 29. 策略盯盘

正式做成 Operations Dashboard。

顶部：

```text
运行中策略
今日信号
需要关注
最新决策
```

Monitor Detail 严格分：

```text
Observation
↓
Signal
↓
Decision
```

例如：

```text
观察
新集团公告

信号
资产整合条件增强

决策
继续观察
71%
```

下方：

```text
Evidence
Strategy
Prediction
Review
```

---

# 30. 产业研究地图

当前后端已有关系数据。

必须改为 Graph Canvas：

```text
公司
行业
商品
客户
供应商
竞争对手
政策
```

Edge：

```text
同业
上游
下游
政策影响
```

布局：

```text
Canvas
+
右侧 Node Inspector
```

顶部：

```text
当前标的
关系来源
as_of
数据质量
```

---

# 31. 全球宏观视图

当前已有真实：

```text
上证
道指
纳指
恒指
黄金
原油
```

等数值层。

UI 做成 Macro Dashboard。

一级：

```text
风险偏好
美元/利率
商品
中国市场
海外市场
```

每个指标：

```text
当前值
涨跌
市场时间
来源
```

---

# 32. 全库研究图谱必须变成真正的图

当前 API 已返回：

```text
nodes
edges
```

但 UI 主要仍是：

```text
类型分组节点列表
+
Lineage 列表
```

`edges` 没有真正用于 Graph Canvas。

必须改成 React Flow：

```text
Report
↓
Experience
↓
Workflow
↓
Screening
↓
Strategy
↓
Decision
↓
Prediction
↓
Validation
↓
Review
```

Filter：

```text
股票
Artifact Type
时间
Relation
Depth
```

Scope：

```text
全库
单股票
当前 Artifact
```

右侧 Inspector：

```text
标题
类型
版本
状态
创建时间
直接上游
直接下游
[打开原模块]
```

默认节点上限保持约 150，支持过滤和 Load More。


---

# 33. 持续研究

正式名称：

```text
持续研究
```

桌面表格：

| 标的 | 类型 | 频率 | 状态 | 上次运行 | 最新结果 | 下次运行 |
|---|---|---|---|---|---|---|

Actions：

```text
立即运行
暂停
删除
```

其余进更多菜单。

创建任务使用 Drawer：

```text
+ 新建持续研究
```

字段：

```text
标的
任务类型
频率
时间
```

Scheduler Tick / claimed / succeeded 完全移到：

```text
系统 → Diagnostics
```

Task Delete 语义继续：

```text
删除未来调度
保留 ResearchRun
保留 Report
保留 Prediction
```

运行中拒绝删除。

---

# 34. 前端 API 层集中

新增：

```text
frontend/src/api/
├─ client.ts
├─ views.ts
├─ research.ts
├─ artifacts.ts
└─ actions.ts
```

页面不再散落大量 `fetch()`。

新增 Query Key Factory：

```text
queryKeys.instrument(id)
queryKeys.watchlistView()
queryKeys.reportLibrary()
queryKeys.commandCenter()
```

---

# 35. Feature 目录逐步落地

```text
frontend/src/
├─ app/
│  ├─ AppShell.tsx
│  ├─ routes.tsx
│  └─ navigation.ts
├─ ui/
├─ features/
│  ├─ command-center/
│  ├─ watchlist/
│  ├─ instrument/
│  ├─ reports/
│  ├─ experience/
│  ├─ workflows/
│  ├─ screening/
│  ├─ strategy/
│  ├─ monitoring/
│  ├─ predictions/
│  ├─ industry-map/
│  ├─ global-context/
│  └─ research-graph/
├─ api/
├─ presentation/
├─ i18n/
└─ shared/
```

不一次搬全仓。

规则：

```text
重构一个页面
→ 搬一个 Feature
```

---

# 36. Empty / Loading / Error / Degraded

统一组件。

禁止：

```text
暂无数据
```

结束。

示例：

报告：

```text
还没有研究报告。
先执行一次完整研究。
[立即研究]
```

经验卡：

```text
还没有研究经验卡。
从报告提炼一张经验卡。
[打开报告库]
```

Workflow：

```text
还没有验证工作流。
从一张经验卡创建验证。
[查看经验卡]
```

Degraded：

```text
宏观数据暂不可用。
当前研究仍基于公告、财务和行情完成。
[查看数据源状态]
```

---

# 37. Appearance / Language

当前单 Select 已符合要求。

必须保持：

```text
外观 [跟随系统 ▾]
界面语言 [简体中文 ▾]
```

不得退回三个按钮。

后续可移动到 Sidebar Footer / 设置。

---

# 38. 视觉风格

目标：

> 专业投研工作台，不是 SaaS 营销页，也不是数据库后台。

原则：

```text
信息密度高
视觉层级强
装饰少
数据优先
留白克制
状态清楚
交互一致
```

Card 只用于独立语义对象。

普通数据区：

```text
Section
Table
List
```

不要所有东西都套 Card。

字体建议：

```text
Page Title    24–28
Entity Title  22–24
Section Title 16
Body          14
Secondary     12–13
Metric        20–28
```

---

# 39. 当前架构文档同步

`docs/v2/ARCHITECTURE-V2.md` 仍描述旧阶段：

```text
Phase A 缺 Artifact
跨模块 ❌
RunEvent 未完成
```

而实际 STATUS 已经是 A–J DONE。

本轮更新：

```text
docs/v2/ARCHITECTURE-V2.md
docs/v2/DOMAIN-MAP.md
```

使其描述 Current As-Is。

---

# 40. 本轮阶段

```text
UI0 — Foundation Audit & Token Repair
UI1 — App Shell / Navigation / Layout
UI2 — Read Model / Query Layer
UI3 — Semantic Component System
UI4 — Command Center + Instrument Workspace
UI5 — Core Libraries
UI6 — Validation & Strategy Surfaces
UI7 — Maps / Graph / Workflow Canvas
UI8 — Quality / Visual Regression / Performance
```

---

# 41. UI0

必须：

```text
统一 CSS Token
删除 undefined alias
清理 hardcoded colors
定义 spacing/radius/typography
逐步拆 global.css
```

DoD：

```text
Light PASS
Dark PASS
System PASS
所有 var(...) 有正式 token
```

---

# 42. UI1

必须：

```text
Sidebar 分组导航
AppShell
TopContextBar

ReadingLayout
WorkspaceLayout
CommandCenterLayout
CanvasLayout
```

在：

```text
1920×1080
1440×900
1280×800
```

均：

```text
无横向溢出
导航不换两行
Command Center 主栏足够宽
```

---

# 43. UI2

第一批 Read Model：

```text
CommandCenterView
WatchlistView
InstrumentOverviewView
ReportLibraryView
ContinuousResearchView
PredictionReviewView
```

DoD：

```text
Watchlist 50 条无 N+1
Reports 无 2N
Tasks 无 2N
```

---

# 44. UI3

完成：

```text
Layout
Badge
Metric
Table
Entity Header
Research Summary
Empty/Error/Degraded
Technical Details
Action Menu
```

组件直接服务真实页面，不先做空 Storybook 工程。

---

# 45. UI4

先只重构两张基准页面：

```text
AI 研究中枢
Instrument Workspace
```

这两张达到目标后，其他模块才继续。

000831 验收：

```text
中国稀土
000831 · 深交所 · 主板

Quote
Research Stance
Valuation
Catalysts
Risks
Latest Change
Report
Prediction
Continuous Research
```

主界面不得出现：

```text
SZSE:000831
CN
main_board
```


---

# 46. UI5

依次重构：

```text
关注池
报告库
持续研究
预测与复盘
研究经验卡
```

---

# 47. UI6

依次：

```text
智能选股
策略实验室
策略盯盘
```

---

# 48. UI7

完成：

```text
研究验证工作流
产业研究地图
全球宏观视图
全库研究图谱
```

其中 Workflow 必须有独立路由和一级导航。

---

# 49. UI8 — Visual Regression

当前 Playwright 功能 E2E 保留。

新增：

```text
expect(page).toHaveScreenshot()
```

核心页面：

```text
AI研究中枢
关注池
Instrument Workspace
报告库
Interactive Report
经验卡
Workflow Studio
Screening
Strategy
Monitoring
Global Context
Research Graph
```

核心 6 页矩阵：

```text
zh-CN Light
zh-CN Dark
en-US Light
```

至少 18 张 baseline。

其他页：

```text
zh-CN Light
```

---

# 50. 新增 UI E2E

```text
E2E-UI-01 Sidebar Navigation
E2E-UI-02 Watchlist Aggregated
E2E-UI-03 Workspace Summary
E2E-UI-04 Command Center
E2E-UI-05 Workflow Canvas
E2E-UI-06 Research Graph Canvas
E2E-UI-07 Technical Details Hidden
E2E-UI-08 zh-CN No Raw Enum
```

现有 17 条产品 E2E 不得删除。

---

# 51. 数据一致性验收

同一股票在：

```text
Command Center
Watchlist
Workspace
Reports
Predictions
```

必须显示同一：

```text
Name
Exchange
Research Stance
Report Version
```

如果不同：

```text
必须明确 as_of 不同
```

---

# 52. 数据时点

核心页显示：

```text
研究数据截至
行情时间
最新更新
```

至少一个清晰位置。

---

# 53. 性能验收

本地 Docker：

```text
Command Center 首屏 <= 1.5s
Workspace 首屏 <= 1.5s
Watchlist 20只 <= 1.5s
```

不把外部实时 Source 阻塞首屏。

先显示持久化最新状态，再异步刷新。

Browser Test 加请求数量断言，禁止网络瀑布。

---

# 54. Accessibility

至少：

```text
所有按钮有文本/aria-label
键盘可导航
Focus 明显
Select 有 Label
Dialog/Drawer 可 Esc
```

---

# 55. 中文本地化自动检查

zh-CN 页面业务区搜索：

```text
SZSE:
SSE:
main_board
monitor
succeeded
APPROVED
artifact_
run_
snapshot_
```

目标：

```text
0
```

技术详情区域除外。

---

# 56. 不破坏现有 V2 能力

UI 重构不得破坏：

```text
PIT
Artifact
Provenance
Handoff
RunEvent
ReportVersion
Prediction maturity
Experience version
Workflow version
Strategy version
Replay feedback
```

---

# 57. Read Model 不得复制业务规则

例如 ResearchStance：

```text
可抽明确 Projection Service
```

禁止：

```text
Frontend 自己算
```

也禁止：

```text
View Endpoint 复制第二套 ResearchPipeline
```

---

# 58. 不切换大型 UI 框架

当前：

```text
React/Vite
React Query
React Flow
i18n
Theme Tokens
```

足够。

本轮不建议：

```text
Ant Design
MUI
Tailwind
```

整体迁移。

避免：

```text
业务 UI 重构 + 框架迁移
```

双重风险。

---

# 59. CSS 迁移方式

```text
新语义组件
→ 新样式
→ 页面迁移
→ 最后删除旧 global.css 规则
```

不要一次删除全部旧 CSS。

---

# 60. 完成一个页面的标准

不是：

```text
能打开
```

而是：

```text
数据正确
层级清楚
技术信息隐藏
中文完整
Light/Dark
Empty/Error/Degraded
E2E
Screenshot
请求预算
```

全部通过。

---

# 61. 状态管理

开工：

```text
STATUS.md

Current Phase:
UI Information Architecture Rebuild — DOING
```

PLAN：

```text
UI0 → UI8
```

---

# 62. 文档治理

当前事实总纲：

```text
docs/archive/A-Share-Research-OS-最终产品与架构修改方案.md（V2 总纲，已归档）
本任务说明书
docs/v2/*
```

旧整改文档只做历史参考。

更新：

```text
docs/00-文档索引.md
```

明确：

```text
当前任务
架构总纲
历史整改
```

---

# 63. Claude / Agent 执行规则

1. 读取 `AGENTS.md / CLAUDE.md / TASK.md / PLAN.md / STATUS.md`；
2. 状态改为 `UI Information Architecture Rebuild — DOING`；
3. 暂停新增业务模块；
4. 从 UI0 开始；
5. 不允许跳过 Read Model 只“美化页面”；
6. 不允许继续大量使用 `.result-row`；
7. 不允许 Page 自己拼多个 Domain API 成研究结论；
8. 不允许 Frontend 自算 Research Stance；
9. 不允许技术 ID 泄露业务主界面；
10. 不允许全站继续 `max-width:1080`；
11. 不允许列表冒充全库图谱；
12. 不允许 Workflow 只作为经验卡内嵌小组件；
13. 每阶段必须 Build + Unit + Integration + E2E；
14. UI4 完成前不新增业务模块；
15. UI8 后做 Reviewer Pass。

---

# 64. 每阶段自检

```text
代码是否真实调用？
数据是否来自 Read Model？
是否出现 N+1？
是否出现 raw enum？
是否出现 raw technical id？
是否有 Empty State？
是否有 Degraded State？
是否 Light/Dark？
是否只有一个 Primary Action？
是否存在清楚视觉层级？
是否有 E2E？
```

---

# 65. 最终产品 E2E

以：

```text
000831 中国稀土
```

执行：

```text
AI 研究中枢
↓
搜索/对话选择中国稀土
↓
完整研究
↓
实时研究过程
↓
Workspace Summary
↓
报告 vN
↓
提炼研究经验卡
↓
研究验证工作流
↓
智能选股
↓
策略实验室
↓
策略盯盘
↓
Prediction
↓
Validation
↓
复盘回灌
↓
ExperienceCard vN+1
↓
全库研究图谱
```

每一步必须让用户清楚：

```text
我在哪
研究谁
当前状态
核心结论
下一步动作
```

---

# 66. 最终验收总表

```text
[ ] Sidebar 分组导航
[ ] Layout System
[ ] Token System 修复
[ ] Semantic Component System

[ ] Read Model Layer
[ ] Watchlist 无 N+1
[ ] Report Library 无 N+1
[ ] Tasks 无 N+1
[ ] Command Center 聚合

[ ] Research Stance 唯一来源

[ ] AI研究中枢重构
[ ] Instrument Workspace重构
[ ] Watchlist重构
[ ] Report Library重构
[ ] Prediction/Review重构
[ ] Continuous Research重构
[ ] Experience Card重构

[ ] Workflow Studio 独立模块
[ ] Screening重构
[ ] Strategy Lab重构
[ ] Strategy Monitor重构

[ ] Industry Map Graph
[ ] Global Macro Dashboard
[ ] Full Research Graph Canvas

[ ] zh-CN 无 Raw Enum
[ ] Technical ID 默认隐藏

[ ] Appearance Single Select
[ ] Language Single Select

[ ] Light PASS
[ ] Dark PASS

[ ] Functional E2E PASS
[ ] Visual Regression PASS
[ ] Request Budget PASS

[ ] 000831 全闭环 PASS

[ ] STATUS / PLAN / ARCHITECTURE-V2 同步
```

只有全部完成后才能：

```text
UI Information Architecture Rebuild — COMPLETE
```

---

# 67. 最终判断标准

不能再用：

```text
Phase A–J DONE
```

等同：

```text
产品完成
```

A–J 证明：

```text
业务闭环存在
```

本轮必须证明：

```text
用户体验成熟
```

---

# 68. 一句话 UI 总纲

> **后端继续坚持“事实完整”，前端必须坚持“信息压缩”：先给结论，再给依据，最后才给技术细节。**

---

# 69. 一句话最终任务

> **保留现有已经完成的 V2 研究、验证与决策闭环，停止继续堆功能；通过 Read Model、分组导航、布局体系、语义组件、真实 Canvas 和三级信息层级，把 A-Share Research OS 的 Experience Layer 重构成专业、清晰、可扩展的 A 股智能投研工作台。**
