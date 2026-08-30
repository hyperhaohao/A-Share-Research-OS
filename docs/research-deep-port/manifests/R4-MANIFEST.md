# R4-MANIFEST — Research Commander Autonomous Loop

```text
donor basis:      98f1398（REFERENCE_ONLY：intent router/soft_deps/progress 语义 → 行为适配）
backend:
  - Intent Router 扩至方案 §10.1 九类焦点（event/earnings/policy/mainline/
    overseas_mapping/thesis_review/comparison/industry/company + general），
    纯确定性关键词（donor intent.py 语义 ASRO 化）；焦点不改执行动作，
    只收敛证据面（profile）与计划问题
  - Agent Profiles（app/domain/profiles.py，方案 §10.4）：profile→
    capabilities+analysts 白名单；未知 profile → general（不漂移）；
    pipeline.run(profile=..., max_collection_passes=...) 过滤采集面与分析师面，
    profile_applied 事件显形裁剪了什么
  - 结构化 Plan（方案 §10.2）：research_plans.meta_json（migration
    d4e5f6a7b8c9）：objective/focus/profile/questions[]/required_sources[]/
    completion_criteria[]/expected_artifacts/max_collection_passes；
    九类焦点各带研究问题与完成标准（研究启发，非事实）
  - Missing Data Loop（方案 §10.3，有界）：max_collection_passes≥2 时对
    本 run 快照上 OPEN ResearchRequest 点名的 capability 再采一轮；
    waiting_data/missing_data_summary 事件显形（仍缺失 → 下一周期继承，
    禁止同 run 重复建 Claim）
  - run 状态语义（方案 §10.5）：waiting_data/reviewing 事件 +
    run_events stage/title 映射（WAITING_DATA/REVIEWING）
frontend:
  - ResearchPipelineCard SSE 接入 4 新事件：研究面（Profile）收敛行/
    等待补充数据行/研究复核行/缺失数据摘要行（§10.5「当前缺什么」可见）
live verify (manifests/R4-LIVE-VERIFY.md):
  黄金问题「研究中国稀土近期资产整合信号」→
  plan focus=event profile=event passes=2 + 三条事件研究问题 +
  required_sources=[T0 交易所公告, T1 集团/国资委表态, T3 财经媒体报道]；
  run_completed，事件链 profile_applied（裁剪 financials/industry/
  historical_data 三项显形）/waiting_data/reviewing/missing_data_summary
  全 PRESENT —— §44 DoD 1/2/4/10 达成；3（T0/T1 优先）由 profile 收敛
  公告/事件面落地，5-9 由管线完成（Claims/Thesis/Risk/Report）+ R5/R8 深化
tests:            backend 全量 exit 0；vitest 30/30；build PASS；E2E 30/30
next: R5 Research Product System
```
