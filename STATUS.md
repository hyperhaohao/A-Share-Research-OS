# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
V2 Phase A DONE + Phase B DONE（AI 研究中枢三栏 + ResearchPlan + ConversationSession）。
compose 栈已重建并在生产路径完成全链真机验证（E2E 8/8 于 compose 栈）。
当前执行线：Phase C（研究经验卡，总纲 §72）
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态解析/Pipeline 中英阶段名，git 13f7346）
Phase B（本轮，DONE）：
  - 后端：command_sessions/command_turns/research_plans 表 + ConversationRepository
    （迁移 c9d0e1f2a3b4）；ResearchCommander 确定性意图解析（代码正则+注册表名
    匹配，识别不了显式拒绝）；按意图生成结构化 ResearchPlan（完整研究/持续研究/
    预测三意图）；逐步执行器（步骤状态/产物引用/失败落计划）；§42 闭环：
    对话→ResearchRun→ReportVersion→Artifact→报告链接
  - 前端：HomePage 重构为三栏中枢（左 当前计划/正在运行/最近研究；中 直接驱动
    +对话面板；右 当前研究产物+待验证预测）；commander.* 全量本地化
  - E2E-08：对话「研究中国稀土…」→ 计划步骤实时可见 → 管线真实运行 →
    右栏产物「打开报告」→ 报告页（§42 全闭环）
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
1. Phase C 研究经验卡（总纲 §72/§43）：ReportVersion → ExperienceCard Draft →
   Refine → Validate → Approve；handoff 注册 report→experience:
   create_experience_draft（复用 Phase A 信封与 shared/handoff.ts）；
   Phase C 完成定义：报告页 → 炼成经验卡 → 卡片可版本化并保留
   report_version_id/claim_ids/evidence_ids 的产品 E2E（E2E-09）。
```

## Tests

```text
backend: 312 passed（+ Phase B command 6 测试：解析/拒绝/闭环/预测/无报告失败）
frontend: 7 passed + build PASS
e2e: Playwright 产品 E2E 8/8 passed（E2E-01…08，真实浏览器+真实源，
     全量打在 compose 栈：vite :5173 → compose backend :8000）
```

## Live Verification（本轮实测）

```text
产品流（PW）：000831 搜索/名称解析/Watchlist 直加/重启持久/SSE 实时阶段/
报告卡片/生成预测/预测卡片/总控台 —— 全 PASS（另 Playwright 6/6 回归）
compose 栈重建后真机验证（Docker 修复后，000831）：
  迁移 c9d0e1f2a3b4 应用（alembic current = head）PASS
  真实 000831 run（run_90458a76aee4）43/43 事件回放 PASS
  by-domain 解析报告（业务标题字节级断言）PASS
  lineage：version ← produced ← run；version --derived_from--> report PASS
  §42 指挥官闭环（POST /command）3 个计划全部 completed，
  各带自身 run_id + 报告 artifact PASS
  :8080 生产 bundle 含 Phase B 中枢代码 PASS
  E2E 8/8 于 compose 栈（E2E-08 锁定自身计划完成 + 回放 + 产物）PASS
Phase B（本轮真机，000831，E2E-08 实测）：
  对话一句话 → 结构化计划三步可见 → 管线真实完成 → 右栏产物出现报告
  （业务标题，无 rpt_ 裸 id）→ 点击「打开报告」进入报告页 PASS
  无法识别标的 → 显式拒绝回复（不留死计划）PASS（单测覆盖）
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
7. [已解决 2026-08-29] Docker Desktop 引擎故障 —— 用户修复后 compose 重建完成，
   全链真机验证通过（见 Live Verification）。经验：多后端并存时先确认
   :5173 代理目标（vite ASRO_API_PROXY），E2E 断言须锁定自身创建的对象
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
