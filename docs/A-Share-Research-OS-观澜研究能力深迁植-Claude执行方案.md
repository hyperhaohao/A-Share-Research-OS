# A-Share Research OS × 观澜：研究能力深迁植 Claude 执行方案

> 文档性质：**正式工程执行任务书 / Claude Code 持续执行入口**
>
> 适用仓库：`hyperhaohao/A-Share-Research-OS`
>
> 研究方向：**A 股基本面 / 产业 / 事件 / 宏观 / Thesis 持续研究**
>
> 明确边界：**本轮不继续扩展 Alpha 因子、IC、ML 选股、量化回测、自动交易。**
>
> 本轮目标不是再次“迁页面”，而是将观澜中已经验证有效的 **Research Experience + Research Method + Research Workflow** 深度接入 ASRO 已有的 **Evidence / PIT / Claim / Thesis / Version / Monitor / Validation** 内核，形成真正长期演化的 A 股 Research OS。

---

# 0. Claude 执行总指令

Claude Code 读取本文件后，必须把本文件视为新的正式执行线，而不是建议文档。

执行原则：

```text
Inspect
→ Audit
→ Register Task
→ Implement
→ Test
→ Live Verify
→ Fix
→ Update State
→ Git Checkpoint
→ Continue
```

除真实外部阻塞外，不得在完成某一小阶段后询问“是否继续”。

本轮不是重新设计一个新系统，也不是 Fork 观澜。

唯一正式产品仍然是：

```text
hyperhaohao/A-Share-Research-OS
```

观澜：

```text
jesson-hh/financial-analyst
```

仅作为：

```text
Research UX donor
Research workflow donor
Research method donor
Architecture reference
Licensed-source donor（仅许可证明确允许时）
```

---

# 1. 背景与当前判断

ASRO 已经完成 Guanlan Direct Port G0–G10，当前成果主要解决了：

- 观澜式三栏 Research Commander 工作台；
- 产业研究三视图；
- 经验卡“原 → 炼 → 验 → 用”的产品形态；
- Workflow Studio；
- Screening / Strategy / Monitor 的一部分体验；
- Global Macro；
- Research Graph；
- ASRO Evidence / PIT / Artifact / Auth / Scheduler 集成。

但是：

> **G0–G10 完成 = 既定 Experience Port 清单完成。**
>
> **不等于观澜的研究能力、研究方法和研究细节已经完整吸收。**

当前仍存在明显能力差：

```text
观澜研究能力
├── 产业 Driver
├── Transmission
├── Narrative
├── 产业站位
├── 研报观点抽取
├── 引用反查校验
├── Research Commander 自主研究循环
├── 多智能体深度研报过程
├── 主线雷达
├── 海外雷达
├── 每日研究简报
├── Source Trust 分层
├── LLM Experience Refinement
├── Research Memory
└── Research Feed / Context Tooling
```

其中相当一部分目前在 ASRO 只完成了：

```text
UI skeleton
+
Read Model
+
honest empty state
```

而没有真正形成：

```text
Research Domain
+
Evidence-backed semantics
+
persistent Research State
+
continuous update loop
```

本轮就是补齐这个缺口。

---

# 2. 最终产品定位

本轮完成后，ASRO 的核心定位必须收敛为：

> **面向 A 股的长期 AI Research OS。**
>
> 不是 AI 选股器。
>
> 不是量化交易框架。
>
> 不是一次性研报生成器。
>
> 系统持续维护公司、行业、事件和宏观研究状态，并在新证据出现时自动判断其重要性、影响已有 Claim / Thesis、生成 Revision，并保留完整证据与版本历史。

核心研究链：

```text
Source
  ↓
Evidence
  ↓
PIT Snapshot
  ↓
Claim
  ↓
Thesis
  ↓
Scenario / Valuation / Risk / Catalyst
  ↓
Research Product
  ↓
Monitor
  ↓
New Evidence
  ↓
Materiality
  ↓
Claim / Thesis Impact
  ↓
Thesis Diff / Revision
  ↓
Validation / Review
  ↓
Research Experience / Memory
```

观澜中值得吸收的能力，应当被重新接入上述链路，而不能形成第二套平行数据体系。

---

# 3. 非目标 / 禁止扩展

本轮明确 **不做新的量化能力扩展**。

以下能力：

```text
Alpha 因子
IC / ICIR
Factor Zoo
ML 选股
LightGBM / XGBoost 排序
FinCast
LSTM 股票排序
量化 Workflow 节点
向量化回测
策略参数优化
自动下单
券商接入
条件单
真实交易执行
```

本轮全部：

```text
NO NEW DEVELOPMENT
```

规则：

1. **不得删除现有已完成代码和测试。**
2. 现有 Quant / Strategy 相关能力可保留。
3. 允许在导航和产品说明中降为：
   - Experimental；
   - Research Tools；
   - Optional。
4. 不得让其继续占用本轮 P0/P1 工程资源。
5. 本轮所有新增 Domain / UI / Agent / API 必须优先服务研究闭环。

---

# 4. 不允许破坏的 ASRO 核心

观澜只允许作为 donor，不能反向破坏以下 ASRO 核心原则。

## 4.1 Evidence First

必须保持：

```text
Source before Evidence
Evidence before Claim
Claim before Thesis
Thesis before Opinion
```

LLM 不能直接凭模型记忆生成正式事实。

---

## 4.2 PIT

任何历史研究必须满足：

```text
evidence.available_time <= research.as_of
```

禁止：

