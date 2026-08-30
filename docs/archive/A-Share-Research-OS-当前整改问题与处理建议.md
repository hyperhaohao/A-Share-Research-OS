# A-Share Research OS 当前整改问题与处理建议
## Repository Integrity Closure

> 适用仓库：
>
> `https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 本文档用于 Claude Code / Coding Agent 直接执行当前收口整改。
>
> 当前项目核心架构和研究主链已经成立，**禁止推倒重来**。
>
> 本轮目标不是继续新增功能，而是：
>
> > **修复当前代码真实行为与系统宣称能力之间仍存在的不一致，使 PIT、报告版本、英文报告、状态治理、量化、成本统计和产品交互真正闭环。**

---

# 1. 当前总体判断

当前已具备并应保留：

```text
FastAPI
React / Vite / TypeScript
SQLAlchemy / Alembic
Multi-Source
Evidence
PIT Snapshot
Analyst
Claim
Thesis
Debate
Scenario
Valuation
Risk
Report
Prediction
Scheduler
Quant Baseline
Research Graph
Workspace
Copilot
Docker
Backup / Restore
```

以下问题已经基本修复，不要重复实现：

```text
httpx runtime dependency
psycopg runtime dependency
backend / scheduler DB URL 基本统一
Financial balance 按 REPORT_DATE 对齐
Prediction Mark-to-Market / FinalValidation 分离
Claim / Thesis 基础 snapshot/instrument integrity
Reports API 已接 Narrative 调用点
Workspace Reports 路由链接
```

当前仍需要集中整改的问题如下。

---

# 2. P0 — 必须整改

## P0-01：Report Revision 仍不是真正一致的新版本

### 当前问题

当前 Revision Accept 仍类似：

```python
revised_markdown = previous.markdown.replace(
    proposal.original_text,
    proposal.proposed_text,
)

ReportVersion(
    markdown=revised_markdown,
    html=previous.html,
)
```

存在以下问题：

1. Markdown 已变化，HTML 仍是旧版本；
2. `str.replace()` 可能同时替换多处相同文本；
3. 没有确认 `original_text` 是否存在；
4. 没有确认目标 section / claim；
5. 没有检查 proposal 的 `base_version_id` 是否仍然有效；
6. 修订后没有重新执行 FinalReportQualityGate；
7. Interactive Report 主页面仍可能展示基础 Report，而不是最新 accepted ReportVersion。

### 建议处理

Revision 必须改成：

```text
RevisionProposal
↓
base_version_id 校验
↓
target_section / target_claim_id 定位
↓
original_text 精确校验
↓
Structured Patch
↓
Structured Report State
↓
Render Markdown
↓
Render HTML
↓
FinalReportQualityGate
↓
New immutable ReportVersion
```

### 最低实现要求

禁止：

```python
whole_markdown.replace(...)
```

建议至少：

```text
按 section key 定位
+
只修改目标 section
```

更推荐：

```text
ReportVersion.content_json
作为修订主数据
↓
Markdown / HTML 都重新 Renderer
```

### Frontend

Interactive Report 默认读取：

```text
Latest Accepted ReportVersion
```

支持：

```text
Version Picker
Old Version
Latest Version
Diff
```

### 验收

必须新增：

```text
同样文本出现两次，只修改目标位置
original_text 不匹配 → FAIL
stale base_version → FAIL
Markdown / HTML 内容一致
修订后 Gate FAIL → 不生成正式 accepted version
旧版本保持不可变
最新版本在 UI 可见
```

### DoD

```text
Revision Structured Patch PASS
Markdown/HTML Consistency PASS
Revision Gate PASS
Latest Version UI PASS
Version Immutability PASS
```

---

## P0-02：英文 Narrative 调用了，但核心研究文本仍不会真正翻译

### 当前问题

ReportCompiler 当前仍存在：

```python
"text_zh": claim.statement,
"text_en": claim.statement,
"text_language": "zh-CN",
```

Thesis / Bull-Bear / Risk 等也有类似逻辑。

Narrative Layer 的筛选条件却是：

```python
if zh and not en and text_language == "zh-CN":
    translate()
