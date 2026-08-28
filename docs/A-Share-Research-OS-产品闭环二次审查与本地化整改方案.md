# A-Share Research OS 产品闭环二次审查与本地化整改方案

> 仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 当前复核基于最新产品整改提交：`13f734660db7a35077c274a1ec3246a22ea9ab78`
>
> 本文档用于 Claude Code / Coding Agent 继续完成产品层整改。
>
> 核心原则：**不再增加后端对象，不推翻 Research Core；集中完成“用户能真正用懂”的研究工作流。**

---

## 1. 本轮审查结论

上一轮 Product Workflow Rebuild 有实质进展：

```text
✓ 首页删除 Theme / Sample Quote Demo
✓ 标的搜索结果可进入 Workspace
✓ 搜索结果可选择为研究标的
✓ 首页 Pipeline 删除 instrument=600519 硬编码
✓ Pipeline 增加中文/英文阶段名称
✓ Pipeline 完成后增加“打开报告 / 打开工作台”
✓ 未收录股票代码可尝试通过真实行情源动态解析
```

但当前真实状态仍应判断为：

```text
UX0 — PARTIAL
UX1 — PARTIAL
UX2 — TODO / 基本未实现
UX3 — TODO
UX4 — TODO
```

当前核心问题已经从“页面没有”变成：

```text
标的身份没有真正统一
研究过程没有真正实时
关注列表仍是技术 ID 列表
研究任务仍是 Scheduler 管理页
报告仍是数据库列表
预测仍没有生产入口
首页仍不是研究总控台
中文界面仍暴露大量英文 Enum / 技术 ID
```

---

## 2. P0：Instrument Identity 仍未真正闭环

当前输入 `000831` 时，搜索接口可以：

```text
normalize_code
→ 行情 Source
→ 获取股票名称
→ default_catalog().resolve_or_create()
```

但 `default_catalog()` 仍然是进程内缓存。

因此：

```text
搜索 000831
→ 动态出现 中国稀土
→ 可以打开 Workspace

服务重启
→ 动态 InstrumentProfile 消失
→ Watchlist 中 SZSE:000831 还在
→ Workspace 可能 404
```

而且直接在 Watchlist 输入 `000831` 时，当前逻辑只是保存 canonical ID，并不会保证对应 InstrumentProfile 已创建。

另外，非 Seed 股票如果第一次直接搜索中文名，例如：

```text
中国稀土
```

当前也不一定能远程解析。

### 必须整改

建立持久化：

```text
Instrument Registry
```

以及统一：

```text
InstrumentService
```

所有入口：

```text
Search
Watchlist
Task
Pipeline
Workspace
Report
Prediction
```

必须调用同一个服务。

流程：

```text
resolve(query)
→ DB Instrument Registry
→ 不存在
→ Remote Resolver
→ Source 校验
→ upsert Instrument
→ 返回 InstrumentProfile
```

数据库至少保存：

```text
instrument_id
code
exchange
board
name
aliases
listed_status
industry
sector
created_at
updated_at
```

必须保证：

```text
Search("000831")
Watchlist Add("000831")
Task Create("000831")
Pipeline Run("000831")
Workspace("SZSE:000831")
```

全部稳定指向：

```text
中国稀土
000831
深交所
```

且服务重启后不丢失。

---

## 3. P0：Watchlist 实际仍未整改

当前 Watchlist 主界面仍是：

```text
SZSE:000831
note
×
```

这和原问题基本一致。

必须改成研究卡片：

```text
中国稀土
000831 · 深交所 · 主板

24.83  +2.31%

最近研究
今天 18:32

研究状态
已有最新报告

[打开工作台]
[立即研究]
[查看报告]
[持续跟踪]
```

如果没有研究：

```text
中国稀土
000831 · 深交所

尚未进行研究

[立即研究]
```

普通用户主界面禁止把：

```text
SZSE:000831
SSE:600519
```

作为主要显示名称。

---

## 4. P0：Research Pipeline 仍不是真正实时

当前组件虽然创建：

```text
new EventSource(...)
```

但没有把各类 SSE 事件持续解析并 `setEvents`。

实际还是：

```text
点击研究
→ loading
→ POST /pipeline/run 完整结束
→ 一次性 setEvents(data.events)
```

所以用户仍看不到实时研究过程。

### 必须实现真正 SSE Live Progress

监听：

