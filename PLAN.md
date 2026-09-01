# PLAN.md

# A-Share Research OS — Execution Plan

> 现行执行线：
> 1. **Research Capability Deep Port（R0–R9，当前 DOING）**——依据
>    `docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md`：
>    观澜非量化 Research Capability（Source Trust / Extraction / Industry
>    Driver-Transmission-Narrative / Commander 自主循环 / Research Products /
>    非量化 Experience / Memory / Inbox / Thesis Diff / Graph）深度融合
>    ASRO Evidence/PIT/Claim/Thesis/Version/Monitor/Validation 内核。
>    Quant 本轮冻结（NO NEW DEVELOPMENT，保留不删）。
> 2. Guanlan Direct Port（G0–G10）——DONE（PORT COMPLETE，历史事实）；
> 3. PW0–PW3 / V2 Phase A–J / M0–M29——DONE（历史）。
>
> License Gate：donor 无 LICENSE → 全程 REFERENCE_ONLY / BEHAVIORAL ADAPTATION。
> 黄金场景：000831 中国稀土资产整合研究 → docs/research-deep-port/R10-CLOSURE.md。

---

# Research Capability Deep Port（R 线，当前执行线）

## 第三轮整改 — Correctness & Product Closure Remediation（F0–F15，当前 DOING）

> 依据 docs/A-Share-Research-OS-第三轮验收整改任务书-Research-State与观澜核心功能完整迁移.md（R10 REOPEN）
> 两条主线：Research OS 正确性闭环 + 观澜核心功能完整迁移（帷幄统帅层）
> 基线冻结：docs/final-remediation/F0-BASELINE.md（ASRO 4c2e506 / donor 98f1398）

- [x] F0 Reopen 与基线冻结
- [x] F1 Closure Truth Gate
- [x] F2 Research State Review Fix
- [x] F3 Signal Production Fix
- [x] F4 Integrity Migration（confidence/source independence/subject swap）
- [x] F5 Weiwo Event Foundation
- [x] F6 Weiwo Tool Orchestration
- [ ] F7 Weiwo Approval Governance
- [ ] F8 Weiwo Dynamic Workbench
- [ ] F9 Weiwo Background / Session / Memory
- [ ] F10 Weiwo Product Cards & UI
- [ ] F11 Guanlan Core Parity Audit
- [ ] F12 Research Product Productization
- [ ] F13 Full Regression
- [ ] F14 Golden E2E
- [ ] F15 Final Evidence & Closure

---

## 整改线 — Correctness & Product Closure Remediation（F0–F12，当前 DOING）

> 依据第二轮验收整改任务书（R10 REOPEN 第二次）。
> P0：Thesis Revision Research State / Current Thesis / Signal Production / Golden 语义。

- [x] F0 Reopen Closure
- [ ] F1 Current Thesis Correctness（get_current_thesis 唯一选择器）
- [ ] F2 New Snapshot Revision（apply 建新快照，禁旧快照）
- [ ] F3 Claim Revision Apply（新证据 → 新/修订 Claim → 新 Thesis）
- [ ] F4 Signal Production Integration（BUILTIN_RULES 正式 API）
- [ ] F5 Golden Semantic Rewrite（减持≠整合；builtin rules）
- [x] F6 Semantic Entailment（方向/计划/范围冲突）+ confidence_level 函数 + Source Independence PARTIAL（需 entity dict）
- [x] F7 Thesis Center（current + version history + diff detail）
- [x] F8 Inbox（聚合面板）+ Memory（candidate/promote/active + type filter）
- [x] F9 三编译器（mainline/overseas/brief）+ API 就绪
- [x] F10 Full Regression（backend exit 0 / vitest 30 / build PASS / visual 12/12 / product 11/12）
- [x] F11 Golden Real Verify（26/26 PASS）
- [x] F12 Final Closure（R10-CLOSURE-V2.md 生成，Capability Matrix 19 项）

## 前整改线 — Correctness & Closure Remediation（C0–C11，部分 DONE）

> 依据验收整改任务书 docs/A-Share-Research-OS（ASRO）.md（R10 REOPENED）。
> Correctness > Research Integrity > Traceability > Product Completeness >
> Test Pass > Documentation。