```

结果：

```text
中文 Claim
↓
text_zh = 中文
text_en = 中文
↓
Narrative 判断 text_en 已存在
↓
跳过翻译
```

所以虽然 Reports API 已调用 Narrative：

```text
en-US
→ narrativize_report()
```

核心研究文本实际仍可能保持中文。

### 建议处理

对于中文原始研究文本：

```python
"text_zh": original_text,
"text_en": None,
"text_language": "zh-CN",
```

只对真正确定性双语文本直接填两种语言。

例如：

```text
价格
估值数字
Scenario 概率
固定系统状态
```

可以：

```python
text_zh = ...
text_en = ...
text_language = None
```

### 必须统一正式报告链

建议建立唯一函数：

```text
compile_report_for_language()
```

流程：

```text
Snapshot
↓
ReportCompiler.compile()
↓
Narrative Layer
↓
Renderer
↓
FinalReportQualityGate
↓
Persist
```

以下入口都调用同一条链：

```text
ResearchPipeline
POST /reports/compile
Scheduled Full Research
Delta Research
```

不要让不同入口有不同英文行为。

### 验收

必须通过真实集成测试：

```text
Same Snapshot
→ zh-CN report
→ en-US report
```

断言：

```text
Evidence IDs 相同
Claim IDs 相同
Thesis IDs 相同
Valuation 数字相同
引用相同
核心中文 Narrative != 英文 Narrative
```

LLM 不可用时：

```text
允许 fallback 为中文原文
但必须显示 original-language marker
```

不能伪装成英文。

### DoD

```text
Pipeline en-US PASS
Reports API en-US PASS
Core Claim Translation PASS
Core Thesis Translation PASS
Evidence/Numbers Consistency PASS
```

---

## P0-03：CorporateEvent 仍缺少跨标的引用约束

### 当前问题

Claim / Thesis 已增加：

```text
instrument
snapshot
reference
```

一致性检查。

但 CorporateEvent 当前仍主要：

```python
_require_evidence(event.evidence_refs)
```

只检查 Evidence 是否存在。

理论上仍可构造：

```text
贵州茅台 CorporateEvent
↓
引用 平安银行 Evidence
```

### 建议处理

新增：

```python
_require_instrument_evidence(
    event.instrument_id,
    event.evidence_refs,
)
```

至少保证：

```text
Evidence.instrument_id == CorporateEvent.instrument_id
```

如果未来 CorporateEvent 绑定 Research Snapshot，则进一步：

```text
Evidence ∈ Snapshot
```

### 负向测试

补：

```text
Event cross instrument → FAIL
Missing Evidence → FAIL
```

同时补全已有 integrity 测试：

```text
Thesis cross instrument
Thesis cross snapshot
Missing snapshot
```

### DoD

```text
Claim Integrity PASS
Thesis Integrity PASS
CorporateEvent Integrity PASS
Negative Tests PASS
```

---

## P0-04：状态文件仍然与真实仓库不一致

### 当前问题

`STATUS.md` 仍存在：

```text
Final Integrity Pass — COMPLETE
Commit: 8aacbcf
backend: 283 passed
```

但当前实际 HEAD 已经变化。

状态文件不应出现：

```text
旧 commit
旧 test count
仍宣布 COMPLETE
```

### 建议处理

当前状态改成：

```text
Repository Integrity Closure — DOING
```

职责固定：

```text
TASK.md
= 最终要求

PLAN.md
= 当前执行计划

STATUS.md
= 当前唯一实时状态

ROADMAP.md
= 历史路线

