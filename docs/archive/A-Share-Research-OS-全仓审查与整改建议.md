# A-Share Research OS 全仓审查与整改建议
## Repository-Wide Audit & Final Remediation Plan

> 审查仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 审查基准：`main`
>
> 审查时 HEAD：`df73cceaf1b69db6b8c39525886979d10b61ef15`
>
> 本文档用于 Claude Code / Coding Agent 直接整改。
>
> 本轮不是再次推倒重构，也不是继续增加表面功能。
>
> **目标：修复会影响研究可信度、PIT 一致性、预测学习闭环、版本审计、部署一致性与最终验收可信度的问题。**

---

# 1. 总体审查结论

当前项目已经具备较扎实的 Research OS 内核：

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

同时已经有：

```text
FastAPI
React / Vite / TypeScript
SQLAlchemy / Alembic
Evidence / PIT
Quality Gates
LLM Provider
Quant baseline
Scheduler Worker
Research Graph
九 Tab Workspace
Copilot
Report Version
Docker
Backup / Restore
```

因此：

> **禁止推倒重来。**

但当前仍不能认定为 `Final Complete`。

本次全仓审查发现的问题不再主要是“功能有没有”，而是：

```text
功能是否真正进入正式运行链？
↓
PIT 是否绝对不穿越？
↓
引用是否严格属于当前标的和当前 Snapshot？
↓
预测验证是否真的能在到期后完成？
↓
报告修订是否真正生成一致的新版本？
↓
生产 backend / scheduler 是否连接同一数据库？
↓
量化文档描述是否与正式运行代码一致？
↓
测试结果是否有 CI 独立证明？
```

综合当前真实实现，建议将项目定位为：

```text
Research OS Beta
— Core Research Loop Available
— Repository-wide Integrity Remediation Required
```

而不是：

```text
Final Integrity Pass COMPLETE
```

---

# 2. 整改优先级

本轮问题分为：

```text
P0 — 必须整改，直接影响正确性 / PIT / 数据一致性 / 生产运行
P1 — 高优先级，影响系统可信度、可维护性和真实产品能力
P2 — 产品收口、测试和工程成熟度
```

执行顺序：

```text
P0
↓
P1
↓
P2
↓
Full Regression
↓
Live E2E
↓
CI Evidence
↓
Final Reviewer Pass
```

---

# 3. P0-01：生产 Docker 缺少 httpx Runtime Dependency

## 问题

文件：

```text
backend/pyproject.toml
backend/Dockerfile
backend/app/sources/http.py
backend/app/ai/llm_provider.py
```

当前 `httpx` 位于：

```toml
[dependency-groups]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
]
```

但正式运行代码直接：

```python
import httpx
```

而 Docker 构建执行：

```bash
uv sync --frozen --no-dev --no-install-project
```

因此生产镜像不会安装 dev dependencies。

这意味着：

> **正式 backend / scheduler 镜像对 httpx 的依赖声明不成立。**

即使某次环境因为间接依赖碰巧可用，也不能视为正确。

## 处理

将：

```toml
httpx>=0.27
```

移动到：

```toml
[project].dependencies
```

Dev 组只保留：

```text
pytest
测试专用工具
```

## 验证

必须从 clean cache 构建：

```bash
docker compose build --no-cache backend scheduler
```

容器内验证：

```bash
python -c "import httpx; print(httpx.__version__)"
python -c "from app.sources.http import http_json"
python -c "from app.ai.llm_provider import OpenAICompatibleProvider"
```

## DoD

```text
backend clean build PASS
scheduler clean build PASS
httpx runtime import PASS
```

---

# 4. P0-02：PostgreSQL“生产支持”当前并没有真正闭环

## 问题 A：缺少 PostgreSQL Driver

`.env.example` 已提供：

```text
postgresql+psycopg://user:password@db:5432/asro
```

但正式 dependencies 中没有：

```text
psycopg
```

因此 PostgreSQL 配置目前只是文档级。

## 问题 B：backend / scheduler 会连接不同数据库

当前 Docker Compose：

```text
backend
→ 使用 ${ASRO_DATABASE_URL}
```

但 scheduler：

```text
ASRO_DATABASE_URL=sqlite:///./data/asro.db
```

是硬编码 SQLite。

如果生产设置：

```text
backend → PostgreSQL
scheduler → SQLite
```

那么：

```text
用户创建 ResearchTask
→ 写入 PostgreSQL

scheduler
→ 查询 SQLite

结果：
任务永远不会执行
```

这是生产级 P0。

## 处理