- [x] C0 验收状态回退（R10 REOPENED）
- [ ] C1 Thesis Diff Correctness（ClaimImpact relation 模型，禁 stale 误标）
- [ ] C2 Thesis Revision / Version Model（Current Thesis 规则 + parent 链）
- [ ] C3 Signal Ladder 重构（正/负 patterns + entities + source trust + 完整输出）
- [ ] C4 Citation Semantic Entailment（主体/方向/时间/计划一致性 → uncertain）
- [ ] C5 000831 Semantic Golden Test（SEM-01…04 + DIFF-01…05）
- [x] (C6 ↑已被 F 线覆盖) Transmission Real Verification — **BLOCKED_REAL_EVIDENCE**（语料无稀土链级传导证据句）
- [x] (C7 ↑已被 F 线覆盖) 三市场级产品编译器（Mainline 2/Overseas 6/Daily Brief 3 sections，真实栈验证）
- [x] (C8 ↑已被 F 线覆盖) Research Inbox UI + Research Memory UI + Thesis Center（三页 + nav + i18n + 视觉基线重生成）
- [x] (C9 ↑已被 F 线覆盖) LLM Real Verification — **BLOCKED_EXTERNAL** + confidence_level 四级定性函数
- [ ] C10 Full Regression（backend/frontend/E2E 全量）
- [ ] C11 Final R10 Closure（R10-EVIDENCE/CLOSURE 重生成）

---

## R0 — Donor Delta Audit + Bootstrap（DONE）
- [x] 三方 commit 固定（ASRO 89b4f6c / donor 98f1398 / 无 drift）
- [x] License Gate：无 LICENSE → REFERENCE_ONLY / BEHAVIORAL ADAPTATION
- [x] 源码级差距矩阵 27 项（docs/research-deep-port/00-观澜研究能力差距矩阵.md）
- [x] TASK/PLAN/STATUS/ROADMAP/CLAUDE 执行线注册
- [x] 基线测试全绿（backend 368 exit 0 / vitest 30 + build PASS / Playwright 30）
- [x] Git checkpoint

## R1 — Research Domain Boundary & Product Repositioning（DONE）
- [x] ADR-Research-First-Product-Boundary（docs/adr/）
- [x] 一级导航研究优先（研究 9 / 实验·冻结 6；修复工作流双入口同 label）
- [x] README 定位更新 + i18n 回归（vitest 30/30）+ 视觉基线容差内（E2E 30/30）
- [x] manifests/R1-MANIFEST.md

## R2 — Source Trust + Evidence-backed Extraction（DONE，P0）
- [x] Source Trust T0-T4 业务层（读时派生映射 authority；market_quote 持牌
      转载=T0；未知保守 T4）
- [x] Claim 升级规则：extraction verifier + AnalysisQualityGate
      analysis.source_trust_escalation（FAIL）双防线
- [x] Extraction 契约 + CitationVerifier + extraction_records 表 +
      POST/GET /extractions + promote-to-claim（rejected 留档审计）
- [x] Prompt Injection 防线（指令样文本=纯数据；T4 只能是 lead）+ 真实公告
      live verify（4 场景全符合预期，manifests/R2-LIVE-VERIFY.md）
- [x] THIRD_PARTY_NOTICES 增补 R 线 License Gate 结论

## R3 — Industry Semantic Research Engine（DONE，P0）
- [x] IndustrySemantic 单表四类对象（driver/transmission/narrative/position，
      migration c3d4e5f6a7b8，append-only 版本化）+ 引用反查强制（422 显形）
- [x] /industry-semantics API + /views/industry semantics 并入（链级聚合）
- [x] Narrative 可复算温度（不足 → insufficient，不造数字）
- [x] UI：产业链面板消费真实语义（方向/状态徽章），空时诚实置空
- [x] 稀土试点：广晟减持 Driver(negative)+Narrative(active)，2+2 条真实证据
      引用反查通过；伪造 span 422；Transmission/五轴无真实证据 → 诚实置空
      （§23 禁造假，manifest 如实记录偏离）
- [x] 验证：backend exit 0（+4）+ vitest 30/30 + build + E2E 30/30 + 真机核验

## R4 — Research Commander Autonomous Loop（DONE，P0）
- [x] Intent Router 九类焦点（确定性关键词；识别不了 → general 不猜）
- [x] Agent Profiles 白名单（7 profiles；pipeline 采集面/分析师面过滤，
      profile_applied 事件显形裁剪）
- [x] 结构化 Plan（meta_json migration d4e5f6a7b8c9：objective/questions/
      required_sources/completion_criteria/max_collection_passes）
- [x] Missing Data Loop（有界第二遍：ResearchRequest 点名 capability 补采，
      waiting_data/missing_data_summary 显形；禁同 run 重复建 Claim）
- [x] run 状态语义扩展（waiting_data/reviewing 事件 + 前端卡片渲染）
- [x] Live Verify（黄金问题：focus=event 路由正确 + 事件链全 PRESENT +
      run_completed；manifests/R4-LIVE-VERIFY.md）

## R5 — Research Product System（DONE，P0/P1）
- [x] 7 类产品契约（app/domain/research_products.py：required_sections/
      intent/missing_data_behavior=disclose/market_wide/notes 显式）