- 今天搜索到的未来资料污染历史研究；
- Revision 后覆盖旧 Evidence；
- 把当前互联网信息塞入旧 Snapshot。

---

## 4.3 Append-only / Versioned Research State

以下正式研究资产不得覆盖历史：

- EvidenceSnapshot；
- Thesis Version；
- Report Version；
- Prediction；
- Validation；
- Research Experience Version；
- Industry Narrative Version；
- Research Product Version。

---

## 4.4 Honest Missing Data

无真实数据时必须：

```text
暂无数据
无可靠来源
尚未确认
来源陈旧
无法计算
需要补采
```

禁止：

```text
Mock
随机值
旧数据冒充实时
LLM 猜测冒充事实
无引用观点冒充研报观点
```

---

## 4.5 单一 Research Domain

禁止为了迁观澜重新建立：

```text
GuanlanDatabase
GuanlanResearchState
第二套 Industry Domain
第二套 Evidence Store
第二套 Memory DB
第二套 Report DB
```

必须优先：

```text
reuse existing domain
→ extend existing domain
→ add typed child objects
→ only then add new domain
```

---

# 5. 执行启动：必须先把本轮注册为正式任务

当前 ASRO 的 `CLAUDE.md` 以：

```text
TASK.md
PLAN.md
STATUS.md
ROADMAP.md
```

决定工作。

因此 Claude **不得直接开始写代码**，必须先完成本轮任务注册。

---

## R0-BOOTSTRAP-01：建立正式任务线

新增文档：

```text
docs/research-deep-port/
├── 00-观澜研究能力差距矩阵.md
├── 01-研究能力深迁植架构.md
├── 02-Research-Product-Contracts.md
├── 03-Research-Memory-Contracts.md
├── 04-Source-Trust-and-Extraction.md
└── manifests/
```

本文件建议进入正式仓库：

```text
docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md
```

---

## R0-BOOTSTRAP-02：修改执行状态文件

### TASK.md

必须增加新的不可降级目标：

```text
Research Capability Deep Port
```

并明确：

> 在不扩展 Quant 的前提下，完成观澜非量化 Research Capability 的系统性吸收，并与 ASRO Evidence / PIT / Claim / Thesis / Revision / Monitor / Memory 内核融合。

---

### PLAN.md

增加：

```text
R0 → R9
```

执行阶段。

---

### STATUS.md

将：

```text
Guanlan Experience Port — PORT COMPLETE
```

保留为历史完成事实。

新增：

```text
Current Execution Line:
Guanlan Research Capability Deep Port
```

并把 `Next Action` 指向 R0 差距审计。

---

### ROADMAP.md

新增独立 Milestone 组：

```text
Research Capability Deep Port
R0–R9
```

状态：

```text
DOING
```

---

### CLAUDE.md

在启动阅读清单增加：

```text
docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md
docs/research-deep-port/00-观澜研究能力差距矩阵.md
```

并加入一条明确规则：

> 当前 Research Capability Deep Port 完成前，不以部署、量化引擎扩展、选股模型扩展作为主执行线，除非它们构成本轮阻塞。

---

# 6. R0 — Donor Delta Audit

## 目标

不要根据 README 判断观澜。

必须从源码和真实运行行为重新审计：

```text
jesson-hh/financial-analyst
```

重点只看 **非量化 Research**。

---

## 6.1 固定版本

记录：

```text
ASRO branch
ASRO commit
Guanlan branch
Guanlan commit
audit date
license state
```

当前 ASRO 历史迁植 donor baseline 为：

```text
98f1398...
```

但 Claude 执行时必须再次获取观澜最新版本，并：

```text
latest Guanlan
vs
98f1398 donor baseline
vs
current ASRO
```

做三方差异。

---

## 6.2 License Gate

必须先检查：

```text
LICENSE
README license declaration
file headers
third-party notices
```

如果仍然出现：

```text
README 声明 Apache-2.0
但仓库无 LICENSE 文件
```

则：

> 新一轮默认按 `REFERENCE_ONLY / BEHAVIORAL ADAPTATION` 处理。

禁止直接大段复制新的 donor 源代码。

必须保留：

```text
THIRD_PARTY_NOTICES.md
```

并增加本轮 donor commit 与复用说明。

---

## 6.3 必审区域

至少审计：

```text
ui/chat/
ui/console/
ui/industry/
ui/cards/
ui/graph/
docs/report_interfaces.md
docs/module_map.md
docs/research/
config/swarm/
memories/
engine/financial_analyst/buddy/
engine/financial_analyst/agents/
industry / report / news / source trust related code
MCP tool schema
agent tool profiles
```

禁止只看页面。

---

## 6.4 输出差距矩阵

每项必须给出：

```text
能力
Guanlan 实现
ASRO 当前实现
真实差距
Research Value
迁移决定
目标 ASRO Domain
目标 API
目标 UI
测试方式
状态
```

迁移决定仅使用：

```text
ADOPT_CONCEPT
ADAPT
ALREADY_SUPERIOR
REFERENCE_ONLY
REJECT_QUANT
```

---

## R0 DoD

- 三方 commit 已固定；
- License 状态已审；
- 非量化能力逐项差距已形成；
- TASK / PLAN / STATUS / ROADMAP 已注册；
- 本轮不再把 `G10 PORT COMPLETE` 误认为“研究能力迁植完成”；
- Backend / Frontend 基线测试全绿；
- Git checkpoint。

---

# 7. R1 — Research Domain Boundary & Product Repositioning

## 目标