### 1. 增加正式 PostgreSQL driver

推荐：

```toml
"psycopg[binary]>=3.2"
```

### 2. backend / scheduler 共用同一个变量

Docker Compose：

```yaml
environment:
  ASRO_DATABASE_URL: ${ASRO_DATABASE_URL:-sqlite:///./data/asro.db}
```

backend 与 scheduler 必须完全一致。

不要分别定义。

### 3. 建立生产 Compose

推荐：

```text
docker-compose.yml
= local/dev

docker-compose.production.yml
= PostgreSQL production
```

Production：

```text
postgres
backend
scheduler
frontend
```

### 4. PostgreSQL 实际回归

必须验证：

```text
Alembic upgrade
Instrument
Evidence
Snapshot
Pipeline
ResearchTask
Scheduler claim
ReportVersion
Prediction
```

## DoD

```text
PostgreSQL clean deployment PASS
Alembic PASS
backend/scheduler same DB PASS
scheduler reads backend-created task PASS
```

---

# 5. P0-03：Financial Provider 存在严重 PIT 穿越风险

## 问题

文件：

```text
backend/app/sources/providers/eastmoney_financials.py
```

当前逻辑：

```text
records_raw[0]
→ 取最新 report period

只请求一次最新资产负债表
→ balance

然后循环历史 4 期财务记录
→ 每一期都合并同一个最新 balance
```

类似：

```python
latest_period = records_raw[0]["REPORT_DATE"]
balance = latest_balance_sheet

for rec in records_raw[:4]:
    payload = {
        historical_period_fields,
        **balance,
    }
```

但每个历史记录又有自己的：

```text
NOTICE_DATE
→ available_time
```

结果可能变成：

```text
2025Q3 Evidence
available_time = 2025-10-30

但里面的：
total_assets
total_liabilities
monetary_funds

实际上来自 2026Q2
```

这是标准的：

> **Look-ahead / PIT contamination**

会直接污染：

```text
历史研究
估值
回测
预测验证
```

## 处理

资产负债表必须按 period 对齐。

正确：

```text
Financial Indicator Records
        │
        ├─ 2026Q2
        ├─ 2026Q1
        ├─ 2025Q4
        └─ 2025Q3

Balance Sheet Fetch
        ↓
按 REPORT_DATE 建索引

report_date
→ matching balance row
```

禁止：

```text
latest balance
→ merge into all historical periods
```

如果某一期资产负债表取不到：

```text
该字段 = null
```

不能拿新期数据补旧期。

## 必须新增 PIT 回归

构造：

```text
2025Q3 notice = 2025-10-30
2026Q2 notice = 2026-08-20
```

验证：

```text
as_of = 2025-12-31
```

不得看到任何：

```text
2026Q2 balance values
```

## DoD

```text
financial period join PASS
historical PIT test PASS
valuation historical input PASS
```

---

# 6. P0-04：Prediction 的 Mark-to-Market 会永久吞掉正式到期验证

## 当前问题

文件：

```text
backend/app/services/validation_service.py
backend/app/api/predictions.py
```

当前：

```python
if now >= prediction.due_at:
    target = prediction.due_at
else:
    target = now
```

即未到期时也允许验证。

随后：

```text
ValidationRecord
→ 永久保存
```

以后：

```python
existing = validation_repo.get_for_prediction(...)
if existing:
    return existing
```

并且：

```text
due_unvalidated()
```

会排除已经存在 Validation 的 Prediction。

因此：

```text
创建 5D Prediction
↓
当天立即 validate
↓
保存 0% mark-to-market
↓
第 5 个交易日到期
↓
scheduler 认为已经 validated
↓
永远不会生成真正 5D Validation
```

当前 Live E2E 正在这样做。

这会破坏整个：

```text
Prediction
→ Actual Result
→ Validation
→ RegressionReview
→ ResearchExperience
```

学习闭环。

## 正确设计

严格区分：

```text
MarkToMarket
≠
FinalValidation
```

### 推荐方案

#### A. `validate()` 只允许 matured

```python
if now < prediction.due_at:
    raise PredictionNotMatured
```

只在到期后持久化正式 Validation。

#### B. 增加单独：

```text
GET /predictions/{id}/mark-to-market
```

或：

```text
POST /predictions/{id}/mark-to-market
```

返回：

```text
current_return
current_excess_return
as_of
```

但：

```text
不写 ValidationRecord
不改变 prediction final-validation status
```

如果一定要存：

```text
ValidationKind.MARK_TO_MARKET
ValidationKind.FINAL
```

并保证：

