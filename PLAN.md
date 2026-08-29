# PLAN.md

# A-Share Research OS — Execution Plan

> 现行两层执行线：
> 1. **产品闭环二次整改（PW0–PW3）**——依据
>    `docs/A-Share-Research-OS-产品闭环二次审查与本地化整改方案.md`；
> 2. **V2 产品与架构总纲（Phase A–J）**——依据
>    `docs/A-Share-Research-OS-最终产品与架构修改方案.md`（观澜吸收 / Artifact 总线 /
>    AI 研究中枢）。PW 线与总纲 Phase A 重叠项已完成的部分直接计入。

---

# PW 线（产品闭环二次整改）

> 核心原则：不增加后端对象规模、不推翻 Research Core；
> 集中完成「用户能真正用懂」的研究工作流。核心回归标的：000831 中国稀土
> （禁止为其写特殊业务逻辑）。

## PW0 — Instrument Identity & Localization（DONE）
- [x] 持久化 Instrument Registry（instrument_registry 表 + migration a1f2c3d4e5b6）
- [x] 统一 InstrumentService（Search/Watchlist/Task/Pipeline/Workspace/Report/Prediction
      全部经 resolve_instrument_id / InstrumentService）
- [x] 000831 直接 Watchlist 添加 → Workspace 打开；容器重启后仍正常（实测 PASS）
- [x] 非种子标的中文名搜索远程解析（smartbox + 行情校验，「中国稀土」实测 PASS）
- [x] Exchange/Board/Capability/Analyst/TaskType/TaskStatus/Gate/Materiality/
      Direction/Horizon 本地化（frontend/src/presentation/）
- [x] 外观单 Select；界面语言单 Select
- [x] 离线降级 code_only profile（显形，不造假名）；上线后搜索自愈

## PW1 — Research Live Experience（DONE）
- [x] SSE 真正实时（逐事件 setEvents；事件名自 SSE event 字段合并）
- [x] Source 逐项显示（数据采集 8 能力分组 + n/8 进度，不去重）
- [x] Analyst 逐项显示（分析 8 分析师业务名 + running/ok/failed 三态）
- [x] Capability / Analyst 中文化
- [x] 最终研究摘要 + Report CTA + Workspace CTA

## PW2 — Watchlist / Task / Report / Prediction Closure（DONE）
- [x] Watchlist 研究卡片（名称/代码/交易所/板块/实时行情/最近研究/报告状态 + 4 CTA）
- [x] Task: 频率/时间 schedule UI（每天/工作日/每周 + 时间）、任务卡片、
      run now（POST /tasks/{id}/run 后台 worker）、DELETE /tasks/{id}
      （running → 409 task.running）、报告 handoff、Scheduler Tick 移入技术详情
- [x] Report: 业务卡片（判断/版本/质量）、GET /reports list-all + latest_version_no、
      生成预测 CTA（报告页 + 列表页）
- [x] Prediction: SSE:600519 hardcode 已删、GET /predictions list-all、
      POST /predictions/from-report（诚实推导：论点方向 + 估值域 + 快照价；
      缺输入 → 422 prediction.underivable）、lifecycle 卡片

## PW3 — Command Center & Product E2E（DONE）
- [x] Research Command Center（最近研究/运行中任务/待验证预测/最近报告；
      GET /research-runs 新端点 + UTC 时区标注）
- [x] Playwright 产品 E2E（E2E-01…06 全绿，6/6 passed）
- [x] E2E 纳入常用验证循环（npx playwright test，vite 复用 + compose 后端）

---

# V2 总纲执行线（docs/A-Share-Research-OS-最终产品与架构修改方案.md）

> 红线：不建第二套 Research Core；Artifact 不取代强类型 Domain；PIT 全覆盖；
> 业务物料不进 localStorage；跨模块走 Artifact+Context+Handoff；LLM 不创造事实；
> 失败/降级显形；每个"完成"必须有产品级 E2E。

## Phase A — 统一研究基础协议（DOING，PW 完成后立即开始）
- [x] ARCHITECTURE-V2.md / DOMAIN-MAP.md / ARTIFACT-PROTOCOL.md / HANDOFF-PROTOCOL.md
      （§84：基于当前代码做映射与接口细化，不改顶层方向）→ docs/v2/
- [x] ArtifactRecord + ArtifactRegistry（跨领域索引/导航/溯源/搜索/Handoff）
- [x] ProvenanceEdge（8 关系 + 每关系上游方向表 + BFS lineage）
- [x] ResearchContext（模型 + Handoff 信封内嵌；独立持久化按需 Phase B）
- [x] HandoffEnvelope（注册动作表 + 422 显式拒绝 + POST/GET /handoffs）
- [x] RunEvent 持久化（SSE 事件同时落库，回放/任务历史/失败分析，§37）
- [x] Instrument Registry 持久化（PW0 已完成，计入 Phase A）
- [x] Presentation Localization（PW0 已完成，计入 Phase A）
- [x] ReportVersion / Prediction / ResearchRun(+Validation) 注册为 Artifact，
      lineage/replay 真机验证（000831 全新 run 43 事件 43/43 回放）
- [x] 前端 shared/context.ts + handoff.ts + instrument.ts；报告→预测 CTA 走信封；
      ReportCard 研究脉络 lineage；Playwright E2E-07（7/7 绿）
- [x] 代码审查修复（from-report 标题覆盖 / run-now 失败标记 / 回放排序 / 导入）

