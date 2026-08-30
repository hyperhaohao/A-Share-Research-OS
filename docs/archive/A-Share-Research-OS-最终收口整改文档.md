# A-Share Research OS 最终收口整改文档
## Final Closure Fix

> 适用仓库：
>
> `https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 当前审查基于最新 `main` 分支。
>
> 本文档用于 Claude Code / Coding Agent 直接执行最终收口。
>
> 当前系统核心架构、Research Pipeline、Evidence/PIT、Prediction、Scheduler、Workspace 等均已建立，**禁止推倒重来**。
>
> 本轮只处理当前仍未真正闭环的问题。

---

# 1. 当前总体结论

当前系统已经具备：

```text
Instrument
→ Multi-Source
→ Evidence
→ PIT Snapshot
→ Analysts
→ Claims
→ Thesis
→ Debate
→ Scenario
→ Valuation
→ Risk
→ Report
→ Review / Revision
→ Monitor
→ Prediction / Validation
```

以及：

```text
FastAPI
React / Vite / TypeScript
SQLAlchemy / Alembic
LLM Provider
Baseline Quant
Scheduler Worker
Research Graph
Research Workspace
Report Copilot
Docker
Backup / Restore
```

以下整改已经基本完成，不要重复实现：

```text
Runtime httpx dependency
PostgreSQL psycopg dependency
backend / scheduler DB URL 基本统一
Financial balance 按 REPORT_DATE 对齐
Prediction Mark-to-Market 与 Final Validation 分离
Claim / Thesis snapshot/instrument integrity
CorporateEvent cross-instrument integrity
ReportCompiler 核心中文文本 text_en=None
Reports API Narrative 调用入口
Workspace Reports 路由
```

当前真正需要继续整改的是：

```text
Revision Version Integrity
Latest ReportVersion Rendering
Revision Quality Gate
Narrative E2E
Quant Capability Truth
Cost Ledger
SourceManifest Traceability
Data Quality Coverage
Readiness
Overview
TOC
Frontend Tests
GitHub CI
Live 4/4 Acceptance
State Truth
```

---

# 2. P0 — 当前唯一核心阻断：Report Revision

## P0-01：Revision 当前仍不是可靠的结构化版本修订

### 当前实现问题

当前 Accept Revision 已经加入：

```text
stale base version check
original_text count check
replace(..., 1)
HTML re-render
```

这是进步。

但当前重新生成 HTML 的方式仍然存在严重问题：

```text
revised_markdown
↓
_markdown_to_structured()
↓
ReportRenderer.render_html()
```

而 `_markdown_to_structured()` 会：

```text
instrument_id = ""
snapshot_id = ""
as_of = 当前时间
```

并根据 Markdown 标题动态生成 section key。

但正式 `ReportRenderer` 只识别：

```text
executive_summary
market_and_capital
key_theses
corporate_events
valuation
scenarios
bull_bear
risks
data_quality
source_manifest
disclaimer
```

如果 Markdown 中标题是中文：

```text
投资结论
估值
风险
```

解析后的 key 无法与 canonical section key 对应。

结果可能：

```text
新版 Markdown 正常
新版 HTML 大量 No Data
instrument / snapshot 丢失
citation 丢失
结构语义丢失
```

---

## 正确处理方式

禁止继续使用：

```text
Markdown
→ 反向解析 StructuredReport
```

Markdown 和 HTML 都应该是：

> **Structured Report State 的渲染结果，而不是主数据。**

正确模型：

```text
ReportVersion.content_json
        ↓
StructuredReport
        ↓
Apply Structured Revision
        ↓
ReportRenderer
        ├─ Markdown
        └─ HTML
        ↓
FinalReportQualityGate
        ↓