```text
due_unvalidated
只判断 FINAL
```

## 测试

必须覆盖：

```text
T0 创建预测
T0+1 未到期 MTM
→ 可以查看
→ FinalValidation 不存在

due_at
→ scheduler
→ 创建 FINAL Validation

再次 validate
→ 幂等返回同一个 FINAL
```

## DoD

```text
mark-to-market non-final PASS
matured validation PASS
scheduler matured validation PASS
learning loop preserved PASS
```

---

# 7. P0-05：Report Revision 接受后不是一个真正一致的新版本

## 当前问题

文件：

```text
backend/app/storage/revision_repo.py
frontend/src/pages/InteractiveReportPage.tsx
frontend/src/components/RevisionPanel.tsx
```

当前 Accept：

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

存在 5 个问题。

### 问题 1：Markdown / HTML 不一致

```text
Markdown = 新内容
HTML = 旧内容
```

### 问题 2：`str.replace()` 不是结构化修订

如果相同文本出现 3 次：

```text
3 处全部替换
```

而不是只修改目标 section/claim。

### 问题 3：不验证 original_text 是否精确匹配

可能：

```text
original_text 根本不存在
```

但仍然创建一个新版本。

### 问题 4：Accept 后没有重新 FinalReportQualityGate

修改报告后：

```text
Citation
Risk
Data Quality
```

可能被破坏，但没有重新 Gate。

### 问题 5：用户主界面仍显示 ReportRepository 基础 HTML

InteractiveReportPage：

```text
GET /reports/{report_id}
```

读取基础 report。

Accepted ReportVersion 并不会自动成为主视图显示版本。

因此当前：

> Version History 存在，但用户可能看不到 Accepted Revision 的实际正文。

## 正确处理

修订必须变成：

```text
RevisionProposal
↓
锁定 base_version_id
↓
锁定 target_section / target_claim
↓
验证 original_text
↓
Structured Patch
↓
Re-render Markdown
↓
Re-render HTML
↓
FinalReportQualityGate
↓
New immutable ReportVersion
```

### 至少要求

```text
target section 必须存在
original text 必须唯一/明确匹配
base_version 必须仍是指定版本
```

避免 stale revision。

### Frontend

Report 页面必须支持：

```text
Latest Version
Version Picker
```

默认显示：

```text
最新 accepted ReportVersion
```

而不是永远显示最初 ReportORM。

## DoD

```text
revision modifies exactly target PASS
markdown/html consistent PASS
gate rerun PASS
latest version visible PASS
old versions immutable PASS
```

---

# 8. P0-06：Claim / Thesis 的写时引用完整性不足

## 当前问题

文件：

```text
backend/app/storage/research_repo.py
backend/app/api/research.py
```

当前 Claim：

```python
_require_evidence(evidence_ids)
```

只检查：

```text
Evidence ID 是否存在
```

没有检查：

```text
Evidence.instrument_id == Claim.instrument_id
Evidence ∈ Claim.snapshot_id
```

因此 API 可以构造：

```text
贵州茅台 Claim
↓
引用 宁德时代 Evidence
```

或者：

```text
Snapshot B 的 Claim
↓
引用 Snapshot A 才有、B 没有固定的 Evidence
```

这违反：

```text
PIT
Snapshot isolation
Traceability
```

Thesis 同样只检查：

```text
Claim ID 是否存在
```

没有检查：

```text
Claim.instrument_id == Thesis.instrument_id
Claim.snapshot_id == Thesis.snapshot_id
```

CorporateEvent 也存在类似问题。

## 处理

新增强制写时不变量：

```python
_require_snapshot_evidence(
    instrument_id,
    snapshot_id,
    evidence_ids,
)
```

检查：

```text
Snapshot exists
Snapshot.instrument == instrument
Evidence.instrument == instrument
Evidence.id in Snapshot.evidence_ids
```

Thesis：

```python
_require_snapshot_claims(
    instrument_id,
    snapshot_id,
    claim_ids,
)
```

Event 至少：

```text
Evidence.instrument == Event.instrument
```

如果 Event 属于某 research snapshot，则同样要求 pinned。

## 负向测试必须有

```text
cross-instrument evidence → FAIL
cross-snapshot evidence → FAIL
cross-instrument claim → FAIL
cross-snapshot claim → FAIL
missing snapshot → FAIL
```

## DoD

```text
write-time PIT integrity PASS
cross-instrument rejection PASS
cross-snapshot rejection PASS
```

---

# 9. P0-07：英文 Narrative 仍未真正统一进入正式报告链

## 当前问题 A

