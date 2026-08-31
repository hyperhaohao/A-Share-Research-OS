# C5-MANIFEST — 000831 Semantic Golden Test（整改 P0-06）

```text
golden test 扩展：26/26 PASS（原 24 + SEM-01 减持≠整合 + SEM-02 否定重组 A=false）
SEM-01: 减持证据经 signal-ladder → integration_signals=0 ✓
SEM-02: 「不存在重大资产重组计划」→ results=0（A=false）✓
Thesis Diff affected_claims 2289→61（C1 修复后真机确认）
Evidence 744→745（真实采集）；Claims 2396；报告 27266 chars
tests: backend 全量 exit 0；vitest 30/30；build PASS；E2E 30/30
next: C6-C11
```
