# G13-MANIFEST — 语义测试与 Golden

> 观澜研究能力语义迁移任务书 §G13（P0）| 日期：2026-09-02

## 交付

### 1. 语义否定测试（§G13 必须新增的否定测试 → 分布于 G1–G12 各套件）

| 否定语义 | 覆盖 |
|---|---|
| 分类树不能通过产业链边测试 | G1：分类视图无边；边必须经 /industry-graph 显式创建 + 环节归属校验 |
| 跨产业 Evidence 不能支撑 Edge | G1 test #3（evidence_ownership_rejected 422） |
| 未批准 Experience 不能生产筛选 | G5 test #1（screen.source_not_approved 422） |
| 不同 Experience 必须生成不同规则 | G5 test #2（holding_reduction vs earnings_positive） |
| Workflow Edge 无数据时下游不能执行 | G4 test #5（失败传播 → 下游 skipped） |
| 无 Entry 时 Backtest 不产生交易 | G6 test #1（INSUFFICIENT_SIGNALS 零交易） |
| Monitor 不能把通用新闻全当策略 Signal | G7 test #1（strategy_entry_exit 信号与通用观察分离计数） |
| 重复运行不产生重复决策 | G7 Cursor 幂等（二跑零新增） |
| 无关 Prediction 不能 Replay | G8 test #1（严格因果过滤） |
| 无 Artifact 的 Research Product 不能发布 | G9（compile 即注册；失败 → INCOMPLETE_PROVENANCE 显形） |
| 不存在路由不能通过导航测试 | G9 页面走真实 /research-products 路由；前端 tsc/构建校验 |

### 2. Golden A/B/C（tests/test_g13_golden.py，3 用例，全部生产 API）

| Golden | 链路断言 | 结果 |
|---|---|---|
| A 稀土产业链 | 5 环节/5 边 + 边证据可追溯 + 000831/600259 位置隔离 + 历史 PIT + Thesis Diff 入口 | PASS |
| B 经验到策略闭环 | Approved Experience → ScreenDefinition（规则编译断言）→ 未发布 422 → 发布 → PIT 运行（Artifact）→ 策略版本 + backtest-v2（event_backtest_v1） | PASS |
| C 研究产品与帷幄 | 产品版本+Artifact → Thesis Diff → 帷幄确认门（拒绝不执行 422 → 批准 → Thesis 修订 + Artifact） | PASS |

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（528 collected）
frontend：tsc PASS + vitest 35/35 + build PASS（G9 后基线）
```

## 状态

SEMANTIC GOLDEN VERIFIED（A/B/C 全部经生产 API，无手工制造结果）。
