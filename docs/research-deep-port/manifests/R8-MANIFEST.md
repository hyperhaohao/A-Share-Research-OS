# R8-MANIFEST — Research Inbox / Thesis Diff / Signal Ladder

```text
donor basis:      98f1398（REFERENCE_ONLY）
backend:
  - app/services/research_inbox.py + GET /research-inbox（只读投影，方案 §14.1）：
    聚合 新证据（窗口）/ 重要性决策（DELTA+FULL）/ OPEN ResearchRequest /
    到期预测 / 失败采集 —— 全部来自既有真实表，不建第二 Domain
  - Thesis Diff（方案 §14.3）：GET /research-inbox/thesis-diff（确定性影响分析：
    new_evidence → affected_claims → affected_theses → suggested_action）；
    POST /thesis-diff/apply（新 Thesis 行 append-only + Artifact
    generated_from 旧 Thesis + RunEvent 落库；新证据必须 pinned by snapshot ——
    PIT 强制；无新证据 → 422 显式拒绝）
  - Signal Ladder（方案 §14.5）：POST /signal-ladder/evaluate ——
    A/B 分级确定性关键词规则 + 证据引用强制（伪造 evidence → 422）；
    每次命中带 evidence_ids（§14.5：展示证据）
  - Pipeline 缺口补齐：Thesis 注册 Artifact（此前漏注册导致图谱断链），
    run produced thesis 边落库
deviations（如实）:
  - Monitor 类型扩展（company/industry/event/thesis/catalyst 分型）：
    v1 由 SignalLadder + Inbox 的 event_type scope 承接语义；
    独立 monitor 类型枚举在 R9 图谱扩展时随 Graph 节点类型一并落
  - Materiality 的 affected_* 扩展由 ThesisDiff 承接（同一影响分析），
    MaterialityJudge 本体保持确定性阈值不变
frontend: ResearchPipelineCard 已渲染 waiting_data/missing_data_summary/
  reviewing/profile_applied（R4）；Inbox 专属页面随 R9 图谱整合一并挂导航
live verify (manifests/R8-LIVE-VERIFY.md): 真实栈
  inbox count=24（8 新证据 + 8 失败采集）；thesis diff new_evidence=20/
  affected_claims=2289/affected_theses=177/suggested_action=delta_research
tests:            tests/test_r8_inbox.py 3/3；全量 backend exit 0
next: R9 Research Graph + Final Closure
```