Pipeline 已经：

```text
language=en-US
→ narrativize_report()
```

但 ReportCompiler 创建 Claim / Thesis 等时：

```python
text_zh = 中文
text_en = 同一段中文
text_language = "zh-CN"
```

而 Narrative 只翻译：

```python
if zh and not en
```

所以核心研究内容被跳过。

## 当前问题 B

公开接口：

```text
POST /api/v1/reports/compile?language=en-US
```

路径仍然：

```text
compile
→ render_and_gate
```

没有进入 Narrative。

因此：

```text
Pipeline en-US
```

和：

```text
Reports API en-US
```

行为不一致。

## 正确方案

原始中文：

```python
text_zh = original
text_en = None
text_language = "zh-CN"
```

对真正已生成双语的确定性数字项：

```python
text_zh = ...
text_en = ...
text_language = None
```

然后统一创建唯一正式业务函数：

```text
compile_report_for_language(
    snapshot,
    language
)
```

内部：

```text
Structured Research State
↓
ReportCompiler.compile
↓
Narrative Layer（en-US）
↓
Renderer
↓
Final Gate
```

Pipeline 与 Reports API 都必须调用它。

## 测试

```text
same snapshot
→ zh-CN
→ en-US

Evidence IDs identical
Claim IDs identical
numbers identical
valuation identical

Chinese narrative != English narrative
```

## DoD

```text
Pipeline English PASS
Reports API English PASS
same research state PASS
```

---

# 10. P0-08：当前状态文件再次过早宣布 COMPLETE

## 当前问题

当前：

```text
STATUS.md
→ Final Integrity Pass COMPLETE
```

但实际还有上述 P0。

并且状态内容本身仍存在：

```text
STATUS test count = 283
README test count = 239
STATUS commit = 8aacbcf
actual HEAD = df73cce
```

ROADMAP 中：

```text
M23 表格 = PLANNED
```

后文：

```text
M23 = DONE
```

也发生自相矛盾。

更重要的是：

```text
f503599 code commit
```

自己的提交信息明确写：

```text
F2 Product Integrity (partial)
```

之后：

```text
df73cce
```

只修改文档/状态文件，就把：

```text
F2 / F3
```

宣布为 COMPLETE。

这不符合项目自己的长期任务规则。

## 处理

立即将：

```text
STATUS.md
```

改成：

```text
Current Phase:
Repository-wide Integrity Remediation — DOING
```

历史：

```text
R0-R5
F0-F3
```

可以保留为历史记录，但必须说明：

```text
later full-repo audit reopened integrity issues
```

## 状态源职责

```text
TASK.md
= final requirements

PLAN.md
= current remediation plan

STATUS.md
= ONLY current truth

ROADMAP.md
= historical roadmap

REMEDIATION.md
= remediation history
```

## 自动化建议

增加脚本：

```text
scripts/check-project-state.py
```

检查：

```text
README / STATUS test count一致
STATUS commit == git rev-parse --short HEAD
ROADMAP 同 milestone 不能同时 PLANNED/DONE
只有一个 current phase
```

放进 CI。

---

# 11. P1-01：Quant 文档严重高估正式 Runtime 能力

## 当前文档声称