## Phase B — AI 研究中枢 + 报告 Handoff（DONE）
- [x] ResearchCommandCenter（计划/运行中/产物三栏，§38）
- [x] ResearchPlan + ConversationSession（先只控制 Search/Pipeline/Report/
      Continuous Research/Prediction，§87）
- [x] §42 闭环产品 E2E（E2E-08）：对话→计划→管线→产物→打开报告

## Phase C — 研究经验卡（DONE）
- [x] ExperienceCard 模型 + Draft/Refine/Validate/Approve（§72）
- [x] 报告页「炼成经验卡」CTA（走 handoff 信封 report→experience，§43）
- [x] 卡片保留 report_version_id/claim_ids/evidence_ids；E2E-09
- [x] 注：简单 Quant validation 由 Phase D 工作流节点承接（quant_expression 已保留）

## Phase D — 研究验证工作流（DONE v1）
- [x] 最小强类型 DAG：Data(真实日线)→Rule(前向收益)→Validation(指标)→Output（§73）
- [x] 经验卡发起验证工作流（handoff experience→workflow:run_validation，§44）
- [x] 工作流运行落 Artifact + RunEvent；E2E-10（诚实终态契约）
- [x] 注：自定义 quant_expression 表达式节点留待后续扩展

## Phase E — 智能选股（DONE v1）
- [x] ScreeningRun + Candidate Artifact（Why Selected 解释，§74）
- [x] Universe 数据面 + 筛选规则（复用经验卡/工作流产物）
- [x] E2E-11（候选解释 + 排除聚合披露）
- [x] 注：因子/模型打分规则留待 Phase F 策略线扩展（v1 规则集为研究状态规则）

## Phase F — 策略实验室（DONE v1）
- [x] StrategyDefinition/StrategyVersion（Screening+Cards+Workflow 组装，§21/§75）
- [x] Cross-Instrument Backtest + 失败案例显形（§47）
- [x] handoff screening→strategy:create_strategy；E2E-12
- [x] 注：Regime Split/Sensitivity 等全套 §47 验证留待后续版本（v1 一律 EXPERIMENTAL）

## Phase G — 策略盯盘（DONE v1）
- [x] MonitorDefinition + Scheduler Worker 后台运行（§48）
- [x] Observation/Signal/DecisionRecord 三分离（§24，仅 Paper/Research Decision §25）
- [x] E2E-13
- [x] 注：新公告/新闻/资金/宏观观察源按数据可用性逐项接入（v1 行情变化+公司事件）

## Phase H — 产业研究地图 + 全球宏观（DONE v1）
- [x] 产业链示图 + 宏观资讯主题视图（Research Inputs，§76）
- [x] open_with_context 衔接（视图 → 标的研究上下文不丢失）
- [x] E2E-14
- [x] 注：上下游/同业关系源与官方宏观数值源未接入（视图内显式披露），
      接入后视图自动补全

## Phase I — 全库研究图谱（DONE v1）
- [x] Global Graph UI + Lineage Explorer（§78，Artifact/Edge 已持续积累）
- [x] 跨模块 Handoff 可视化（节点 route 跳转）
- [x] E2E-15

## Phase J — 完整复盘回灌（DONE v1，总纲最后阶段）
- [x] Decision → Prediction → Validation → RegressionReview →
      ExperienceCard v2 → StrategyVersion v2 闭环（§79）
- [x] E2E-16

## 总纲验收全链复查（DONE）
- [x] 红线 1-10 逐项复核（§83）+ §80-§82 验收清单对照
- [x] 架构缺陷修复：写后读竞态（commit 中间件，响应前提交）
- [x] 红线缺口修复：盯盘信封（红线5）+ 回测/盯盘事件化（红线6）
- [x] 复查测试 +6；全量 344/7/16 三线全绿

## 深度扩展（DONE a–e）
- [x] a. 产业链关系源接入（东财板块成员 → 产业地图）
- [x] b. 官方宏观数值源接入（腾讯行情数值层，6 指标真机全通）
- [x] c. quant_expression 自定义工作流节点（类型化 DSL，无 eval）
- [x] d. §47 全套策略验证（regime split + sensitivity → VALIDATED 通道）
- [x] e. 盯盘观察源扩展（公告/新闻/资金/宏观）

## 部署准备 + 持续打磨（DOING）
- [x] 预测一致性披露（方向/区间异号显形）+ 中报口径年化修复（000831 问题）
- [ ] 认证（登录/会话）+ TLS 终止 + PostgreSQL 迁移验证
- [ ] 宏观数值层扩指标；关系源扩展；LLM 润色开启

## Phase C–J（按 §72–§79 纵向闭环，依次）
- [ ] C 研究经验卡（原炼验用 + 版本 + Evidence）
- [ ] D 研究验证工作流（最小强类型 DAG）
- [ ] E 智能选股（Why Selected 解释）
- [ ] F 策略实验室（真实失败不隐藏）
- [ ] G 策略盯盘（Observation/Signal/Decision 分离，后台运行）
- [ ] H 产业研究地图 + 全球宏观（Research Inputs，非孤立 Dashboard）
- [ ] I 全库研究图谱（Artifact/Edge lineage）
- [ ] J 完整复盘回灌（Decision→Prediction→Validation→Review→经验卡 v2）

---

# 历史执行线（已完成）

首轮 M0–M29（ROADMAP.md）与整改 R0–R5（REMEDIATION.md）均已完成；
Final Integrity Pass F0–F3 与 Repository Integrity Closure P0–P3 已完成
（git 5a0cec7 起）。四轮产品整改（git 13f7346）与五轮 PW0–PW2 见 git 历史。

