# F1-F3-MANIFEST — Research State Correctness（整改 P0-A）

```text
F1 Current Thesis:
  - app/services/current_thesis.py: get_current_thesis() —
    meta_json.is_current=true 最新行；无标记 → created_at 最新（legacy fallback）
  - demote_other_currents(): 切换时将同 instrument 其他 thesis 降级
  - GET /research-inbox/theses/current/{instrument_id}：正式 Current Thesis API
  - GET /research-inbox/theses/history/{instrument_id}：版本链
  - GET /research-inbox/theses/{id}/diff/{other_id}：两版差异

F2 New Snapshot Revision:
  - apply_thesis_diff 重写：build NEW PIT snapshot at now（pins ALL visible
    evidence including new）；新 Thesis 钉在新快照上（不再复用旧快照）
  - old_snapshot_id / new_snapshot_id / added_evidence_ids 记录在 meta_json

F3 Claim Revision Apply:
  - ClaimImpact → New Claims pinned to NEW snapshot（[修订] 关系前缀）
  - 新 Thesis supporting_claims = new_claim_ids（新快照上的 claims）
  - 旧 Claims 留在旧 Thesis（append-only 保留）；不混用跨快照 claims
  - 新 Thesis 是 CURRENT（meta.is_current=true），旧 Thesis is_current=false

问题修复：
  - select().first() 替换为 get_current_thesis()
  - 旧快照不再用于正式 Revision（New Snapshot 强制）
  - meta_json.new_evidence_ids 不再冒充 Thesis 引用 New Evidence
    （新证据通过 New Claim → New Thesis 真正进入 Research State）
tests:    全量 backend exit 0（test_r8 3/3 + test_r7 3/3）
next:     F4 Signal Production Integration
```