```text
run_started
source_progress
evidence_ready
snapshot_built
quality_gate
analyst_progress
claims_compiled
thesis_ready
debate_ready
valuation_ready
scenario_ready
risk_ready
report_ready
run_completed
run_failed
```

每收到一条：

```typescript
setEvents(prev => [...prev, parsedEvent])
```

POST 负责触发 ResearchRun 和最终结果。

SSE 负责实时 UI。

---

## 5. Pipeline 当前的去重逻辑会丢信息

目前同一个 `event type` 只显示一次。

这会导致：

```text
source_progress
```

只剩一个数据源，例如：

```text
数据采集 · market_data
```

而真实可能有：

```text
行情
公告
财务
新闻
资金流
行业
历史行情
宏观政策
```

同理 `analyst_progress` 也可能只留下一个 Analyst。

### 正确 UI

按业务阶段分组，不按 event name 去重。

```text
数据采集            7/8
✓ 实时行情
✓ 公司公告
✓ 财务数据
✓ 新闻资讯
✓ 资金流
✓ 行业数据
✓ 历史行情
⚠ 宏观政策

分析                8/8
✓ 行业分析
✓ 财务分析
✓ 公司事件分析
✓ 新闻分析
✓ 资金流分析
✓ 宏观政策分析
✓ 市场分析
✓ 量化分析
```

---

## 6. 中文模式必须统一隐藏后端 Enum

中文主界面不要出现：

```text
SSE
SZSE
BSE
market_data
financials
capital_flow
main_board
monitor
succeeded
PASS
DELTA_RESEARCH
```

建立统一 Presentation Layer：

```text
frontend/src/presentation/
├─ instrumentFormat.ts
├─ enumLabels.ts
├─ dateFormat.ts
└─ numberFormat.ts
```

### Exchange

```text
SSE  → 上交所
SZSE → 深交所
BSE  → 北交所
```

英文：

```text
SSE  → Shanghai Stock Exchange
SZSE → Shenzhen Stock Exchange
BSE  → Beijing Stock Exchange
```

### Board

```text
main_board  → 主板
chinext     → 创业板
star_market → 科创板
bse         → 北交所
```

### Capability

```text
market_data      → 实时行情
announcements    → 公司公告
financials       → 财务数据
news             → 新闻资讯
capital_flow     → 资金流
industry         → 行业数据
macro_policy     → 宏观政策
historical_data  → 历史行情
quant            → 量化分析
```

### Task Type

```text
monitor                  → 持续研究
periodic_full_research   → 定期完整研究
prediction_validation    → 预测验证
```

### Task Status

```text
pending    → 待执行
running    → 运行中
succeeded  → 已完成
failed     → 失败
disabled   → 已暂停
```

### Gate

```text
PASS → 通过
WARN → 有警告
FAIL → 未通过
```

### Materiality

```text
NO_MATERIAL_CHANGE → 无重要变化
DELTA_RESEARCH     → 发现重要变化，已增量研究
FULL_RESEARCH      → 触发完整重研
```

后端继续使用稳定英文 Enum，不要改协议。

---

## 7. 技术 ID 统一放进“技术详情”

主界面不要直接显示：

```text
instrument_id
run_id
report_id
task_id
prediction_id
snapshot_id
claim_id
thesis_id
```

业务界面显示：

```text
中国稀土
2026-08-28 研究
完整研究报告 v3
持续研究任务
5日预测
```

技术信息统一：

```text
技术详情 ▾
```

---

## 8. 新 UI 要求：外观改成单选择项

当前 Header 是：

```text
外观：
[跟随系统] [浅色] [深色]
```

用户明确要求不要三个并排按钮。

最终改为：

```text
外观
[ 跟随系统 ▾ ]
```

展开：

```text
跟随系统
浅色
深色
```

第一版直接使用 `<select>` 即可。

保留现有 ThemeProvider / localStorage / prefers-color-scheme 逻辑。

---

## 9. 新 UI 要求：界面语言同样改成单选择项

当前：

```text
语言：
[跟随系统] [简体中文] [English]
```

改为：

```text
界面语言
[ 简体中文 ▾ ]
```

展开：

```text
跟随系统
简体中文
English
```

继续使用现有 LanguageProvider。

只改 Presentation，不重做 i18n 架构。

---

## 10. Header 推荐形式

```text
A-Share Research OS

研究总览 | 关注池 | 研究任务 | 报告库 | 预测验证

外观 [跟随系统 ▾]
语言 [简体中文 ▾]
```

