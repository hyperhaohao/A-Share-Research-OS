# G14 — GOLDEN-EVIDENCE（语义 Golden A/B/C）

> 全部经生产 API 驱动，无手工制造结果；测试文件：
> backend/tests/test_g13_golden.py（3 用例全 PASS，全量 528 collected / 0 FAILED）

## Golden A — 稀土产业链

    资源开采 → 冶炼分离 → 金属/合金 → 永磁材料 → 电机/新能源应用

- 链结构：5 环节 + 5 传导边（material_flow×2 / price_transmission /
  demand_transmission / supply_constraint）—— 生产 API `/industry-graph/seed/rare-earth`；
- 传导证据：`/edges/{id}/evidence` 挂载真实证据（Ownership Gate：存在 + PIT +
  产业归属），边状态 active/degraded 由独立来源组派生；
- 受益公司位置：000831（冶炼分离，processor，证据归属本公司）；
  600259 未登记位置 → 不冒充链上公司（隔离断言）；
- 历史 PIT：`as_of` 早于结构创建 → 边不可见（可重放）；
- 进入 Thesis/Signal：`/research-inbox/thesis-diff` 由链上标的新证据驱动。

## Golden B — 经验到策略闭环

    Report/Thesis → Experience（Approved，PASS 验证） → ScreenDefinition
    （holding_reduction 规则编译断言） → 未发布 422 → 确认发布 → PIT 运行
    （Artifact） → StrategyVersion → backtest-v2（event_backtest_v1）

- 编译断言：preconditions「减持比例 ≥1%」→ holding_reduction{min_pct:1.0}；
- 发布门：未确认 422；draft 运行 422；
- 运行 Artifact 注册（universe + 候选/排除全量落档）；
- 回测执行 G6 引擎（engine=event_backtest_v1 落 aggregate）。

## Golden C — 研究产品与帷幄

    新证据 → Daily Brief 版本+Artifact → Thesis Diff → 帷幄确认门
    （拒绝不执行 422 → 批准 → Thesis 修订 Artifact）

- 产品版本：compile+register v1 → artifact_id + provenance complete；
- 帷幄确认门：拒绝 → 422 不执行；批准 → consumed → Thesis 修订
  （thesis_id 落回 + artifact_ids）；
- 全程生产 API，跨模块 ID 链完整可回放。