New ReportVersion
```

---

## P0-01A：以 content_json 为 Revision 主数据

### RevisionProposal 必须定位目标

至少：

```text
target_section
target_claim_id（可选）
original_text
proposed_text
base_version_id
```

Accept 时：

```text
1. 获取 latest ReportVersion
2. 验证 latest.version_id == base_version_id
3. 从 content_json 还原 StructuredReport
4. 定位 target_section
5. 如果提供 target_claim_id，优先按 claim 定位
6. 验证 original_text
7. 只修改目标 item
8. 保留其余 section / citations / numbers / evidence refs
9. 重新 Renderer
10. 重新 FinalReportQualityGate
11. PASS/WARN 才允许保存正式 ReportVersion
```

禁止：

```python
whole_markdown.replace(...)
```

作为正式 Revision 主实现。

---

## P0-01B：Revision 必须重新运行 FinalReportQualityGate

当前提交说明声称：

```text
FinalReportQualityGate re-run
```

但实际 Accept 流程必须确认真正执行：

```text
FinalReportQualityGate
```

检查：

```text
Citation ⊆ Snapshot
Claim support
Valuation assumptions
Risk section
Data Quality
Missing Capability Disclosure
Disclaimer
```

如果：

```text
gate.status == FAIL
```

则：

```text
不得生成正式 accepted ReportVersion
```

可以返回：

```text
revision_gate_failed
```

---

## P0-01C：Latest ReportVersion 必须成为主报告正文

当前 Interactive Report 页面主要读取：

```text
GET /reports/{report_id}
```

RevisionPanel 只展示 Version History。

Accept Revision 后：

```text
v2 创建
```

但主正文仍可能显示：

```text
原始 report
```

### 必须整改

Report 页面加载时：

```text
GET /reports/{report_id}/versions
↓
如果存在 versions
↓
默认 latest accepted version
↓
否则 fallback original report
```

建议增加正式 API：

```text
GET /reports/{report_id}/latest-version
```

或直接：

```text
GET /reports/{report_id}?version=latest
```

Frontend：

```text
Latest Version
Version Picker
```

切换后正文：

```text
markdown/html
```

必须切换。

---

## P0-01D：Revision 测试必须补完整

新增测试：

### 1. stale version

```text
proposal.base_version = v1
当前 latest = v2
→ Accept FAIL
```

### 2. original text 不存在

```text
→ FAIL
```

### 3. original text 出现多次

```text
如果没有 target_claim/section 唯一定位
→ FAIL
```

### 4. 目标 section 精确修改

```text
相同文本在其他 section 出现
→ 只能改 target_section
```

### 5. Markdown / HTML 一致

```text
proposed_text
必须同时出现在：
new_version.markdown
new_version.html
```

### 6. 元数据不丢失

```text
instrument_id 保持
snapshot_id 保持
citations 保持
numbers 保持
```

### 7. Gate 真执行

人为制造非法 Citation：

```text
Revision
→ Gate FAIL
→ 不生成正式 Version
```

### 8. UI latest version

```text
Accept v2
→ Interactive Report 默认显示 v2
```

---

## P0 DoD

只有全部满足：

```text
Structured Revision PASS
No Markdown Reverse Parsing
HTML/Markdown Consistency PASS
Instrument/Snapshot Preservation PASS
Citation Preservation PASS
FinalReportQualityGate PASS
Latest Version UI PASS
Old Version Immutable PASS
```

才能关闭 P0。

---

# 3. P1 — 必须完成的真实性整改

这些不能再降级成“可选增强”。

## P1-01：英文 Narrative 缺少真实 E2E 证明

当前代码已经正确：

```text
text_zh = 中文
text_en = None
```

Narrative Layer 可以进入翻译。

但仍缺真正集成测试。

### 必须新增

```text
Real Snapshot
→ Real Claims
→ Real Thesis
→ compile zh-CN
→ compile en-US
```

使用测试 LLM Provider 返回可预测英文。

断言：

```text
Claim 中文 != English Claim
Thesis 中文 != English Thesis

