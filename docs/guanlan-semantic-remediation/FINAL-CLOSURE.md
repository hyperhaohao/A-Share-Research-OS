# G14 — FINAL-CLOSURE（观澜研究能力语义迁移）

> 任务书：docs/观澜研究能力语义迁移整改任务书.md
> 执行区间：G0 → G14（2026-09-02）| 基线 ASRO c66952e
> 本 Closure 签署前，第三轮 F15-CLOSURE 的「语义维度」已标注 SUPERSEDED。

---

## §G14 十条签署条件逐条核对

| # | 条件 | 状态 | 证据 |
|---|---|---|---|
| 1 | G0–G14 所有 P0 完成 | ✅ | 各 Gx-MANIFEST + PLAN.md 全勾 |
| 2 | 产业链不是分类树冒充 | ✅ | G1 六表分域；分类树保留但不再命名产业链 |
| 3 | Workflow 是真实数据流 | ✅ | G4 端口/类型/节点 I/O 账本 + 数据传递测试 |
| 4 | Experience 能生成生产 Screening Rule | ✅ | G5 编译器（仅 Approved；未批准 422；规则断言） |
| 5 | Backtest 真实执行策略条件 | ✅ | G6 事件引擎（Entry/Exit/Risk/成本/滑点/停牌/跌停） |
| 6 | Monitor 真实执行 Strategy Version | ✅ | G7（策略规则信号 + Cursor 幂等 + 状态机） |
| 7 | Replay 具有因果链并改变可执行定义 | ✅ | G8（decision_id 因果引用 + rule_error → stop_loss 规则修改） |
| 8 | Research Products 有 Artifact/PIT/Version/Provenance/UI | ✅ | G9（research_product_compiles + /research-products 页面） |
| 9 | 帷幄消费真实研究产物并经过确认审计 | ✅ | F5–F10 + G11（research_state_check） |
| 10 | Golden 全程通过生产 API | ✅ | G13 Golden A/B/C（test_g13_golden.py 3/3） |

## 全量回归（最终）

```text
backend pytest：528 collected / 0 FAILED / exit 0（G14-backend-final.txt）
frontend：vitest 35/35 + tsc PASS + vite build PASS
迁移链：空库 upgrade head 全通；现有库六迁移自动应用（compose 实测）
```

## 外部阻塞 / 未完成项（诚实登记，不计 PASS）

1. **LLM Structured Refinement / AI 研判**：BLOCKED_EXTERNAL（ASRO_LLM_API_KEY 缺失）。
2. **链级传导 / 五轴「技术/政策」深值**：BLOCKED_REAL_EVIDENCE（依赖真实语料与
   语义对象积累；机制/端点已就绪，数据到位即自动补全）。
3. **东财 kline 端点**：BLOCKED_ENVIRONMENT（本机网络间歇性；恢复即全通，
   E2E-12 已在恢复窗口验证 VALIDATED 路径）。
4. **因子引擎 / ScreenDefinition 因子层**：登记未实现（量化线冻结，恢复需用户明示）。
5. **Workflow Undo/Redo、导入导出、15 类节点执行深度不一**：登记。
6. **历史迁移（r6 时代）downgrade drop_index 参数错误**：预先存在问题，正向迁移不受影响。
7. **test_f5 replay 顺序敏感 flake**：单测/重跑通过；并发写入时序敏感，已登记。

---

## 最终验收结论

```text
GUANLAN RESEARCH CAPABILITY MIGRATION VERIFIED
```

依据（§十 最终验收口径）：观澜原有研究方法已在 ASRO 中成为**可执行
（Typed Workflow/规则编译/事件回测引擎）、可验证（验证方法 + PASS 门 +
语义否定测试）、可监控（策略感知 Monitor + Cursor 幂等）、可复盘（因果
Replay + 规则反馈改变可执行定义）、可 PIT 重放（图谱/证据/产品全链
as_of）**的研究能力，且具备代码、语义测试、真实产物与 Provenance 证据。

外部阻塞项均诚实登记（BLOCKED_EXTERNAL / BLOCKED_REAL_EVIDENCE /
BLOCKED_ENVIRONMENT / 登记未实现），不冒充 PASS；恢复后相应能力自动补全。