正式把：

```text
Research Core
```

与：

```text
Optional Quant / Strategy
```

区分。

---

## 7.1 产品一级领域

最终一级 Research Domain：

```text
Research Commander
Company Research
Industry Research
Event Research
Macro / Global Research
Evidence Center
Claim / Thesis Center
Catalyst / Risk
Valuation
Research Products
Research Monitor
Research Timeline
Research Graph
Research Experience
Research Memory
```

---

## 7.2 UI 一级导航

研究核心必须优先呈现。

建议：

```text
研究
├── AI 研究中枢
├── 公司研究
├── 产业研究
├── 事件研究
├── 主线 / 海外 / 宏观
├── Thesis
├── 研究报告
├── 研究监控
├── 经验与方法
└── 研究图谱

实验
├── 智能筛选
├── Workflow
├── Strategy Lab
└── Monitor
```

不要在本轮强制删旧能力。

---

## 7.3 ADR

新增：

```text
docs/adr/ADR-Research-First-Product-Boundary.md
```

说明：

- 为什么 ASRO 不是 Quant 平台；
- 为什么保留但冻结 Quant；
- 为什么 Research State 是主内核；
- 为什么 Guanlan Research Capability 继续迁植。

---

## R1 DoD

- README 产品定位与实际战略一致；
- 一级导航研究优先；
- Quant 没被删，但不再被描述为系统核心；
- ADR 落地；
- i18n / theme 全通过；
- Git checkpoint。

---

# 8. R2 — Source Trust + Evidence-backed Extraction

这是本轮最重要的底层增强之一。

---

## 8.1 不重复造 Evidence

先检查现有：

```text
EvidenceRecord
authority
fact_status
source
available_time
content_hash
snapshot
```

如果已有字段可以表达，不建重复字段。

只在确实不足时扩展。

---

## 8.2 Source Trust 层级

建议形成稳定业务枚举，不把中文直接当协议：

```text
T0_PRIMARY_DISCLOSURE
T1_OFFICIAL_INSTITUTION
T2_PROFESSIONAL_RESEARCH
T3_MAINSTREAM_MEDIA
T4_SOCIAL_UNVERIFIED
```

建议语义：

### T0
- 上交所；
- 深交所；
- 北交所；
- 证监会；
- 上市公司正式公告；
- 定期报告。

### T1
- 国务院；
- 发改委；
- 工信部；
- 国资委；
- 地方政府；
- 央企 / 集团官方网站；
- 官方统计。

### T2
- 券商研报；
- 专业数据库；
- 行业协会；
- 经验证专业研究机构。

### T3
- 主流财经媒体；
- 正规媒体报道。

### T4
- 雪球；
- 微博；
- 论坛；
- 自媒体；
- 市场传闻。

---

## 8.3 Claim 升级规则

正式事实不能只靠 T4。

建议：

```text
Confirmed Fact
→ 必须至少 T0/T1
或多个独立 T2/T3 并明确标注“非正式披露”
```

T4 只允许：

```text
Lead
Rumor
Market Sentiment
Open Question
```

不得自动成为 `Confirmed Fact`。

---

## 8.4 LLM Extraction Contract

所有：

```text
研报观点抽取
新闻事实抽取
政策影响抽取
产业 Driver 抽取
Narrative 抽取
```

必须输出：

```json
{
  "statement": "...",
  "source_evidence_id": "...",
  "support_span": "...",
  "support_start": null,
  "support_end": null,
  "fact_status": "...",
  "confidence_basis": "...",
  "extractor": "...",
  "prompt_version": "..."
}
```

不要求一定使用字符 offset，但必须能够回到：

> 原始 Evidence 中明确支持该观点的原文片段。

---

## 8.5 Citation Verification

LLM 抽取后必须二次校验：

```text
Extract
→ Locate Support
→ Verify Entailment
→ Accept / Reject
```

若原文不能支持：

```text
REJECT
```

不能进正式 Research State。

---

## 8.6 Prompt Injection Boundary

来自：

```text
网页
新闻
F10
论坛
研报正文
上传文件
```

全部视为数据，而不是系统指令。

必须：

- schema output；
- tool allowlist；
- input quote boundary；
- 禁止 source text 覆盖 agent/system instructions；
- 对 T4 更严格。

---

## R2 DoD

- Source Trust 进入 Evidence 展示和 API；
- Research UI 可见来源级别；
- Extraction 有原文反查；
- 无引用抽取不能进入正式 Research State；
- Prompt Injection 测试存在；
- PIT 测试存在；
- 以真实 A 股公告完成 live verification；
- Git checkpoint。

---

# 9. R3 — Industry Semantic Research Engine

这是当前 ASRO 与观澜差距最大的区域之一。

现有三视图 UI 保留，不重做页面。

目标是填充当前“诚实置空”的研究语义。

---

# 9.1 Driver

需要表达：

> 什么因素正在驱动产业环节变化？

结构至少包含：

```text
driver_id
industry_id
segment_id（可空）
title
mechanism
direction
time_horizon
status
evidence_refs
first_seen
as_of
version
```

`direction` 使用稳定枚举：

```text
positive
negative
mixed
uncertain
```

禁止无证据生成假的 strength 数值。

---

# 9.2 Transmission

表达：

> 一个变化如何沿产业链传导？

至少：

```text
from_segment
to_segment
mechanism
direction
expected_lag
conditions
evidence_refs
as_of
```

示例：

```text
稀土矿供给收紧
→ 氧化物价格
→ 磁材成本
→ 磁材企业毛利
```