REMEDIATION.md
= 历史整改记录
```

### STATUS 必须动态维护

至少：

```text
Current Phase
Current Commit
Completed
In Progress
Next Action
Backend Tests
Frontend Tests
CI
Docker
Live Verification
Open Issues
```

### 推荐增加状态校验脚本

```text
scripts/check-project-state.py
```

至少检查：

```text
STATUS commit == git rev-parse HEAD
STATUS 不允许 COMPLETE 且存在 P0 Open Issue
README / STATUS 测试数字一致
ROADMAP 同一 Milestone 不允许同时 PLANNED / DONE
```

后续加入 CI。

### DoD

```text
STATUS Truthful PASS
Commit SHA Correct
Test Count Correct
README / STATUS / ROADMAP Consistent
```

---

# 3. P1 — 高优先级整改

## P1-01：Quant 文档与正式 Runtime 能力不一致

### 当前问题

当前 `docs/quant-audit.md` 仍描述：

```text
Alpha101
GTJA191
Qlib158
450+ factors
ChinaAEngine
T+1
佣金
印花税
涨跌停
optimizer
```

这些来自：

```text
upstream TideTrading 审计
```

但正式运行代码当前主要是：

```text
5D Momentum
20D Momentum
20D Volatility
Simple Long/Flat Backtest
Sharpe
Max Drawdown
Win Rate
```

这再次出现：

> **Upstream capability ≠ Formal runtime capability**

### 建议处理

推荐当前先诚实定义：

```text
BaselineQuantEngine
```

正式能力：

```text
Momentum
Volatility
Simple Backtest
Basic Metrics
Quant Claim
```

高级能力改为：

```text
Future / Not Integrated
```

### 如果确实需要高级量化

再真实接：

```text
TideQuantAdapter
```

并验证：

```text
ChinaA T+1
Fees
Stamp Duty
Limit Up/Down
Factor Registry
Backtest
Metrics
```

真正进入正式 Pipeline 后，才能恢复对应文档描述。

### DoD

```text
Quant Docs == Runtime
No Upstream-as-Product Claims
```

---

## P1-02：Cost Accounting 仍是假统计

### 当前问题

当前 `/costs`：

```python
llm_calls = 0
```

仍为硬编码。

SourceManifest 与 ResearchRun 通过：

```text
created_at == started_at
```

精确时间匹配。

这不是可靠关系。

### 建议处理

建立显式 run linkage。

至少：

```text
SourceManifest.run_id
LLMUsage.run_id
```

建议：

```text
RunCostLedger
```

字段：

```text
run_id
instrument_id
source_calls
source_latency_ms
llm_provider
llm_model
prompt_tokens
completion_tokens
llm_calls
llm_latency_ms
estimated_cost
```

### LLMProvider

每次调用：

```text
record usage
↓
attach run_id
```

SourceCollector：

```text
attach run_id
```

### DoD

```text
Run → Source Calls Trace PASS
Run → LLM Calls Trace PASS
No Timestamp Guessing
No Hardcoded llm_calls=0
```

---

## P1-03：Scheduler Claim 仍不是数据库级原子操作

### 当前问题

现在：

```text
get task
↓
check running_for_instrument
↓
update
```

属于典型：

```text
check-then-update
```

单 scheduler 情况问题较小。

如果以后：

```text
manual tick
+
background scheduler
```

或：

```text
multiple workers
```

就可能重复 claim。

### 建议处理

SQLite 当前单 scheduler：

```text
可以暂时保持
```

但进入 PostgreSQL Production 前必须改成原子 claim。

推荐：

```sql
UPDATE research_tasks
SET status='running'
WHERE task_id=:id
  AND status!='running'
  AND enabled=true
