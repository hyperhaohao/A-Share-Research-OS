# TASK.md

# A-Share Research OS — 最终交付任务契约

> 本文件定义本项目当前不可自行降低的最终任务目标。
>
> Claude / Coding Agent 可以调整实现计划、内部架构细节和技术方案，
> 但不得通过修改本文件、缩减验收范围或删除功能来适应当前实现。
>
> 完整领域规格和详细验收见：
>
> `docs/A-Share-Research-OS-最终实施任务书.md`

---

## 1. Canonical Repository

唯一正式交付仓库：

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

所有最终：

- Source Code
- Frontend
- Backend
- Worker / Scheduler
- Database Migration
- Tests
- Documentation
- Docker / Deployment
- CI / Quality Configuration

必须存在于该正式仓库。

任何上游项目只能作为审计、参考、Adapter 或许可证允许的源码来源，不得替代正式产品仓库。

---

## 2. 最终任务

持续实现、测试、修复并交付：

> **完整、可部署、可持续运行的 A-Share Research OS。**

系统定位不是：

- 单次 LLM 股票分析；
- TradingAgents A 股 Fork；
- TideTrading 换皮；
- 觀瀾复制品；
- OpenAlpha CN 换皮；
- 针对某一个个股的事件研究工具。

最终系统必须是面向通用 A 股研究的长期 Research OS。

---

## 3. 核心 Research Loop

必须实现真实闭环：

```text
Instrument
→ Source
→ Evidence
→ EvidenceSnapshot
→ Claim
→ Thesis
→ Analysis
→ Debate
→ Scenario
→ Deterministic Valuation
→ Risk
→ ResearchReport
```

所有关键结论必须满足：

```text
Report
→ Thesis
→ Claim
→ Evidence
→ Source
```

可追溯。

---

## 4. Report Review Loop

必须实现：

```text
ResearchReport
→ Ask / Audit
→ Evidence Refresh
→ Claim Audit
→ RevisionProposal
→ Diff
→ Accept
→ New ReportVersion
```

要求：

- 旧版本永久保留；
- LLM 不得直接覆盖历史报告；
- Explain 和 Refresh 必须明确区分；
- Explain 只能使用当前 Research State；
- Refresh 才允许获取新 Evidence。

---

## 5. Continuous Research Loop

必须实现：

```text
Monitor
→ MaterialityJudge
→ NO_MATERIAL_CHANGE
   or DELTA_RESEARCH
   or FULL_RESEARCH
```

支持：

- 单股票定时监控；
- 周期完整研究；
- 事件触发研究；
- 任务失败重试；
- restart recovery；
- idempotency；
- concurrency control。

不能每天无差别运行完整 Agent 流程。

---

## 6. Prediction / Validation Loop

必须实现：

```text
PredictionRecord
→ Time
→ ValidationRecord
→ RegressionReview
→ ResearchExperience
```

Prediction 第一版至少支持：

```text
5D
20D
60D
```

预测创建后不可修改。

必须支持 Benchmark、Excess Return、Direction、Range Hit 等真实验证。

---

## 7. Point-in-Time

历史研究必须强制：

```text
Evidence.available_time <= ResearchRun.as_of_time
```

Evidence 至少支持：

```text
event_time
available_time
ingested_time
revision_time
```

禁止未来信息泄漏。

EvidenceSnapshot 必须不可变。

---

## 8. Evidence Discipline

必须严格区分：

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

LLM 不得凭模型记忆制造：

- 财务事实；
- 公司公告；
- Corporate Event；
- 市场数据；
- 政策事实；
- 重大新闻。

缺失数据必须显示为缺失。

---

## 9. A 股研究覆盖

系统不得围绕任何单一股票或单一事件类型设计。

必须适用于：

- 沪市主板；
- 深市主板；
- 创业板；
- 科创板；
- 金融；
- 消费；
- 科技；
- 新能源；
- 制造；
- 周期/资源；
- 高股息；
- 主题/事件驱动。

研究维度至少覆盖：

- Fundamental；
- Financial；
- Valuation；
- Market；
- Technical；
- Capital Flow；
- News / Sentiment；
- Industry / Supply Chain；
- Macro / Policy；
- Corporate Events；
- Quant；
- Risk。

---

## 10. Source Layer

M0 后根据真实源码客观选用成熟能力。

候选至少审计：

- TideTrading；
- OpenAlpha CN；
- 觀瀾；
- Qlib；
- RD-Agent；
- TradingAgents。

每个候选必须给出：

```text
ADOPT
ADAPT
REFERENCE_ONLY
REJECT
```

不得只看 README。

最终 Source Layer 必须具备：

- capability-based Provider；
- fallback；
- structured failure；
- provenance；
- dedup；
- cache；
- source health。

---

## 11. Deterministic Valuation

估值数值必须由可测试代码计算。

根据适用性支持：

