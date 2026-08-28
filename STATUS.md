# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
Product Workflow Rebuild — 二次整改 PW0（Instrument Identity & Localization）
依据: docs/A-Share-Research-OS-产品闭环二次审查与本地化整改方案.md
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态标的解析/Pipeline 中英阶段名/CTA，git 13f7346）
```

## In Progress

```text
PW0 — Instrument Identity & Localization
```

## Next Action

```text
PW0: 持久化 Instrument Registry（DB 表 + migration）+ 统一 InstrumentService，
     所有入口（Search/Watchlist/Task/Pipeline/Workspace/Report/Prediction）走同一服务；
     之后依次：本地化 Presentation Layer、外观/语言单 Select、
     PW1 SSE 实时、PW2 四页闭环、PW3 Command Center + Playwright。
```

## Tests

```text
backend: 285 passed（PW0 前基线）
frontend: 8 passed + build PASS
```

## Live Verification

```text
R1: 4 只真实 A 股 × 4 能力 → Evidence + Manifest
R2: 真实贵州茅台全链（无手工补链）
R5: 4 标的 live E2E + 3 分支 continuous + scheduler
13f7346: 搜索 000831 → 动态解析 中国稀土 → Workspace 打开
```

## Open Issues

```text
（产品闭环二審确认）
1. Instrument Registry 仅进程内存 → 重启丢失动态标的（PW0 修）
2. Pipeline SSE 未逐事件实时渲染 + 按事件名去重丢信息（PW1 修）
3. Watchlist/Tasks/Reports/Predictions 仍为技术列表（PW2 修）
4. Prediction 无生产入口 + SSE:600519 hardcode（PW2 修）
5. 首页非研究总控台（PW3 修）
6. 无浏览器级 E2E（PW3 修）
（遗留）
7. 基准指数（IDX）行情数据未接入 → 预测超额收益显式 null
8. 法定节假日历未接入 → 预测到期日 ±1-3 天
9. 公网部署需认证/TLS（当前单用户/内网定位）
10. SQLite 仅适合当前单机规模；生产多用户需 PostgreSQL
11. Macro 官方原始源（gov.cn 等）未接入；当前为媒体转载 + 机构标注
12. Quant docs 描述为 upstream 审计能力，正式 runtime 为 baseline 引擎
13. Cost accounting 当前为 hardcoded 统计，待 RunCostLedger 真实化
14. Scheduler claim 为 check-then-update，PostgreSQL 前需原子化
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