`docs/quant-audit.md`：

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
完整真实性测试
```

并据此：

```text
M22 Qlib = NOT_REQUIRED
```

## 但正式仓库实际

```text
backend/app/quant/
├── __init__.py
└── engine.py
```

当前正式 Pipeline Quant 是：

```text
5D momentum
20D momentum
20D volatility
long/flat backtest
Sharpe
drawdown
win rate
```

没有看到正式 runtime 中：

```text
Alpha101
GTJA191
Qlib158
ChinaAEngine
T+1
fee model
limit-up/down
optimizer
```

仓库也不存在：

```text
upstreams/TideTrading
```

正式目录。

因此这里再次出现：

> **Upstream 审计能力 ≠ 正式运行能力**

## 处理方案

二选一。

### A. 推荐：诚实降级当前 Quant 定位

改文档：

```text
Current Formal Quant:
BaselineQuantEngine
```

支持：

```text
Momentum
Volatility
Simple long/flat backtest
Basic metrics
```

然后将高级量化：

```text
Advanced Quant Integration
= TODO / FUTURE
```

M22 是否 NOT_REQUIRED 重新判断。

### B. 真正接入 TideTrading Quant

如果确实需要高级量化：

```text
QuantEngine Interface
↓
TideTradingQuantAdapter
```

真实接入：

```text
factor registry
ChinaA execution rules
fees
T+1
limit up/down
backtest
metrics
```

并进入：

```text
QuantBrief
→ Claim
→ Thesis
```

后才能保留当前文档能力声明。

## 原则

> 不允许再以“曾经审计过 upstream 源码”作为“正式系统已具备该能力”的证据。

---

# 12. P1-02：Cost Accounting 当前不是可信成本统计

## 当前问题

文件：

```text
backend/app/api/costs.py
```

当前：

```python
llm_calls = 0
```

直接硬编码。

Source call 关联：

```python
manifest.created_at == run.started_at
```

这种精确 timestamp equality 非可靠关系。

因此：

```text
/costs
```

不能作为：

```text
模型成本
Source 调用成本
单次研究成本
```

的真实依据。

## 正确方案

建立显式：

```text
RunCostLedger
```

或最少给 SourceManifest 增加：

```text
run_id
```

LLM Call 增加：

```text
run_id
model
prompt_tokens
completion_tokens
calls
latency
```

SourceManifest：

```text
run_id
provider
capability
attempt
status
latency
```

成本查询：

```text
ResearchRun.run_id
→ Source manifests
→ LLM usages
```

严禁再通过时间戳猜关联。

---

# 13. P1-03：Scheduler Claim 并非真正原子

## 当前问题

`TaskRepository.claim()`：

```text
get task
↓
running_for_instrument
↓
update task
```

属于：

```text
check-then-update
```

两个 scheduler 并发时：

```text
Worker A read idle
Worker B read idle
Worker A update running
Worker B update running
```

都有机会成功。

目前还提供：

```text
POST /tasks/scheduler/tick
```

所以手工 Tick + Background Worker 也可能并发。

## 处理

PostgreSQL 正式方案建议：

```text
SELECT ... FOR UPDATE SKIP LOCKED
```

或：

```text
UPDATE research_tasks
SET status='running'
WHERE task_id=?
AND status!='running'
RETURNING ...
```

Instrument 互斥：

```text
advisory lock
```

或：

```text
instrument lease table
```

## 验证

开两个 DB session 同时 claim：

```text
只有 1 个成功
另 1 个返回 None
```

---

# 14. P1-04：Source 仍高度集中于 Eastmoney

当前：

```text
market:
Tencent → Eastmoney

announcements:
CNINFO → Eastmoney

financials:
Eastmoney only

news:
Eastmoney only

capital:
Eastmoney only

industry:
Eastmoney only

macro:
Eastmoney only

