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

## R4 — Research Commander Autonomous Loop（DOING，P0）
- [ ] Intent Router 九类 + 结构化 Plan 扩展 + Missing Data Loop
- [ ] Agent Profiles（七类职责/工具白名单契约）+ run 状态机扩展
- [ ] DeepResearchLoop（max iterations/终止条件）+ Thesis 变异规则（禁静默覆盖）

## R5 — Research Product System（PENDING，P0/P1）
- [ ] ResearchProduct 类型契约（复用 Report/Artifact/Version；逐类型 Contract）
- [ ] P0：COMPANY_DEEP_DIVE / INDUSTRY_DEEP_DIVE / EVENT_INVESTIGATION / THESIS_REVIEW
- [ ] P1：MAINLINE_RADAR / OVERSEAS_MAPPING / DAILY_RESEARCH_BRIEF

## R6 — Experience 非量化改造（PENDING，P1）
- [ ] LLM Refinement 结构化（九字段；原文+炼果双存；无 KEY 422 显形）
- [ ] 非量化验证方法（case/historical/counterexample/cross-company/cross-cycle/review）
- [ ] Playbook（批准后可检索；Memory≠Evidence 边界测试）

## R7 — Research Memory（PENDING，P1）
- [ ] ResearchMemory domain（七类/scope/version/staging→review 晋升）
- [ ] 检索（instrument/industry/event_type/intent/tags）+ Agent 三段上下文

## R8 — Research Inbox / Continuous Monitoring / Thesis Diff（PENDING，P0）
- [ ] Research Inbox（九类聚合）+ Materiality 扩展（affected_*+suggested_action）
- [ ] Thesis Diff → 新 Thesis Version（UI 对比视图）
- [ ] Monitor 类型（Company/Industry/Event/Thesis/Catalyst）+ A/B Signal Ladder

## R9 — Research Graph + Final Closure（PENDING）
- [ ] Graph 节点/边类型扩展（Driver/Transmission/Narrative/Product/Memory/Event/Catalyst/Risk）
- [ ] Context Handoff（任意研究对象 → Commander 带 context）
- [ ] 000831 黄金场景全链真实运行 + R10-CLOSURE.md 逐项 PASS/FAIL

---

# Track B — Guanlan Direct Port（当前执行线）

> Donor：`upstreams/financial-analyst`（觀瀾，jesson-hh/financial-analyst，
> HEAD 98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28）。
> 迁植策略默认 PORT_AND_ADAPT：JSX→TSX、组件化、删 Mock/localStorage/no-build
> runtime、接 ASRO API/Read Model/Artifact/Handoff（总纲 §5/§21/§22）。

## G0 — Shared UI Foundation（DONE）
- [x] Donor token 兼容层（styles/guanlan-tokens.css：--paper/--ink/--zhu/--dai/--jin
      → ASRO 语义 token 映射，light/dark 双套 + serif 字体 token；
      不覆盖 ASRO 语义色，--yin 印章红独立于 danger/涨跌）
- [x] Donor 共享组件 TSX 化（ui/guanlan/：Brandmark→ASRO wordmark / MarketTicker /
      Sparkline / Candles / ResearchStep / MetricCell，donor shared.jsx 全 6 组件）
- [x] G0 组件集：Panel / Badge / Button / Toolbar(+Sep) / Drawer / Tooltip / Inspector
- [x] guanlan-bus / guanlan-nav 行为承接登记（→ HandoffEnvelope / AppShell navigation，
      基建不迁，PORT-MANIFEST-G0 记录）
- [x] THIRD_PARTY_NOTICES.md（donor 无 LICENSE 文件、README 标 Apache-2.0，
      差异如实记录）+ docs/port/PORT-MANIFEST-G0.md
- [x] i18n（zh-CN/en-US guanlan.*）+ Theme 双套验证 + 附加修复：AppShell 品牌裸
      i18n key（app.name → app.title，a0d200c 引入）
- [x] 验证：vitest 19/19（+12 新测试）+ build PASS + 视觉回归 12/12 +
      产品 E2E 18/18（compose 栈，Docker 修复后全量跑）

## G1 — AI 研究中枢 / 深度研究（DONE）
- [x] features/command-center/ 四组件 + plan.ts + css（donor 三栏/多会话/墨痕计划链/
      上下文 chip/右栏真实 Workbench：标的速记卡 + 计划产物 + 待验证预测）
- [x] 替换：观澜 Agent API/localStorage/mock 假流式 → ASRO 视图/会话/Artifact/行情
- [x] 验证：vitest 23/23 + build PASS + Playwright 30/30（含 E2E-08 全链 +
      command-center 双主题基线按内容变更重生成）+ PORT-MANIFEST-G1

## G2 — 产业研究三视图（DONE）
- [x] backend：GET /views/industry/{id} + /segment/{segment_id}（industry_view_service，
      真实证据组装只读投影，携带 map_id/context_snapshot_id 溯源）
- [x] frontend：features/industry-research/ 四组件（三视图一体：产业链 + 全球坐标
      β/Δ/Ω/Θ/Ψ 五轴 + 环节详情；open_with_context 保留）
- [x] 诚实置空：Driver/Transmission/Narrative/站位/动量/温度 无证据源 → 显形
      暂无观点/暂无定位（不迁 donor YAML 板库，不造假边假象限）
- [x] 验证：backend 367 passed（+2 G2）+ vitest 23/23 + build PASS +
      Playwright 30/30（E2E-14/17 契约保留）+ 真机截图核验（三视图 + 诚实披露）
- [x] PORT-MANIFEST-G2

## G3 — 研究经验卡（DONE）
- [x] backend：GET /views/experience/{card_id}（原=主张原文+cite 序号+证据摘要/
      炼=卡字段/验=验证记录/用=已批准 KB；markdown 三桶库不迁）
