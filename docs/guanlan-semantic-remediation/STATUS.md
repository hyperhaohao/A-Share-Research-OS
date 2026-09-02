# 观澜研究能力语义迁移整改 — STATUS

## Current Phase

```text
Guanlan Research Capability Semantic Migration Remediation（G0–G14）
Status: REJECT — GUANLAN RESEARCH CAPABILITY MIGRATION INCOMPLETE（2026-09-02）
依据：docs/观澜研究能力语义迁移整改任务书.md

Baseline: ASRO c66952e | backend 459/0 | vitest 35/35 | tsc/build PASS
台账：MIGRATION-MATRIX.md（G0 代码实读；六项关键指控全部核实属实）

G1 DONE（见 G1-MANIFEST.md）。G2 DONE（见 G2-MANIFEST.md）。G3 DONE（见 G3-MANIFEST.md）。G4 DONE（见 G4-MANIFEST.md）。G5 DONE（见 G5-MANIFEST.md）。G6 DONE（见 G6-MANIFEST.md）。G7 DONE（见 G7-MANIFEST.md）。G8 DONE（见 G8-MANIFEST.md）。G9 DONE（见 G9-MANIFEST.md）。执行中：G10 Thesis Center/Inbox/Memory。
```

## 关键核实结论（代码实读）

1. 产业链来自行业分类字符串（industry_view_service），无边/无传导 → G1 FAIL；
2. Workflow Edge 不传数据（_node_output 返回标签串）→ G4 FAIL；
3. Screening 用 DEFAULT_RULES 常量，Experience 内容不进规则 → G5 FAIL；
4. Backtest entry=forward_return 阈值、exit=horizon_end 固定，无仓位/成本/风险 → G6 FAIL；
5. Monitor 用 quote_move 阈值 + 新事件，不执行策略规则 → G7 FAIL；
6. Replay candidate 按 universe 任选已验证 Prediction，与 Decision 无因果引用 → G8 FAIL；
7. 三市场产品编译器返回临时 dict，无 Artifact/PIT/Version → G9 FAIL。

旧验收文档处置：F15-CLOSURE.md 与 F11-GUANLAN-PARITY.md 已加 REOPENED/SUPERSEDED
标注（第三轮范围内 F0–F15 自身口径成立；观澜**语义**维度由本轮重新裁决）。
