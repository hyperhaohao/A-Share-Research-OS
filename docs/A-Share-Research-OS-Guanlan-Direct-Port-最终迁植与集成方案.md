# A-Share Research OS × Guanlan Direct Port 最终迁植与集成方案
## Guanlan Experience Layer Direct Port & ASRO Integration

> 目标仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> Donor 仓库：`https://github.com/jesson-hh/financial-analyst.git`
>
> 本方案是后续 Claude Code / Codex / Coding Agent 的**产品界面与交互重构总纲**。
>
> 本轮核心方向正式调整：
>
> **ASRO 不再“参考观澜后重新设计”，而是采用 Donor-First：优先直接迁植观澜已经成熟的 Experience Layer，并用 ASRO 自己更严格的 Research Core / PIT / Evidence / Artifact / Provenance / Version / Prediction / Scheduler / Auth 替换其底层数据和运行时。**

---

# 1. 总体结论

当前 ASRO 的问题不是后端能力不足，而是 Experience Layer 重复造轮子：

```text
观澜已有成熟产品形态
↓
ASRO 只抽象了功能名称
↓
重新设计页面
↓
重新实现交互
↓
结果：模块有了，但完成度和工作台体验差距很大
```

此前路线：

```text
观澜
→ 抽象功能
→ ASRO 自己重做页面
```

正式调整为：

```text
观澜成熟 UI / UX / 页面状态机
→ Direct Port
→ JSX → TSX
→ 拆组件
→ 删除 Mock / localStorage / no-build runtime
→ 接 ASRO API / Read Model / Artifact / Handoff
→ 保留 ASRO PIT / Evidence / Version / Auth / Scheduler
```

核心原则：

> **后端坚持 ASRO，前端优先迁观澜。**

---

# 2. 最终架构

```text
┌───────────────────────────────────────────┐
│      Guanlan Experience Layer Donor       │
│ Chat / Industry / Cards / Workflow       │
│ Screen / Seats / Macro / Overseas        │
└───────────────────┬───────────────────────┘
                    │ Direct Port
                    ▼
┌───────────────────────────────────────────┐
│          ASRO Experience Layer            │
│ AI Research Command Center               │
│ Industry Research Workspace              │
│ Experience Workbench                     │
│ Workflow Studio                          │
│ Screening Workbench                      │
│ Strategy Lab / Strategy Monitor          │
│ Global Macro Workspace                   │
└───────────────────┬───────────────────────┘
                    │ Adapter / ViewModel
                    ▼
┌───────────────────────────────────────────┐
│         ASRO Application Layer            │
│ Read Model / ResearchContext             │
│ ArtifactRegistry / ProvenanceEdge        │
│ HandoffEnvelope / RunEvent               │
└───────────────────┬───────────────────────┘
                    ▼
┌───────────────────────────────────────────┐
│           ASRO Research Core              │
│ Evidence / PIT / Claim / Thesis          │
│ ReportVersion / Prediction / Validation  │
│ Scheduler / Auth / PostgreSQL            │
└───────────────────────────────────────────┘
```

---

# 3. 正式产品命名

| Guanlan | ASRO 正式名称 |
|---|---|
| 帷幄 | **AI 研究中枢** |
| 对话·研报 | **深度研究 / 研究报告** |
| 河图 | **产业研究 · 产业链** |
| 全球坐标 | **产业研究 · 全球产业坐标** |
| 环节明细 | **产业研究 · 环节详情** |
| 全球情绪 | **全球宏观** |
| 海外 | **全球市场 / 海外市场** |
| 经验卡 | **研究经验卡** |
| AI 工作流 | **研究验证工作流** |
| 选股 | **智能选股** |
| 席位·校场 | **策略实验室** |
| 席位·盯盘 | **策略盯盘** |
| 落子 | **研究决策** |
| 研究图谱 | **全库研究图谱** |
| 复盘 | **研究复盘** |

---

# 4. 一级产品结构

