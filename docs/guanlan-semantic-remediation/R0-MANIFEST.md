# R0-MANIFEST — 可复现基线与 Closure Gate

> 观澜研究能力语义迁移第二轮整改任务书 §R0（P0）| 日期：2026-09-02
> 复审基线 main@b25eede；复审结论 REJECT — G14 CLOSURE INVALID

## 复现与修复

| 复审声称 | 复现结果 | 处置 |
|---|---|---|
| uv lock --check FAIL | ✅ 复现（pyproject 与 uv.lock 漂移） | `uv lock` 修复；`--check` exit 0 |
| 全新 frozen 环境回归失败 | ✅ 复现 1 例（test_pw0_reports newest-first 顺序不确定） | **系统性修复**：11 个列表端点 created_at 排序补 id-desc tiebreaker（created_at 同值时排序确定） |
| 18 failed / 7 skipped | 部分复现（frozen 环境 1-3 个顺序敏感失败，随机器负载浮动） | 属 created_at 排序 + 后台线程 deadline 两类；tiebreaker + await deadline 120s 修复；live 测试默认排除 |
| live 测试隐式访问外网 | ✅ | pyproject addopts `-m 'not live'` 默认排除；独立运行 `-m live` |

## 新增

1. **Closure Gate**：`scripts/verify_remediation.py`（§17.5 十四项机器核验：
   worktree/锁文件/回归/前端/daemon 扫描/固定 confidence 扫描/{confirm:true}
   绕过扫描/PLAN P0/STATUS 状态）；任一失败输出 FINAL CLOSURE — REJECTED。
2. tiebreaker：predictions/regression/research-inbox/artifacts/conversation/
   handoff/scheduler/background_runway/confirmation_gate/experience_screening/
   session_memory/workbench 共 11 文件。
3. test_phase_f await deadline 60→120s（后台线程 deadline 机器负载容差）。

## 验证

- backend：528→519 collected（live 默认排除）/ 0 FAILED / exit 0；
- `uv lock --check` exit 0；
- frontend：tsc/vitest/build PASS（G9 基线维持）；
- gate --quick 实测：剩余 FAIL 项均为 R1–R12 待办
  （daemon thread 登记为 WARN、STATUS REOPEN 等），符合当前整改中状态。

## 状态

R0 IMPLEMENTED / TESTED。