historical:
Eastmoney only
```

所以虽然叫“多源”，实际上：

> **大多数研究能力仍有单供应商集中风险。**

## 建议优先增加

### Financial

至少第二来源：

```text
CNINFO filing parsing
或其他稳定公开源
```

### Historical Market

增加：

```text
mootdx / Tencent history / another provider
```

### Macro

至少接一个直接官方源：

```text
PBOC
NBS
CSRC
gov.cn
```

不用一次全部接。

---

# 15. P1-05：CNINFO 使用明文 HTTP

文件：

```text
backend/app/sources/providers/announcements.py
```

当前：

```text
http://www.cninfo.com.cn/...
http://static.cninfo.com.cn/...
```

对于投研 Evidence 原始来源：

> 能用 HTTPS 时不应使用 HTTP。

## 处理

验证 CNINFO HTTPS endpoint。

如果支持：

```text
全部切 https://
```

如果某个 endpoint 确实只支持 HTTP：

```text
明确记录 limitation
```

并对内容使用：

```text
content hash
```

继续保证存档一致性。

---

# 16. P1-06：SourceManifest 追踪信息不完整

## 问题 A

公告有：

```text
announcement_id
```

但 Evidence：

```python
source_document_id = None
```

失去了一个非常重要的稳定外部标识。

## 问题 B

Manifest：

```python
evidence_ids = created_ids
```

如果证据被 Dedup：

```text
这次 Source 调用确实返回并使用了该 Evidence
```

但因为不是新建：

```text
Manifest 中没有它
```

于是 SourceManifest 不能完整回答：

> 本次调用最终对应哪些 Evidence？

## 处理

Evidence：

```text
source_document_id = announcement_id / article id / filing id
```

Manifest：

```text
resolved_evidence_ids
created_evidence_ids
deduped_evidence_ids
```

或至少：

```text
evidence_ids = all resolved ids
```

---

# 17. P1-07：Data Quality 目前只完整检查 3 类能力

`ReportCompiler._missing_capabilities()` 当前主要检查：

```text
market_data
financials
announcements
```

但 Pipeline 实际还依赖：

```text
news
capital_flow
industry
macro_policy
historical_data
quant
```

如果这些失败：

```text
报告可能没有充分披露
```

## 正确方案

建立统一：

```text
CapabilityStatus
```

例如：

```text
market_data       SUCCESS
announcements     SUCCESS
financials        PARTIAL
news              SOURCE_UNAVAILABLE
capital_flow      SUCCESS
industry          SUCCESS
macro_policy      NO_DATA
historical_data   SUCCESS
quant             SUCCESS
```

报告 Data Quality 应直接展示。

## Research Mode

可以定义：

```text
required
recommended
optional
```

并按 research mode 决定是否阻断。

不是要求所有 Source 永远成功。

---

# 18. P1-08：Health 只有 Liveness，没有 Readiness

当前：

```text
GET /health
```

只返回：

```text
status
service
version
```

这只能证明：

```text
Python 进程活着
```

不能证明：

```text
DB 可以访问
migration 正确
```

## 建议

保留：

```text
GET /health
```

作为 Liveness。

新增：

```text
GET /ready
```

检查：

```text
DB SELECT 1
Alembic revision compatible
关键 repository access
```

Source Health 不必作为 Readiness 硬阻断，可单独：

```text
/source-health
```

---

# 19. P1-09：无认证时不应该默认直接暴露 Backend 8000

项目当前定位：

```text
单用户 / 内网 Beta
```

可以暂时没有登录体系。

但 Docker Compose 又：

```text
8000:8000
```

直接发布 backend。

任何能访问服务器 8000 的客户端都可以调用：

```text
创建 Claim
创建 Thesis
创建 Revision
Accept Revision
创建 Task
手工 Scheduler Tick
运行 Pipeline
```

## 当前 Beta 推荐

如果只通过 frontend nginx：

```text
backend 不 publish host port
```

仅：

```text
expose 8000
```

frontend：

```text
proxy_pass backend:8000
```

开发模式才公开 8000。

若确实要给 LAN：

```text
绑定 127.0.0.1
或受控网卡
```

## 公网前

必须：

```text
Authentication
Authorization
TLS
TrustedHost
Rate Limit
Audit User
```

---

# 20. P1-10：LLM 配置和 Usage 需要统一进入 Settings / Run

当前 LLM：

```text
ASRO_LLM_API_KEY
ASRO_LLM_BASE_URL
ASRO_LLM_MODEL
```

直接通过 `os.environ` 获取。

`.env.example` 没有说明。

同时：

```text
get_llm_provider()
```

每次新建 Provider，Usage 是内存级。

## 建议

统一进入：

```python
Settings
```

例如：

```text
llm_api_key
llm_base_url
llm_model
llm_timeout
```

API Key 使用 SecretStr 或保持不打印。

并将每次调用写入：

```text
RunCostLedger
```

---

# 21. P2-01：Workspace Overview 仍然不像真正 Research Summary

当前 Overview 主要是：

```text
Price
Change
Evidence Count
```

建议补：

```text
Research Confidence
Top Thesis
Top Catalysts
Top Risks
Valuation
Data Quality
Latest Research Run
Latest Prediction
```

所有数据必须来自真实 API。

无需重新做大 UI。

---

# 22. P2-02：Workspace Reports 链接与 BrowserRouter 不一致

当前：

```tsx
<a href={`#/reports/${r.report_id}`}>
```

但 App 使用：

```tsx
<BrowserRouter>
<Route path="/reports/:reportId" />
```

这是两种不同路由模式。

## 修改

使用：

```tsx
<Link to={`/reports/${r.report_id}`}>
```

---

# 23. P2-03：Interactive Report TOC 实际没有目标 Anchor

前端生成：

```text
sec-0
sec-1
...
```

然后：

```javascript
document.getElementById(anchor)
```

但服务端 HTML：

```html
<h2>...</h2>
```

没有：

```html
id="sec-0"
```

因此目录跳转可能无效。

## 处理

不要靠序号。

ReportRenderer 输出：

```html
<h2 id="executive_summary">
<h2 id="valuation">
```

Frontend：

```text
#executive_summary
#valuation
```

使用稳定 section key。

---

# 24. P2-04：Interactive Report 仍未真正实现“选中文字→研究动作”

原设计目标：

```text
选中报告文本
↓
解释依据
查看 Evidence
审查 Claim
寻找反证
刷新数据
提出修订
```

当前：

```text
Explain / Audit / Refresh
```

是报告级按钮。

Revision：

```text
用户手动复制 original_text
手动输入 proposed_text
```

仍然比较原始。

## 建议

加入 Selection Context：

```text
selected_text
section_key
claim_ids
evidence_ids
```

然后：

```text
Explain(selection)
Audit(selection)
CounterEvidence(selection)
ProposeRevision(selection)
```

---

# 25. P2-05：Frontend 测试覆盖率明显不足

当前 frontend test 文件主要只有：

```text
app.test.tsx
i18n-theme.test.ts
```

但实际页面已经很多：

```text
Workspace
Graph
Report
Revision
Tasks
Predictions
Copilot
Watchlist
```

## 增加

### Component / Integration

```text
Workspace tabs
Report router
TOC
Citation viewer
Revision
Task enable/disable
Prediction states
Copilot
Graph trace
```

### 推荐 E2E

引入：

```text
Playwright
```

至少：

```text
search stock
→ open workspace
→ run research
→ open report
→ citation
→ revision
```

---

# 26. P2-06：Live Research E2E 仍然只要求 ≥3/4

当前：

```python
if run.status_code != 202:
    continue
