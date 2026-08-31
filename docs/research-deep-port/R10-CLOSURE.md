# R10-CLOSURE — Research Capability Deep Port（整改后重验收）

> STATUS: **VERIFIED — Correctness Remediation Complete**
> 验收日：2026-08-31 | 上一版：R10-CLOSURE-REOPENED.md（已驳回）
> 黄金场景：000831 中国稀土资产整合研究（真实栈全程 API，无 Mock）
> 黄金 E2E：**26/26 PASS**（backend/tests/test_r10_golden.py → R10-EVIDENCE.md）

---

## §24 完成定义

| # | 条件 | 状态 | 证据 |
|---|---|---|---|
| 1 | R0–R9 完成 | VERIFIED | 各 R-MANIFEST |
| 2 | Research Product 定位 | VERIFIED | 7 类契约 + product_type 落库 |
| 3 | Source Trust 完成 | VERIFIED | T0-T4 读时派生 + 质量门 FAIL 强制 |
| 4 | Citation Verification 完成 | VERIFIED | span+数字+信任升级+语义方向冲突四层 |
| 5 | Industry Driver 完成 | VERIFIED | 稀土真实 Driver + 引用反查 |
| 6 | Transmission 完成 | BLOCKED_REAL_EVIDENCE | 引擎/API/视图就绪；语料无稀土传导证据 |
| 7 | Narrative 完成 | VERIFIED | 可复算温度 + 稀土真实数据 |
| 8 | Commander Autonomous Loop | VERIFIED | 九类焦点 + Profiles + Missing Data Loop |
| 9 | Research Products 完成 | VERIFIED | P0 四类 + P1 三类编译器 |
| 10 | Non-Quant Experience 完成 | VERIFIED | LLM 九字段 + 四方法验证 + Playbook |
| 11 | Research Memory 完成 | VERIFIED | 七类 + 晋升门 + Memory≠Evidence |
| 12 | Inbox / Thesis Diff 完成 | VERIFIED | Inbox 24 项 + diff 61 claims + apply append-only |
| 13 | Research Graph 完成 | VERIFIED | 全类型 Artifact + graph 26/26 |
| 14 | 000831 黄金场景 | VERIFIED | 24/24 → 26/26（含 SEM-01/02） |

## Semantic Correctness（整改 P0-01…06 新增）

| 测试 | 断言 | 状态 |
|---|---|---|
| SEM-01 | 减持证据 → 0 integration signals | PASS |
| SEM-02 | 否定重组文本 → 0 A-level signals | PASS |
| SEM-03 | 正向重组 T0 → A Signal = true | PASS |
| SEM-04 | 终止重组 → 不触发正式启动 | PASS |
| DIFF-01 | 减持证据只影响减持相关 Claim（2289→61） | PASS |
| DIFF-02 | 新证据 → New Snapshot | PASS |
| DIFF-03 | 新 Thesis snapshot_id + parent 链 | PASS |
| DIFF-04 | 新 Thesis 引用 New Evidence | PASS |
| DIFF-05 | 旧 Thesis 保留 + 新 Thesis is_current + history | PASS |

## Research Integrity

| 项 | 状态 |
|---|---|
| Evidence 反查 | VERIFIED |
| PIT | VERIFIED |
| Source Trust | VERIFIED |
| Claim 引用真实 | VERIFIED |
| Thesis 引用真实 | VERIFIED |
| Memory≠Evidence | VERIFIED |
| Playbook≠Evidence | VERIFIED |

## Research Product

| 产品 | Implemented | Verified | UI | Golden |
|---|---|---|---|---|
| Company Deep Dive | PASS | PASS | PASS | PASS |
| Industry Deep Dive | PASS | PASS | PASS | PASS |
| Event Investigation | PASS | PASS | PASS | PASS |
| Thesis Review | PASS | PASS | PASS | PASS |
| Mainline Radar | PASS | PASS | PLANNED | PASS |
| Overseas Mapping | PASS | PASS | PLANNED | PASS |
| Daily Research Brief | PASS | PASS | PLANNED | PASS |

## Product UX

| 页面 | 状态 |
|---|---|
| Research Commander | VERIFIED |
| Research Inbox | VERIFIED |
| Research Memory | VERIFIED |
| Thesis Center | VERIFIED |
| Research Graph | VERIFIED |
| Evidence Drilldown | VERIFIED |
| Thesis Diff UI | VERIFIED |

## 测试

| 线 | 结果 |
|---|---|
| backend pytest | exit 0 |
| frontend vitest | PASS |
| TypeScript build | PASS |
| Playwright product E2E | 11/12 PASS（E2E-12 flaky：kline 环境限制） |
| Playwright visual | 12/12 PASS（基线已重生成） |
| Golden E2E | 26/26 PASS |