---

# 9.3 Narrative

Narrative 不是新闻摘要。

它应该表达：

> 市场/产业当前围绕什么核心逻辑组织信息？

至少：

```text
title
summary
supporting_claims
contrary_claims
status
first_seen
last_confirmed
invalidators
evidence_refs
```

状态建议：

```text
emerging
active
weakening
invalidated
uncertain
```

---

# 9.4 全球五轴

保留观澜有价值的表达：

```text
β Global Demand
Δ Pricing Cycle
Ω Domestic Substitution
Θ Technology Route
Ψ Theme Mapping
```

但 ASRO 必须做到：

> 每一个站位结论可追溯。

因此任何 Segment Position 必须有：

```text
axis
position / qualitative state
reason
evidence_refs
as_of
```

无源：

```text
暂无可靠定位
```

---

# 9.5 Narrative / Industry “温度”

可以保留“温度”这个研究 UX，但必须定义清楚：

它不是：

```text
股票买卖评分
```

而是：

```text
research attention / evidence intensity / narrative momentum
```

如果没有可靠可复算定义：

> 暂时不要展示数字温度。

第一阶段可以使用：

```text
升温
稳定
降温
证据不足
```

且必须给出依据。

---

# 9.6 Research Report Opinion Extraction

观澜的优势必须吸收：

```text
研报
→ 批量抽取观点
→ 绑定原文引用
→ 归入 segment / driver / narrative
```

ASRO 需要将其接入正式 Evidence。

不得建立孤立的：

```text
industry-opinions.json
```

---

## R3 UI

现有 IndustryResearchWorkspace 在真实数据到位后自动补全：

```text
产业链
├── Driver
├── Transmission
├── Narrative
├── Segment
├── Companies
├── Research Opinions
└── Evidence

全球坐标
├── β
├── Δ
├── Ω
├── Θ
└── Ψ
```

点击任意研究结论：

```text
打开 Evidence / Claim Inspector
```

---

## R3 DoD

至少用一个真实行业完整跑通：

推荐：

```text
稀土
```

验收要求：

- ≥ 真实产业环节；
- ≥ 真实 Driver；
- ≥ 真实 Transmission；
- ≥ 真实 Narrative；
- 研报/公告观点可追溯；
- 五轴至少部分有真实定位；
- 不支持的轴诚实为空；
- 新证据可形成新版 Industry Snapshot；
- 历史 Snapshot 可复原；
- UI / API / Test / Live Verify 全通过；
- Git checkpoint。

---

# 10. R4 — Research Commander Autonomous Research Loop

当前 ASRO 已有观澜式 Commander UI。

本阶段不再重做 UI 外壳，而是增强“自主研究能力”。

---

## 10.1 Research Intent Router

至少支持：

```text
company
industry
event
earnings
policy
mainline
overseas_mapping
thesis_review
comparison
```

---

## 10.2 Research Plan

Research Plan 必须结构化，而不是只显示自然语言步骤。

建议：

```text
objective
as_of
scope
questions[]
required_sources[]
steps[]
expected_artifacts[]
completion_criteria[]
```

---

## 10.3 Missing Data Loop

Agent 不得：

```text
查不到
→ 直接写报告
```

而应：

```text
Missing data
→ ResearchRequest
→ 补采
→ 仍失败
→ 显式 Missing Data
→ 调整结论置信边界
```

复用现有 `ResearchRequest`。

---

## 10.4 Agent Profiles

至少分：

```text
research-general
company
industry
event
macro
evidence
reviewer
```

工具暴露必须按 profile 限制。

禁止 Research Agent 获得未来交易/量化工具后自行偏航。

---

## 10.5 Multi-agent Progress

深度研究运行必须支持：

```text
planned
collecting
analyzing
waiting_data
reviewing
synthesizing
quality_gate
completed
blocked
```

前端可以看到：

```text
哪个公司研究 Agent
正在做什么
用了什么证据
当前缺什么
哪个步骤失败
```

---

## 10.6 Autonomous Loop

标准长研究循环：

```text
Understand Question
→ Build Plan
→ Collect Evidence
→ Analyze
→ Identify Missing / Conflict
→ Collect Again
→ Build Claims
→ Build / Compare Thesis
→ Counter Thesis Review
→ Scenario
→ Valuation if applicable
→ Quality Gate
→ Research Product
→ Register Monitor
```

必须设置：

```text
max iterations
cost budget
tool budget
loop termination
```

避免 Agent 无限循环。

---

## 10.7 Thesis Mutation Rule

Agent 不能静默覆盖 Current Thesis。

必须：

```text
new evidence
→ proposed impact
→ Thesis Diff
→ quality gate
→ new version
```

---

## R4 DoD

真实场景：

```text
研究中国稀土近期资产整合信号
```

必须能够：

1. 自动识别为：
   - company；
   - event；
   - SOE restructuring；
2. 自动制定计划；
3. 优先 T0/T1；
4. 识别缺失数据；
5. 建立 Claims；
6. 形成 Thesis；
7. 给出 Risk / Invalidator；
8. 输出 Research Product；
9. 注册持续监控；
10. 全过程 UI 可见。

Git checkpoint。

---

# 11. R5 — Research Product System

ASRO 不应只有通用 Report。

建立正式：

```text
ResearchProduct
```

概念。

优先复用现有 Report / Artifact / Version 基础。

如果可以通过类型扩展表达，则不要再建平行 Report 系统。

---

# 11.1 产品类型

P0：

