# C2-MANIFEST — Thesis Revision / Version Model（整改 P0-02）

```text
problem:  Current Thesis 用 select().first()（无规则）；apply 只复制 claims
          不记录 parent/reason/new_evidence。
fix:
  - theses.meta_json 列（migration b8c9d0e1f2a4）
  - apply_thesis_diff 写入 meta：parent_thesis_id / is_current=true /
    revision_reason / revision_at / new_evidence_ids / affected_claim_count
  - 旧 Thesis meta.is_current 降为 false（Current Thesis 唯一性）
  - GET /research-inbox/thesis-history/{instrument_id}：版本链 +
    current_thesis_id + 每版 meta（parent/is_current/revision_reason）
  - Current Thesis 规则：meta.is_current=true 的最新行；无 meta 回退 created_at
live verify: 真实栈 thesis-history 30 版本（current=ths_71894754…）
tests:    tests/test_r8_inbox.py 3/3 PASS
next:     C3 Signal Ladder 重构
```