```

最终：

```python
assert completed >= 3
```

这不能作为最终 4 标的验收。

## 建议测试分两类

### External Source Smoke

允许：

```text
network unavailable → SKIP
provider degraded → report
```

### Final Live Acceptance

受控网络环境下：

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

Source 可以 partial，但：

```text
Pipeline 不能直接被 continue 隐藏失败
```

---

# 27. P2-07：当前没有 GitHub Actions CI

GitHub 当前没有 workflow run。

因此：

```text
283 passed
frontend 8 passed
build PASS
```

只能算本地执行记录。

## 建议新增

```text
.github/workflows/ci.yml
```

至少：

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

SQLite：

```bash
alembic upgrade head
```

PostgreSQL 以后增加 service container。

### Live

不要放成每个 PR 必须过。

做：

```text
workflow_dispatch
schedule weekly
```

---

# 28. P2-08：公开 Version API 可创建任意 ReportVersion

当前：

```text
POST /reports/{report_id}/versions
```

调用者可以直接提供：

```text
markdown
html
content_json
```

然后生成一个 Version。

这绕开：

```text
Compiler
Narrative
Quality Gate
Revision Audit
```

## 建议

这个接口二选一：

### A

改 internal/admin-only。

### B

删除任意内容写入能力，只允许：

```text
compiler
revision accept
```

生成版本。

---

# 29. P2-09：CorporateEvent 仍主要依赖人工 API 创建

虽然 ResearchGraph 已支持：

```text
CorporateEvent
```

但 EventAnalyst 当前主要生成：

```text
Announcement Claim
```

并没有自然持久化 CorporateEvent。

所以 Graph 中 Event 节点不会随着普通 Pipeline 自动丰富。

## 建议

只对可确定分类的公告做：

```text
Announcement Evidence
→ deterministic CorporateEvent
```

例如：

```text
earnings
dividend
share buyback
executive change
major contract
M&A
```

无法确定时：

```text
只保留 Evidence
```

不要让 LLM 猜事件事实。

---

# 30. P2-10：SSE / Pipeline 当前仍是单进程 Beta 模型

当前：

```text
POST /pipeline/run
```

会在 HTTP 请求中同步执行完整 Pipeline。

状态码虽然：

```text
202
```

实际上工作已经在请求线程里执行。

EventBus 也是进程内。

这在：

```text
单用户 Beta
```

可接受。

但未来：

```text
multi worker
long research
multi user
```

会遇到：

```text
HTTP timeout
SSE subscriber 不在同进程
worker scaling
```

## 后续生产演进

```text
POST /research-runs
↓
create job
↓
return run_id immediately
↓
scheduler/worker executes
↓
Redis/DB Event Stream
↓
SSE
```

本轮可列为非阻断后续。

---

# 31. 推荐整改执行阶段

不要再次搞几十个 Milestone。

只建立 5 个 Closure 阶段：

```text
C0 — Runtime & State Truth
C1 — Research Integrity
C2 — Learning & Version Integrity
C3 — Product & Capability Truth
C4 — Production Verification
```

---

# 32. C0 — Runtime & State Truth

必须完成：

```text
httpx runtime dependency
PostgreSQL driver
backend/scheduler DB config统一
STATUS/README/ROADMAP 修正
CI basic workflow
```

退出条件：

```text
clean Docker build PASS
state files consistent
CI green
```

---

# 33. C1 — Research Integrity

必须完成：

```text
financial period PIT fix
claim snapshot/instrument integrity
thesis snapshot/instrument integrity
SourceManifest resolved evidence
full capability data-quality status
```

退出条件：

```text
cross-snapshot tests PASS
cross-instrument tests PASS
historical financial PIT PASS
```

---

# 34. C2 — Learning & Version Integrity

必须完成：

```text
mark-to-market vs final validation
matured scheduler validation
revision structured patch
markdown/html一致
revision gate rerun
latest ReportVersion UI
English Narrative统一主链
```

退出条件：

```text
5D simulated maturity test PASS
revision E2E PASS
English E2E PASS
```

---

# 35. C3 — Product & Capability Truth

必须完成：

```text
Quant capability documentation纠正或真实高级Quant接入
Cost ledger真实化
Overview Research Summary
Report Link
TOC anchor
```

推荐：

```text
selection-based report actions
front-end tests
```

退出条件：

```text
documentation == runtime
cost association真实
frontend integration tests PASS
```

---

# 36. C4 — Production Verification

必须完成：

```text
backend/scheduler same DB
PostgreSQL smoke
scheduler concurrency
Docker clean build
backup/restore
4/4 live pipeline
CI evidence
final review
```

---

# 37. 最终验收矩阵

只有以下全部满足，才允许再次声明：

```text
Repository Integrity COMPLETE
```

必须：

```text
Runtime Dependencies PASS
Docker Clean Build PASS
PostgreSQL Driver PASS
Backend/Scheduler Same DB PASS