```text
PE
PB
PS
EV/EBITDA
DCF
DDM
SOTP
NAV
Historical Percentile
Peer Comps
```

LLM 负责解释，不负责凭自然语言生成无来源目标值。

---

## 12. Quant

先客观审计现有 Quant / Factor / Backtest 能力。

只有现有能力不足时才接入 Qlib。

不得为了满足清单同时维护两套重复量化底层。

如果接入 Qlib，至少完成一个真实 A 股：

```text
Data
→ Feature / Factor
→ Model
→ Prediction
→ Backtest
→ Metrics
```

闭环。

---

## 13. 中英双语

从基础工程开始原生支持：

```text
zh-CN
en-US
```

Language Preference：

```text
system
zh-CN
en-US
```

必须覆盖：

- Navigation；
- Buttons；
- Status；
- Error；
- Forms；
- Tables；
- Tooltips；
- Report；
- Export；
- Empty / Degraded states。

中文报告和英文报告必须共享同一个：

- EvidenceSnapshot；
- Claim；
- Thesis；
- Valuation；
- ResearchRun。

不得各运行一次研究形成两套事实。

Evidence 原文必须永久保留。

翻译文本不得覆盖原始 Evidence。

---

## 14. Theme

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

当 OS `prefers-color-scheme` 变化时：

- Workspace；
- Reports；
- Charts；
- Research Graph；
- Dialog；
- Tooltip；
- Markdown；
- Code；
- Tables

必须同步正确切换。

必须通过 Design Tokens / CSS Variables 管理颜色。

---

## 15. Research Workspace

最终至少包含：

```text
Dashboard
Watchlist
Research Workspace
Research Tasks
Reports
Predictions & Validation
Evidence
Settings
```

Stock Workspace 至少包含：

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

右侧提供：

```text
Research Copilot
```

正式 UI 不得以多个 Agent Markdown 输出作为主要信息架构。

---

## 16. Report UI

必须实现：

- TOC；
- structured report body；
- citation；
- evidence viewer；
- Explain；
- Audit；
- Counter Evidence；
- Refresh；
- Revalue；
- Propose Revision；
- Revision Diff；
- version history。

全部支持：

- zh-CN / en-US；
- System / Light / Dark。

---

## 17. Production

最终必须提供真实可用：

```text
.env.example
docker-compose.yml
database migrations
health checks
frontend
api
worker
scheduler（如果独立）
database
redis（如果实际采用）
backup
restore
deployment
upgrade
logs
known limitations
```

部署目标优先：

```text
Linux
Docker Compose
```

---

## 18. Test Requirements

必须存在并通过与实际架构匹配的：

- Unit Tests；
- Integration Tests；
- E2E Tests；
- Live Source Verification；
- PIT Tests；
- Traceability Tests；
- i18n Tests；
- Theme Tests；
- Revision Tests；
- Scheduler Tests；
- Prediction Math Tests；
- Multi-instrument Regression。

Live Source 不要求成为所有 CI 的硬依赖，但正式 Source Milestone 必须执行真实验证。

---

## 19. 禁止伪完成

以下均不算完成：

```text
TODO
FIXME
placeholder
NotImplemented
pass
空方法
固定值
Mock业务数据
随机演示数据
仅UI
仅API
仅Schema
仅后端未接UI
仅前端Mock
按钮无行为
报告引用不可追溯
Scheduler不真正运行
ReportVersion覆盖旧报告
Prediction可被事后修改
```

---

## 20. 不允许主动降级

不得通过以下方式完成任务：

- 删除要求；
- 删除测试；
- 跳过测试；
- 弱化断言；
- 使用 Mock 替代真实业务；
- 把失败 Source 当作 no_data；
- 取消双语；
- 取消主题；
- 取消 E2E；
- 用文档替代实现。

---

## 21. 最终完成条件

只有同时满足：

```text
TASK requirements complete
AND
PLAN necessary phases complete
AND
ROADMAP mandatory milestones complete
AND
Backend Build PASS
AND
Frontend Build PASS
AND
Unit Tests PASS
AND
Integration Tests PASS
AND
E2E PASS
AND
Core Research Flow PASS
AND
Report Review Flow PASS
AND
Continuous Research Flow PASS
AND
Prediction Validation Flow PASS
AND
i18n PASS
AND
Theme PASS
AND
PIT PASS
AND
Traceability PASS
AND
Production Deployment PASS
AND
Backup / Restore Drill PASS
AND
Final Reviewer Pass
AND
No blocking issue
AND
No obvious TODO / Mock / Placeholder
```

才允许声明：

> **TASK COMPLETE**

否则继续执行。

---

## 22. 详细规格

所有领域字段、Milestone 细节、UI、Source、Report、Quant、API、测试和部署规范见：

```text
docs/A-Share-Research-OS-最终实施任务书.md
```

该文档是本 TASK 的详细规格附件。

TASK 目标不得被 PLAN、STATUS 或实现现状降低。
