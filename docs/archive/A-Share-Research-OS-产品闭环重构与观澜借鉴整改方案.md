# A-Share Research OS 产品闭环重构与观澜借鉴整改方案
## Product Workflow Rebuild

> 适用仓库：
>
> `https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 参考项目：
>
> `https://github.com/jesson-hh/financial-analyst`
>
> 本文档用于 Claude Code / Coding Agent 直接执行产品体验与业务闭环整改。
>
> 本轮不是继续补零散页面，也不是推翻后端 Research Core。
>
> 核心目标：
>
> > **把当前“后端对象/API 的页面集合”重构成“围绕一只股票完成关注 → 研究 → 报告 → 跟踪 → 预测 → 验证”的真实研究工作台。**

---

# 1. 当前最核心的问题

当前系统后端 Research Core 已经比较完整，但产品层仍然存在明显断层：

```text
Search
Watchlist
Pipeline
Tasks
Reports
Predictions
Workspace
```

这些模块目前基本是：

```text
各自调用一个 API
↓
显示一张表 / 一个列表
↓
结束
```

而不是：

```text
用户选择标的
↓
进入研究上下文
↓
执行研究
↓
看到研究过程
↓
得到结论
↓
打开报告
↓
加入持续跟踪
↓
生成预测
↓
等待验证
↓
回顾预测准确性
```

因此用户会产生非常直接的感受：

> **“点了以后不知道干什么，也不知道系统做了什么，更不知道下一步在哪里。”**

这不是 UI 美化问题，而是：

> **Product Workflow 没有建立。**

---

# 2. 观澜真正值得借鉴的地方

不要照搬观澜源码和视觉。

重点借鉴它的产品结构。

观澜的核心不是“页面很多”，而是：

```text
一个总控入口
+
任务计划
+
研究过程
+
研究产物
+
跨模块 handoff
+
共享研究档案
```

其典型工作方式：

```text
用户一句话
↓
Agent 拆解计划
↓
执行工具
↓
左栏逐项显示进度
↓
中间输出研究结论
↓
右侧自动打开真实产物
↓
继续操作
```

观澜工具结果不是：

```text
run_started
analyst_ready
report_ready
```

这种开发者事件。

而是：

```text
artifact:
  kind
  page
  payload
  ref
```

然后：

```text
artifact
→ handoff
→ 自动打开对应工作台
```

A-Share Research OS 应借鉴这种：

> **“结果自动接下一步”**

而不是继续展示 API 状态。

---

# 3. 产品主线必须重新定义

最终产品主线统一成：

```text
发现股票
↓
关注
↓
标的工作台
↓
立即研究 / 创建持续研究
↓
研究运行
↓
研究结果
↓
研究报告
↓
预测
↓
持续监控
↓
增量研究
↓
验证
↓
研究经验
```

其中：

```text
Instrument Workspace
```

必须成为所有模块的中心。

---

# 4. 最终导航建议

当前顶部导航不要继续按后端数据对象划分。

推荐：

```text
研究总览
关注池
研究任务
报告库
预测验证
```

其中：

```text
标的工作台
```

不是一级菜单。

它通过：

```text
搜索
关注池
报告
任务
预测
```

进入。

---

# 5. 借鉴观澜：新增 Research Command Center

建议将当前 HomePage 重构为：

```text
研究总控 / Research Command Center
```

类似观澜“帷幄”的产品理念，但保持 A-Share Research OS 自身架构。

布局：

```text
┌────────────┬───────────────────────┬────────────────────┐
│ 左：研究计划 │ 中：当前研究 / 结论     │ 右：研究产物         │
│            │                       │                    │
│ 最近研究    │ 标的搜索               │ 标的摘要             │
│ 正在运行    │ 研究输入               │ Report              │
│ 关注动态    │ Pipeline Progress     │ Evidence            │
│ 任务状态    │ Analyst Result        │ Valuation           │
│            │ Final Summary         │ Prediction          │
└────────────┴───────────────────────┴────────────────────┘
```

第一版不一定需要 Agent 对话。

可以先做：

```text
Instrument Search
→ Select Instrument
→ Action
```

Actions：

