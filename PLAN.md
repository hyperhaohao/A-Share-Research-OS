# PLAN.md

# A-Share Research OS — Execution Plan

> 当前执行线为产品闭环二次整改（PW0–PW3），依据
> `docs/A-Share-Research-OS-产品闭环二次审查与本地化整改方案.md`。
> 任务清单与状态见 `REMEDIATION.md` §产品闭环。历史线（M0–M29 / R0–R5 /
> Final Integrity）保留于文末历史节与 ROADMAP.md。

---

# Product Workflow Rebuild — 二次整改（当前执行）

> 核心原则：不增加后端对象规模、不推翻 Research Core；
> 集中完成「用户能真正用懂」的研究工作流。核心回归标的：000831 中国稀土
> （禁止为其写特殊业务逻辑）。

## PW0 — Instrument Identity & Localization（DOING）
- [ ] 持久化 Instrument Registry（DB 表 + migration）
- [ ] 统一 InstrumentService（Search/Watchlist/Task/Pipeline/Workspace/Report/Prediction 全部入口）
- [ ] 000831 直接 Watchlist 添加 → Workspace 打开；服务重启后仍正常
- [ ] 非种子标的中文名搜索可远程解析（如「中国稀土」）
- [ ] Exchange/Board/Capability/TaskType/TaskStatus/Gate/Materiality 本地化（Presentation Layer）
- [ ] 技术 ID（run_id/report_id/task_id…）主界面隐藏，归入「技术详情」
- [ ] 外观改为单 Select；界面语言改为单 Select

## PW1 — Research Live Experience（TODO）
- [ ] SSE 真正实时更新（逐事件 setEvents，POST 只负责触发）
- [ ] Source 逐项显示（按阶段分组，不去重）
- [ ] Analyst 逐项显示（不去重）
- [ ] Capability / Analyst 中文化
- [ ] 最终研究摘要 + Report CTA + Workspace CTA

## PW2 — Watchlist / Task / Report / Prediction Closure（TODO）
- [ ] Watchlist 研究卡片（名称/代码/交易所/板块/行情/最近研究/状态 + CTA）
- [ ] Task: schedule UI（每天/工作日/每周 + 时间）、任务卡片展示结果、
      run now、DELETE /tasks/{id}（running → 409 task.running）、报告 handoff、
      Scheduler Tick 移出普通界面
- [ ] Report: 业务卡片（标的/标题/时间/研究判断/版本/质量）、list-all API、
      Prediction CTA
- [ ] Prediction: 删除 SSE:600519 hardcode、from-report PredictionBuilder（5D/20D/60D）、
      lifecycle UI

## PW3 — Command Center & Product E2E（TODO）
- [ ] Research Command Center（关注变化/最近研究/运行中任务/待验证预测/最近报告）
- [ ] Playwright 引入 + 000831 产品 E2E（E2E-01…06）
- [ ] 语言/主题 E2E；Task Delete E2E

---

# 历史执行线（已完成）

首轮 M0–M29（ROADMAP.md）与整改 R0–R5（REMEDIATION.md）均已完成；
Final Integrity Pass F0–F3 与 Repository Integrity Closure P0–P3 已完成
（git 5a0cec7–HEAD）。

