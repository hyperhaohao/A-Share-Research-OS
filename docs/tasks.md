# Tasks（任务书 §48/§49）

## ResearchTask 字段

task_id / instrument_id / task_type（monitor | periodic_full_research |
event_trigger | prediction_validation）/ schedule（`interval:<秒>`）/
research_level / filters / enabled / last_run_at / next_run_at / status。

## 调度保证

| 保证 | 实现 |
|------|------|
| 幂等 | claim 原子推进 next_run_at；同周期第二 tick 不再认领 |
| 重试 | 失败 attempts+1，指数退避（30s×2^n，封顶 1h）；5 次后 FAILED |
| 恢复 | running 超 15 分钟租约 → 重启扫描标记并重新调度 |
| 并发 | 同一 instrument 同时仅一个 running 任务 |

## 业务函数注册表

```python
HANDLERS = {
    TaskType.MONITOR: run_monitor_task,                     # MonitorService
    TaskType.PERIODIC_FULL_RESEARCH: run_periodic_full_research,  # 编译报告
    TaskType.PREDICTION_VALIDATION: run_prediction_validation,    # 到期验证
}
```

调度器只决定「何时」；每个 handler 可独立调用与测试（§49）。
`event_trigger` 的处理器随事件源接入扩展（同注册表模式）。

## API

```text
POST   /api/v1/tasks                     创建（首跑在下一 tick）
GET    /api/v1/tasks?enabled=
PATCH  /api/v1/tasks/{id}?enabled=       启用/停用
POST   /api/v1/tasks/scheduler/tick      执行一轮：恢复→认领→运行→完成
```