```text
AI 研究中枢

研究
├─ 关注池
├─ 深度研究 / 报告库
├─ 产业研究
│  ├─ 产业链
│  ├─ 全球产业坐标
│  └─ 环节详情
└─ 全球宏观
   ├─ 全球市场
   ├─ 利率 / 汇率
   ├─ 商品
   └─ 风险偏好

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

---

# 5. Donor Matrix —— 必须文件级指定

| ASRO 模块 | Guanlan Donor | 迁植策略 |
|---|---|---|
| AI 研究中枢 | `ui/chat/app.jsx` | CORE_DIRECT_PORT |
| 深度研究/研报 | `ui/chat/app.jsx` + `agent-adapter.jsx` | CORE_DIRECT_PORT |
| 产业链 | `ui/industry/industry-app.jsx` | CORE_DIRECT_PORT |
| 全球产业坐标 | `industry-app.jsx` matrix/global view | CORE_DIRECT_PORT |
| 产业环节详情 | `industry-app.jsx` detail view | CORE_DIRECT_PORT |
| 全球宏观 | `ui/macro/macro-app.jsx` | PORT_AND_ADAPT |
| 海外市场 | `ui/overseas/overseas-app.jsx` | PORT_AND_ADAPT |
| 研究经验卡 | `ui/cards/validation.jsx` | CORE_DIRECT_PORT |
| 研究验证工作流 | `ui/factor/workflow.jsx` | CORE_DIRECT_PORT |
| 智能选股 | `ui/screen/screen-app.jsx` + `screen-data.jsx` | CORE_DIRECT_PORT |
| 策略实验室 | `ui/seats/luozi-foundry.jsx` + `luozi-fleet.jsx` + `luozi-panels.jsx` | CORE_DIRECT_PORT |
| 策略盯盘 | `luozi-app.jsx` + `luozi-chart.jsx` + `luozi-panels.jsx` + `luozi-data.jsx` | CORE_DIRECT_PORT |
| 公共视觉 | `ui/_shared/tokens*.css` | TOKEN_MAPPING |
| 公共组件 | `ui/_shared/shared.jsx` | COMPONENT_PORT |
| 跨模块行为 | `guanlan-bus.js` | BEHAVIOR_PORT_ONLY |

以后任务书禁止写：

```text
“参考观澜经验卡实现经验卡页面”
```

必须写：

```text
DONOR: ui/cards/validation.jsx
ACTION: PORT_AND_ADAPT
TARGET: frontend/src/features/experience/
KEEP: 左中右布局、原炼验用、验证指标、KB、Handoff
REPLACE: API、Mock、localStorage、Guanlan naming
```

---

# 6. AI 研究中枢

## Donor

```text
ui/chat/app.jsx
ui/chat/agent-adapter.jsx
ui/_shared/shared.jsx
```

## Target

```text
frontend/src/features/command-center/
frontend/src/features/deep-research/
```

## 必须保留

```text
三栏 Research Workspace
任务/计划区
对话主区域
工具执行过程
Evidence 引用
动态研究输出
Artifact Workbench
跨模块 Handoff
```

## 必须替换

```text
观澜 Agent API
观澜 Local Bus
Mock
localStorage 业务真数据
iframe/embed
```

改接：

```text
ResearchPlan
ResearchRun
RunEvent
Artifact
ResearchContext
HandoffEnvelope
ReportVersion
Evidence
```

## 最终形态

```text
┌──────────────┬──────────────────────────────┬─────────────────────┐
│ 研究计划      │ 当前研究 / 对话              │ 动态工作区           │
│ ✓ 数据采集    │ 研究中国稀土资产整合信号       │ Report              │
│ ✓ 财务       │ AI：正在核对集团资产……         │ Industry            │
│ ● 事件分析    │ [证据] [公告] [财务]           │ Experience          │
│ ○ 多空辩论    │                              │ Workflow            │
│ ○ 估值       │ 最终结论                       │ Screening           │
│              │                              │ Strategy            │
└──────────────┴──────────────────────────────┴─────────────────────┘
```

右栏必须是**真实当前 Workbench**，不是固定 Artifact List。

---

# 7. 产业研究必须整体迁植

观澜 `ui/industry/industry-app.jsx` 本身是三视图一体：

```text
产业链（河图）
+ 全球产业坐标
+ 环节详情
```

ASRO 不再把它拆成一个简单 IndustryMapPage + 一个 Macro Dashboard。

正式建立：

```text
IndustryResearchWorkspace
```

Target：

```text
frontend/src/features/industry-research/
```

拆成：

```text
IndustryResearchWorkspace.tsx
IndustryChainView.tsx
GlobalIndustryPositionView.tsx
IndustrySegmentDetail.tsx
IndustryDriverPanel.tsx
IndustryNarrativePanel.tsx
IndustryStockPool.tsx
IndustryTransmissionEdge.tsx
IndustryTemperature.tsx
IndustryMomentum.tsx
```

---

# 8. 产业链必须迁植的能力

必须保留：

```text
产业阶段分组
产业环节
上游/中游/下游布局

