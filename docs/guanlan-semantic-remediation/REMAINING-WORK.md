# 观澜研究能力语义迁移第二轮整改 — 执行状态与剩余工作

> 复审基线 main@b25eede | 本轮执行 R0–R2（已完成）+ R3–R12（待执行）
> 当前状态：REJECT — G14 CLOSURE INVALID → R0–R2 已完成，R3–R12 待执行

## 已完成（R0–R2，3 commits）

| 阶段 | commit | 核心交付 |
|---|---|---|
| R0 | 4d41519 | uv.lock 修复、11 文件排序 tiebreaker、live marker 默认排除、Closure Gate 脚本（scripts/verify_remediation.py）、G14 closure 标 REOPEN |
| R1 | 020bb6e | ResearchProductionFacade（ScreenRun → Strategy 唯一路径，input_digest/idempotency/因果 ID）；Replay 回退路径封存旧 create_from_screening |
| R2 | 84bba01 | 反例验证 Fail-closed（空语料 INCONCLUSIVE / 0 反例 NO_COUNTEREXAMPLE_FOUND / 命中 FAIL）；approve 必须 Confirmation-gated（digest 绑定 card_version）；ToolSpec.confirmation_consumed_by_executor |

## R3–R12 剩余工作（按任务书 §四/§五 详细规格）

### R3 — Fail-closed Screen Compiler（P0）
- 未知规则不得返回 pass（signal_rule 目前无条件通过 → 改 BLOCKED）；
- 未编译前置条件不静默保存为可发布定义；
- Publish 必须走持久 Confirmation（当前 {confirm:true} → 改 POST confirmation → decide approved）；
- ScreenRun 冻结定义版本和数据快照（当前已冻结定义，需冻结证据 PIT）；
- rule-by-rule evaluation trace 落结果；
- Strategy 创建只消费已发布 ScreenDefinitionVersion（R1 Facade 已强制）。

### R4 — StrategyDefinition 与真实条件回测（P0）
- StrategyDefinition 增加 Universe/ScreenRun 引用（R1 Facade 已传）、
  Position Sizing、Capital Constraint、Rebalance Policy、Commission、Slippage、
  Benchmark、Evaluation Window、OOS Policy、Overlap Policy 显式字段；
- 禁止 legacy forward_return 自动解释为 quote_move 策略（R1 已改为显式转换）；
- G5 ScreenRun 可直接创建 StrategyDefinition（R1 Facade from-screen-run ✓）；
- 旧 forward-return analyzer 不再作为默认生产路径（G6 引擎已替代）。

### R5 — 策略监控与游标治理（P0）
- Monitor 冻结 StrategyDefinitionVersion（当前 version_id ✓）；
- 复用 Backtest 同一 Rule Evaluator（G7 已用 G6 引擎 spec）；
- Monitor Run 走持久任务跑道（当前 Scheduler.tick 直接泵，需迁移到
  command_background_tasks 或等价持久队列）。

### R6 — 严格因果 Replay（P0）
- Replay 因果链验证扩展：Strategy Signal → Monitor Run → StrategyDefinition →
  ScreenRun → ExperienceVersion（当前仅 Prediction→Decision 链）；
- 固定 confidence 已移除（F4/G12 归因数 basis）；
- 版本号事务安全分配（当前 version_no=max+1 需 SELECT FOR UPDATE 或唯一约束）。

### R7 — Industry Graph PIT 与证据归属（P1）
- 双时间模型（valid_from/valid_to/recorded_at）→ 当前 as_of 过滤只查
  created_at + available_time，需补充 edge/position 的 recorded_at 快照；
- Evidence 归属扩展到 Source/Target Segment + Transmission Mechanism 匹配；
- Global Position PIT 或明确返回 NOT_REPLAYABLE。

### R8 — Typed Workflow 生产化（P1）
- 前端 Studio 迁移到 /workflows-typed API；
- human_confirmation 节点 → 持久 Confirmation + WAITING_CONFIRMATION 状态 +
  下游停执行 + 重启恢复；
- Merge 策略声明；多分支合并不覆盖同端口。

### R9 — Research Products 产品化（P1）
- 内容级 Diff（当前 items 数量对比 → 逐条 ID/内容 Diff）；
- 条目导航到 Evidence/Thesis/Edge/Experience/Strategy/Monitor；
- Compile 使用持久 Confirmation（当前 {confirm:true} → R11 确认门）。

### R10 — Thesis Center 与不可变 Memory 版本（P1）
- strengthened/weakened 按旧→新方向计算（当前简化为 max>min）；
- added/removed/strengthened/weakened/reframed + 具体 Claim/Evidence ID；
- Memory 内容版本不可变表（当前 content 存当前行，需版本历史表）。

### R11 — 帷幄审批、Workbench 与持久任务（P0）
- EventThread 确认卡使用事件携带的原 confirmation_id（当前 EventThread
  创建第二张确认 → 改 POST /confirmations/{event.correlation_id}/decide）；
- Workbench Tab 内渲染真实业务视图（当前只有链接 → 嵌入 Thesis/Evidence/
  Industry 等 Panel 视图）；
- Commander Tool-based Plan（固定三步 → 按意图生成工具序列）；
- Commander Plan / Workflow Run / Screening / Backtest / Replay / Compile
  迁移到持久任务跑道（当前 daemon thread → command_background_tasks）；
- research_state_check 五维度扩展（§R11.5）。

### R12 — 真实 Golden 与 Closure Gate（P0）
- Golden A/B/C 全部去 ORM 种入 → 经 Production API；
- verify_remediation.py 补齐 §17.5 全部 14 项（daemon thread 空扫描、
  {confirm:true} 零命中、PLAN 全勾、STATUS 无 REJECT 等）；
- 机器生成 Closure（非手写数字）。

## 建议执行顺序

R3 → R4（核心：Screening/Strategy 统一到同一 Definition）→
R5（Monitor 对齐）→ R6（因果链补全）→ R11（帷幄持久任务迁移 + 确认卡修复）
→ R7/R8/R9/R10（可并行）→ R12（Golden + Closure Gate 终审）。