Evidence IDs 相同
Claim IDs 相同
Thesis IDs 相同
Valuation 数字相同
Citation 集合相同
Snapshot 相同
```

LLM 不可用：

```text
text_en fallback 中文
text_language = zh-CN
```

必须明确标记，不允许伪装成英语。

---

## P1-02：完整引用负向测试还不够

当前 Event 代码已增加 instrument 检查。

仍需补：

```text
CorporateEvent cross-instrument → FAIL
Thesis cross-instrument → FAIL
Thesis cross-snapshot → FAIL
Missing snapshot → FAIL
Claim cross-snapshot → PASS/FAIL 已有继续保留
```

目标：

```text
Instrument
Snapshot
Evidence
Claim
Thesis
Event
```

所有正式写入对象都满足一致性不变量。

---

## P1-03：Quant 文档必须与正式 Runtime 对齐

当前正式 Quant 实际能力主要是：

```text
5D Momentum
20D Momentum
20D Volatility
Simple Long/Flat Backtest
Sharpe
Max Drawdown
Win Rate
Quant Claim
```

但文档仍大量描述 upstream 能力：

```text
Alpha101
GTJA191
Qlib158
450+ factors
ChinaAEngine
T+1
交易费用
印花税
涨跌停
optimizer
```

### 推荐

正式命名：

```text
BaselineQuantEngine
```

并在文档明确：

```text
Integrated Runtime Capabilities
```

与：

```text
Upstream Audited Capabilities
```

完全分开。

### 如果未真正接入

不得写：

```text
系统已支持 450+ 因子
```

必须写：

```text
TideTrading upstream has these capabilities,
not integrated into formal runtime.
```

---

## P1-04：Cost Accounting 仍不能视为真实成本

当前如果仍存在：

```python
llm_calls = 0
```

或：

```text
SourceManifest.created_at == Run.started_at
```

推断关联，则必须整改。

### 建议数据模型

```text
RunCostLedger
```

至少：

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

所有：

```text
SourceManifest
LLMUsage
```

通过：

```text
run_id
```

显式关联。

禁止时间戳猜关联。

---

## P1-05：SourceManifest 必须记录 Dedup 后真实命中的 Evidence

不能只记录：

```text
created_ids
```

应该至少：

```text
resolved_evidence_ids
```

建议：

```text
resolved_evidence_ids
created_evidence_ids
deduped_evidence_ids
```

这样：

```text
本次 Source Call
→ 最终解析到哪些 Evidence
```

才可完整追踪。

对于公告/新闻：

```text
source_document_id
```

必须尽量保存外部稳定 ID。

---

## P1-06：Data Quality 必须覆盖完整 Research Pipeline

当前不能只看：

```text
market_data
financials
announcements
```

应该覆盖：

```text
market_data
announcements
financials
news
capital_flow
industry
macro_policy
historical_data
quant
```

统一：

```text
CapabilityStatus
```

状态：

```text
SUCCESS
PARTIAL
NO_DATA
NETWORK_ERROR
SOURCE_UNAVAILABLE
DEGRADED
```

并区分：

```text
required
recommended
optional
```

报告 Data Quality 必须真实展示。

---

## P1-07：增加 Readiness

保留：

```text
GET /health
```

作为 Liveness。

增加：

```text
GET /ready
```

检查：

```text
DB SELECT 1
Repository Access
Migration Compatibility
```

外部 Source 不作为硬 Readiness。

---

## P1-08：Scheduler 原子 claim

进入 PostgreSQL Production 前必须解决：

```text
get
→ check
→ update
```

竞态。

建议：

```text
UPDATE ... WHERE status != running RETURNING
```

或：

```text
SELECT FOR UPDATE SKIP LOCKED
```

并发测试：

```text
2 workers claim same task
→ exactly 1 success
```

---

# 4. P2 — 产品收口

## P2-01：Report TOC 仍然无有效 Anchor

当前 Frontend：

```text
sec-0
sec-1
...
```

但 Renderer：

```html
<h2>...</h2>
```

没有对应 ID。

### 修改

Renderer 输出：

```html
<h2 id="executive_summary">
<h2 id="market_and_capital">
<h2 id="key_theses">
<h2 id="valuation">
...
```

Frontend 直接：

```text
#executive_summary
#valuation
```

不要再使用序号。

---

## P2-02：Overview 补真正 Research Summary

当前 Overview 不能只显示：

```text
Price
Change
Evidence Count
```

至少补：

```text
Research Confidence
Data Quality
Top Thesis
Top Risks
Valuation
Latest Research Run
Latest Material Change
Latest Prediction
```

全部使用真实 API。

不需要重新设计 Workspace。

---

## P2-03：Frontend Integration Tests

至少补：

```text
Workspace navigation
Report latest version
Revision accept/reject
TOC anchor
Citation viewer
Prediction state
Task state
Graph trace
Copilot
```

推荐引入：

```text
Playwright
```

最小用户链：

```text
Search Instrument
↓
Workspace
↓
Open Report
↓
Citation
↓
Revision
↓
Accept
↓
Latest Version visible
```

---

## P2-04：GitHub CI 必须建立

新增：

```text
.github/workflows/ci.yml
```

### Backend

```bash
uv sync
uv run pytest -m "not live"
```

### Frontend

```bash
npm ci
npm test
npm run build
```

### Docker

```bash
docker build backend
docker build frontend
```

### Migration

```bash
alembic upgrade head
```

### Live E2E

单独：

```text
workflow_dispatch
weekly schedule
```

不建议作为每个 PR 强制阻断。

---

# 5. Live Acceptance 必须改成真正 4/4

当前测试如果仍：

```python
if run.status_code != 202:
    continue