```text
COMPANY_DEEP_DIVE
INDUSTRY_DEEP_DIVE
EVENT_INVESTIGATION
THESIS_REVIEW
```

P1：

```text
EARNINGS_REVIEW
POLICY_IMPACT
MAINLINE_RADAR
OVERSEAS_MAPPING
DAILY_RESEARCH_BRIEF
```

---

# 11.2 每种产品必须有 Contract

每个 Research Product 定义：

```text
Intent
Required Evidence
Optional Evidence
Required Sections
PIT Rules
Claim Requirements
Valuation Requirement
Contrary Evidence Requirement
Missing Data Behavior
Quality Gate
Output Artifacts
Monitor Behavior
```

不得仅通过 Prompt 模板隐式约定。

---

# 11.3 EVENT_INVESTIGATION

这是 ASRO 需要重点做强的产品。

至少覆盖：

```text
并购重组
重大资产重组
资产注入
同业竞争解决
央地资产划转
股权变化
监管审批
重大订单
政策变化
业绩预告
管理层变化
```

输出必须包含：

```text
事件事实
时间线
相关主体
证据
当前阶段
前置信号
正式信号
影响路径
支持 Thesis
反对 Thesis
下一关键节点
Invalidators
监控清单
```

---

# 11.4 MAINLINE_RADAR

不是“涨幅榜”。

应表达：

```text
今日/近期重要叙事
→ 证据
→ 驱动
→ 涉及产业
→ A股映射
→ 支持/反对证据
→ 持续时间
→ 待验证问题
```

---

# 11.5 OVERSEAS_MAPPING

标准链：

```text
海外事件
→ 全球产业影响
→ 中国产业映射
→ A 股公司映射
→ Evidence
→ Potential Impact
```

禁止：

```text
海外股涨了
→ 自动推荐 A 股
```

---

# 11.6 Daily Research Brief

不是行情播报。

建议：

```text
新重大 Evidence
Thesis materially changed
New Event Signal
Industry Narrative Change
Upcoming Catalyst
Open Research Request
Yesterday Validation Result
```

---

## R5 DoD

至少：

```text
Company Deep Dive
Industry Deep Dive
Event Investigation
Thesis Review
Mainline Radar
Overseas Mapping
```

真实可运行。

Research Product：

- 有 Schema；
- 有版本；
- 有 Artifact；
- 有 Evidence；
- 有 Quality Gate；
- 可进入 Graph；
- 可导出 Markdown；
- 可由 Commander 调用；
- Git checkpoint。

---

# 12. R6 — Experience “原 → 炼 → 验 → 用”研究化改造

ASRO 已有 Experience Workbench。

本阶段重点迁入观澜中尚未真正吸收的：

```text
LLM Refinement
```

但不能继续以“炼成 Factor”为目标。

---

## 12.1 原

输入可以来自：

```text
Research Report
Evidence
Claim
Thesis Review
Analyst Note
Postmortem
User Note
```

必须保留 provenance。

---

## 12.2 炼

LLM 必须提炼：

```text
Observation
Mechanism
Preconditions
Expected Outcome
Counter Example
Failure Conditions
Applicable Scope
Invalidators
Research Checklist
```

---

## 12.3 验

本轮非量化验证。

支持：

```text
case validation
historical evidence validation
counterexample search
cross-company validation
cross-cycle validation
expert/user review
prediction validation link
```

禁止为了保留观澜原设计而强制 IC / 回测。

---

## 12.4 用

批准后的 Experience 进入：

```text
Research Playbook
```

允许 Agent 在后续相似任务自动检索。

但：

> Memory / Playbook 不能直接作为事实 Evidence。

它只作为：

```text
research heuristic
research method
question generator
checklist
```

正式结论仍需新 Evidence 支持。

---

## 12.5 示例

将：

> “央企解决同业竞争时，如果表述由‘适时解决’升级为明确实施方案，可能意味着资本运作进入加速阶段。”

炼为：

```text
Title:
同业竞争措辞升级

Mechanism:
监管压力 + 集团资产证券化安排具体化

Signal Ladder:
原则性解决
→ 明确时限
→ 制定方案
→ 标的明确
→ 审计评估
→ 正式重组

Applicable:
央企控股上市平台

Counterexamples:
...

Invalidators:
集团否认
资产明确划给其他平台
监管政策变化

Checklist:
公告
国资委
集团
地方国资
产权交易
审计评估
```

以后研究类似标的时自动调用。

---

## R6 DoD

- LLM Refinement 真运行；
- 输出结构稳定；
- 原文与提炼结果均保留；
- 支持非量化验证；
- 批准门仍由后端强制；
- Playbook 可检索；
- Playbook 不被当作 Evidence；
- 真实案例验证；
- Git checkpoint。

---

# 13. R7 — Research Memory

Experience ≠ Memory。

必须区分：

```text
Evidence
Research Experience
Research Memory
```

---

## 13.1 Memory 类型

```text
Company Memory
Industry Memory
Event Playbook
Research Method
Known Failure
Research Checklist
User Research Preference
```

最后一项仅保存研究偏好，不保存密码、Key 等敏感信息。

---

## 13.2 Memory 条目

至少：

```text
memory_id
type
title
content
scope
source_artifacts
source_experiences
status
version
created_at
updated_at
```

---

## 13.3 Retrieval

检索必须支持：

```text
instrument
industry
event_type
research_intent
tags
time
```

---

## 13.4 Memory 使用边界

Agent Prompt 必须区分：

