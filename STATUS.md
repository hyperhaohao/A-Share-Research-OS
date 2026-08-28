# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。
> 整改历史见 `REMEDIATION.md`。

---

## Current Phase

```text
Final Integrity Pass — COMPLETE
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 F0 Pipeline Integrity ✓
二轮 F1 Research Integration ✓
二轮 F2 Product Integrity ✓
二轮 F3 Final Verification ✓
```

## In Progress

```text
None（增强项按需排期，见 Open Issues）
```

## Next Action

```text
后续增强（不阻断交付，按需排期）：
- 基准指数（IDX）数据源 → 预测超额收益补全
- 法定节假日历 → 预测到期日精确化
- 公网部署认证/TLS
- PostgreSQL 生产库迁移
```

## Tests

```text
backend: 283 passed
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
```

## Branch / Commit

```text
Branch: main
Commit: 8aacbcf（Final Integrity Pass 完成后）
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