普通界面保持紧凑。

后续也可以合并到：

```text
设置 ▾
```

但本轮先做两个 Select 即可。

---

## 11. P0：研究任务仍然基本没有产品化

当前 TasksPage 仍然是：

```text
输入股票
选择 task_type
schedule = interval:0（硬编码）
创建

Scheduler Tick

列表：
instrument_id
task_type
status
enable/disable
```

这还是调度器管理界面。

---

## 12. 新需求：研究任务必须支持删除

后端当前没有：

```text
DELETE /tasks/{task_id}
```

必须增加。

推荐语义：

```text
删除未来调度配置
停止后续自动运行
从 Active Task List 隐藏
保留历史 ResearchRun / Report / Prediction
```

不要删除已经生成的研究历史。

### 如果任务正在运行

推荐：

```text
HTTP 409 task.running
```

UI：

```text
任务正在执行，暂时不能删除。
```

第一版不需要实现强制终止。

### UI

```text
[立即运行]
[暂停]
[删除]
```

删除确认：

```text
确认删除“中国稀土 · 持续研究”？

删除后不会再自动执行。
已生成的研究历史和报告不会删除。

[取消] [删除任务]
```

---

## 13. Task Schedule 不能继续硬编码 interval:0

第一版至少：

```text
频率
[每天 ▾]

时间
[08:30]
```

支持：

```text
每天
工作日
每周
```

Cron 放高级设置，不直接暴露给普通用户。

---

## 14. Scheduler Tick 移出普通页面

普通用户不关心：

```text
claimed
succeeded
scheduler tick
```

移动到：

```text
Diagnostics / Admin
```

普通 Task Card 使用：

```text
立即运行
```

只执行当前任务。

---

## 15. Task Card 应展示结果

```text
中国稀土
000831 · 深交所

持续研究
每天 08:30

状态
运行正常

上次执行
今天 18:32

结果
发现 3 条新证据
触发增量研究

最新报告
v4 · 今天 18:33

下次执行
明天 08:30

[查看本次结果]
[打开最新报告]
[立即运行]
[暂停]
[删除]
```

---

## 16. P0：Prediction 仍未闭环，而且还有 600519 硬编码

当前 PredictionsPage 仍然存在：

```typescript
if (!ids.includes("SSE:600519")) ids.push("SSE:600519");
```

必须删除。

首页 Pipeline 的硬编码已经修掉，但 Prediction 页面又保留了 Seed Hardcode。

---

## 17. Prediction 仍然没有生产入口

目前只是：

```text
查询已经存在的 Prediction
```

用户不知道怎么产生 Prediction。

推荐第一阶段：

```text
Report
→ [生成预测]
→ PredictionBuilder
```

生成可选：

```text
5D
20D
60D
```

Prediction 页面显示：

```text
中国稀土 · 000831

5个交易日
看多

预期区间
+1.5% ~ +6.0%

当前
+1.2%

状态
验证中

来源
完整研究报告 v3

[查看研究依据]
```

---

## 18. P0：ReportsPage 仍是数据库列表

当前还是：

```text
report_id
instrument_id
language
gate_status
```

必须改为：

```text
中国稀土 · 000831

完整研究报告

2026-08-28 18:32

研究判断
中性偏多

版本
v3

质量
通过

[打开报告]
```

`report_id` 放技术详情。

---

## 19. P1：首页 Research Command Center 仍未实现

当前首页只是：

```text
搜索
→ 选择股票
→ ResearchPipelineCard
```

还不是研究总控台。

至少增加：

```text
今日关注变化
最近研究
正在运行的任务
待验证预测
最近报告
```

第一版不要求 Agent 对话。

---

## 20. Product E2E 仍未建立

当前 frontend 依然只有 Vitest / Testing Library，没有 Playwright。

必须增加浏览器级 E2E。

### E2E-01

```text
首页
→ 输入 000831
→ 显示 中国稀土
→ 显示 深交所
→ 不显示 SZSE
```

### E2E-02

```text
Watchlist 直接输入 000831
→ 中国稀土
→ 打开 Workspace
→ 正常
→ 重启 Backend
→ 仍然正常
```

验证 Instrument Registry 持久化。

### E2E-03

```text
000831
→ 立即研究
→ SSE 实时显示数据采集
→ SSE 实时显示分析
→ 完成
→ 打开报告
```

### E2E-04