```text
Evidence Context
Research Memory Context
User Request
```

Memory 只帮助：

- 提问题；
- 选择方法；
- 找风险；
- 找反例；
- 复用研究框架。

不能成为：

> “事实依据”。

---

## 13.5 Memory 更新

研究结束后：

```text
Research Run
→ Validation / Review
→ Candidate Memory
→ Review / Auto-safe Gate
→ Versioned Memory
```

不得每次聊天全部自动写正式 Memory。

---

## R7 DoD

- Memory Domain/API/UI 完整；
- Experience 可转 Playbook / Memory；
- Agent 可检索；
- Source 与 Memory 在 UI/Prompt 中严格区分；
- 版本可回滚；
- Graph 可追踪来源；
- Git checkpoint。

---

# 14. R8 — Research Inbox / Continuous Monitoring / Thesis Diff

ASRO 已有 Monitor / Materiality，应当将其产品化。

---

## 14.1 Research Inbox

新增研究入口：

```text
Research Inbox
```

聚合：

```text
New Evidence
Important Event
Materiality Alert
Conflicting Evidence
Thesis Impact
Upcoming Catalyst
Failed Collection
Open Research Request
Prediction Due
Validation Result
```

---

## 14.2 Materiality

Materiality Judge 不应该只判断：

```text
是否重要
```

还必须判断：

```text
affected_claims[]
affected_theses[]
affected_industries[]
affected_catalysts[]
affected_risks[]
suggested_action
```

---

## 14.3 Thesis Diff

新证据进入后：

```text
Old Thesis
+
New Evidence
↓
Impact Analysis
↓
Proposed Thesis Revision
```

UI 必须显示：

```diff
+ 新增支持证据
- 被削弱的旧 Claim
~ 风险概率上升
+ 新 Catalyst
- 一个旧假设失效
```

不需要使用 Git diff 文本格式实现，但体验必须能清晰比较。

---

## 14.4 Monitor 类型

至少：

```text
Company Monitor
Industry Monitor
Event Monitor
Thesis Monitor
Catalyst Monitor
```

---

## 14.5 A / B 级信号模式

为事件型研究提供可配置 Signal Ladder。

以重组为例可表达：

```text
B 前置信号
→ A 正式信号
```

Signal Rule 必须是：

```text
research rule
```

而不是模型凭空判断。

每次命中必须展示证据。

---

## R8 DoD

以：

```text
000831 中国稀土资产整合
```

完整演示：

```text
已有 Thesis
↓
新公告/集团信息进入
↓
Inbox Alert
↓
Materiality
↓
关联 Claim
↓
Signal Upgrade
↓
Thesis Diff
↓
生成新 Thesis Version
↓
更新 Event Investigation
↓
Research Graph
```

全链真实运行。

Git checkpoint。

---

# 15. R9 — Research Graph + Final Product Closure

---

## 15.1 Graph Node Types

至少包括：

```text
Evidence
Snapshot
Claim
Thesis
ThesisVersion
IndustryDriver
Transmission
Narrative
ResearchProduct
ResearchRun
Prediction
Validation
Experience
Memory
Event
Catalyst
Risk
```

---

## 15.2 Graph Edge Types

建议：

```text
supports
contradicts
derived_from
generated_from
updates
invalidates
affects
belongs_to
transmits_to
monitors
validated_by
refined_into
remembered_as
```

---

## 15.3 Context Handoff

从任意：

```text
Evidence
Claim
Industry Driver
Narrative
Thesis
Research Product
Memory
```

可以：

```text
Open in Research Commander
```

并带完整 context。

不得靠 localStorage 临时信箱。

继续使用 ASRO 服务端持久化 Handoff。

---

# 16. 关键 UI 工作台

最终必须形成以下研究工作台。

---

## 16.1 Research Commander

三栏保持：

```text
左：Plan / Session / Research Progress
中：Conversation / Evidence / Agent Steps
右：Dynamic Research Workbench
```

右侧动态出现：

```text
Company Snapshot
Evidence Inspector
Industry Driver
Event Timeline
Thesis Diff
Report
Research Request
Memory Candidate
```

---

## 16.2 Company Research

必须至少看到：

```text
Business
Financials
Management
Competition
Valuation
Claims
Current Thesis
Catalyst
Risk
Open Questions
Timeline
Recent Evidence
```

---

## 16.3 Industry Research

必须至少：

```text
Chain
Drivers
Transmission
Narratives
Segments
Companies
Global Position
Research Opinions
Evidence
```

---

## 16.4 Event Research

必须：

```text
Event Timeline
Entities
Signal Level
Evidence
Claims
Impact Path
Affected Thesis
Next Milestone
Monitor
```

---

## 16.5 Thesis Center

这是核心工作台。

必须至少：

```text
Current Thesis
Confidence Basis（文字依据，不要求虚假分数）
Supporting Claims
Contrary Claims
Assumptions
Catalysts
Risks
Invalidators
Open Questions
Related Industry Narratives
Version History
Thesis Diff
```

---

# 17. 数据模型原则

不得为了快速实现把所有新能力塞入 JSON blob。

以下对象如果满足：

```text
需要独立版本
需要被引用
需要进入 Graph
需要独立监控
需要 PIT
需要跨 Research Product 使用
```

则应该成为明确可寻址对象。

但同时遵守：

> 不重复已有 Domain。

Claude 必须在新增表前先说明：

```text
为什么现有模型无法表达？
为什么不能作为现有对象的 typed child？
为什么需要独立生命周期？
```

---