```text
立即研究
加入关注
创建持续研究
查看历史报告
查看预测
```

---

# 6. 用户问题 1：关注列表新增股票后无法正常查看

## 当前真实原因

当前 Watchlist：

```text
输入股票代码
↓
resolve_instrument_id()
↓
保存 instrument_id
```

`resolve_instrument_id()` 可以接受几乎所有合法 A 股代码。

例如：

```text
000831
→ SZSE:000831
```

但是：

```text
GET /instruments/{instrument_id}
```

只从：

```text
default_catalog()
```

读取。

当前静态 catalog 只有十几只 seed 股票。

因此：

```text
000831
→ Watchlist 成功
→ 点击 SZSE:000831
→ Instrument Workspace
→ Instrument API 找不到
```

这是架构不一致。

---

## 必须整改：Instrument Identity 统一

不能继续：

```text
Watchlist 支持全 A 股
Instrument Workspace 只支持 12 只
```

建立统一：

```text
InstrumentResolver
```

流程：

```text
用户输入 000831
↓
Normalize
↓
Local Instrument Registry 查找
↓
不存在
↓
通过真实 Source 获取股票基础身份
↓
upsert Instrument
↓
返回 InstrumentProfile
```

至少：

```text
instrument_id
code
exchange
name
board
listed_status
industry
sector
```

---

## Watchlist 不能再只是代码列表

当前：

```text
SZSE:000831   ×
```

用户当然不知道下一步。

改成卡片：

```text
中国稀土
000831 · 深市主板

24.83   +2.31%

最近研究：
2026-08-28 18:32

研究判断：
中性偏多 · 72%

关键变化：
集团资产整合预期升温

数据状态：
公告 ✓ 财务 ✓ 新闻 ✓ 行情 ✓

[打开工作台]
[立即研究]
[查看报告]
[持续跟踪]
```

没有研究时：

```text
暂无研究结果

[立即研究]
```

---

# 7. 用户问题 2：研究总览标的搜索没有实际作用

## 当前问题

当前 InstrumentSearch：

```text
搜索
↓
显示 code / name / exchange
↓
结束
```

搜索结果：

```text
不能点击
不能进入 Workspace
不能关注
不能研究
```

并且搜索仅基于静态 12 只股票 catalog。

因此搜索：

```text
000831
```

得到：

```text
暂无匹配
```

是当前架构必然结果。

---

## 搜索应该变成 Global Instrument Launcher

结果格式：

```text
中国稀土
000831 · SZSE · 主板
稀土

[打开]
[立即研究]
[+ 关注]
```

点击整行：

```text
→ Instrument Workspace
```

---

## 搜索必须支持全 A 股

优先：

```text
代码精确搜索
```

如果本地没有：

```text
on-demand resolve
```

其次支持：

```text
股票名称
拼音 / 简称
alias
```

不要要求把 5000 多只股票全部硬编码。

推荐：

```text
Local Instrument Registry
+
Remote Resolver
+
Cache
```

---

# 8. 用户问题 3：研究管线执行后只出现列表，看不懂在做什么

## 当前问题非常明确

当前 HomePage 的 ResearchPipelineCard：

```text
点击运行
```

实际上代码甚至硬编码：

```text
instrument=600519
```

也就是说：

> 用户搜索什么股票，与首页 Pipeline 没关系。

这是必须优先删除的逻辑。

---

## 当前 Pipeline UI 只展示开发者事件

例如：

```text
run_started
source_progress
evidence_ready
quality_gate
analyst_progress
valuation_ready
report_ready
run_completed
```

这是：

```text
调试控制台
```

不是用户研究界面。

---

## 改成 Research Run Workspace

执行研究：

```text
中国稀土 000831

正在进行完整研究
```

### 阶段 1：数据收集

```text
✓ 实时行情
✓ 公司公告      32 条
✓ 财务报告       8 期
✓ 新闻          24 条
✓ 资金流
✓ 行业
⚠ 宏观政策       部分数据
```

### 阶段 2：分析

```text
✓ 财务分析
✓ 公司事件
✓ 新闻分析
✓ 行业分析
✓ 资金分析
✓ 市场分析
✓ Quant
```

### 阶段 3：研究合成