- [x] reports.product_type 列（migration e5f6a7b8c9d1）+ pipeline 契约校验
      （缺失 Section 显形不编造）+ Artifact 标题类型化
- [x] commander 焦点→产品类型映射（黄金问题落 EVENT_INVESTIGATION）
- [x] 市场级三类（雷达/映射/简报）编译器在 R8 Inbox 数据就绪后落地
      （契约已定义，顺序依赖在 manifest 如实登记）
- [x] 验证：tests/test_r5 4/4 + 全量 backend exit 0 + 真机核验

## R6 — Experience 非量化改造（DONE，P1）
- [x] LLM 结构化精炼（九字段；原文+炼果双存 refined_json；无 KEY 422 显形；
      schema 校验）
- [x] 非量化验证四方法（反例搜索确定性检索/历史证据 PIT 前向核对/跨公司
      同业成员核对/人工复核留档）——禁 IC/回测回潮
- [x] Playbook 检索（已批准卡片；条目无 authority/fact_status ——
      Playbook≠Evidence 结构锁死）
- [x] 验证：tests/test_r6 3/3 + 全量 backend exit 0 + Playwright 30/30

## R7 — Research Memory（DONE，P1）
- [x] research_memories 表（migration a7b8c9d0e1f3）+ Memory domain（七类/
      scope/instrument+industry+event_type+intent+tags 检索）
- [x] 晋升门：candidate→active→retired（禁跳级）；更新=version+1
- [x] POST/GET /memories + /from-experience/{card}（仅 APPROVED 可转，
      未批准 422 显形；源 artifact/experience 引用保留）
- [x] Memory≠Evidence 结构锁死：条目无 authority/fact_status 字段（测试断言）
- [x] 验证：tests/test_r7 3/3 + 全量 backend exit 0 + Playwright 30/30

## R8 — Research Inbox / Continuous Monitoring / Thesis Diff（DONE，P0）
- [x] Research Inbox（GET /research-inbox：新证据/重要性决策/研究请求/
      到期预测/失败采集 聚合只读投影）
- [x] Thesis Diff（GET thesis-diff 确定性影响分析 + POST apply 落新 Thesis
      行 append-only + Artifact generated_from 旧 Thesis + PIT pinned 校验；
      无新证据 422 显形）
- [x] Signal Ladder（POST signal-ladder/evaluate：A/B 分级确定性规则 +
      证据引用强制）
- [x] Thesis Artifact 注册缺口补齐（pipeline thesis_ready 落 Artifact +
      run produced thesis 边）
- [x] 验证：tests/test_r8 3/3 + 全量 backend exit 0 + 真机核验
      （inbox 24 项 / diff 20 新证据 2289 claims 177 theses / delta_research）

## R9 — Research Graph + Final Closure（DONE）
- [x] 语义对象注册 Artifact（industry_driver/transmission/narrative/position，
      幂等 per domain）+ ArtifactType 枚举扩展 + RESEARCH_MEMORY 就位
- [x] Handoff 动作扩展：evidence/claim/driver/narrative/thesis/memory/
      research_product → commander（open_in_commander，服务端持久化信封）
- [x] 图谱真机：全类型节点 + 148 边可查
- [x] R9-MANIFEST.md

- [x] R10-CLOSURE.md 落盘（24/24 黄金场景 + §24 全条件核对）

## R10 — Closure（DONE）
- [x] docs/research-deep-port/R10-CLOSURE.md：§24 完成定义 14 项逐项 PASS +
      §20.2 十四问可回答性 + 偏离/边界如实登记

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

# V2 总纲执行线（docs/archive/A-Share-Research-OS-最终产品与架构修改方案.md）

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

## 部署准备 + 持续打磨（DONE）
- [x] 预测一致性披露（方向/区间异号显形）+ 中报口径年化修复（000831 问题）

## UX Foundation（DOING，新任务书 docs/A-Share-Research-OS-UI信息架构与全产品体验重构任务说明书.md）
- [x] UI2 首批：/views/watchlist + /views/instruments/{id}/overview（关注池已接视图）
- [ ] UI0 Token 修复（CSS Token 统一/硬编码清理）
- [ ] UI1 Sidebar 分组导航 + 四种 Layout
- [ ] UI2 剩余 Read Model（CommandCenter/ReportLibrary/ContinuousResearch/PredictionReview）
- [ ] UI3 语义组件库
- [ ] UI4 基准页面重构（AI 中枢 + Instrument Workspace）
- [ ] UI5-UI8 依次：核心库/验证与策略面/图谱画布/视觉回归
- [ ] 冻结：UI4 验收前禁止新增一级业务模块
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

