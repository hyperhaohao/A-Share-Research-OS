# F15-EVIDENCE — 第三轮整改最终证据汇总

> 阶段：F15（任务书 §11 F15）| 日期：2026-09-02
> 全部证据为真实运行结果（优先级：真实运行 > 自动化测试 > 生产 API >
> 代码 > Manifest，任务书 §2.2）。

## 1. 原始运行结果

| 项 | 结果 | 原始记录 |
|---|---|---|
| backend pytest（F14 后全量） | 459 collected / 0 FAILED / exit 0 | 本轮 CI 记录 + 各 Fxx-MANIFEST |
| frontend vitest | 35/35 PASS（8 files） | F8/F10 运行记录 |
| TypeScript + vite build | PASS | F8/F10 运行记录 |
| Playwright 全量 | 30/30 PASS（产品 17 + 视觉 12） | F13-MANIFEST（含校准记录） |
| **Golden A**（R10 live 25 步） | **25/25 PASS ×2** | [F14-R10-GOLDEN-RUN.txt](F14-R10-GOLDEN-RUN.txt) |
| **Golden C**（帷幄闭环 live 13 步） | **13/13 PASS ×2** | [F14-WEIWO-GOLDEN-EVIDENCE.md](F14-WEIWO-GOLDEN-EVIDENCE.md) |
| Golden B（Signal 七语义） | 8/8 API 测试 + live 6a/6b | test_f3_signal_production.py |
| Golden D（观澜产品链） | E2E-09…16 覆盖 | Playwright 30/30 |
| Closure 一致性门 | exit 0（R1-R5 全过） | scripts/check_closure_consistency.py |
| 生产固定 confidence=0.6 扫描 | **0 命中** | grep 复核（F15 记录） |
| 迁移：空库 upgrade head | PASS（16+ 迁移全链） | F13-MANIFEST |
| 迁移：现有库（compose 数据卷） | PASS（6 个新迁移自动应用） | docker logs 记录（F10 live verify） |

## 2. Live 栈核验（compose，2026-09-02）

- backend/frontend 镜像重建至整改代码；六迁移自动应用；
- 13 个注册工具可查；events/workbench/confirmations/tasks/memory/snapshot
  端点全部 live 返回真实数据；
- 前端 bundle 含事件线程与动态 Workbench（`cc-event-thread`/workbench 代码验证）；
- Signal API 500 → 200（修复前后对照：F0 基线 500 复现 → F14 Golden 200）。

## 3. 阶段证据索引

F0 [F0-BASELINE.md](F0-BASELINE.md)（基线+原始 pytest 输出）·
F1 [F1-MANIFEST.md](F1-MANIFEST.md) ·
F2 [F2-MANIFEST.md](F2-MANIFEST.md) ·
F3 [F3-MANIFEST.md](F3-MANIFEST.md) ·
F4 [F4-MANIFEST.md](F4-MANIFEST.md) ·
F5 [F5-MANIFEST.md](F5-MANIFEST.md) ·
F6 [F6-MANIFEST.md](F6-MANIFEST.md) ·
F7 [F7-MANIFEST.md](F7-MANIFEST.md) ·
F8 [F8-MANIFEST.md](F8-MANIFEST.md) ·
F9 [F9-MANIFEST.md](F9-MANIFEST.md) ·
F10 [F10-MANIFEST.md](F10-MANIFEST.md) ·
F11 [F11-GUANLAN-PARITY.md](F11-GUANLAN-PARITY.md) ·
F12 [F12-MANIFEST.md](F12-MANIFEST.md) ·
F13 [F13-MANIFEST.md](F13-MANIFEST.md) ·
F14 [F14-MANIFEST.md](F14-MANIFEST.md)（[golden 证据](F14-WEIWO-GOLDEN-EVIDENCE.md)）

## 4. 修复的真实缺陷清单（本轮发现并修复）

1. Signal Production API 500（InstrumentProfile.get 误用）— F3；
2. a3c6be4 引入的 apply 中途回滚丢弃快照 → CrossSnapshotError — F2；
3. 静默丢 Claim（裸 except continue）— F2；
4. supersedes/updates 不创建版本 Claim、irrelevant 证据兜底造 Claim — F2；
5. **demote_other_currents JSON 原地变更 → Current 切换从不落库**（隐性腐化）— F2；
6. 版本语句唯一约束冲突（多轮修订同证据更新）— F14；
7. creates_experience_card 结构化结果缺真实 id — F14；
8. E2E-12 断言写死数据匮乏期终态（kline 恢复后 VALIDATED 才是正确路径）— F13 校准。