RETURNING ...
```

或：

```text
SELECT FOR UPDATE SKIP LOCKED
```

同 instrument 互斥可：

```text
PostgreSQL advisory lock
```

### DoD

并发测试：

```text
2 sessions claim same task
→ exactly 1 success
```

---

## P1-04：Financial PIT 修复缺少真正多期回归测试

### 当前问题

代码已经按：

```text
REPORT_DATE
→ matching balance sheet
```

修复。

但当前单元测试主要还是单期。

### 建议处理

增加：

```text
2025Q3
2025Q4
2026Q1
2026Q2
```

四期不同资产负债表值。

断言：

```text
每期 total_assets
只对应自身 period
```

再做 PIT：

```text
as_of = 2025-12-31
```

不得看到：

```text
2026Q1
2026Q2
```

的字段。

### DoD

```text
Period Join Test PASS
Historical PIT PASS
```

---

## P1-05：SourceManifest 仍不能完整表示 Dedup Evidence

### 当前问题

当前：

```python
manifest.evidence_ids = tuple(created_ids)
```

如果本次 Source 返回的 Evidence 已经存在：

```text
Evidence 被 dedup
```

则：

```text
manifest 不记录这个 Evidence
```

因此 Manifest 无法完整回答：

> 本次 Source Call 最终解析到了哪些 Evidence？

同时：

```text
source_document_id
```

仍有不少正式文档源没有填。

### 建议处理

CollectionOutcome 建议拆：

```text
resolved_evidence_ids
created_evidence_ids
deduped_evidence_ids
```

Manifest 至少保存：

```text
evidence_ids = all resolved evidence ids
```

正式公告/新闻：

```text
source_document_id = announcement_id/article_id
```

### DoD

```text
Dedup Source Call Still Traceable PASS
External Document ID Persisted
```

---

## P1-06：Data Quality 仍只检查少数能力

### 当前问题

报告当前主要检查：

```text
market_data
financials
announcements
```

但正式 Pipeline 已依赖：

```text
news
capital_flow
industry
macro_policy
historical_data
quant
```

这些失败时报告并不一定完整披露。

### 建议处理

建立：

```text
CapabilityStatus
```

例如：

```text
market_data      SUCCESS
announcements    SUCCESS
financials       PARTIAL
news             UNAVAILABLE
capital_flow     SUCCESS
industry         SUCCESS
macro_policy     NO_DATA
historical_data  SUCCESS
quant            DEGRADED
```

每个 ResearchRun 保存。

报告 Data Quality 使用这份真实状态。

定义：

```text
required
recommended
optional
```

按 Research Mode 判定 Gate。

### DoD

```text
All Pipeline Capabilities Visible
Failure != No Data
Report Shows Degraded Sources
```

---

## P1-07：Production Readiness 仍只有 Liveness

### 当前问题

当前：

```text
GET /health
```

只证明 FastAPI 进程存在。

### 建议增加

```text
GET /ready
```

至少：

```text
DB SELECT 1
Migration Revision Compatible
Repository Access
```

Source Health 继续独立：

```text
/source-health
```

不要把外部 Source 故障作为服务 Readiness 硬阻断。

### DoD

```text
Liveness PASS
Readiness PASS
DB Failure → ready FAIL
```

---

## P1-08：无认证时 Backend 不应默认直接暴露 8000

### 当前定位

当前：

```text
单用户 / 内网 Beta
```

暂时没有认证可以接受。

但 Docker：

```text
8000:8000
```

直接暴露 Backend。

### 建议

默认生产 Compose：

```text
backend:
  expose:
    - 8000
```

只由 frontend nginx proxy。

开发 compose 才：

```text
ports:
  8000:8000
```

如果需要 LAN：

```text
绑定特定内网 IP
```

未来公网再补：

```text
Auth
RBAC
TLS
Rate Limit
Audit User
```

---

# 4. P2 — 产品与工程收口

## P2-01：Interactive Report TOC 仍不能正确定位

### 当前问题

Frontend 使用：

```text
sec-0
sec-1
sec-2
```

寻找 DOM：

```javascript
document.getElementById(...)
```

但 Server Renderer：

```html
<h2>...</h2>
```

没有这些 ID。

### 建议处理

服务端使用稳定 section key：

```html
<h2 id="executive_summary">
<h2 id="valuation">
<h2 id="risks">
```

Frontend：

```text
#executive_summary
#valuation
#risks
```

禁止使用易错的序号 anchor。

### DoD

```text
TOC Click → Correct Section
zh-CN PASS
en-US PASS
```

---

## P2-02：Overview 仍应补真正的 Research Summary

建议增加：

```text
Research Confidence
Data Quality
Top Thesis
Top Risks
Valuation
Latest Material Change
Latest Research Run
Latest Prediction
```

全部接真实 API。

不需要重写 Workspace。

---

## P2-03：Frontend 测试覆盖仍偏低

当前应至少补：

```text
Workspace Reports Navigation
Interactive Report TOC
Latest Version Display
Revision Accept/Reject
Copilot
Prediction State
Task State
Research Graph Trace
```

建议增加：

```text
Playwright
```

最小 E2E：

```text
Search Instrument
↓
Workspace
↓
Run Research
↓
Open Report
↓
Citation
↓
Revision
↓
Latest Version
```

---

## P2-04：GitHub CI 仍未建立

### 建议新增

```text
.github/workflows/ci.yml
```

Backend：

```bash
uv sync
uv run pytest -m "not live"
```

Frontend：

```bash
npm ci
npm test
npm run build
```

Docker：

```bash
docker build ./backend
docker build ./frontend
```

Migration：

```bash
alembic upgrade head
```

Live Source：

```text
workflow_dispatch
或 weekly schedule
```

不要放成每个 PR 必须通过。

### DoD

```text
GitHub CI Green
Current HEAD Has Check
```

---

## P2-05：Live E2E 必须区分 External Smoke 与 Final Acceptance

建议：

### External Smoke

```text
网络问题可 SKIP
Source degraded 可接受
```

### Final Acceptance

在受控网络环境：

```text
600519
000001
300750
688981
```

必须：

```text
Pipeline 4/4 complete
```

允许单 Source degraded，但：

```text
整只股票不能 silently continue
```

---

# 5. 推荐执行顺序

不要再次做大规模 Roadmap。

只执行：

```text
C0 — Critical Closure
C1 — Integrity & Truth
C2 — Product Closure
C3 — Final Verification
```

---

# 6. C0 — Critical Closure

必须：

```text
Revision structured patch
Revision HTML/Markdown rerender
Revision Gate
Latest ReportVersion UI

