# HANDOFF-PROTOCOL — ResearchContext / HandoffEnvelope / RunEvent 细化

> §34/§35/§36/§37。Context 只描述"当前研究上下文"，不是业务真数据（红线 4：
> 真实物料永远后端持久化；localStorage 只存 theme/language）。

## 1. ResearchContext

```python
class ResearchContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: str                 # "ctx_<hex12>"
    instrument_ids: tuple[str, ...] = ()
    primary_instrument_id: str | None = None
    as_of_time: datetime | None = None      # PIT：进入任何 Run 前必须落值
    snapshot_id: str | None = None
    research_run_id: str | None = None
    report_version_id: str | None = None
    selected_artifact_ids: tuple[str, ...] = ()
    workflow_run_id: str | None = None      # Phase D+
    screening_run_id: str | None = None     # Phase E+
    strategy_version_id: str | None = None  # Phase F+
    locale: Literal["zh-CN", "en-US"] = "zh-CN"
    created_at: datetime
```

- 载体：URL query（现有 `?instrument=SZSE:000831&run=1` 的推广）+
  可选后端持久化（`research_contexts` 表，跨设备/经 Handoff 传递时用）。
- 规则：页面从 Context 取上下文；Run 类动作把 Context 里缺失的 as_of/
  snapshot 补齐后再执行；Context 变更= 新 context_id（不可变）。

## 2. HandoffEnvelope

```python
class HandoffEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str                 # "ho_<hex12>"
    source_module: str              # "report" / "experience" / "screening" / ...
    target_module: str
    action: str                     # "open" / "create_experience_draft" /
                                    # "create_screen" / "run_validation" / ...
    artifact_ids: tuple[str, ...]   # 携带的产物（ArtifactRegistry id）
    context: ResearchContext
    message: str | None = None
    created_at: datetime
```

- 第一批真实 Handoff（Phase A/B 落地）：
  | from | to | action | 现状 |
  |---|---|---|---|
  | report | prediction | create_prediction | ✅ 已有（PredictionCreateButton，PW2）— Phase A 改为带 artifact_ids 的信封 |
  | report | experience | create_experience_draft | Phase C |
  | experience | workflow | run_validation | Phase D |
  | screening | strategy | create_strategy | Phase F |
  | graph 任意节点 | 原模块 | open_with_context | Phase I |
- 落地形态：`POST /handoffs`（服务端记录 `handoffs` 表 + 校验 artifact 存在）；
  前端 `frontend/src/shared/handoff.ts` 统一构造（URL 参数 + 信封）。
- 校验：target_module 的 action 必须在注册表中（`HANDOFF_ACTIONS`），
  未知 action → 422 handoff.action_unknown（显形，不静默）。

## 3. RunEvent 持久化（§37）

```python
class RunEventORM(Base):
    __tablename__ = "run_events"
    event_id: str          # "evt_<hex16>"
    run_id: str            # index；research-run / workflow-run / monitor-run 通用
    stage: str             # PLANNING/COLLECTING/ANALYZING/SYNTHESIZING/
                           # VALIDATING/SCREENING/BACKTESTING/MONITORING/
                           # REPORTING/COMPLETED/FAILED
    event_type: str        # 现有事件名（run_started/source_progress/…）
    status: str | None     # ok/failed/running/no_data/...
    title: str | None      # 业务可读标题（如 实时行情）
    summary: str | None
    payload_json: JSON     # 原始 payload（created 计数等）
    at: DateTime           # UTC
```

- 写入点：`core/events.py::EventBus.publish` 增加可选 `persist=True` 通道 ——
  publish 时同步 INSERT（由调用方传入的 session 或独立短会话）；
  内存 SSE 行为不变（PW1 前端零改动）。
- 读取：`GET /research-runs/{run_id}/events`（按 at 升序，全量回放）。
  前端"任务历史/研究回放"直接渲染该列表（Stage 分组复用 PW1 的
  collectStage/analysisStage/singleStages 纯函数）。
- stage 映射（现有事件名 → §37 stage）见 ARCHITECTURE-V2.md §5。

## 4. 前端 Shared 层（§60）

```
frontend/src/shared/context.ts     # ResearchContext 构造/URL 编解码
frontend/src/shared/handoff.ts     # HandoffEnvelope 构造与跳转
```

页面只消费这两个模块，不自行拼上下文（跨模块必须 Handoff，红线 5）。

## 5. 验收（Phase A 完成定义补充）

- 报告页 → 生成预测走 Handoff 信封（DB 有 handoff 记录，URL 带 context_id）；
- 任意 run 结束后 `GET /research-runs/{id}/events` 能完整回放
  （后端测试断言事件数 == SSE 记录数）；
- Playwright 扩展 E2E-07：报告 → lineage 图可回溯 run；
  E2E-08：任务详情回放事件列表。