驱动因子
传导路径
正负影响
传导机制
滞后

行情动量
研究热度
行业温度
象限状态

研报观点
产业叙事
主题激活

股票池
标的行情

Hover
边传导
缩放
环节 Detail
返回动效
```

禁止再次退化成：

```text
几个 React Flow Node + Edge
```

---

# 9. 产业链后端映射

观澜前端概念：

```text
GROUPS
SEGS
DRIVERS
EDGES
NARRS
```

ASRO 正式对象：

```text
IndustryMapVersion
IndustryGroup
IndustryNode
IndustryEdge
IndustryDriver
IndustryNarrative
IndustrySnapshot
IndustryStockMembership
```

所有 Node/Edge/Driver/Narrative 必须带：

```text
Evidence refs
as_of_time
source
status
confidence
```

---

# 10. 全球产业坐标

正式名称：

```text
全球产业坐标
```

与产业链共享同一个：

```text
IndustrySnapshot
```

只是不同投影。

保留五条成熟逻辑轴：

```text
β 全球需求
Δ 涨价周期
Ω 国产替代
Θ 技术路线
Ψ 映射主题
```

内部字段：

```text
global_demand
pricing_cycle
domestic_substitution
technology_route
theme_mapping
```

位置：

```text
领先
并跑
追赶
短板
国内市场
```

对象建议：

```text
GlobalIndustryPosition
segment_id
axis
position
score
evidence_ids
as_of
confidence
```

---

# 11. 产业环节详情

点击任意产业环节进入：

```text
IndustrySegmentDetail
```

显示：

```text
环节定义
产业位置
全球位置
驱动
传导
行情动量
研究温度
最新研报
相关上市公司
主要商品
政策
Evidence
```

---

# 12. 全球宏观与全球产业坐标必须分开

### 全球产业坐标

回答：

> 某产业在全球产业竞争中的位置如何？

### 全球宏观

回答：

> 当前整个资本市场处于怎样的全球宏观环境？

两者不是同一个模块。

---

# 13. 全球宏观 Donor

```text
ui/macro/macro-app.jsx
ui/macro/macro-data.jsx
ui/overseas/overseas-app.jsx
```

Target：

```text
frontend/src/features/global-macro/
```

最终结构：

```text
全球宏观

市场状态
├─ 中国
├─ 美国
├─ 香港
└─ 海外

宏观
├─ 利率
├─ 汇率
├─ 美元
└─ 流动性

商品
├─ 黄金
├─ 原油
├─ 铜
└─ 行业关键商品

风险
├─ 风险偏好
├─ 波动率
└─ 全球事件
```

全部形成：

```text
GlobalContextSnapshot
```

并遵守 PIT。

---

# 14. 研究经验卡

Donor：

```text
ui/cards/validation.jsx
```

Target：

```text
frontend/src/features/experience/
```

拆分：

```text
ExperienceWorkbench.tsx
ExperienceSourceLibrary.tsx
ExperienceOriginalPanel.tsx
ExperienceRefinePanel.tsx
ExperienceRulePanel.tsx
ExperienceValidationPanel.tsx
ExperienceMetrics.tsx
ExperienceKnowledgeBase.tsx
```

必须完整迁植：

```text
原
↓
原始经验 / Report / Evidence

