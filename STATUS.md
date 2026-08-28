# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
PW0–PW3 DONE（E2E 6/6 绿）+ V2 Phase A 批次1 DONE（§85 第一批代码全落地）
当前执行线：V2 Phase A 收尾项 → Phase B（AI 研究中枢）
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态解析/Pipeline 中英阶段名，git 13f7346）
五轮 PW0–PW2（DONE，本次）：
  - 持久化 Instrument Registry + 统一 InstrumentService（远程解析/离线降级/重启持久）
  - Presentation Layer（交易所/板块/能力/分析师/任务/门禁/预测 全量本地化）
  - 外观/语言单 Select；研究管线 SSE 真实时（采集 8 能力/分析 8 分析师逐项）
  - Watchlist/Task/Report/Prediction 业务卡片化 + 生成预测/删除任务/立即运行
  - 修复 14 个测试文件的 as_of 定时炸弹（动态 PIT 时间戳）
```

## In Progress

```text
None（Phase A 批次1 完成并真机验证；下一单元为 Phase B）
```

## Next Action

```text
Phase A 收尾（小项）：
1. 前端 shared/handoff.ts + context.ts（URL 编解码统一，报告→预测 CTA 改走信封）；
2. Playwright 扩 E2E-07（lineage 回溯）；
然后进入 Phase B：ResearchCommandCenter 三栏 + ResearchPlan + ConversationSession
（只控制 Search/Pipeline/Report/Continuous Research/Prediction，总纲 §87）。
```

## Tests

```text
backend: 305 passed（+ Phase A artifacts/handoff/replay 4 测试）
frontend: 7 passed + build PASS
e2e: Playwright 产品 E2E 6/6 passed（E2E-01…06，vite+compose 真实栈）
```

## Live Verification（本轮实测）

```text
产品流（PW）：000831 搜索/名称解析/Watchlist 直加/重启持久/SSE 实时阶段/
报告卡片/生成预测/预测卡片/总控台 —— 全 PASS（另 Playwright 6/6 回归）
Phase A（真机 000831 全新 run，43 事件）：
  artifacts 注册 research_run/report/report_version（业务标题）PASS
  事件落库回放 43/43 PASS（GET /research-runs/{id}/events）
  lineage：version ← produced ← run；version --derived_from--> report PASS
  按 instrument 检索 artifacts（SZSE:000831）PASS
```

## Open Issues

```text
1. 资金流/历史行情对部分标的仍失败（源层真实失败，UI ⚠ 显形 —— 符合红线8）
2. 预测区间由估值隐含价导出，000831 当前呈深度负区间（诚实推导，方向与区间
   可能异号 —— 来自论点与估值口径差异，待 Phase C 经验卡/策略线处理）
3. 基准指数（IDX）行情未接入 → 超额收益显式 null
4. 法定节假日历未接入 → 预测到期日 ±1-3 天
5. 公网部署需认证/TLS；SQLite 单机规模；生产多用户需 PostgreSQL
6. Macro 官方原始源未接入；Cost Ledger 待真实化；scheduler claim 待原子化
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