- [x] frontend：features/experience-workbench/ 五组件（原炼验用三栏工作台 +
      verdict chip + 诚实量化指标区 + 生命周期条；动作/门槛全部后端强制）
- [x] 附加修复：thesis/卡片标题业务名化（research_synthesis 注册表名解析，
      界面不裸显 SZSE: 前缀）；E2E-09 来源断言随工作台文案同义更新
- [x] 验证：backend 367 passed + vitest 23/23 + build PASS + Playwright 30/30
      （E2E-09/10/11 全链）+ 真机截图核验（11 主张 cite + 事实状态本地化）
- [x] PORT-MANIFEST-G3

## G4 — Workflow Studio（DONE）
- [x] backend：workflow_definitions + append-only 版本表（migration a9b8c7d6e5f4）
      + 图校验（kinds/必须有 data/恰一 output/无环/可达）+ run_definition 拓扑展开
      + 执行器节点级参数泛化（card 运行向后兼容）
- [x] frontend：features/workflow-studio/（Node Library 分组目录 + Canvas
      增删/连线 + Inspector 按 schema 编辑 + Toolbar 命名/存版本/运行 +
      运行逐节点点灯 + 指标区）—— 不再是 Run Viewer
- [x] 目录与执行器强对应：donor 25 类中 ASRO 能执行的 5 类进目录，
      未接引擎的 20 类不伪造（方案 §25）
- [x] 验证：backend 367 passed（+3 G4）+ vitest 27/27（+4）+ build PASS +
      Playwright 30/30 + 真机全链（保存被图校验拦截显形 → 载入定义 → Run →
      逐节点状态 + 诚实失败）
- [x] PORT-MANIFEST-G4

## G5 — 智能选股（DONE）
- [x] features/screening-workbench/ 三面板工作台（条件侧栏含逐规则排除计数 /
      候选池排名+评级徽标 / 研究解释 Inspector：Why Selected + 进入研究 +
      加入关注 POST /watchlist + 做成策略 §47 门）
- [x] 因子 IC/模型评分无引擎 → 不显示不编数；ScreenDefinition/版本层留待
      因子引擎接入（PORT-MANIFEST-G5 登记）
- [x] 验证：backend 367 passed（无后端改动）+ vitest 27/27 + build PASS +
      Playwright 30/30（E2E-11/12 契约保留）+ 真机核验（全真实数据 Inspector）

## G6 — 策略实验室（DONE）
- [x] features/strategy-lab/：策略配方面板（物料溯源 chips：来源筛选运行/
      来源经验卡；政策三件套 entry/exit/risk；股票池 chips）+ 版本比较
      （同名版本并排回测聚合）+ 列表 已验证 徽标
- [x] donor 自由装配/模板库/时钟条留待因子引擎与 risk_policy 结构化
      （PORT-MANIFEST-G6 登记）
- [x] 验证：backend 367 passed + vitest 27/27 + build PASS + Playwright 30/30
      （E2E-12/13 契约保留）+ 真机核验（配方面板全真实溯源）

## G7 — 策略盯盘（DONE）
- [x] backend：GET /market-data/daily-bars（证据层真实日线，无数据显形）
- [x] frontend：features/strategy-monitor/（K线区 G0 Candles 复用 + 信号
      对位标记 + 观察→信号→决策合并时序 Replay 滑块回放）
- [x] donor AI 研判 prompt/条件单编辑/盘口不迁（决策为确定性规则 §25；
      LLM 研判待 KEY）—— PORT-MANIFEST-G7 登记
- [x] 验证：backend 367 passed（+bars 端点）+ vitest 30/30（+3）+ build PASS +
      Playwright 30/30（E2E-13 诚实双路径/E2E-16 契约保留）

## G8 — 全球宏观 / 海外（DONE）
- [x] backend：GET /views/global-macro（市场级：最新 GlobalContextSnapshot 的
      指数/商品数值层 + 宏观主题；无快照显形）
- [x] frontend：features/global-macro/（区域归组 中国/香港/美国/商品 + 宏观
      主题流 + 风险偏好诚实显形；/global-macro 路由 + nav 新入口；
      旧入口更名 产业研究·全球产业坐标 —— §12 分离落地）
- [x] 验证：backend 367 passed + vitest 30/30 + build PASS + Playwright 30/30
      + 真机核验（四区 6 指标全真实 + 10 主题）

## G9 — 全库研究图谱整合（DONE）
- [x] 审计：research_run/report/prediction/experience_card/screening_run/
      strategy_version/industry_map/global_context 已在册；缺口=定义运行与盯盘
- [x] 补齐：定义运行注册 workflow_run Artifact（route=/workflows/{run_id}）+
      盯盘注册 strategy_monitor Artifact generated_from 策略版本 +
      ArtifactType/前端业务名扩展
- [x] 验证：backend 368 passed（+1）+ vitest 30/30 + build PASS +
      Playwright 30/30（E2E-15 PASS）+ 真机核验（定义运行入图谱）

## G10 — Full Product Closure（DONE）
- [x] Reviewer Pass（新代码 TODO/mock/console 扫描 0 命中）+ §45 parity
      14 项逐项核对（9 模块 parity + Evidence/PIT/Artifact/Auth/Scheduler/CI）
- [x] docs/port/G10-CLOSURE.md（诚实矩阵：环境性限制=本机 kline 断连；
      源依赖展示单元显形不编数）+ known-limitations 增补 4 条
- [x] 验证：backend 368 + vitest 30 + Playwright 30 + build 全绿
- [x] 结论：**Guanlan Experience Port — PORT COMPLETE**（9/9 模块；
      外部源依赖单元按 §25 显形，接入后自动补全）

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