炼
↓
LLM 提炼
机制
适用条件
失效条件
表达式

验
↓
Workflow / Factor / Case Study
IC / ICIR / 收益 / 样本 / 失败案例

用
↓
批准
进入知识库
进入 Screening
进入 Strategy
```

后端继续使用：

```text
ExperienceCard
ExperienceCardVersion
ExperienceValidation
Artifact
Provenance
```

禁止迁其 markdown 三桶数据库。

---

# 15. 研究验证工作流

Donor：

```text
ui/factor/workflow.jsx
```

Target：

```text
frontend/src/features/workflows/
```

必须迁植：

```text
Node Library
Canvas
节点结构
连接线
Inspector
Toolbar
参数配置
模型配置
指标区
运行控制
运行状态
错误状态
IC / ICIR
Portfolio
Backtest
Feature / Model
```

ASRO 后端继续强类型：

```text
WorkflowDefinition
WorkflowVersion
WorkflowNode
WorkflowEdge
WorkflowRun
WorkflowNodeRun
WorkflowOutput
```

不能再以“Run Viewer”宣布 Workflow 完成。

---

# 16. 智能选股

Donor：

```text
ui/screen/screen-app.jsx
ui/screen/screen-data.jsx
```

Target：

```text
frontend/src/features/screening/
```

必须迁植：

```text
因子/条件侧栏
筛选配置
候选池
排序
评级
Inspector
Factor IC
模型评分
研究解释
为什么入选
为什么被排除
进入研究
加入关注
加入策略
```

后端使用：

```text
ScreenDefinition
ScreenVersion
ScreeningRun
ScreeningCandidate
ExperienceCard refs
Workflow refs
Evidence refs
```

---

# 17. 策略实验室

Donor：

```text
ui/seats/luozi-foundry.jsx
ui/seats/luozi-fleet.jsx
ui/seats/luozi-panels.jsx
```

Target：

```text
frontend/src/features/strategy-lab/
```

必须迁：

```text
研究物料池
拖入策略
策略配方
规则组合
经验卡
研报
因子
选股规则
历史验证
跨标验证
市场状态验证
版本比较
失败样本
保存版本
进入盯盘
```

---

# 18. 策略盯盘

Donor：

```text
ui/seats/luozi-app.jsx
ui/seats/luozi-chart.jsx
ui/seats/luozi-panels.jsx
ui/seats/luozi-data.jsx
```

Target：

```text
frontend/src/features/strategy-monitor/
```

必须从 Monitor List 升级到：

```text
股票 + K线 + 策略 + 条件 + AI研判 + Decision + Replay
```

页面：

```text
┌──────────────────────────────────────────┐
│ 中国稀土 000831                          │
│ ¥xx.xx +x.xx%                           │
├──────────────────────────────────────────┤
│                  K Line                  │
│       ▲ Signal             ▼ Signal      │
├──────────────────┬───────────────────────┤
│ 当前策略          │ AI 研判               │
│ 触发条件          │ Evidence              │
│ 风险条件          │                       │
├──────────────────┴───────────────────────┤
│ Decision Timeline                        │
├──────────────────────────────────────────┤
│ Replay |◀ < ▶ > ▶|                      │
└──────────────────────────────────────────┘
```

后端：

```text
StrategyVersion
MonitorDefinition
Observation
Signal
DecisionRecord
Prediction
Validation
```

不迁真实券商交易执行逻辑。

---

# 19. 全库研究图谱

ASRO 继续使用自己的：

```text
ArtifactRegistry
ProvenanceEdge
```

最终链：

```text
Report
→ Experience
→ Workflow
→ Screening
→ Strategy
→ Decision
→ Prediction
→ Validation
→ Review
```

必须支持：

```text
点节点
→ 展开 upstream/downstream
→ 查看溯源
→ 保留 ResearchContext
→ 跳真实模块
```

---

# 20. Shared UI Donor

Donor：

```text
ui/_shared/tokens.css
ui/_shared/tokens-styles.css
ui/_shared/shared.jsx
```

不能原样塞进工程。

执行：

```text
拆分
→ TSX 化
→ ASRO Token 映射
→ i18n
→ Theme
```

Token Mapping 示例：

```text
--paper → --color-bg
--ink   → --color-text
--zhu   → research/positive accent
--dai   → negative
--jin   → warning
```

继续保证：

```text
A股上涨红
下跌绿
错误 danger
```

三者不能混。

---

# 21. 明确不迁植的内容

禁止进入 ASRO 正式架构：

```text
browser Babel
no-build HTML
iframe/embed architecture
localStorage business store
mock business data
window.GUANLAN_BACKEND
GL 本地 bus 实现
markdown folder database
固定 Demo records
静态假图
静态回测值
假 IC
假行情
```

保留行为，不保留基础设施。

例如：

```text
Guanlan GL.handoff
↓ 行为迁移
ASRO HandoffEnvelope + ResearchContext + Router
```

---

# 22. 迁植工程标准

每个 donor 不能复制后继续维护一个 300KB 文件。

必须：

```text
Port
→ Componentize
→ TypeScript
→ Adapterize
→ Test
```

例如 `workflow.jsx` 应拆：

```text
WorkflowStudio.tsx
WorkflowNodePalette.tsx
WorkflowCanvas.tsx
WorkflowInspector.tsx
WorkflowToolbar.tsx
WorkflowMetrics.tsx
WorkflowRunConsole.tsx
```

建议限制：

```text
普通组件 < 400 lines
核心 orchestration < 700 lines
```

超过则继续拆分。

---

# 23. Adapter Layer

新增：

```text
frontend/src/adapters/guanlan-port/
```

用途：

```text
ASRO ViewModel
→ Donor Port UI Shape
```

例如：

```text
toResearchCommandModel()
toIndustryWorkspaceModel()
toExperienceWorkbenchModel()
toWorkflowCanvasModel()
toScreeningWorkbenchModel()
toStrategyLabModel()
toStrategyMonitorModel()
```

迁植 UI 不得直接认识 ORM/Domain persistence shape。

---

# 24. Backend View APIs

新增/升级：

```text
GET /views/research-command-center

