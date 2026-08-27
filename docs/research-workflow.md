# Research Workflow（任务书 §89 场景）

一次研究运行（ResearchPipeline）的完整路径：

```text
POST /api/v1/pipeline/run?instrument=600519
1. run_started
2. collect market_data（Source Layer，结构化失败不伪装）
3. evidence_ready → build snapshot（PIT gate：available_time ≤ as_of）
4. analyst_progress → MarketAnalyst 产出带引用 brief（可选事实 Claim）
5. valuation_ready → 确定性估值可计算
6. compile 结构化报告 → quality_gate（FAIL 则 report_blocked）
7. report_ready → 保存 report + V1 版本 + RunManifest
8. run_completed（绑定 snapshot；run 状态 SUCCEEDED）
```

事件经 `GET /api/v1/events/stream?run_id=` 以 SSE 推送；前端 ResearchPipelineCard
先订阅后触发。

## 持续研究

- `POST /api/v1/monitor/run`：低成本事实更新（新快照 + 差集 + MaterialityJudge
  三分支判定，持久化于 materiality_decisions）。
- `POST /api/v1/tasks`：创建 monitor / periodic_full_research / event_trigger /
  prediction_validation 任务；`POST /tasks/scheduler/tick` 执行到期任务
  （幂等/退避/恢复/互斥见 scheduler 模块文档字符串）。

## 验证与复盘

- `POST /api/v1/predictions` 创建不可变预测；到期后
  `POST /predictions/{id}/validate` 一次性产出 ValidationRecord；
- `POST /api/v1/regression/reviews` 对验证做确定性归因（≥1 维）；
- `POST /api/v1/regression/experiences` 沉淀经验（append-only）；
- `GET /api/v1/regression/performance` 汇总方向准确率/超额/命中率。