```text
创建持续研究
→ 设置每天 08:30
→ 立即运行
→ 查看结果
→ 删除任务
→ 历史报告仍存在
```

### E2E-05

```text
Report
→ 生成 Prediction
→ Predictions
→ 显示中国稀土
→ 不显示 SZSE:000831
```

### E2E-06

中文：

```text
外观 [跟随系统 ▾]
界面语言 [简体中文 ▾]

深交所
主板
持续研究
已完成
```

不得出现：

```text
SZSE
main_board
monitor
succeeded
```

切英文后：

```text
Shenzhen Stock Exchange
Main Board
Continuous Research
Completed
```

---

## 21. 推荐执行阶段

只分四个阶段：

```text
PW0 — Instrument Identity & Localization
PW1 — Research Live Experience
PW2 — Watchlist / Task / Report / Prediction Closure
PW3 — Command Center & Product E2E
```

### PW0

```text
持久化 Instrument Registry
统一 InstrumentService
000831 直接 Watchlist 可打开
重启后仍正常
动态名称搜索
Exchange/Board/业务 Enum 本地化
技术 ID 默认隐藏
Appearance 单 Select
Language 单 Select
```

### PW1

```text
SSE 真正实时更新
Source 逐项显示
Analyst 逐项显示
Capability 中文化
Analyst 中文化
最终研究摘要
Report CTA
Workspace CTA
```

### PW2

```text
Watchlist Card

Task:
schedule UI
task detail
run history
run now
delete
report handoff

Report:
business card
latest version
prediction CTA

Prediction:
删除 SSE:600519 hardcode
prediction builder
lifecycle UI
```

### PW3

```text
Research Command Center
Recent Research
Watchlist Changes
Active Tasks
Pending Predictions
Recent Reports
Playwright
000831 Product E2E
Language E2E
Task Delete E2E
```

---

## 22. 最终验收

只有以下全部通过：

```text
000831 Search PASS
000831 Name Search PASS
000831 Direct Watchlist PASS
Restart Persistence PASS
Workspace PASS

No Raw SSE/SZSE in zh-CN Main UI
No Raw Enum in zh-CN Main UI

Appearance Single Select PASS
Language Single Select PASS

Research SSE Live PASS
Source Progress Understandable PASS
Analyst Progress Understandable PASS

Watchlist Useful PASS

Task Schedule PASS
Task Run PASS
Task Result PASS
Task Delete PASS
Task History Preserved PASS

Report Discoverability PASS
Report Business Card PASS

Prediction Creation PASS
No 600519 Seed Hardcode PASS
Prediction Lifecycle PASS

Command Center PASS
Playwright PASS
000831 Full Product E2E PASS
```

才能宣布：

```text
Product Workflow Rebuild COMPLETE
```

---

## 23. Claude 执行要求

1. 不重构 Research Core；
2. 优先完成持久化 Instrument Registry；
3. 所有入口统一 InstrumentService；
4. 外观改成单 Select；
5. 界面语言改成单 Select；
6. 中文模式建立统一 Presentation Layer；
7. 主界面不得直接输出 SSE/SZSE 等技术码；
8. 增加 Task Delete；
9. 删除 Prediction 中 `SSE:600519` Seed Hardcode；
10. 修复真正 SSE Live Progress；
11. 完成 Watchlist / Task / Report / Prediction 业务闭环；
12. 最后做 Research Command Center；
13. 增加 Playwright；
14. 用 000831 中国稀土作为核心产品回归标的；
15. 禁止为 000831 写特殊业务逻辑；
16. 技术 ID 统一放“技术详情”；
17. 不得因为接口存在就宣布完成。

---

## 24. 最终体验标准

第一次使用系统的人输入：

```text
000831
```

应该自然完成：

```text
搜索
→ 中国稀土 · 000831 · 深交所
→ 加入关注
→ 打开工作台
→ 立即研究
→ 实时看到行情/公告/财务/新闻/行业等采集进度
→ 实时看到财务分析/事件分析/市场分析等进度
→ 看到核心研究结论
→ 打开报告
→ 生成预测
→ 创建每天 08:30 的持续研究
→ 查看每次变化
→ 按需删除未来研究任务
```

全过程普通用户不应需要理解：

```text
SZSE:000831
SSE
run_id
report_id
claimed
succeeded
market_data
main_board
monitor
```

> **产品完成标准不是“页面都有”，而是“用户自然知道下一步做什么”。**
