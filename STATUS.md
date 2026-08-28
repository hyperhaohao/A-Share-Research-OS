# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
Repository Integrity Closure — COMPLETE
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（当前，git b96d3ab–HEAD）
```

## In Progress

```text
None（P1/P2 增强项按需排期，见 Open Issues）
```

## Next Action

```text
P1/P2 增强项（不阻断交付，按需排期）：
- Quant docs == runtime 对齐
- Cost Ledger 真实化
- Overview Research Summary
- Readiness endpoint
- Backend 端口暴露策略
- Frontend integration tests
- GitHub CI
- Macro 官方原始源
```

## Tests

```text
backend: 285 passed
frontend: 8 passed + build PASS
docker compose: 3 services all running
backup/restore: 演练 PASS（WAL 修复后）
```

## Live Verification

```text
R1: 4 只真实 A 股 × 4 能力 → Evidence + Manifest
R2: 真实贵州茅台全链（无手工补链）
R5: 4 标的 live E2E + 3 分支 continuous + scheduler
```

## Open Issues

```text
1. 基准指数（IDX）行情数据未接入 → 预测超额收益显式 null
2. 法定节假日历未接入 → 预测到期日 ±1-3 天
3. 公网部署需认证/TLS（当前单用户/内网定位）
4. SQLite 仅适合当前单机规模；生产多用户需 PostgreSQL
5. Macro 官方原始源（gov.cn 等）未接入；当前为媒体转载 + 机构标注
6. Quant docs 描述为 upstream 审计能力，正式 runtime 为 baseline 引擎
7. Cost accounting 当前为 hardcoded 统计，待 RunCostLedger 真实化
8. Scheduler claim 为 check-then-update，PostgreSQL 前需原子化
```

## Branch / Commit

```text
Branch: main
Commit: 26ddddb（Repository Integrity Closure 完成后）
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
