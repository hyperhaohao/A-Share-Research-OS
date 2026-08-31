# C1-MANIFEST — Thesis Diff Correctness（整改 P0-01）

```text
problem:  旧算法「旧证据∉新证据=stale」→ 20 条新证据误标 2289 claims/177 theses
fix:      app/services/claim_impact.py — ClaimImpactService
          - 七种关系枚举：supports/strengthens/weakens/contradicts/supersedes/updates/irrelevant
          - Gate 1: 实体重叠 ≥ 0.20 AND 共享 token ≥ 2（防单数字 2-gram 误匹配）
          - Gate 2: 事件类型重叠（share_reduction/restructuring/earnings/…八类确定性规则）
          - 事件不重叠 → irrelevant（实体重叠 alone 不构成研究影响）
          - _determine_relation: 否定标记→contradicts / supersede标记→supersedes /
            同事件已有→strengthens / 新引用→updates / 新独立支撑→supports
result:   affected_claims 2289→61（irrelevant 47851 如实返回）
          affected_theses 177→19
tests:    tests/test_c1_claim_impact.py 5/5（事件分类/实体判别/否定标记/关系枚举/核心分歧）
          tests/test_r8_inbox.py 3/3 PASS
next:     C2 Thesis Revision / Version Model
```
