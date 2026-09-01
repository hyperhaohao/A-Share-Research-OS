# F1-MANIFEST — Closure Truth Gate

> 阶段：F1（第三轮整改任务书 §11 F1 / §4 P0-A）
> 日期：2026-09-01 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

1. **R10-CLOSURE-V2.md 重写**（docs/research-deep-port/）：
   - 状态 REOPENED 保留；历史 VERIFIED 正文整体作废（git e9a57ac 留档）；
   - Capability Matrix 重写为事实矩阵（Implemented / Production Integration /
     UI / Real Verify / Golden / Final 六列，任务书 §4.2.3）：
     - Signal Production API：Final **FAIL**（500，F0 基线复现 + 根因定位）；
     - Confidence Migration：Final **FAIL**（生产路径固定 0.6）；
     - Source Independence / Subject Swap：**PARTIAL**；
     - Thesis Carry-forward / ClaimImpact / Thesis Revision：**PARTIAL**
       （七关系/事务/并发/幂等未验 + r8 基线失败）；
     - Thesis Center / Inbox / Memory：**PARTIAL**（§10 产品化目标未达）；
     - Mainline Radar / Overseas Mapping / Daily Brief：**PARTIAL**（UI PLANNED）；
     - 帷幄六项核心：**FAIL**（新增行，对齐任务书 §1）；
     - Transmission / LLM：BLOCKED_* 如实保留；
   - 「未决失败登记」表：Evidence FAIL ↔ Closure 一一对应；
   - §50 DoD 勾选校准：所有未验证项恢复为未勾选或 FAIL 标注，
     不再有「勾选 PASS、说明待实现」的条目。
2. **一致性校验脚本**：scripts/check_closure_consistency.py
   - 规则 R1 Evidence 算术 / R2 Closure Golden 数字 == Evidence 汇总 /
     R3 Evidence FAIL 必须在 Closure 登记 / R4 非 PASS 证据列不得 Final PASS /
     R5 Golden 行残留冲突通过数；
   - 对作废版 Closure 实测命中 8 处冲突；对校准后 Closure exit 0。

## 验证

```text
python scripts/check_closure_consistency.py
→ [R1] OK — Evidence 汇总 24/25 与明细一致
→ [R2] OK — Closure Golden 24/25 == Evidence 汇总
→ [F1-GATE] PASS（exit 0）
```

## 状态

- IMPLEMENTED / TESTED（脚本实测）
- 真实运行验证：脚本为本地静态校验；生产链修复在 F2/F3 继续。
