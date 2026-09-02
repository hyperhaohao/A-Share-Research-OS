# G6-MANIFEST — Executable Strategy Lab

> 观澜研究能力语义迁移任务书 §G6（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §6（无条件未来收益 → FAIL）

## 交付

### 1. 事件驱动回测引擎（app/services/backtest_engine.py）
- **Entry 触发才建仓**（规则全满足）；**Exit/Risk 真实改变交易路径**；
- 规则种类（确定性、可审计）：
  - Entry：price_above_ma / price_below_ma / quote_move{pct,window}
  - Exit：take_profit{pct} / stop_loss{pct} / max_hold_days{days}
  - Risk：max_drawdown{pct}（NAV 回撤触发强制平仓）
- **成本/滑点双边计提**（cost_bps/slippage_bps）；
- **停牌/跌停延迟成交**（不伪造成交；停牌日 NAV 沿用最后价）；
- **非重叠交易序列**（单仓位：下一入场晚于上一退出，测试锁定）；
- 指标：n_trades/win_rate/avg_return/total_return/**max_drawdown**/
  avg_hold_days/**exposure_pct**/turnover_per_year/**benchmark(buy_hold)
  + excess_return**；
- **分期**：in_sample/out_of_sample 70/30 按日期确定性切分、独立重放
  （include_phases=False 防递归 —— 自测捕获修复）；
- **regime 可复现定义**：入场日收盘 vs MA60 → trend_up/trend_down
  （非按年份命名）；
- 无 Entry 规则 → **INSUFFICIENT_SIGNALS 零交易**（§G6 DoD）。

### 2. Strategy API 集成（POST /strategies/{id}/backtest-v2）
- 版本 entry/exit/risk policy → 引擎 spec（现有 forward_return 阈值语义
  可解释转换为 quote_move 规则；**显式空 entry_rules 保留** = 无入场）；
- 逐 universe 标的执行；failure_cases 显形（如无日线数据）；
- 结果落 StrategyBacktestRun（results 含 trades/NAV/metrics/分期/regime；
  aggregate 含 engine 标识/规则快照/合计）+ Artifact 注册
  （失败 → INCOMPLETE_PROVENANCE 显形）。

## 测试

### 引擎级（tests/test_g6_backtest.py，9 用例）
| # | 场景 | 结果 |
|---|---|---|
| 1 | 无 Entry → INSUFFICIENT_SIGNALS 零交易 | PASS |
| 2 | Entry 触发建仓 + take_profit 出场 | PASS |
| 3 | Entry 门槛变化 → 交易变化 | PASS |
| 4 | Exit 变化（tp vs sl）→ 交易路径不同 | PASS |
| 5 | 成本/滑点递减收益 | PASS |
| 6 | 交易非重叠 | PASS |
| 7 | 停牌/跌停顺延出场 | PASS |
| 8-9 | 分期/regime/回撤风险/基准/超额 | PASS |

### API 级（tests/test_g6_strategy_api.py，4 用例）
| # | 场景 | 结果 |
|---|---|---|
| 1 | Entry 变化 → 交易变化（DoD） | PASS |
| 2 | Exit/Risk 变化（回落路径）→ 收益/交易变化（DoD） | PASS |
| 3 | 无 Entry 规则 → INSUFFICIENT_SIGNALS（DoD） | PASS |
| 4 | Artifact 注册 | PASS |
（全量 backend 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G7：Monitor 执行所引用策略版本规则（复用本引擎语义）。
