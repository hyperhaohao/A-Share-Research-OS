# R6-MANIFEST — Experience 非量化改造

```text
donor basis:      98f1398（REFERENCE_ONLY：cards/refine.py 结构 → 行为适配）
backend:
  - LLM 结构化精炼 refine_structured（方案 §12.2 九字段：observation/
    mechanism/preconditions/expected_outcome/counter_example/
    failure_conditions/applicable_scope/invalidators/research_checklist）：
    输入=卡自身 research state；LLM 只重述/归纳/拆分（prompt 硬约束
    禁新增事实）；原文+炼果双存（refined_json 列，migration f7a8b9c0d1e2，
    版本 +1 method=llm_structured）；无 KEY → 422 显式拒绝
  - 非量化验证四方法（§12.3）：
    counterexample_search（本标的语料负面共现确定性检索，命中落档；
    措辞如实「未见反例≠不存在反例」）/
    historical_evidence_validation（历史快照 PIT 入场→其后报价前向核对）/
    cross_company_validation（同业板块成员行情可得性核对，真实关系源）/
    expert_review（人工复核留档）
  - POST /{id}/refine-structured + POST /{id}/validate-non-quant +
    GET /playbook/search（已批准卡片检索；条目无 authority/fact_status
    字段 —— Playbook≠Evidence 由结构锁死，§12.4）
frontend: 无 UI 变更（卡片页验证动作走既有 API；Playbook 检索 API 就绪
  供 R7 Memory 面板与 Commander 检索）
tests:            tests/test_r6_experience.py 3/3（四方法/审批门/Playbook 边界/
  无 KEY 422）；全量 backend exit 0；vitest 30/30；build PASS；E2E 30/30
live:             playbook.search?q=减持 → 10 hits（真实已批准卡片）
deviations:       LLM 精炼的实际运行需 ASRO_LLM_API_KEY（外部阻塞项，管道
  已通 + 422 显形 + schema 校验就绪）；IC/回测验证未实现 = 方案 §12.3 明确禁止
next: R7 Research Memory
```