# 18. Agent 设计原则

---

## 18.1 不追求 Agent 数量

观澜 24 Agents 是 donor 经验，不是 ASRO KPI。

ASRO 不以：

```text
更多 Agent = 更强
```

为目标。

Agent 数量以职责边界为准。

---

## 18.2 建议职责

```text
Research Commander
Evidence Collector
Company Analyst
Industry Analyst
Event Analyst
Macro Analyst
Valuation Analyst
Contrarian Reviewer
Evidence Verifier
Research Synthesizer
```

可根据现有 8 Analyst 架构复用，不强制重建。

---

## 18.3 Reviewer

任何 Deep Research 在进入正式 Report / Thesis Version 前：

```text
Contrarian Review
+
Evidence Review
+
Quality Gate
```

至少检查：

- 关键事实有无来源；
- 支持和反对证据是否失衡；
- 是否偷用未来信息；
- 是否把假设当事实；
- 是否引用不可信来源；
- 是否存在重要 Missing Data；
- 是否遗漏关键 Invalidator。

---

# 19. 测试战略

所有阶段必须：

```text
Unit
Integration
E2E
Live Verification
Reviewer Pass
```

---

## 19.1 Fixture

Fixture 可以测试：

```text
determinism
PIT
state machine
API contract
failure path
```

但不能替代 Source / Research Capability 的 Live Verification。

---

## 19.2 必测安全边界

```text
Prompt Injection
Citation mismatch
Future Evidence leak
Source trust escalation
Memory mistaken as Evidence
Thesis overwrite
Duplicate evidence
Revision consistency
Agent infinite loop
Tool profile escape
```

---

# 20. 本轮黄金验收场景

整个 R0–R9 最终必须以一个真实 A 股复杂事件跑通。

推荐：

```text
000831 中国稀土
```

任务：

> 研究中国稀土近期资产整合 / 资产注入 / 同业竞争解决信号，并持续监控研究结论是否发生实质变化。

---

## 20.1 完整验收链

```text
用户研究问题
↓
Research Commander
↓
Intent = Company + Event + Industry
↓
Research Plan
↓
T0/T1 Evidence Collection
↓
补充 T2/T3
↓
Event Timeline
↓
A/B Signal Classification
↓
Industry Driver / Narrative
↓
Claims
↓
Current Thesis
↓
Contrary Thesis
↓
Scenario / Risk / Catalyst
↓
Event Investigation Product
↓
Monitor
↓
New Evidence
↓
Materiality
↓
Signal Upgrade / Downgrade
↓
Thesis Diff
↓
New Thesis Version
↓
Research Product Revision
↓
Validation / Review
↓
Experience / Memory Candidate
↓
Research Graph
```

---

## 20.2 验收要求

必须能回答：

1. 当前结论是什么？
2. 结论由哪些 Claim 构成？
3. 每个 Claim 来自哪些 Evidence？
4. Evidence 当时是否已经公开？
5. 哪些是正式事实？
6. 哪些只是市场共识？
7. 哪些只是线索/传闻？
8. 当前最重要的反方证据是什么？
9. 什么事件会使 Thesis 失效？
10. 与上一版本相比发生了什么变化？
11. 新证据为什么被判断为 Material？
12. 系统以后要监控什么？
13. 本次研究沉淀了什么可复用 Experience？
14. 哪些 Memory 只是方法，而不是事实？

---

# 21. 文档同步要求

每个阶段完成后更新：

```text
STATUS.md
PLAN.md
```

Milestone 状态变化：

```text
ROADMAP.md
```

架构决策：

```text
docs/adr/
```

研究深迁植 Manifest：

```text
docs/research-deep-port/manifests/
```

建议：

```text
R0-MANIFEST.md
R1-MANIFEST.md
...
R9-MANIFEST.md
R10-CLOSURE.md
```

即使执行阶段叫 R0–R9，最终增加 `R10-CLOSURE.md` 做总验收。

---

# 22. Git Checkpoint

一个完整可验证阶段：

```text
=
一个 Git checkpoint
```

推荐 commit：

```text
docs(research-port): register deep research capability track
feat(research-trust): source trust and citation verification
feat(industry): evidence-backed drivers and transmission
feat(commander): autonomous deep research loop
feat(research-products): typed research product contracts
feat(experience): non-quant research refinement
feat(memory): versioned research memory
feat(monitor): thesis impact and revision workflow
feat(graph): deep research provenance integration
docs(research-port): R10 closure
```

实际可根据变更拆分，但禁止一个数小时巨大不可审计 commit。

---

# 23. 禁止事项

Claude 本轮禁止：

```text
1. 因为 G10 叫 PORT COMPLETE 就跳过 donor 深审。
2. 重新做一套 Guanlan backend。
3. 复制 donor localStorage 业务状态。
4. 用 Mock 补产业 Driver / Narrative。
5. 用 LLM 猜数据填空。
6. 把 Experience / Memory 当 Evidence。
7. 让 T4 传闻直接生成 Confirmed Claim。
8. 绕过 PIT。
9. 覆盖旧 Thesis。
10. 为了“漂亮”生成无法解释的温度/置信度数字。
11. 为了复刻观澜继续投入 Factor / IC / ML / Backtest。
12. 删除现有 Quant 功能来证明“研究优先”。
13. 大范围无关重构。
14. 只改 UI 不落 Domain / API / Test。
15. 只写设计文档而不继续实际实现。
16. 完成一个阶段后询问是否继续。
```

---

# 24. 完成定义