```text
✓ Claims           18
✓ Thesis            3
✓ Bull / Bear
✓ Valuation         4 种方法
✓ Scenarios         3
✓ Risks             6
```

### 阶段 4：完成

```text
研究完成

核心判断：
中性偏多

置信度：
72%

主要 Thesis：
集团资产整合是未来估值弹性的主要来源

估值：
Base 31.20

关键风险：
资产注入时间无法确定

[查看完整报告]
[打开标的工作台]
[创建持续跟踪]
[生成预测]
```

---

## 原始 SSE Events 保留

但是放在：

```text
高级详情 / Debug
```

默认用户不看：

```text
run_started
claim_compiled
```

---

# 9. 用户问题 4：Watchlist 输入 000831 后只得到 SZSE:000831

这和问题 1 是同一根因，但产品层还需要继续处理。

禁止用户主界面以：

```text
SZSE:000831
```

作为主要标题。

Canonical ID 只能用于：

```text
URL
API
数据库
Debug
```

用户界面始终：

```text
中国稀土
000831
```

次要位置：

```text
SZSE
```

---

# 10. 用户问题 5：研究任务创建完了没有结果

## 当前问题

TasksPage 当前本质是 CRUD：

```text
创建 Task
↓
显示 Task
↓
Scheduler Tick
↓
claimed=1
success=1
```

用户根本不关心：

```text
claimed
```

用户关心：

```text
它研究了什么？
有没有变化？
报告在哪里？
下一次什么时候运行？
```

---

## 当前创建任务还有一个明显产品问题

页面创建任务时：

```text
schedule = interval:0
```

被硬编码。

UI 根本没有真正的调度设置。

---

## 研究任务必须变成“持续研究任务”

Task Card：

```text
中国稀土 · 000831

任务：
持续研究

频率：
每天 08:30
重大公告立即检查

状态：
运行正常

上次执行：
今天 18:32

结果：
发现 3 条新 Evidence
判定 DELTA_RESEARCH

影响：
1 条 Thesis 被更新

最新报告：
v7 · 今天 18:33

下次执行：
明天 08:30

[查看本次运行]
[打开最新报告]
[查看变更]
[暂停]
```

---

## Scheduler Tick 不应该出现在普通用户首页

```text
手工执行 Scheduler Tick
```

属于：

```text
运维 / Debug
```

不应该成为主要业务按钮。

普通用户按钮：

```text
立即运行
```

对应：

```text
run this task now
```

而不是：

```text
tick global scheduler
```

---

## 增加 Task Detail / Run History

```text
Task
├─ Current Config
├─ Next Run
├─ Run History
│   ├─ Run #24
│   ├─ Run #23
│   └─ Run #22
├─ Evidence Changes
├─ Thesis Changes
├─ Reports
└─ Predictions
```

---

# 11. 用户问题 6：预测页面没有东西

## 根因

当前 ResearchPipeline：

```text
完整研究
→ Report
```

**没有自动创建 Prediction。**

PredictionsPage 只是：

```text
到 Watchlist 找 instrument
↓
查询已有 Prediction
↓
如果没有就空
```

所以这是：

> **没有生产者，却做了消费者页面。**

---

## 必须建立 Prediction Creation Flow

两种方式：

### 方案 A — 推荐

完整研究完成后：

```text
ResearchReport
↓
PredictionBuilder
↓
5D
20D
60D
```

不是每次必须生成三个。

可根据：

```text
data quality
thesis confidence
```

决定是否创建。

---

### 方案 B

Report 页面：

```text
[生成预测]
```

用户确认后：

```text
PredictionBuilder
```

---

## Prediction Page 应该展示生命周期

```text
中国稀土 · 000831

5D
预期：上涨
区间：+1.5% ~ +6.0%
置信度：68%

创建时间：
08-28

到期：
09-04

当前：
+1.2%

状态：
验证中

来源：
Report v7

[打开研究依据]
```

到期后：

```text
实际：+4.8%
方向：✓
区间命中：✓
```

---

## Prediction 总览

顶部：

```text
方向准确率
区间命中率
平均超额收益
校准度
```

下面：

```text
待验证
已验证
失败案例
```

而不是一个空列表。

