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

图谱节点：{"experience_card": 109, "thesis": 60, "report_version": 69, "report": 68, "research_run": 68, "strategy_backtest": 15, "strategy_version": 36, "screening_run": 51, "workflow_run": 7, "prediction": 15, "industry_narrative": 1, "industry_driver": 1}
图谱边：458


---

## 汇总：24/25 PASS

- PASS · 1 Commander 意图/计划 · focus=event profile=event product=EVENT_INVESTIGATION questions=3
- PASS · 2 研究管线完成 · status=completed run=run_2081e8d1cbd8
- PASS · 3a 证据层（真实采集） · 793 条证据
- PASS · 3b Claims（带引用） · 3021 条；样例引用=['ev_b95223fd5d8f0186b3e03ec8', 'ev_6b68c2330b02423285d0313b', 'ev_6cfd59818cf39cb888250c8e', 'ev_8100d41670
- PASS · 3c Current Thesis（append-only） · 236 条；title=中国稀土 研究综合论点
- PASS · 4a Source Trust（authority 映射 T0-T4） · authority=B2
- PASS · 4b Citation 反查（编造数字拒绝） · verdict=rejected reason=number_not_in_source
- PASS · 5a Industry Driver（真实证据引用） · 1 条
- PASS · 5b Industry Narrative · 1 条
- PASS · 6a GOLD-SIGNAL-01 减持→整合信号=NONE · integration_hits=0
- FAIL · 6b Production Signal API · status=500 count=None
- PASS · 7a Thesis Diff 影响分析 · new_evidence=20 affected_claims=123 affected_theses=17 action=delta_research
- PASS · 7b Thesis Diff apply（append-only 新版本） · new=ths_d90995f6c29042e7 old=ths_aefe5e7f6e8b42fe 保留=True
- PASS · 8 Research Product（类型化报告 Artifact） · title=中国稀土 · 事件调查
- PASS · 9 Research Inbox（§14.1 聚合） · new_ev=8 alerts=0 requests=8 failed=4
- PASS · 10a 原→炼（报告→经验卡） · card=exp_90ffedbfd3d8
- PASS · 10b 验（case + 反例搜索） · case=case cq=语料反例检索：命中 0 条（语料范围=本标的当前可见证据；未见反例≠不存在反例）
- PASS · 10c 用（批准门） · status=APPROVED
- PASS · 10d Playbook 检索 · 10 条
- PASS · 11a Experience→Memory candidate · memory=mem_fead53baa676
- PASS · 11b Memory promote（人工晋升门） · status=active
- PASS · 11c Memory≠Evidence（结构锁死） · 无 authority/fact_status 字段
- PASS · 12 Research Graph（方案 §15.1 类型覆盖） · missing=无
- PASS · 13 PIT 快照门（snapshot_built 事件） · evidence.available_time <= as_of 强制
- PASS · 14 报告渲染（markdown） · 30317 chars