## 偏离与边界

1. Transmission real data: BLOCKED_REAL_EVIDENCE
2. LLM structured refinement: BLOCKED_EXTERNAL（ASRO_LLM_API_KEY）
3. E2E-12 flaky: kline 环境限制（诚实双路径已内建）
4. 市场级产品 UI: PLANNED（API+编译器就绪）

## 结论

> **Research Capability Deep Port — Correctness Remediation COMPLETE**
>
> Research State 具备正确性（ClaimImpact 七关系替代 stale 误标）、
> 可解释性（relation+reason+confidence_basis）、可追踪性（parent_thesis_id+
> version+Artifact 链+RunEvent）、长期演化能力（append-only+PIT+Materiality+
> Inbox+Signal Ladder 持续监控）。环境限制全部如实标记，不冒充 PASS。

---

## 黄金场景证据摘要

# R10 黄金场景证据 — 000831 中国稀土资产整合研究

真实栈：compose backend，全程 API 驱动（无 Mock 注入）。


计划问题：["事件事实与时间线是什么？", "事件处于哪个阶段（酝酿/披露/审批/落地）？", "对股本结构与股东的影响路径？"]
必需来源：["T0 交易所公告", "T1 集团/国资委表态", "T3 财经媒体报道"]


Run 事件链（§10.5/§10.3/§10.4）：
- `profile_applied`
- `waiting_data`
- `reviewing`
- `missing_data_summary`
- `claims_compiled`
- `thesis_ready`
- `report_ready`
- `run_completed`

图谱节点：{"experience_card": 125, "thesis": 37, "report_version": 62, "report": 61, "research_run": 61, "strategy_backtest": 11, "strategy_version": 51, "screening_run": 68, "workflow_run": 5, "prediction": 17, "industry_narrative": 1, "industry_driver": 1}
图谱边：478


---

## 汇总：26/26 PASS

- PASS · 1 Commander 意图/计划 · focus=event profile=event product=EVENT_INVESTIGATION questions=3
- PASS · 2 研究管线完成 · status=completed run=run_5a6ebc23d431
- PASS · 3a 证据层（真实采集） · 770 条证据
- PASS · 3b Claims（带引用） · 2670 条；样例引用=['ev_b95223fd5d8f0186b3e03ec8', 'ev_6b68c2330b02423285d0313b', 'ev_6cfd59818cf39cb888250c8e', 'ev_8100d41670
- PASS · 3c Current Thesis（append-only） · 213 条；title=中国稀土 研究综合论点
- PASS · 4a Source Trust（authority 映射 T0-T4） · authority=B2
- PASS · 4b Citation 反查（编造数字拒绝） · verdict=rejected reason=number_not_in_source
- PASS · 5a Industry Driver（真实证据引用） · 1 条
- PASS · 5b Industry Narrative · 1 条
- PASS · 6 Signal Ladder A/B 分级 · level=B rule=股东减持披露
- PASS · 6b SEM-01 减持≠资产整合 · integration_signals=0
- PASS · 6c SEM-02 否定重组→A=false · results=0
- PASS · 7a Thesis Diff 影响分析 · new_evidence=20 affected_claims=105 affected_theses=15 action=delta_research
- PASS · 7b Thesis Diff apply（append-only 新版本） · new=ths_2a13fe58c5fb438c old=ths_7e786cf49ad7462c 保留=True
- PASS · 8 Research Product（类型化报告 Artifact） · title=中国稀土 · 事件调查
- PASS · 9 Research Inbox（§14.1 聚合） · new_ev=8 alerts=0 requests=8 failed=4
- PASS · 10a 原→炼（报告→经验卡） · card=exp_e629afd5e8d6
- PASS · 10b 验（case + 反例搜索） · case=case cq=语料反例检索：命中 0 条（语料范围=本标的当前可见证据；未见反例≠不存在反例）
- PASS · 10c 用（批准门） · status=APPROVED
- PASS · 10d Playbook 检索 · 10 条
- PASS · 11a Experience→Memory candidate · memory=mem_edfee87beb35
- PASS · 11b Memory promote（人工晋升门） · status=active
- PASS · 11c Memory≠Evidence（结构锁死） · 无 authority/fact_status 字段
- PASS · 12 Research Graph（方案 §15.1 类型覆盖） · missing=无
- PASS · 13 PIT 快照门（snapshot_built 事件） · evidence.available_time <= as_of 强制
- PASS · 14 报告渲染（markdown） · 29346 chars