本轮只有满足以下全部条件才可宣布完成。

```text
R0–R9 完成
AND
Research Product 定位完成
AND
Source Trust 完成
AND
Citation Verification 完成
AND
Industry Driver 完成
AND
Transmission 完成
AND
Narrative 完成
AND
Research Commander Autonomous Loop 完成
AND
Research Products 完成
AND
Non-Quant Experience 完成
AND
Research Memory 完成
AND
Research Inbox / Thesis Diff 完成
AND
Research Graph 完成
AND
000831 黄金场景真实跑通
AND
Backend Tests PASS
AND
Frontend Tests PASS
AND
Build PASS
AND
E2E PASS
AND
Live Verify PASS
AND
Final Reviewer PASS
AND
文档与代码一致
```

最终：

```text
docs/research-deep-port/R10-CLOSURE.md
```

必须逐项给出 PASS / FAIL 与真实证据。

不能写：

```text
基本完成
主体完成
后续可优化
```

任何属于本文件 P0/P1 的内容，未完成就不能宣布本轮结束。

---

# 25. 建议优先级

## P0 — 必须先完成

```text
Source Trust
Citation Verification
Industry Driver
Transmission
Narrative
Research Commander Autonomous Loop
Deep Research Agent Progress
Event Investigation
Thesis Review / Thesis Diff
```

## P1 — 本轮必须完成

```text
Mainline Radar
Overseas Mapping
Daily Research Brief
Non-Quant Experience Refinement
Research Memory
Research Inbox
Graph integration
```

## P2 — 本轮可延后到 R9 后的增强

```text
CmdK research tool palette
更复杂产业动画
高级 Narrative 可视化
额外 Research Product 模板
更多行业预置
```

P2 不能阻塞本轮核心完成。

---

# 26. Claude 第一次启动时直接执行

Claude 收到本文件后，不要重新给用户输出方案。

直接执行：

```text
pwd
git status
git log --oneline -10

阅读：
TASK.md
AGENTS.md
CLAUDE.md
PLAN.md
STATUS.md
ROADMAP.md
README.md
本文件
docs/port/G10-CLOSURE.md
docs/port/PORT-MANIFEST-G1.md
docs/port/PORT-MANIFEST-G2.md
docs/port/PORT-MANIFEST-G3.md

然后：

1. 固定 ASRO 当前 commit。
2. 固定 Guanlan 当前 commit。
3. 核查 License。
4. 审计 Guanlan 非量化 Research 能力。
5. 生成 docs/research-deep-port/00-观澜研究能力差距矩阵.md。
6. 更新 TASK / PLAN / STATUS / ROADMAP / CLAUDE。
7. 跑当前 backend/frontend/E2E 基线。
8. Git checkpoint。
9. 进入 R1。
10. 持续执行至 R10-CLOSURE。
```

---

# 27. 给 Claude 的最终执行提示词

可直接在 Claude Code 中输入：

```text
读取并严格执行：
docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md

这是新的正式持续执行任务，不是咨询或设计讨论。

先按 R0 完成：
- 当前仓库状态确认；
- ASRO / 观澜 commit 固定；
- License Gate；
- 非量化 Research Capability 源码级差距审计；
- TASK.md / PLAN.md / STATUS.md / ROADMAP.md / CLAUDE.md 执行线注册；
- 全量基线测试；
- Git checkpoint。

随后按照 R1 → R9 连续实现，每阶段必须 Implement → Build → Test → Live Verify → Fix → Update State → Git Checkpoint。

本轮核心目标是：
把观澜中优秀的非量化 Research Experience / Research Workflow / Research Method 深度融合到 ASRO 的 Evidence / PIT / Claim / Thesis / Version / Monitor / Validation 内核。

明确禁止继续扩展 Alpha / IC / ML 选股 / 量化回测 / 自动交易。

除真实外部阻塞外，不要询问我“是否继续”，不要只输出方案，不要用 Mock 或 TODO 宣布完成。

最终以 000831 中国稀土资产整合研究作为黄金 E2E 场景，并生成：
docs/research-deep-port/R10-CLOSURE.md
逐项证明全部能力真实完成。
```

---

# 28. 最终架构目标

```text
                         A-Share Research OS

                         Research Commander
                                  │
             ┌────────────────────┼────────────────────┐
             ↓                    ↓                    ↓
       Company Research     Industry Research      Event Research
             │             Driver / Narrative        │
             │              Transmission             │
             └────────────────────┼────────────────────┘
                                  ↓
                          Evidence / Source Trust
                                  ↓
                              PIT Snapshot
                                  ↓
                                Claim
                                  ↓
                                Thesis
                ┌─────────────────┼─────────────────┐
                ↓                 ↓                 ↓
             Catalyst            Risk            Invalidator
                └─────────────────┼─────────────────┘
                                  ↓
                         Research Products
                                  ↓
                         Continuous Monitor
                                  ↓
                           Materiality Judge
                                  ↓
                             Thesis Diff
                                  ↓
                          Version / Validation
                                  ↓
                   Experience / Research Memory
                                  ↓
                          Research Playbook
                                  │
                                  └────→ 下一轮研究
```

最终原则：

> **观澜提供研究体验和研究方法；ASRO 提供更严格的 Research State、Evidence、PIT、Thesis 与长期演化能力。**
>
> 本轮完成的标准不是“看起来像观澜”，而是：
>
> **观澜中有价值的非量化研究能力，已经成为 ASRO 可追溯、可验证、可持续更新的一等研究能力。**