---

# 12. 用户问题 7：报告页面也没有东西

## 根因

Report 只有 Pipeline 成功后才产生。

但当前：

```text
首页 Pipeline 硬编码 600519
↓
研究结束
↓
只显示 events
↓
没有自动打开 Report
```

用户自然不知道报告已经生成。

---

## 报告必须成为 Research Run 的主要产物

完成研究后：

```text
Report Ready
↓
自动出现 Report Card
```

例如：

```text
中国稀土完整研究报告

生成：
18:32

Gate：
PASS

Evidence：
82

Claims：
18

Thesis：
3

Valuation：
4

[打开报告]
```

---

## ReportsPage 不能展示 report_id

当前类似：

```text
rpt_abcd1234
SZSE:000831
zh-CN
pass
```

完全是数据库管理页。

改为：

```text
中国稀土 · 000831

完整研究报告

2026-08-28 18:32

研究判断：
中性偏多

置信度：
72%

版本：
v7

Data Quality：
GOOD

[打开]
[查看版本]
```

---

# 13. 必须建立统一 Instrument Context

当前每个页面自己输入：

```text
instrument
```

这是非常大的体验问题。

建立：

```text
CurrentInstrumentContext
```

或者直接通过 route：

```text
/instrument/SZSE:000831/*
```

管理。

---

## 标的工作台 Header

无论在哪个 Tab：

```text
中国稀土   000831

24.83  +2.31%

[关注中]
[立即研究]
[持续跟踪]
[最新报告]
```

下面 Tab：

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

右栏：

```text
Research Copilot
```

---

# 14. 标的总览必须重新设计

当前 Overview：

```text
Price
Change
Evidence Count
```

远远不够。

参考买方研究工作台：

```text
┌───────────────┬───────────────┐
│ 核心观点       │ 估值           │
│ 中性偏多       │ Base ¥31.20    │
│ 72%           │ +25.6%         │
├───────────────┼───────────────┤
│ 催化剂         │ 风险           │
│ 资产整合       │ 注入不确定      │
├───────────────┼───────────────┤
│ 最新变化       │ Data Quality   │
│ 新公告 3 条    │ 7/8 可用       │
└───────────────┴───────────────┘
```

底部：

```text
Recent Research
Recent Reports
Prediction
Task Status
```

---

# 15. 借鉴观澜：研究过程必须“可理解”

不要显示：

```text
analyst_progress
```

改成：

```text
财务分析
正在分析近 12 期财务数据
```

完成：

```text
✓ 财务分析

营收：
+12.4%

ROE：
8.7%

主要结论：
盈利能力改善但现金流仍偏弱

查看依据 >
```

---

# 16. 借鉴观澜：所有执行结果必须产生 Artifact

定义统一：

```text
ResearchArtifact
```

至少：

```text
kind
title
instrument_id
run_id
ref_id
summary
route
created_at
```

Kind：

```text
research_run
report
thesis
valuation
prediction
task_run
evidence_delta
```

---

## Pipeline 完成

返回：

```text
artifact:
  kind: report
  report_id
  route: /reports/{id}
```

UI 自动：

```text
打开 Report Card
```

---

## Task 完成

返回：

```text
artifact:
  kind: task_run
  run_id
  report_id
  materiality
```

UI：

```text
查看本次结果
```

---

## Prediction

```text
artifact:
  kind: prediction
  prediction_id
```

---

# 17. 借鉴观澜：Cross-Module Handoff

统一定义：

```text
ResearchHandoff
```

例如：

```text
Watchlist
→ Workspace

Pipeline
→ Report

Report
→ Prediction

Task
→ Run Detail

Prediction
→ Source Report

Graph
→ Evidence / Claim / Report
```

禁止：

```text
用户自己到菜单里重新寻找下一页面
```

---

# 18. 首页不应该展示 Theme / Sample Quote

当前 HomePage 还有：

```text
Backend Status
Current Theme
Sample Quote
```

这些属于：

```text
Demo / 开发验证
```

不应该占用正式研究首页。

---

## 移动到 Settings / Diagnostics

正式首页应该只展示：

```text
今日研究
关注池变化
待处理任务
待验证预测
最近报告
标的搜索
```