Narrative text_en=None
Narrative统一编译路径

CorporateEvent instrument integrity

STATUS 状态纠正
```

完成后：

```text
Backend Tests
Frontend Build
```

---

# 7. C1 — Integrity & Truth

必须：

```text
Quant docs == runtime
Cost Ledger
Financial multi-period PIT test
SourceManifest dedup trace
CapabilityStatus
Readiness
```

---

# 8. C2 — Product Closure

必须：

```text
TOC anchors
Overview Research Summary
Frontend integration tests
Backend port exposure strategy
```

---

# 9. C3 — Final Verification

必须：

```text
Full backend test
Full frontend test
GitHub CI
Docker clean build
Migration
Backup / Restore
Prediction maturity
Revision E2E
English Report E2E
4/4 Live Acceptance
Final Reviewer Pass
```

---

# 10. 最终完成条件

只有以下全部满足：

```text
P0 全部 PASS
P1 无阻断项
P2 必要收口完成

AND

Revision Version Integrity PASS
English Narrative PASS
Snapshot / Instrument Integrity PASS
Prediction Final Validation PASS
Financial PIT PASS
Quant Documentation Accuracy PASS
Cost Ledger PASS
Capability Disclosure PASS
TOC PASS
Latest Version UI PASS

Backend Tests PASS
Frontend Tests PASS
Frontend Build PASS
GitHub CI PASS
Docker Clean Build PASS
Migration PASS
Backup Restore PASS
Live Research 4/4 PASS
Final Reviewer PASS

STATUS / README / ROADMAP / REMEDIATION consistent
```

才允许：

```text
Repository Integrity Closure — COMPLETE
```

---

# 11. Claude 直接执行要求

收到本文档后：

1. 读取 `TASK.md / AGENTS.md / CLAUDE.md / PLAN.md / STATUS.md`；
2. 将当前状态改为 `Repository Integrity Closure — DOING`；
3. 将本文档纳入 `PLAN.md`；
4. 不重新输出总体方案；
5. 不重构现有 Research Core；
6. 从 P0-01 开始；
7. 每个问题必须代码修复 + 测试；
8. 禁止用状态文档改成 DONE 代替真实实现；
9. 每个 Closure 阶段完成后 Git checkpoint；
10. 除真实外部阻塞外持续执行；
11. 最终重新以 Reviewer 身份全仓扫描；
12. 只有第 10 节全部满足后才能宣布完成。

---

# 12. 核心整改原则

当前不要再问：

```text
有没有这个类？
有没有这个 API？
有没有这个页面？
```

只检查：

```text
真实业务链有没有调用？
↓
数据有没有正确归属？
↓
PIT 有没有穿越？
↓
版本有没有保持一致？
↓
报告语言是否真的正确？
↓
预测是否真的能到期验证？
↓
成本是否真实可追溯？
↓
系统宣称能力是否等于正式 Runtime？
↓
测试是否有 CI 客观证据？
```

最终目标：

> **把当前已经具备较完整功能的 Research OS，从“功能存在”收口到“研究可信、版本可信、运行可信、状态可信”。**