Financial PIT PASS
Snapshot Reference Integrity PASS
Cross-Instrument Isolation PASS
Cross-Snapshot Isolation PASS

Evidence Gate PASS
Analysis Gate PASS
Citation Gate PASS
Capability Disclosure PASS

Prediction Mark-to-Market PASS
Matured Final Validation PASS
Regression Learning Loop PASS

Revision Structured Patch PASS
Markdown/HTML Version Consistency PASS
Revision Quality Gate PASS
Latest Version Rendering PASS

English Narrative API PASS
English Narrative Pipeline PASS

Quant Runtime Documentation Accurate PASS
Cost Accounting Accurate PASS

Workspace Overview PASS
Report Router PASS
TOC PASS

Backend Tests PASS
Frontend Tests PASS
CI PASS
Docker PASS
Backup/Restore PASS
Live Research 4/4 PASS

STATUS / README / ROADMAP consistent
Final Reviewer PASS
```

---

# 38. Claude 执行要求

Claude 收到本文档后：

1. 不要重新输出新的总体方案；
2. 先读取 `TASK.md / AGENTS.md / CLAUDE.md / PLAN.md / STATUS.md`；
3. 将本文档纳入 `PLAN.md`；
4. 把 `STATUS.md` 当前状态改为 `Repository-wide Integrity Remediation — DOING`；
5. 从 C0 开始实际编码；
6. 每一项整改必须有测试；
7. 不得用文档修改代替代码修复；
8. 不得因旧测试通过而忽略新发现的业务不变量；
9. 不得降低 PIT / Traceability / Prediction / Version 要求；
10. 除真实外部阻塞外持续执行；
11. 每个 Closure 阶段通过 DoD 后 Git checkpoint；
12. 最终再次以 Reviewer 身份做全仓审查；
13. 只有本文第 37 节全部通过后才允许宣布完成。

---

# 39. 建议 Git Checkpoint

```text
fix(runtime): declare production dependencies and unify database config

fix(pit): align financial balance sheet data by report period

fix(integrity): enforce snapshot-scoped research references

fix(prediction): separate mark-to-market from final validation

fix(report): make revisions produce gated consistent versions

fix(i18n): unify bilingual narrative compilation path

fix(cost): persist run-linked source and llm usage

fix(scheduler): make task claiming atomic

fix(ui): repair workspace report routing and report toc

test(ci): add repository CI and closure regression suite

docs(state): align runtime capabilities and current project state
```

---

# 40. 最终判断

当前系统最值得保留的部分：

```text
Research Core
Evidence / PIT Model
Multi-Source Layer
Research Pipeline
Quality Gates
Valuation
Report Version Concepts
Scheduler
Research Graph
Workspace
```

当前最需要修的并不是“再加更多功能”，而是：

```text
PIT 绝对正确
+
引用绝对闭合
+
Prediction 真正到期验证
+
Revision 真正版本化
+
生产进程连接一致
+
Runtime 能力与文档一致
+
测试结果有独立 CI 证据
```

完成这些后，项目才真正具备从：

```text
Research OS Beta
```

升级到：

```text
可长期真实试用、可继续演进的 A 股 Research OS
```

的基础。
