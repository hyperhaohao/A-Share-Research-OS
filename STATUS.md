# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
PW0–PW3 DONE（E2E 7/7 绿）+ V2 Phase A 全部 DONE（§84 文档 + §85 代码 + 前端收尾）
当前执行线：Phase B（AI 研究中枢：三栏总控台 + ResearchPlan + ConversationSession）
（compose 栈重建因 Docker Desktop 引擎故障暂挂，见 Open Issues #7）
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态解析/Pipeline 中英阶段名，git 13f7346）
Phase A 收尾（本轮，DONE）：
  - 前端 shared/context.ts + handoff.ts + instrument.ts（URL 编解码/信封/身份 hook 唯一入口）
  - 报告→生成预测 CTA 走 Handoff 信封（创建→解析 report artifact→POST /handoffs→
    携 handoff/context 参数跳转；E2E-05 断言 URL 信封参数）
  - ReportCard 新增「研究脉络」lineage 显形（上游 研究运行/报告版本，下游 预测/验证）
  - Playwright E2E-07（报告 lineage 回溯 run）全绿；三页重复 useInstrumentName 收敛
  - 代码审查修复：from-report 不再覆盖 pipeline 注册的报告业务标题；
    run-now 失败路径先 rollback 再标记（防 session 中毒卡 running）；
    run_events 回放加 id tiebreaker；_payload 补 ValidationRecord 导入
五轮 PW0–PW2（DONE，本次）：
  - 持久化 Instrument Registry + 统一 InstrumentService（远程解析/离线降级/重启持久）
  - Presentation Layer（交易所/板块/能力/分析师/任务/门禁/预测 全量本地化）
  - 外观/语言单 Select；研究管线 SSE 真实时（采集 8 能力/分析 8 分析师逐项）
  - Watchlist/Task/Report/Prediction 业务卡片化 + 生成预测/删除任务/立即运行
  - 修复 14 个测试文件的 as_of 定时炸弹（动态 PIT 时间戳）
```

## In Progress

```text
None（Phase A 完成；下一单元 Phase B，唯一外部挂起项见 Open Issues #7）
```

## Next Action

```text
0. compose 栈重建（外部阻塞解除后）：修复 Docker Desktop（引擎 API 500/无法启动，
   需人工查看其 GUI 报错/更新）→ docker compose up -d --build → :8000 冒烟
   （by-domain 404/200、43 事件回放、lineage）→ :8080 产品冒烟；
1. 进入 Phase B：ResearchCommandCenter 计划/运行中/产物三栏（§38）+
   ResearchPlan + ConversationSession（先只控制 Search/Pipeline/Report/
   Continuous Research/Prediction，总纲 §87）；
2. Phase B 完成定义：000831 在三栏中完成 计划→运行→产物 全流程的产品 E2E。
```

## Tests

```text
backend: 306 passed（新增 by-domain 路由测试）
frontend: 7 passed + build PASS
e2e: Playwright 产品 E2E 7/7 passed（E2E-01…07，真实浏览器+真实源；
     本轮跑在新后端 :8001（本地 uvicorn+迁移）+ 新前端 vite，见 Open Issues #7）
```

## Live Verification（本轮实测）

```text
产品流（PW）：000831 搜索/名称解析/Watchlist 直加/重启持久/SSE 实时阶段/
报告卡片/生成预测/预测卡片/总控台 —— 全 PASS（另 Playwright 6/6 回归）
Phase A 收尾（本轮真机，000831）：
  E2E-05 生成预测落库 handoff 信封，URL 携 handoff=ho_*&context=ctx_* PASS
  E2E-07 报告「研究脉络」：上游 报告版本(派生自)←研究运行(产出)；
  下游 预测(生成自) PASS
  artifact by-domain 路由（Report rpt_* → artifact，缺失 404）PASS
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
7. Docker Desktop 引擎故障（本轮开始前 API 已 500，重启+WSL reset 后仍无法启动
   docker-desktop 发行版，需人工查看 GUI 报错/更新）。解除后执行 Next Action #0
   （compose 重建 + 冒烟）。挂起期间本地 uvicorn :8001 + vite :5173 可跑全产品
   （vite 代理支持 ASRO_API_PROXY 覆盖）
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
