# A-Share Research OS 全仓代码审查与最终整改方案
## Production Integrity · Research State Integrity · UX Final Closure

> 仓库：`https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 审查日期：2026-08-30
>
> 审查基线 HEAD：`93cc573b22111d917765d300e77f85a6f293be2e`
>
> 本文用于 Claude Code / Codex / Coding Agent 直接执行。

## 0. 总体结论

当前系统已经真实具备：

```text
Evidence / PIT / Claim / Thesis / ReportVersion
Prediction / Validation / RegressionReview
Artifact / Provenance / Context / Handoff / RunEvent

AI 研究中枢
关注池
Instrument Workspace
研究报告
研究经验卡
研究验证工作流
智能选股
策略实验室
策略盯盘
产业研究地图
全球宏观视图
全库研究图谱
持续研究
研究复盘

React Flow:
Research Graph / Industry Map / Workflow Studio

UX:
Sidebar / Layout / Read Model / Visual Regression

Deployment foundation:
PostgreSQL / nginx TLS / JWT+bcrypt / Roles
```

因此**不应重新架构，也不应继续新增一级业务模块**。

但当前不能认可 `deployment + UX + Workflow Studio all green`。本次代码审查发现多个生产阻断和研究状态一致性问题。当前阶段应改为：

```text
Production Integrity & Research State Closure — DOING
```

建议状态：
- Research Core：90%+
- 产品闭环 v1：80–85%
- UI 信息架构：75–80%
- Workflow Studio：55–65%
- Production deployment：当前不可正式上线

---

# 1. 本轮红线

1. P0 未清零前禁止新增一级功能模块。
2. 本地 E2E green 不等于 Production Ready。
3. Read Model 只能投影研究事实，不能改变历史研究状态。
4. 历史报告、历史 Workflow、历史 Strategy 必须保持 PIT。
5. Backend 与 Scheduler 在生产环境必须使用同一 PostgreSQL。
6. Auth 必须覆盖 REST、SSE、写操作和后台链路。
7. “搬到后端”不代表算法就自动成为业务真相。


# 2. P0 — 生产访问与认证完整性

## P0-01：登录后大量业务 API 仍可能 401

虽然新增了：

```text
frontend/src/api/client.ts → authFetch()
```

但大量正式页面仍直接：

```typescript
fetch("/api/v1/...")
```

例如：
- InstrumentWorkspacePage
- WorkflowStudioPage
- ResearchGraphCanvas
- ResearchPipelineCard
- 多个旧组件

Production Compose 又启用：

```text
ASRO_AUTH_ENABLED=true
```

因此可能出现：

```text
登录成功
→ token 写 localStorage
→ 跳首页
→ 页面 raw fetch 不带 Bearer
→ API 401
```

### 修改措施

建立唯一 API Client：

```text
frontend/src/api/
├─ client.ts
├─ auth.ts
├─ views.ts
├─ research.ts
├─ reports.ts
├─ experience.ts
├─ workflow.ts
├─ screening.ts
├─ strategy.ts
└─ graph.ts
```

业务目录禁止直接 `fetch("/api/v1")`。

CI 加静态扫描。

---

## P0-02：SSE 在认证开启后失效

当前 ResearchPipeline 使用：

```typescript
new EventSource("/api/v1/events/stream?... ")
```

后端 auth middleware 保护 `/api/v1/*`。

原生 EventSource 无法按当前方式附加 Bearer Header，因此 Production 模式下实时研究流会 401。

### 推荐路线

优先推荐公司内部生产场景改为：

```text
HttpOnly + Secure + SameSite Cookie
```

这样：
- fetch 自动带 Cookie
- EventSource 自动带同源 Cookie
- token 不暴露给 JS

写请求增加 CSRF 防护。

若继续 Bearer，则 SSE 改成：

```text
fetch + Authorization
→ ReadableStream
→ SSE frame parser
```

禁止把长期 JWT 放 URL query。

### DoD

Auth Enabled 模式：

```text
login
→ 000831
→ 立即研究
→ run_started
→ source_progress
→ analyst_progress
→ report_ready
→ run_completed
```

实时 UI 必须可见。

---

## P0-03：Production Backend 与 Scheduler 可能使用不同数据库

Base Compose：
- backend 默认 SQLite
- scheduler 默认 SQLite

Prod overlay 只给 backend 强制 PostgreSQL，没有同步覆盖 scheduler。

如果 `.env` 未显式设置 `ASRO_DATABASE_URL`：

```text
backend → PostgreSQL
scheduler → SQLite
```

持续研究将直接失效。

### 修改措施

建议拆：

```text
docker-compose.yml
docker-compose.dev.yml
docker-compose.prod.yml
```

Production 统一数据库环境变量，backend/scheduler 引用同一 anchor 或同一 `.env.production`。

必须保证：

```text
Backend DATABASE_URL == Scheduler DATABASE_URL
```

---

## P0-04：Scheduler 时区依赖容器本地时区

当前：

```python
local = after.astimezone()
```

代码注释假设容器 `Asia/Shanghai`，但 Compose/Dockerfile 没有保证。

用户设置：

```text
每天 08:30
```

在 UTC 容器中可能执行成中国时间 16:30。

### 修改措施

Settings：

```python
scheduler_timezone = "Asia/Shanghai"
```

实现：

```python
ZoneInfo(settings.scheduler_timezone)
```

所有 DB 时间仍存 UTC。

固定测试：

```text
08:30 Asia/Shanghai
→ 00:30 UTC
```

---

## P0-05：Production 可能仍暴露 8000/8080，绕过 nginx/TLS

Base Compose 发布：

```text
8000:8000
8080:80
```

Prod overlay 增加 80/443，并没有可靠移除基础 published ports。

### 修改措施

Production：
- backend internal only
- frontend internal only
- db internal only
- scheduler internal only
- nginx only publish 80/443

验证：
```text
443 reachable
80 redirect
8000 closed
8080 closed
5432 closed
```

---

## P0-06：PostgreSQL 生产密码存在固定默认值

当前：

```text
${ASRO_PG_PASSWORD:-asro_prod}
```

生产必须改为：

```text
${ASRO_PG_PASSWORD:?set ASRO_PG_PASSWORD}
```

禁止固定默认密码。

---

## P0-07：首次注册存在管理员抢占

当前：

```python
repo.count() == 0
→ first registration = admin
```

公网/不可信网络首次启动时，任何先访问 register 的人可能成为 admin，而且并发 bootstrap 也存在竞态。

### 修改措施

取消公开 first-user bootstrap。

使用：
- CLI bootstrap，或
- 一次性 bootstrap token

完成后普通注册永远 admin-only。

---

# 3. P0 — Research State / Read Model 正确性

## P0-08：Report Library 存在历史时点污染

当前 `report_library_rows()` 给同一股票所有报告使用“当前最新 Thesis”。

ReportORM 明明保存：

```text
snapshot_id
```

旧报告应使用对应 snapshot 的 Thesis，而不是今天最新 Thesis。

### 必须修复

```text
Report.snapshot_id
→ Thesis.snapshot_id
```

如果版本内容已固化 stance，则优先使用 ReportVersion / content_json 中的历史状态。

### 负面测试

```text
snapshot A → down → report A
snapshot B → up   → report B

report A 必须仍 down
report B 必须 up
```

---

## P0-09：Research Stance 仍是 Claim 数量投票

当前：

```python
supporting_count > opposing_count → up
```

只能叫 baseline heuristic，不能作为正式研究判断。

### 建立 ResearchStanceProjection

字段：

```text
direction
confidence
basis_type
basis_text
source_thesis_id
source_snapshot_id
source_report_id
scenario_bias
valuation_consistency
prediction_consistency
as_of
```

最终方向优先来自：
1. 主 Thesis / structured synthesis
2. Scenario probabilities
3. Debate synthesis

Claim 数量只作为 `support_balance`，不能直接决定最终 stance。

---

## P0-10：Prediction KPI 把绝对收益显示成“超额收益”

Validation 已经有：

```text
instrument_return_pct
benchmark_return_pct
excess_return_pct
```

但 prediction review 当前平均的是 `instrument_return_pct`，前端却显示“平均超额收益”。

### 修复

View 中完整返回：

```text
instrument_return_pct
benchmark_return_pct
excess_return_pct
```

KPI 分开：

```text
avg_instrument_return_pct
avg_excess_return_pct
```

无 benchmark 时：

```text
avg_excess_return_pct = null
```

UI 显示“暂无超额收益数据”。

---

# 4. P0 汇总

| ID | 问题 | 等级 |
|---|---|---|
| P0-01 | 前端认证 Client 未全量接管 | BLOCKER |
| P0-02 | SSE 无认证 | BLOCKER |
| P0-03 | Scheduler / Backend DB 分叉 | BLOCKER |
| P0-04 | Scheduler 时区 | BLOCKER |
| P0-05 | Production 端口绕过 TLS | BLOCKER |
| P0-06 | PG 默认密码 | BLOCKER |
| P0-07 | Admin Bootstrap 抢占 | BLOCKER |
| P0-08 | Report Library PIT 污染 | BLOCKER |
| P0-09 | Research Stance 语义 | HIGH |
| P0-10 | 超额收益 KPI 错误 | BLOCKER |


# 5. P1 — Read Model 性能

## P1-01：浏览器 N+1 消失，但 SQL N+1 仍存在

`watchlist_cards()` 每个标的逐个调用：
- `_identity`
- `_latest_quote`
- `_research`
- `_latest_report`
- `_latest_prediction`
- `_monitor`

50只股票可能产生数百 SQL。

### 修改措施

Batch Projection：

```text
Watchlist IDs
→ instruments IN (...)
→ latest quote batch
→ latest thesis batch
→ latest report batch
→ latest prediction batch
→ validations batch
→ monitors batch
→ memory join
```

Postgres/SQLite 共用 window function：

```sql
ROW_NUMBER() OVER (
  PARTITION BY instrument_id
  ORDER BY created_at DESC
)
```

### Query Budget Test

```text
1 / 10 / 50 股票
SQL query 数应近似常量
```

建议控制在 10–15 条级别，而不是 O(N)。

---

## P1-02：Latest Quote 不应加载整份 Evidence Ledger

增加 Repository API：

```text
latest_by_type(instrument_id, evidence_type, visible_at)
```

SQL：

```text
WHERE instrument_id
AND evidence_type
AND available_time <= as_of
ORDER BY available_time DESC
LIMIT 1
```

增加复合索引。

---

## P1-03：Monitor JSON universe 扫描

当前读取最近 monitors 再扫描 `universe_json`。

小规模可用，后续建议：

```text
strategy_monitor_instruments
monitor_id
instrument_id
```

用于 Watchlist/Workspace/Monitor 查询。

---

# 6. P1 — Instrument Workspace / 中枢

## P1-04：Workspace 仍有明显旧实现

当前仍有：
- raw `fetch`
- raw `SZSE/SSE`
- raw `market/board`
- raw `evidence_type`
- raw source
- Overview “估值”其实只显示当前价格

### Header 目标

```text
中国稀土
000831 · 深交所 · 主板 · 稀土

¥xx.xx +x.xx%
中性偏多 · 72%
数据质量：良好
数据截至：...

[立即研究] [打开最新报告] [···]
```

技术 ID 只进“技术详情”。

---

## P1-05：InstrumentOverviewView 加真实 Valuation

结构：

```text
valuation:
  current_price
  bear_price
  base_price
  bull_price
  base_upside_pct
  methods
  as_of
  consistency
```

无估值返回 null，UI 显示“估值暂不可用”。

---

## P1-06：Latest Change 不能只是 Evidence Count

新增：

```text
latest_change:
  materiality
  new_evidence_count
  changed_thesis_count
  changed_claim_count
  last_research_run_at
  summary
```

---

## P1-07：Data Quality

从：

```text
evidence_count
source_kinds
```

升级为：

```text
overall
available_capabilities
missing_capabilities
degraded_capabilities
stale_capabilities
```

---

## P1-08：Command Center 没有完整消费聚合 View

后端已经返回 names，但前端 RunRow/TaskRow/PredRow 又 `useInstrumentName()`。

删除二次 identity request。

同时：

```typescript
current_plan ?? recent_plans[0]
```

必须改成：

```text
currentPlan = only running
recentPlans = recent only
```

避免已完成计划冒充当前计划。

---

# 7. P1 — Workflow Studio

当前 React Flow 是真实进步，但本质还是：

```text
Workflow Run Visualizer + 参数重跑
```

DAG 来自 `selected.nodes`，edges 按顺序串起来，用户不能真正设计 Definition。

## 正式拆三层

```text
Workflow Library
Workflow Definition / Version Editor
Workflow Run Viewer
```

### WorkflowDefinition

```text
workflow_id
version
name
description
nodes[]
edges[]
input_schema
output_schema
created_from_card_ids
status
```

Node：

```text
node_id
node_type
config
input_ports
output_ports
```

### Studio 必须支持

```text
Node Palette
拖入 Canvas
删除节点
配置节点
Typed Handle
连接校验
Cycle 校验
必填参数校验
保存 Version
运行
Run Console
```

节点分组：

```text
Data
Research
Quant
Validation
Selection
Output
```

Run 必须固定引用：

```text
workflow_version_id
```

---

# 8. P1 — Research Graph / Industry Map

## Research Graph

已从列表升级成真实 React Flow，应保留。

但当前：
- hashPos 随机式布局
- relation label 仍 raw enum
- hardcoded hex colors
- Inspector 在画布下
- 缺 instrument/as_of/relation/depth filter

### 修改

使用 ELK/Dagre 分层布局。

推荐泳道：

```text
Research
Experience
Validation
Strategy
Decision
Learning
```

过滤：

```text
Scope: 全库 / 单股票 / 当前 Artifact
Instrument
Artifact Type
Relation
Time / as_of
Depth
```

右侧统一 Context Inspector。

---

## Industry Map

当前 v1 更接近“同板块关系图”。

最终逐步扩展：

```text
company
business
product
material
supplier
customer
competitor
commodity
policy
region
theme
```

Edge 必须 Evidence-backed。

此项放在生产完整性关闭后，不属于 P0。

---

# 9. P1 — Visual Regression / CI

## Visual Regression 当前问题

已有 12 baseline 是进步，但：

```text
maxDiffPixelRatio = 0.35
```

过宽。

且 mask 整个 `.mono` 会掩盖重要布局变化。

### 正确做法

建立稳定 Visual Fixture：
- 固定 000831
- 固定 Quote
- 固定 Report
- 固定 Prediction
- 固定时间

只 mask 真正动态时间。

稳定后：

```text
maxDiffPixelRatio <= 0.01–0.03
```

核心页面矩阵：

```text
zh-CN light
zh-CN dark
en-US light
```

至少覆盖：
- AI 中枢
- Workspace
- Report Library
- Interactive Report
- Experience
- Workflow Studio
- Research Graph
- Monitor

---

## 当前没有 GitHub CI

最新 HEAD 没有 commit status、workflow run，仓库也没有 `.github/workflows`。

当前 365 tests / 29 E2E 等只能算本地证据。

### 新建 `.github/workflows/ci.yml`

Jobs：

```text
backend-test
frontend-test-build
postgres-migration-smoke
product-e2e
visual-regression
docker-build
prod-compose-config
```

真实外网 Source 测试可 nightly/manual，不阻塞所有 PR，但发布前必须跑。

---

# 10. P1 — Readiness / Production Security

## Readiness

当前 `/ready` DB 失败仍返回 HTTP 200。

应：
```text
ready → 200
not ready → 503
```

生产 Docker healthcheck 使用 `/ready`，保留 `/health` 作为 liveness。

---

## JWT / RBAC

当前 token 包含 role，middleware 不重新加载用户。

因此：
```text
disable 用户
修改角色
修改密码
```
旧 token 直到到期仍有效。

### 最低生产要求

JWT：

```text
sub=user_id
auth_version
iat
exp
iss
aud
```

每请求确认：
```text
user exists
enabled
auth_version
current role
```

禁用/改密/改角色：
```text
auth_version += 1
```

旧 token 失效。

登录增加 throttling。

nginx 增加：
```text
CSP
HSTS
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
```

---

## Multi-user 数据边界

当前有用户和角色，但 Watchlist/Tasks/Strategy 等多数是全局共享。

必须明确：

推荐公司场景：

```text
Default Company Workspace
```

Research Artifact 公司共享。

个人化：
```text
Watchlist
UI preferences
Notifications
Saved Views
```

写操作记录 actor：
```text
created_by_user_id
updated_by_user_id
```

尤其 Revision / Experience Approve / Strategy Validate / Task Delete / User Manage。

---

# 11. P1 — 部署配置一致性

## PostgreSQL Driver 统一

当前同时依赖：
```text
psycopg2-binary
psycopg[binary]
```

`.env.example` 用 psycopg，prod compose 用 psycopg2。

建议统一：
```text
psycopg3
postgresql+psycopg://
```

删除 psycopg2-binary。

---

## `.env.example` 更新

补：
```text
ASRO_AUTH_ENABLED
ASRO_JWT_SECRET
ASRO_JWT_EXPIRY_HOURS
ASRO_PG_PASSWORD
ASRO_SCHEDULER_TIMEZONE
ASRO_SCHEDULER_INTERVAL
ASRO_CORS_ORIGINS
LLM provider/base/model/key
```

---

## 部署文档更新

当前 `deployment-pg-verified.md` 仍写“Authentication: not yet implemented”。

必须和当前代码同步。

---

# 12. P1 — Cost / SourceManifest / Scheduler Concurrency

## Cost API 仍是假账本

当前：
```text
llm_calls = 0
source calls 用 manifest.created_at == run.started_at 猜关联
```

建立 `UsageRecord`：

```text
usage_id
run_id
kind
provider
capability
model
request_count
input_tokens
output_tokens
duration_ms
cost_amount
currency
status
created_at
```

Source/LLM 调用全部落账。

---

## SourceManifest

当前：
- `source_document_id=None`
- manifest.evidence_ids 只含 created_ids
- 没有显式 run_id

增加：

```text
run_id
resolved_evidence_ids
created_evidence_ids
reused_evidence_ids
```

Provider 提供稳定 `source_document_id`。

---

## Scheduler Claim 仍不是真原子

当前：
```text
get
→ running_for_instrument
→ update
```

多个 worker 可 race。

PostgreSQL 使用：
```text
FOR UPDATE SKIP LOCKED
```
或条件 `UPDATE ... RETURNING`。

一标的一任务并发限制用 advisory lock / lease。

Postgres 并发集成测试：
```text
worker A + worker B 同时 claim
→ 只能一个成功
```

---

# 13. P1 — Revision 剩余问题

旧 `str.replace` 已修复，这是明确进步。

当前已经：
- structured patch
- markdown/html 同源重渲染
- quality gate
- immutable ReportVersion

但还存在：

1. 生产 DEBUG print。
2. Revision 重构时 `as_of = now()`，历史报告会被改成当前时点。
3. Gate 使用 `known_evidence_ids = citations`，引用成员检查近似自证。
4. proposal Evidence 只验证存在，不充分验证 snapshot/report 边界。
5. target 仍靠 `original_text` 精确匹配；重复文本可造成歧义。
6. `target_claim_id` 没成为稳定 patch target。

### 修复

引入：
```text
section_item_id
```

Revision 默认保持：
```text
previous.as_of
previous.snapshot_id
```

只有明确 Evidence Refresh 才产生新的 research state。

Gate：
```text
known_evidence_ids = snapshot.evidence_ids
```

增加：
- stale version
- duplicate text
- cross snapshot evidence
- historical as_of preservation
负面测试。

---

# 14. P2 清理

1. Workflow Studio / Research Graph 又引入硬编码 HEX，改 Design Tokens。
2. Sidebar collapsed 模式增加 icon。
3. Workflow 主界面不要显示 run_id 作为主要名称。
4. Graph edge relation 必须 `formatRelation()`。
5. Graph/Industry/Workflow 统一右侧 Inspector。
6. `ViewService` 逐步拆成 `application/views/*`，避免 God Query Service。
7. API 不要调用 `_names_for()` 这类 private method。
8. 清理重复/无用 import、DEBUG print。
9. 文档 STATUS/PLAN/部署文档保持一致。


# 15. 最终实施阶段

```text
C0 — Production Access Integrity
C1 — Research State / Read Model Integrity
C2 — Scheduler & Performance Integrity
C3 — UX Product Integrity
C4 — Workflow / Graph Depth
C5 — Provenance / Cost / Audit
C6 — CI / Production Acceptance
```

## C0
先完成：
- API client
- SSE auth
- prod DB统一
- scheduler timezone
- prod port
- secret fail closed
- admin bootstrap

P0 未清零前禁止继续扩功能。

## C1
- Report PIT
- ResearchStanceProjection
- Prediction excess KPI
- Workspace valuation/change/quality

## C2
- Batch Read Model
- SQL query budget
- latest evidence query
- atomic scheduler claim
- Postgres concurrency tests

## C3
- Workspace raw enum
- Evidence authority UI
- Command Center context
- Sidebar icons
- Diagnostics 移系统
- Workflow business title
- relation localization

## C4
- Workflow Definition/Version Editor
- layered Research Graph
- richer Industry Map

## C5
- Usage Ledger
- SourceManifest run linkage
- actor audit
- Revision final integrity

## C6
- GitHub Actions
- Auth-enabled Product E2E
- PG E2E
- visual regression
- production compose
- live source release check

---

# 16. 关键文件修改地图

## Backend
```text
backend/app/auth.py
backend/app/api/auth.py
backend/app/main.py
backend/app/config.py

backend/app/api/views.py
backend/app/services/view_service.py
backend/app/application/views/*

backend/app/scheduler/tasks.py

backend/app/services/evidence_collector.py
backend/app/storage/repository.py
backend/app/api/costs.py
backend/app/storage/revision_repo.py
backend/app/api/health.py
```

## Frontend
```text
frontend/src/api/*
frontend/src/pages/*
frontend/src/components/ResearchPipelineCard.tsx
frontend/src/pages/InstrumentWorkspacePage.tsx
frontend/src/pages/HomePage.tsx
frontend/src/pages/WorkflowStudioPage.tsx
frontend/src/pages/ResearchGraphCanvas.tsx
frontend/src/pages/ResearchMapPages.tsx
frontend/src/app/*
frontend/src/presentation/*
frontend/src/styles/*
```

## Deployment
```text
docker-compose.yml
docker-compose.dev.yml
deploy/docker-compose.prod.yml
deploy/nginx.conf
.env.example
backend/Dockerfile
```

## CI
```text
.github/workflows/ci.yml
```

---

# 17. 强制自动检查

## Raw API Fetch

业务目录扫描：

```text
fetch("/api/v1
```

目标：
```text
0
```

仅 `api/client.ts` / 登录 bootstrap 允许。

## zh-CN Raw Enum

遍历：
```text
/
/watchlist
/instrument/*
/reports
/predictions
/tasks
/experience
/workflows
/workflow-studio
/screening
/strategy
/monitoring
/industry-map
/global-context
/research-graph
```

业务区域不得出现：
```text
SZSE:
SSE:
main_board
monitor
succeeded
APPROVED
EXPERIMENTAL
artifact_
run_
snapshot_
```

技术详情除外。

---

# 18. Production Security Acceptance

必须：
```text
unauthenticated GET → 401
viewer POST → 403
analyst research → allowed
admin user create → allowed
disabled user old token → rejected
expired token → rejected
login brute throttle → 429
```

网络：
```text
443 reachable
80 redirect
8000 closed
8080 closed
5432 closed
```

---

# 19. Scheduler Acceptance

1. backend / scheduler DATABASE_URL 完全一致。
2. 创建每天 08:30 任务。
3. `next_run_at` 对应 08:30 Asia/Shanghai。
4. 两 worker 同时 claim，只能一方成功。
5. Restart 后 lease recovery 正常。

---

# 20. PIT Final Regression

至少：
```text
Financial PIT
Report Library PIT
Revision PIT
Workflow as_of
Screening as_of
Strategy Backtest as_of
Global Context as_of
Industry Map as_of
```

---

# 21. 000831 最终 Production E2E

```text
Production Auth
↓
Login
↓
搜索 000831
↓
中国稀土 · 深交所
↓
关注
↓
Workspace
↓
完整研究
↓
Authenticated SSE
↓
Report vN
↓
Experience Card
↓
Workflow Definition / Run
↓
Screening
↓
Strategy
↓
Monitor
↓
Decision
↓
Prediction
↓
Validation
↓
Review
↓
Experience vN+1
↓
Research Graph
```

再执行：
```text
restart frontend
restart backend
restart scheduler
restart PostgreSQL
```

历史：
```text
Watchlist
Task
Report
Experience
Workflow
Strategy
Prediction
```
必须仍存在。

---

# 22. 状态文件建议

当前不要写：
```text
all lines green
```

改：

```text
Current Phase:
Production Integrity & Research State Closure — DOING
```

Completed：
```text
V2 Research Loop
Guanlan-style Product Loop v1
UX Foundation v1
Research Graph Canvas v1
Industry Map Canvas v1
Workflow Run Canvas v1
Auth Foundation
PostgreSQL Compatibility
```

Open：
```text
Production Auth REST/SSE
Prod Scheduler DB
Scheduler Timezone
PIT Read Model
ResearchStanceProjection
Cost Ledger
SourceManifest Run Linkage
Atomic Scheduler Claim
Workflow Definition Editor
CI
```

只有当前 HEAD 有 CI GREEN 后才能进入：
```text
Production Ready Beta
```

---

# 23. 本轮明确不做

暂时不要：
```text
更多 Agent
更多模型
更多宏观指标
更多因子库
更多观澜模块
更多一级页面
动画美化
```

当前优先级：

```text
真实性
> 生产可运行
> PIT
> 并发
> 权限
> 可审计
> UI细节
> 新功能
```

---

# 24. Agent 执行指令

1. 本文作为本轮唯一整改任务书。
2. 不重新架构 Research Core。
3. 不新增一级业务模块。
4. C0/P0 先执行。
5. 每个 P0 必须有负面或真实集成测试。
6. 全业务请求统一 API Client。
7. SSE 必须 Auth Enabled 验收。
8. Backend/Scheduler 必须同 PostgreSQL。
9. Scheduler 显式 Asia/Shanghai。
10. Historical Report 必须 snapshot-bound。
11. Claim 数量不得冒充正式 Stance。
12. 超额收益必须 benchmark-relative。
13. Read Model 增加 SQL Query Budget。
14. Scheduler Claim 必须数据库原子。
15. Revision 保留历史 as_of/snapshot。
16. SourceManifest 绑定 run。
17. Usage Ledger 持久化。
18. Workflow 区分 Definition/Version/Run。
19. Graph 使用 provenance layered layout。
20. 完成结论必须有 GitHub CI 证据。
21. 未通过最终 Production E2E 不得写 COMPLETE。

---

# 25. 最终完成定义

只有：

```text
Research Integrity PASS
PIT PASS
Authentication PASS
SSE PASS
Scheduler PASS
PostgreSQL PASS
Concurrency PASS
Read Model PASS
Cost / Manifest PASS
Revision PASS
UX PASS
Workflow Definition PASS
Research Graph PASS
CI PASS
Production E2E PASS
```

才能：

```text
Production Ready Beta
```

> **当前 A-Share Research OS 的业务能力已经足够丰富。下一阶段的价值不在继续“加功能”，而在把认证、Scheduler、PIT、Read Model、成本与溯源、Workflow Definition 和 CI 真正收口，让现有研究生产闭环从“功能完整的 Beta”升级为“可信、可审计、可持续运行的生产级投研系统”。**
