# R9-MANIFEST — Research Graph + Context Handoff

```text
donor basis:      98f1398（REFERENCE_ONLY）
backend:
  - IndustrySemantic upsert 注册 Artifact（industry_driver/transmission/
    narrative/position，幂等 per domain_id —— 更新刷新 title/version），
    进入 /artifacts/graph 全库视图
  - ResearchMemory promote 后为 graph 就绪（RESEARCH_MEMORY 枚举就位；
    memory→artifact 注册在 promote 时调用方触发）
  - Handoff 动作扩展（方案 §15.3）：evidence/claim/driver/narrative/thesis/
    memory/research_product → commander（open_in_commander），
    服务端持久化信封（禁 localStorage 临时信箱）
  - Pipeline Thesis Artifact 注册补齐（R8 已并入）
graph state (真实栈 /artifacts/graph):
  experience_card 42 / screening_run 24 / report_version 20 / report 20 /
  research_run 20 / strategy_version 18 / prediction 6 / edges 148
  + semantic objects（driver/narrative 已注册，真实数据 1+1）
deviations:
  - Memory→artifact 注册在 promote 调用点触发，R7 内 create_candidate 不注册
    （candidate 未进图谱，active 才进 —— 与方案 §13.5 晋升语义一致）
  - CorporateEvent/Catalyst/Risk 独立 Artifact 类型：Catalyst/Risk 内嵌于
    Thesis/Report（§29/§37 设计），Event 由 CorporateEvent ORM + 时间线
    承载 —— 图谱节点经由 claim/thesis 边可达，不重复建独立节点
tests:            全量 backend exit 0；vitest 30/30；build PASS；E2E 30/30
next: R10-CLOSURE（000831 黄金场景逐项证明）
```
