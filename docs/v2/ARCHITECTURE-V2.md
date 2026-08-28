# ARCHITECTURE-V2 — 当前代码 → V2 五层架构映射

> 依据 `docs/A-Share-Research-OS-最终产品与架构修改方案.md`（§5/§59/§60/§83）。
> 本文只做代码映射与接口细化，不改变顶层方向。
> 代码现状基线：git e90002e（PW0–PW3 完成后）。

---

## 1. 五层对照（现状 → 目标）

| V2 层 | 现有落点（已存在） | 缺口（Phase A–B 补齐） |
|---|---|---|
| 5 Infrastructure | `backend/app/sources/*`（capability registry/fallback/health/cache，7 provider）、`app/core/events.py`（SSE bus）、`app/db.py`、scheduler worker（`scheduler_worker.py` + compose service） | RunEvent 持久化（事件落库可回放） |
| 4 Research Foundation | `app/domain/instrument.py`、`instrument_registry` 表 + `InstrumentService`（PW0）、`domain/evidence.py`、`storage/repository.py`、`domain/snapshot.py`（PIT 强制）、`storage/snapshot_repo.py`、manifest/version 仓储 | 无（本层已达标） |
| 3 Domain | `domain/research.py`（Claim/Thesis/CorporateEvent）、`domain/agents.py`、`domain/debate.py`、`domain/valuation.py`、`domain/prediction.py`、`domain/regression.py`、`domain/manifest.py`（RunManifest/ReportVersion） | 8 域切分：新域进 `app/domain/<域>/`（industry/experience/workflow/screening/strategy/knowledge_graph），不搬家旧代码（§59 渐进） |
| 2 Application | 目前散在 `app/services/pipeline.py`（ResearchPipeline 编排）、`services/monitor.py`、`services/prediction_builder.py`、`services/instrument_service.py`、`scheduler/scheduler.py` | 新增 `app/application/`：ResearchCommandService、ArtifactService、HandoffService（§7）；旧 service 不迁移，新编排进新边界 |
| 1 Experience | `frontend/src/pages/*`（Command Center/Watchlist/Tasks/Reports/Predictions/Workspace/InteractiveReport）、`frontend/src/presentation/*`（本地化）、CopilotSidebar | 页面→`features/` 渐进迁移（§60）；Phase B 中枢三栏布局 |

## 2. 红线核查（§83）对现状

1. 不建第二套 Research Core —— ✅ ResearchPipeline 是唯一全链（F0.1）。
2. Artifact 不取代强类型 —— ✅ 现有全部强类型；Artifact 将只做索引（Phase A）。
3. PIT —— ✅ snapshot 强制 `available_time <= as_of`；新增 Run 必须 `as_of_time`。
4. localStorage —— ✅ 只存 theme/language；业务全部后端持久化。
5. 跨模块 —— ❌ 现状为页面直连各 API；Phase A 以 Artifact+Context+Handoff 收敛。
6. 事件化可回放 —— 部分：SSE 实时已通（PW1），事件未落库 → Phase A RunEvent。
7–10. LLM 边界/失败显形/策略红线/E2E —— 现状符合；策略线未开始（Phase F/G）。

## 3. 数据库现状（26+1 表）

强类型表不动。Phase A 仅新增：
`artifacts`（ArtifactRecord）、`provenance_edges`（ProvenanceEdge）、
`research_contexts`（可选持久化上下文）、`handoffs`（HandoffEnvelope）、
`run_events`（RunEvent 持久化）。迁移继续走 Alembic（现链头 `a1f2c3d4e5b6`）。

## 4. 目录边界（§59/§60 增量规则）

```
新代码落点：
backend/app/application/{artifacts,handoff,research_command}/
backend/app/domain/{experience,workflow,screening,strategy,industry,macro,knowledge_graph}/
frontend/src/features/<module>/
旧代码：不迁移；跨域动作只允许经由 Application 层。
```

## 5. 事件统一（§37 → 现状映射）

现状：`core/events.py` 的 `_EVENT_NAMES`（15 个 pipeline 事件）+ 内存 bus。
目标：BusEvent 发布时同步写 `run_events`（event_id/run_id/stage/event_type/status/
payload/at）；`GET /research-runs/{id}/events` 回放。SSE 通道不变（前端已按
逐事件消费，PW1 完成）。Stage 枚举按 §37 映射：
run_started→PLANNING, source_progress/evidence_ready→COLLECTING,
snapshot/quality_gate→VALIDATING, analyst_progress→ANALYZING,
claims/thesis/debate/valuation/scenario/risk→SYNTHESIZING,
report_ready→REPORTING, run_completed/failed→COMPLETED/FAILED。