---

# 19. 推荐最终信息架构

```text
研究总览
│
├─ 搜索股票
├─ 今日关注
├─ 最近研究
├─ 新 Evidence
├─ 待运行任务
├─ 待验证预测
└─ 最近报告

关注池
│
└─ Instrument Cards

Instrument Workspace
│
├─ Overview
├─ Timeline
├─ Research Graph
├─ Thesis
├─ Financials
├─ Valuation
├─ Evidence
├─ Reports
└─ Predictions

研究任务
│
├─ Active Tasks
├─ Task Detail
└─ Run History

报告库
│
├─ Latest
├─ Version History
└─ Interactive Report

预测验证
│
├─ Pending
├─ Matured
├─ Performance
└─ Regression Review
```

---

# 20. 产品动作必须统一

任何股票页面都只使用以下核心动作：

```text
打开工作台
加入关注
立即研究
持续研究
查看报告
生成预测
```

避免出现大量技术按钮。

---

# 21. Research Run 状态模型

前端不要直接依赖 SSE Event 名。

建立：

```text
ResearchRunViewModel
```

阶段：

```text
COLLECTING
ANALYZING
SYNTHESIZING
VALUATING
REPORTING
COMPLETED
FAILED
```

每阶段：

```text
title
description
progress
status
result_summary
artifact
```

---

# 22. Empty State 必须告诉用户“下一步”

禁止：

```text
暂无数据
```

结束。

改为：

## Report 空

```text
还没有研究报告。

先对该股票执行一次完整研究。

[立即研究]
```

## Prediction 空

```text
还没有预测。

预测需要基于已完成的研究报告生成。

[查看最新报告]
```

## Task 空

```text
还没有持续研究任务。

创建后系统会定时检查新公告、新闻和研究变化。

[创建持续研究]
```

## Watchlist 空

```text
关注股票后，可以在这里看到：
行情、研究状态、最新报告和变化提醒。

[搜索股票]
```

---

# 23. 000831 必须作为回归案例

本系统后续 UI / 产品测试必须加入：

```text
000831 中国稀土
```

但只作为回归测试股票，不允许架构特殊化。

测试：

```text
搜索 000831
↓
显示中国稀土
↓
加入关注
↓
Watchlist 显示真实名称/行情
↓
打开 Workspace
↓
立即研究
↓
进度可理解
↓
完成后打开报告
↓
创建持续研究
↓
生成预测
```

---

# 24. 产品级 E2E 必须新增

当前后端 Live E2E 不够。

新增：

```text
Product E2E
```

推荐 Playwright。

---

## E2E-01 Discover → Research

```text
打开首页
↓
输入 000831
↓
选择中国稀土
↓
打开 Workspace
↓
立即研究
↓
等待完成
↓
页面出现核心结论
↓
点击完整报告
↓
Report 可读
```

---

## E2E-02 Watchlist

```text
搜索 000831
↓
加入关注
↓
进入关注池
↓
看到中国稀土
↓
看到行情/研究状态
↓
打开 Workspace
```

---

## E2E-03 Task

```text
Workspace
↓
创建持续研究
↓
设定频率
↓
Task Detail
↓
立即运行
↓
看到 Run
↓
看到 Materiality
↓
打开生成报告
```

---

## E2E-04 Prediction

```text
Report
↓
生成 Prediction
↓
Prediction Page
↓
显示 5D
↓
Mark-to-Market
↓
模拟到期
↓
Final Validation
```

---

# 25. 观澜借鉴清单

建议借鉴：

```text
1. 单一研究总控入口
2. 左侧任务进度
3. 中间研究结论
4. 右侧研究产物
5. 工具结果 Artifact 化
6. Cross-module handoff
7. Empty State 指向下一步
8. 降级状态显形
9. 对话 / 研究过程与工作台联动
10. 一个研究档案贯穿各模块
```

不要照搬：

```text
无构建 React
localStorage 档案库
页面 iframe
具体视觉风格
24 Agent 数量
440+ 因子宣传
```

A-Share Research OS 保留自己的：

```text
FastAPI
React/Vite
SQLAlchemy/PostgreSQL
Evidence/PIT
ReportVersion
ResearchTask
Prediction
```