```

最终：

```python
assert completed >= 3
```

不能称为：

```text
4 标的 Live E2E PASS
```

## 正确分两类

### External Smoke

允许：

```text
network unavailable → skip
single provider degraded → continue pipeline
```

### Final Live Acceptance

在受控网络：

```text
600519
000001
300750
688981
```

必须：

```text
4/4 Pipeline complete
```

允许某些 Source：

```text
PARTIAL
NO_DATA
DEGRADED
```

但整只股票：

```text
不能 silently skip
```

---

# 6. 状态文件必须重新真实

当前不建议写：

```text
Repository Integrity Closure — COMPLETE
```

在本轮完成前，改成：

```text
Repository Final Closure — DOING
```

STATUS 至少：

```text
Current Phase
Current HEAD
Implementation Commit
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

建议：

```text
Current HEAD: <git rev-parse HEAD>
Implementation Commit: <last code commit>
```

不要混用。

---

# 7. 推荐最后执行阶段

只保留三步：

```text
FC0 — Revision Integrity
FC1 — Capability & Product Truth
FC2 — Final Verification
```

---

# 8. FC0 — Revision Integrity

必须：

```text
Structured ReportVersion patch
FinalReportQualityGate
Latest Version UI
English Narrative E2E
Reference negative tests
```

---

# 9. FC1 — Capability & Product Truth

必须：

```text
Quant docs == runtime
Cost Ledger
SourceManifest resolved ids
CapabilityStatus
Readiness
TOC
Overview
Frontend integration tests
```

---

# 10. FC2 — Final Verification

必须：

```text
Backend full tests
Frontend full tests
Frontend build
GitHub CI
Docker clean build
Migration
Backup/Restore
Prediction maturity
Revision E2E
English Report E2E
Concurrent scheduler claim
Live Research 4/4
Final Reviewer Pass
```

---

# 11. 最终验收

只有以下全部满足：

```text
Revision Structured State PASS
Revision Gate PASS
Revision Latest UI PASS
English Narrative E2E PASS
Reference Integrity PASS

Quant Docs Accuracy PASS
Cost Ledger PASS
SourceManifest Trace PASS
Capability Disclosure PASS
Readiness PASS

TOC PASS
Overview PASS
Frontend Integration Tests PASS

Backend Tests PASS
Frontend Tests PASS
Frontend Build PASS
GitHub CI PASS
Docker Clean Build PASS
Migration PASS
Backup Restore PASS
Scheduler Concurrency PASS
Live Research 4/4 PASS

STATUS / README / ROADMAP consistent
Final Reviewer PASS
```

才能：

```text
Repository Final Closure — COMPLETE
```

---

# 12. Claude 直接执行要求

Claude 收到本文档后：

1. 阅读 `TASK.md / AGENTS.md / CLAUDE.md / PLAN.md / STATUS.md`；
2. 将状态改为 `Repository Final Closure — DOING`；
3. 将本文档纳入 PLAN；
4. 不重新设计整体架构；
5. 不新增无关功能；
6. 从 Revision P0 开始；
7. 每项必须代码修复 + 自动测试；
8. 不允许用 Commit Message 或 STATUS 替代真实验证；
9. 不得把本文 P1/P2 再降级为“非阻断增强”；
10. 普通问题自行处理；
11. 完成 FC0 后 checkpoint；
12. 完成 FC1 后 checkpoint；
13. 完成 FC2 后做 Final Reviewer Pass；
14. 只有第 11 节全部通过才能结束。

---

# 13. 最终原则

当前项目已经不缺“大功能”。

最后阶段只判断：

```text
报告版本是否真实一致？
英文是否真的翻译？
Evidence / Snapshot 引用是否绝对可靠？
Prediction 是否真正到期验证？
Quant 宣称是否等于 Runtime？
成本是否可追溯？
Source 调用是否可追溯？
Data Quality 是否真实？
UI 是否展示最新正式版本？
测试是否有 CI 客观证据？
Live Acceptance 是否真 4/4？
```

最终目标：

> **结束反复整改循环，让 A-Share Research OS 进入真实长期试用阶段。**