GET /views/industry/{instrument_id}
GET /views/industry/{instrument_id}/segment/{segment_id}

GET /views/global-macro

GET /views/experience/{card_id}
GET /views/workflows/{workflow_id}
GET /views/workflow-runs/{run_id}
GET /views/screening/{run_id}
GET /views/strategy/{version_id}
GET /views/monitor/{monitor_id}
```

---

# 25. 真实性要求

所有观澜 donor 中的：

```text
mock
synthetic
fallback demo
```

必须：

```text
删除
```

或明确：

```text
DEMO / 示例
```

生产状态禁止静默回退假数据。

无数据就显示：

```text
—
暂无观点
数据源暂不可用
```

---

# 26. 统一 Handoff

必须完整串：

```text
Report → Experience
Experience → Workflow
Workflow → Screening
Screening → Strategy
Strategy → Monitor
Decision → Prediction
Validation → Review
Review → Experience v2
```

AI 研究中枢能够通过自然语言触发这些 Handoff。

---

# 27. i18n / Theme / 技术 ID

迁植所有中文硬编码都要进入：

```text
i18n
```

支持：

```text
system
zh-CN
en-US
```

必须支持：

```text
Light
Dark
System
```

主界面继续禁止：

```text
run_id
artifact_id
SZSE
raw enum
```

技术字段统一进入：

```text
技术详情
```

---

# 28. Port Manifest

每个迁植模块建立：

```text
PORT-MANIFEST.md
```

内容：

```text
donor repo
donor path
donor commit
ASRO target
ported components
replaced APIs
removed mock
removed persistence
remaining drift
```

---

# 29. License / Third Party Notice

按开放许可证迁植执行。

仓库新增：

```text
THIRD_PARTY_NOTICES.md
```

记录：

```text
source repo
license
source commit
ported files
modified files
copyright notice
```

如果 donor 文件带版权头，保留要求的 Notice。

---

# 30. 迁植优先级

严格按：

```text
G0 — Shared UI Foundation
G1 — AI 研究中枢 / 深度研究
G2 — 产业研究三视图
G3 — 研究经验卡
G4 — Workflow Studio
G5 — 智能选股
G6 — 策略实验室
G7 — 策略盯盘
G8 — 全球宏观 / 海外
G9 — 全库研究图谱整合
G10 — Full Product Closure
```

---

# 31. G0 — Shared UI

迁：

```text
Tokens
Panel
Badge
Button
Toolbar
Drawer
Tooltip
Inspector
```

先统一视觉语言，再迁业务页。

---

# 32. G1 — AI 研究中枢

目标：

```text
用户输入：研究中国稀土近期资产整合信号
```

必须：

```text
左：计划实时更新
中：对话 + Evidence + Research Output
右：自动打开真实 Artifact / Workbench
```

报告完成后右栏直接显示 Report。

---

# 33. G2 — 产业研究三视图

000831：

```text
中国稀土
→ 产业研究
→ 稀土产业链
→ 点击分离冶炼
→ 环节详情
→ 全球产业坐标
→ 查看全球需求/国产替代/技术路线
```

三视图必须共享同一 `IndustrySnapshot`。

---

# 34. G3 — Experience

```text
Report
→ 炼成经验
→ 原
→ 炼
→ 验
→ 用
```

禁止做成 CRUD。

---

# 35. G4 — Workflow

必须达到 Donor 工作流主要工作台同级：

```text
Node Library
Canvas
Inspector
Config
Run
Metrics
Error
Save
Version
Handoff
```

---

# 36. G5 — Screening

必须形成：

```text
左：因子/条件
中：候选
右：研究解释
```

并支持：

```text
进入研究
加入关注
进入 Strategy
```

---

# 37. G6 — Strategy Lab

必须：

```text
物料装配
策略配置
验证
版本
失败样本
```

---

# 38. G7 — Strategy Monitor

必须：

```text
K线
Signal
Conditions
AI Judgement
Decision Timeline
Evidence
Prediction
Replay
Review
```

---

# 39. G8 — Global Macro

迁 `macro-app.jsx + overseas-app.jsx`，整合：

```text
GlobalMacroWorkspace
```

保持和产业全球坐标分离。

---

# 40. G9 — Research Graph

所有迁植后的 Workbench 必须注册：

```text
Artifact
Provenance
Handoff
```

Graph 点击任意节点能带上下文回原模块。

---

# 41. G10 — Full Product Closure

最终主闭环：

```text
AI研究中枢
↓
深度研究 / 研报
↓
研究经验
↓
研究验证工作流
↓
智能选股
↓
策略实验室
↓
策略盯盘
↓
Decision
↓
Prediction
↓
Validation
↓
研究复盘
↓
Experience v2
```

产业研究与全球宏观横向服务全链路。

---

# 42. 与 Production Integrity 双轨并行

不要因为迁植 Experience Layer 停掉生产完整性整改。

双轨：

```text
Track A — Production Integrity
Track B — Guanlan Direct Port
```

## Track A

```text
Auth REST/SSE
PostgreSQL
Scheduler
PIT
Read Model
Cost
Manifest
Concurrency
CI
```

## Track B

```text
AI中枢
产业研究
经验卡
Workflow
选股
策略实验室
策略盯盘
全球宏观
研究图谱
```

每个 Track B 模块进 main 前必须通过 Track A 的：

```text
Auth
PIT
Artifact
Handoff
```

边界。

---

# 43. 模块验收不再以“页面存在”为标准

### 产业研究 Checklist

```text
[ ] 产业阶段
[ ] 产业环节
[ ] Driver
[ ] Transmission
[ ] Momentum
[ ] Research Heat
[ ] Narrative
[ ] Stock Pool
[ ] Global Industry Coordinates
[ ] Segment Detail
[ ] Evidence
[ ] Handoff
```

### Experience Checklist

```text
[ ] Source Library
[ ] Original
[ ] Refine
[ ] Rules
[ ] Expression
[ ] Validation
[ ] Metrics
[ ] Failure Case
[ ] Approval
[ ] KB
[ ] Handoff
```

### Workflow Checklist

```text
[ ] Node Library
[ ] Canvas
[ ] Inspector
[ ] Config
[ ] Run
[ ] Metrics
[ ] Error
[ ] Save
[ ] Version
[ ] Handoff
```

### Screening Checklist

```text
[ ] Factor Library
[ ] IC
[ ] Filters
[ ] Candidate Ranking
[ ] Rating
[ ] Inspector
[ ] Why Selected
[ ] Why Rejected
[ ] Research Handoff
[ ] Strategy Handoff
```

### Strategy Lab Checklist

```text
[ ] Material Pool
[ ] Strategy Composition
[ ] Rules
[ ] Backtest
[ ] Regime
[ ] Failure Samples
[ ] Version
[ ] Compare
[ ] Monitor Handoff
```

### Monitor Checklist

```text
[ ] Kline
[ ] Signals
[ ] Conditions
[ ] AI Judgement
[ ] Decision Timeline
[ ] Evidence
[ ] Prediction
[ ] Replay
[ ] Review
```

---

# 44. 000831 最终端到端验收

```text
登录
↓
AI研究中枢
↓
“研究中国稀土近期资产整合”
↓
产业研究
  ├─ 产业链
  ├─ 全球产业坐标
  └─ 环节详情