---

# 26. 整改阶段

不要再做新的大 Milestone。

只分：

```text
UX0 — Instrument & Navigation
UX1 — Research Run Experience
UX2 — Task / Report / Prediction Closure
UX3 — Guanlan-style Command Center
UX4 — Product E2E
```

---

# 27. UX0 — Instrument & Navigation

必须：

```text
动态 Instrument Resolver
000831 可搜索
搜索结果可点击
搜索结果可关注
Watchlist 富卡片
Watchlist → Workspace
统一 Instrument Context
```

DoD：

```text
000831 Search PASS
000831 Watchlist PASS
000831 Workspace PASS
```

---

# 28. UX1 — Research Run Experience

必须：

```text
删除 Pipeline 硬编码 600519
Research Run 绑定当前 instrument
Human-readable stages
每阶段结果摘要
Final Research Summary
Report Artifact CTA
```

DoD：

```text
用户不看 Debug Event
也能理解系统正在做什么
```

---

# 29. UX2 — Task / Report / Prediction Closure

必须：

```text
Task schedule UI
Task Detail
Run History
Task → Report
Report Cards
Report → Prediction
Prediction Builder
Prediction lifecycle UI
```

DoD：

```text
Task 创建后有结果
Report 有来源
Prediction 有生产入口
```

---

# 30. UX3 — Guanlan-style Command Center

首页重构为：

```text
Research Command Center
```

最少：

```text
Global Search
Recent Research
Watchlist Changes
Active Tasks
Pending Predictions
Recent Reports
```

后续可加入：

```text
Agent Command Input
```

但不应阻塞第一版产品闭环。

---

# 31. UX4 — Product E2E

必须：

```text
000831
600519
300750
688981
```

执行：

```text
Search
→ Watch
→ Workspace
→ Research
→ Report
→ Task
→ Prediction
```

真实产品链。

---

# 32. 最终验收

只有以下全部通过：

```text
Full A-share Search PASS
Dynamic Instrument Identity PASS

Watchlist Useful PASS
Workspace Reachable PASS

Research Run Understandable PASS
No hardcoded 600519 PASS
Final Summary PASS

Task Produces Visible Result PASS
Task Run History PASS

Report Discoverability PASS
Report Cards PASS

Prediction Creation PASS
Prediction Lifecycle PASS

Empty States Actionable PASS

Cross Module Handoff PASS

000831 Product E2E PASS
4-instrument Product E2E PASS

Frontend Tests PASS
Playwright PASS
```

才允许：

```text
Product Workflow Rebuild COMPLETE
```

---

# 33. Claude 直接执行要求

收到本文档后：

1. 不要继续把重点放在后端 Domain Object；
2. 保留当前 Research Core；
3. 先解决 Instrument Identity；
4. 删除 Home Pipeline 的 `instrument=600519` 硬编码；
5. 重构 Watchlist；
6. 重构 Instrument Search；
7. 重构 Research Run UI；
8. 再做 Task / Report / Prediction 闭环；
9. 最后重构 Research Command Center；
10. 参考观澜的 workflow / artifact / handoff 思路；
11. 不复制观澜技术实现；
12. 所有页面必须回答：
    - 我现在在哪？
    - 我正在研究谁？
    - 系统正在干什么？
    - 得到了什么？
    - 下一步是什么？
13. 所有 Empty State 必须有下一步 CTA；
14. 用 000831 做核心产品回归；
15. 最终必须通过 Product E2E。

---

# 34. 最终判断标准

本轮结束后，一个第一次打开系统的人应该能自然完成：

```text
我想研究中国稀土
↓
搜索 000831
↓
看到中国稀土
↓
加入关注
↓
打开工作台
↓
立即研究
↓
看懂研究进度
↓
看到结论
↓
打开报告
↓
创建持续跟踪
↓
看到后续研究变化
↓
看到预测
↓
等待验证
```

如果仍然需要用户理解：

```text
SZSE:000831
run_id
claimed
succeeded
report_id
analyst_progress
```

才能操作系统，

则产品整改仍未完成。

> **最终目标不是“页面都有”，而是“研究流程自然”。**