↓
生成报告
↓
炼成经验
↓
工作流验证
↓
智能选股
↓
策略实验室
↓
策略盯盘
↓
Decision
↓
Prediction
↓
Validation
↓
复盘
↓
Experience v2
↓
全库研究图谱
```

全过程：

```text
Instrument
as_of
Report
Experience
Workflow
Strategy
```

通过 `ResearchContext` 保持，禁止用户重复输入标的。

---

# 45. 最终完成定义

只有以下全部通过：

```text
AI Research Commander parity PASS
Industry Research parity PASS
Experience parity PASS
Workflow parity PASS
Screening parity PASS
Strategy Lab parity PASS
Strategy Monitor parity PASS
Global Macro parity PASS
Research Graph integration PASS

ASRO Evidence/PIT integration PASS
Artifact/Provenance PASS
Auth PASS
Scheduler PASS
CI PASS
```

才能：

```text
Guanlan Experience Port — COMPLETE
```

---

# 46. Claude / Codex 执行指令

1. 将本文设为 Experience Layer 唯一总任务书。
2. 不再使用“参考观澜”这种模糊描述。
3. 每个模块必须指定 donor path。
4. 默认策略 `PORT_AND_ADAPT`。
5. 迁植后必须 TSX 化、组件化。
6. 不保留观澜 localStorage/mock/no-build runtime。
7. 后端全部使用 ASRO。
8. 不重新发明观澜已经成熟的工作台交互。
9. 产业链 / 全球产业坐标 / 环节详情必须整体迁。
10. 全球宏观 / 海外与产业坐标分离。
11. Experience 必须完整“原炼验用”。
12. Workflow 必须真正 Editor，不是 Run Viewer。
13. Screening 必须因子/候选/解释三面板。
14. Strategy Lab 必须有物料装配。
15. Strategy Monitor 必须有 K线/Signal/Decision/Replay。
16. Research Graph 必须跨模块 Handoff。
17. Mock 必须清零或明确 Demo。
18. 每个模块维护 `PORT-MANIFEST.md`。
19. 保留第三方 License / Notice。
20. 每模块必须与 donor 做功能级对标，不得以“页面能打开”宣布完成。

---

# 47. 一句话总纲

> **后端坚持 ASRO，前端优先迁观澜；不再重复造 Experience Layer。把观澜已经成熟的 AI 研究中枢、产业链/全球产业坐标、经验验证、工作流、选股、策略实验室、策略盯盘和全球宏观直接迁植到 ASRO，再用 Evidence/PIT/Artifact/Provenance/Version/Auth/Scheduler 将它们升级为真正可追溯、可生产运行的 A 股智能投研操作系统。**
