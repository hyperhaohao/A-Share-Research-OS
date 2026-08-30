# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
历史事实（保留）：Guanlan Direct Port G0–G10 全部 DONE —— PORT COMPLETE
（G10 完成 = Experience Port 清单完成，不等于研究能力吸收完成）。

Current Execution Line: **Guanlan Research Capability Deep Port（R0–R9）**
依据 docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md。
License Gate：donor 无 LICENSE → REFERENCE_ONLY / BEHAVIORAL ADAPTATION。
三方 commit：ASRO（见 git log）/ donor 98f1398（无 drift）。
Quant 本轮冻结（NO NEW DEVELOPMENT，保留不删）。

R0-R3 DONE：
  R0 差距矩阵 27 项（docs/research-deep-port/00-*.md）；
  R1 ADR-Research-First + 导航研究优先 + README 定位；
  R2 Source Trust T0-T4（读时派生）+ Claim 升级双防线 + Extraction 契约/
    CitationVerifier/extraction_records + 注入防线 + 真实公告 live verify 4/4；
  R3 industry_semantic_objects 四类语义对象（append-only 版本化）+
    引用反查强制（422 显形）+ /industry-semantics API + /views/industry
    semantics 并入 + 可复算温度 + 稀土试点真实数据（广晟减持 Driver/
    Narrative，真实证据引用反查通过）+ UI 真机显示。

当前 R4 — Research Commander Autonomous Loop（DOING）。
黄金场景：000831 中国稀土资产整合研究 → docs/research-deep-port/R10-CLOSURE.md
```

## Completed

```text
Guanlan Direct Port G10 — Full Product Closure（本轮，DONE）：
  - Reviewer Pass：新代码 TODO/FIXME/mock/console.log 扫描 0 命中；
    §45 parity 14 项逐项核对（9 模块 + Evidence/PIT/Artifact/Auth/
    Scheduler/CI[本地全量三线]）全 PASS
  - docs/port/G10-CLOSURE.md：§44 端到端链覆盖说明（E2E-01…17 + 确定性
    后端覆盖）+ 环境性限制（本机 kline 断连）如实记录
  - docs/known-limitations.md 增补 4 条（kline 网络限制/工作流目录边界/
    风险偏好温度计/盯盘 AI 研判）
  - 结论：**PORT COMPLETE** —— 9/9 模块迁植 + 整合验收 PASS；
    Track A 边界（Auth/PIT/Artifact/Handoff）全满足
Guanlan Direct Port G9 — 全库研究图谱整合（本轮，DONE）：
  - 审计：八类产物已在册（research_run/report/prediction/experience_card/
    workflow_run[卡路径]/screening_run/strategy_version/industry_map/
    global_context）；两缺口：定义运行不注册、盯盘无 Artifact
  - 补齐：run_definition 注册 workflow_run Artifact（route=/workflows/{id}）+
    create_monitor 注册 strategy_monitor Artifact generated_from 策略版本
    + ArtifactType.STRATEGY_MONITOR + 前端业务名（策略盯盘）
  - 验证：backend 368 passed（+1 G9）+ vitest 30/30 + build PASS +
    Playwright 30/30（E2E-15 PASS）+ 真机核验（定义运行 wr_* 入图谱
    153 节点/157 边）
  - PORT-MANIFEST-G9
Guanlan Direct Port G8 — 全球宏观 / 海外（本轮，DONE）：
  - backend：industry_view_service.global_macro_view + GET /views/global-macro
    （市场级视图：最新 GlobalContextSnapshot 的 6 指标真实数值 + 宏观主题；
    无快照显形「宏观快照未采集」）
  - frontend：features/global-macro/（区域归组 中国/香港/美国/商品 MetricCell
    复用 + 宏观主题流 官方提及标注 + 风险偏好诚实显形「不编温度」）；
    /global-macro 路由 + nav 研究组入口；旧入口更名 产业研究·全球产业坐标
    —— §12 分离正式落地（产业坐标=产业位置 vs 全球宏观=市场环境）
  - donor PM/Kalshi 预测市场温度计无源不迁（风险偏好区显形）；overseas
    静态卡并入区域面板
  - 验证：backend 367 passed + vitest 30/30 + build PASS + Playwright 30/30
    + 真机核验（四区 6 指标全真实：上证 3952.18/道指 53559.99/纳指 29433.43/
    恒指 25584.79/金 4503.37/油 88.33 + 10 主题）
  - PORT-MANIFEST-G8
Guanlan Direct Port G7 — 策略盯盘（本轮，DONE）：
  - backend：GET /market-data/daily-bars（证据层真实日线 PIT 可见；
    无 K 线证据 → has_data=false 显形，不回退假图）
  - frontend：features/strategy-monitor/：MonitorCandles（G0 Candles 复用 +
    信号日期对位标记条）+ MonitorReplay（观察→信号→决策合并时序滑块回放，
    回放真实落库记录）—— 装配进 StrategyMonitorDetailPage（K线区置顶）
  - 诚实边界：donor AI 研判 prompt/条件单编辑/盘口不迁（决策为确定性规则
    §25；LLM 研判待 ASRO_LLM_API_KEY）；信号标记仅对位 K 线范围内日期
  - E2E 契约全保留（三分离面板/复盘回灌/replay-feedback）；E2E-13 诚实
    双路径 + E2E-16 PASS
  - 验证：backend 367 passed（exit 0）+ vitest 30/30（+3）+ build PASS +
    Playwright 30/30
  - PORT-MANIFEST-G7
Guanlan Direct Port G6 — 策略实验室（本轮，DONE）：
  - features/strategy-lab/：StrategyCompositionPanel（策略配方：物料溯源
    chips 来源筛选运行/来源经验卡 + 政策三件套 entry/exit/risk（exit/risk
    此前未渲染）+ 股票池 chips 带排名链接）+ StrategyVersionCompare
    （同名版本并排回测聚合：组合平均收益/命中率/标的覆盖；无回测显形 —）
  - 列表行加 已验证 徽标；donor 物料装配观 → §46 ASRO 现实（筛选候选=池 +
    经验卡=理念 + 工作流=入场规则，全部真实溯源可点）
  - 诚实边界：donor 假模板/假时钟/自由装配面板不迁（组装走 §46 后端编排；
    待因子引擎后开面板）；E2E-12/13 契约全保留
  - 验证：backend 367 passed + vitest 27/27 + build PASS + Playwright 30/30
    + 真机核验（配方面板：筛选运行/经验卡/股票池 3 标的/政策三件套全真实）
  - PORT-MANIFEST-G6
Guanlan Direct Port G5 — 智能选股工作台（本轮，DONE）：
  - features/screening-workbench/：三面板（左 筛选条件侧栏 来自经验卡 +
    逐规则排除计数徽标 / 中 候选池 排名+评级 A 徽标（rank≤3，可推导展示）/
    右 研究解释 Inspector：Why Selected 真实 explanation + 命中规则 + 风险 +
    CTA 进入研究/加入关注（POST /watchlist）/做成策略（§47 门保留））
  - ScreeningRunDetailPage 重定向工作台；screening-excluded/candidates 等
    E2E 契约全保留（E2E-11/12 PASS）
  - 诚实边界：因子 IC/模型评分/regime 无引擎源 → 不显示不编数（§25）；
    ScreenDefinition/版本层待因子引擎接入（G4 模式，manifest 登记）
  - 验证：backend 367 passed + vitest 27/27 + build PASS + Playwright 30/30
    + 真机核验（中国稀土 命中全部 3 条规则 全真实数据）
  - PORT-MANIFEST-G5
Guanlan Direct Port G4 — Workflow Studio 真 Editor（本轮，DONE）：
  - backend：workflow_definitions + append-only 版本（migration a9b8c7d6e5f4）
    + workflow_definition_service（图校验矩阵：未知 kind/缺 data/双 output/
    环/output 不可达 → 422 workflow.graph_invalid）+ run_definition 拓扑展开
    （Kahn）+ API（list/create/get/versions/run 202 后台）+ 执行器节点级
    参数泛化（card 运行回退全局参数，向后兼容）
  - frontend：features/workflow-studio/ 五文件（Node Library 分组目录点击加节点 /
    React Flow Canvas 交互连线+Delete 删节点 / Inspector 按 schema 编辑参数 /
    Toolbar 命名+存版本+运行 / 运行面板逐节点点灯+指标区+错误显形）
  - 目录与执行器强对应（5 类可执行 kind 进目录；donor 20 类未接引擎节点
    不伪造）；定义/版本/运行全部服务端持久化（donor localStorage 不迁）
  - 真机全链：加节点 → 保存被图校验正确拦截（未连线 422 显形）→ API 建图 →
    UI 载入（4 节点 3 边 v1 徽标）→ Run → 逐节点点灯 + 日线源诚实失败
    （本机 kline 源断连为已知问题，DAG 行为正确）
  - 验证：backend 367 passed（+3）+ vitest 27/27（+4）+ build PASS +
    Playwright 30/30；PORT-MANIFEST-G4
Guanlan Direct Port G3 — 研究经验卡（本轮，DONE）：
  - backend：experience_view_service + GET /views/experience/{card_id}
    （原=报告+主张原文 cite 序号+证据摘要 / 炼=机制条件表达式 /
    验=验证记录 / 用=已批准 KB；只读装配，不迁 donor markdown 三桶库）
  - frontend：features/experience-workbench/ 五组件三栏工作台（原炼验用 +
    生命周期条 + verdict chip 通过/存疑/驳回 + 诚实量化指标区 — +
    CardWorkflowPanel/ScreeningLaunchButton/批准门槛保留）
  - 附加修复：thesis 标题业务名化（research_synthesis 经注册表名解析，
    消除 SZSE: 技术前缀泄漏）；E2E-09 来源断言随工作台文案同义更新
  - 验证：backend 367 passed + vitest 23/23 + build PASS + Playwright 30/30
    （E2E-09 全链：炼卡→拦截未验证批准→案例验证→批准）+ 真机截图核验
  - PORT-MANIFEST-G3
Guanlan Direct Port G2 — 产业研究三视图（本轮，DONE）：
  - backend：industry_view_service + GET /views/industry/{id}（方案 §24 命名）
    + GET /views/industry/{id}/segment/{segment_id}（链外环节 404 显式拒绝）；
    只读投影复用 industry_map_snapshots + global_context_snapshots（无新表），
    携带 map_id/context_snapshot_id 供 open_with_context 溯源
  - frontend：features/industry-research/（IndustryResearchWorkspace 三视图一体
    双 tab + IndustryChainView 阶段列/环节 tile/股票池 + GlobalIndustryPositionView
    β/Δ/Ω/Θ/Ψ 五轴/宏观主题/指标网格 + IndustrySegmentDetail 环节详情）；
    替换旧 ResearchMapPages（两孤立页面 → 三视图一体，方案 §7）
  - 诚实置空：Driver/Transmission/Narrative/站位/动量/温度 无证据源 → 显形
    「暂无观点/暂无定位」（不迁 donor YAML 板库/假边/假象限；关系源接入后自动补全）
  - 修复：evidence 标题技术串泄漏（改显真实摘要）+ artifactByDomain 域类型
    （IndustryMapSnapshot，E2E-14 契约）+ i18n industryWs.*（zh/en）
  - 验证：backend 367 passed（+2：三视图装配/环节证据+404）+ vitest 23/23 +
    build PASS + Playwright 30/30 + 真机截图核验（产业链列/五轴/披露/环节详情）
  - PORT-MANIFEST-G2
Guanlan Direct Port G1 — AI 研究中枢 / 深度研究（本轮，DONE）：
  - features/command-center/：CommandCenterPage（三栏编排 + 会话自举）/
    CommandCenterLeft（计划墨痕 ResearchStep 三态 + 正在运行 + 最近计划 +
    多会话切换）/ CommandCenterTranscript（对话 + 计划执行链 + 上下文 chip
    Composer）/ CommandCenterWorkbench（真实当前 Workbench：标的速记卡
    真实行情 价格/涨跌/PE/PB/市值/行情时间 + 计划产物报告 CTA 置顶 +
    待验证预测）/ plan.ts + command-center.css
  - 替换：观澜 GuanlanAgent SSE/GUANLAN_BACKEND/localStorage 持久化/
    mock 假流式报告/假步骤定时器 → ASRO /views/command-center 单请求聚合 +
    /command/sessions + /artifacts + /market-data/quote（全部真实数据，
    缺行情显形「行情暂不可用」）
  - E2E 契约全保留（commander-* testid 矩阵 + artifact-row/-open + plan-row）；
    修复回归中发现的 commander-reply testid 缺失 + 计划完成文案国际化
  - i18n cc.* 16 组（zh/en）；附加修复：删除会话切换草稿中的 hook 规则违规
  - 验证：vitest 23/23（+4 command-center）+ tsc/build PASS +
    Playwright 30/30（product 18 含 E2E-08 全链 + visual 12，
    command-center 双主题基线按内容变更重生成）+ 真机三栏截图核验
    （左 计划墨痕 01→03 完成 · 中国稀土 / 中 对话+链 / 右 60.18 -1.04%
    PE 257.7 PB 12.69 639亿 全真实行情）
  - PORT-MANIFEST-G1（donor 3442 行 chat/app.jsx 行为级对标记录）
Guanlan Direct Port G0 — Shared UI Foundation（本轮，DONE）：
  - token 映射层 styles/guanlan-tokens.css：donor 变量（--paper/--ink/--zhu/--dai/
    --jin/--yin/--serif + .seal/.up/.down/.paper-bg/ink-rule/gl-pulse）全部以
    ASRO 语义 token 重定义；涨跌/danger 红线不混；真机双主题探针验证
    （light --zhu=#c23a2f 涨红、dark --yin=#d8584a 印章红，均正确切换）
  - ui/guanlan/ 组件库（donor shared.jsx 全 6 组件 TSX 化 + G0 基础组件集）：
    Brandmark（ASRO wordmark，i18n 印章字符）/ MarketTicker / Sparkline / Candles /
    ResearchStep / MetricCell / Panel / Badge / Button / Toolbar+Sep / Drawer /
    Tooltip / Inspector + guanlan.css + barrel index.ts
  - i18n：guanlan.brandSeal/drawerClose/drawerTitle（zh-CN + en-US）
  - THIRD_PARTY_NOTICES.md（donor 无 LICENSE 文件 vs README Apache-2.0 badge，
    差异如实记录，commit 98f1398）+ docs/port/PORT-MANIFEST-G0.md
  - 附加修复：AppShell 品牌裸 i18n key（t("app.name")→t("app.title")，a0d200c 引入）
  - 验证：vitest 19/19（+12 guanlan-ui）+ tsc/vite build PASS +
    视觉回归 12/12 PASS + 产品 E2E 18/18 PASS（compose 栈全量真机）
Guanlan Direct Port 状态集成（本轮）：
  - 总任务书入库（docs/A-Share-Research-OS-Guanlan-Direct-Port-*.md）
  - Donor 审计确认：upstreams/financial-analyst 存在，非 git clone；
    GitHub HEAD = 98f1398（2026-08-21）；license=None（README badge 标 Apache-2.0）
    —— 已记录，THIRD_PARTY_NOTICES.md 落 G0 交付
  - PLAN/ROADMAP/STATUS 增 Track B G0–G10；文档索引登记为现行 Experience 总任务书
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态解析/Pipeline 中英阶段名，git 13f7346）
UI5–UI8（本轮，DONE）：
  - UI5：经验卡 Library 数据表格（§25）+ 生命周期条（原→炼→验→用）+
    视图 /views/experience-cards
  - UI6：筛选候选表（§27）+ Monitor Ops KPI 头 + Strategy layout-workspace
  - UI7：研究图谱 React Flow 画布（150 节点/类型着色/关系边标/过滤/Inspector）
    + 产业地图画布（主体→板块成员，basis 边标）；Lineage 列表保留
  - UI8：视觉回归 12 基线（10 页 zh light + 2 dark），活数据 mask + 0.35 容差，
    连续 3 轮稳定
  - 全面自查报告 docs/ux-foundation-self-review.md：§66 总表 33/34 PASS
UX Foundation 全面自查（本轮，DONE）：
  - §66 验收总表 34 项逐项核查：29 PASS / 4 部分（UI5-UI7 深化项）/ 1 待做（UI8 截图）
  - 自查过程修复 8 项（详见 docs/ux-foundation-self-review.md 第二节），
    含 2 个 500 级缺陷（watchlist 视图列名、prediction-review str/enum shim）
  - 渲染层裸枚举扫描（E2E-UI-08）：reports/experience/strategy/graph/source-health 0 命中
  - 请求预算：五张基准页全部单视图请求（≤3 预算达标）
UX Foundation 开工（本轮，UI2 首批 DONE）：
  - 后端 Read Model：services/view_service.py + api/views.py
    （GET /views/watchlist、GET /views/instruments/{id}/overview）——
    一次请求装配身份/行情/研究判断/报告/预测/盯盘，纯只读投影不建第二 Domain
  - 关注池页面重写为单请求消费视图（原每卡 3 个 useQuery 客户端拼装），
    卡片新增 研究状态/预测摘要/盯盘状态 行（评审 §四 的架构缺口已闭合）
  - 任务书入库并确立执行线（业务功能冻结，UI0–UI8）
深度扩展 a–e（本轮，DONE）：
  a. 产业链关系源：eastmoney_industry_relations provider（suggest→板块→
     成员→规范 id）；产业地图 related=真实板块成员（basis 东财同业板块），
     证据共现保留为交叉参考，源不可用回落并披露
  b. 宏观数值层：tencent_global_macro provider（上证/道指/纳指/恒指/金/油，
     双响应形态解析）；GlobalContextSnapshot.indicators_json（迁移
     d8e9f0a1b2c3）；真机验证 6 指标全通（numeric_source=tencent_global_macro）
  c. quant_expression：受约束 DSL（无 eval）→ 类型化 DAG 表达式节点
     （validation 后评 verdict，诚实记录成立/不成立）；卡片字段+API 透传
     （迁移 e9f0a1b2c3d4）；解析失败 422
  d. §47 全套验证：回测聚合含 regime_split（按退出年分域）+ sensitivity
     （参数邻域 9 组合）；全电池+正收益 → VALIDATED（可进正式盯盘），
     分域不足/负收益 → EXPERIMENTAL 并显式说明
  e. 盯盘观察源：公告/新闻/资金/宏观证据入观察池（按种类去重+限额），
     每种独立信号（new_announcement/new_news/…），rule_kind 按观察推导
  - 产品面：工作流面板表达式输入；全球坐标指标网格；E2E-17 全链
  - 附加修复：E2E-03 亚秒运行竞态（面板经 §37 回放补全）；WatchCard
    瞬时失败回退裸 id → 回退纯代码（红线安全）
验收 Reviewer Pass（本轮，DONE）：
  - 架构缺陷（复现并修复）：FastAPI 依赖 teardown 在响应送达后才 commit
    DB 会话 → 写后立即读可见预提交状态（真机复现：create 201 → 立即 GET 404）。
    修复：commit 中间件在响应返回前提交请求会话（get_session 挂载
    request.state.db_session）；真机结构验证：create/validate 后立即读
    状态一致 PASS
  - 红线5：strategy→monitor:create_monitor 注册 + CTA 携信封
  - 红线6：回测/盯盘运行事件落库（BACKTESTING/MONITORING stage）+ 回测事件路由
  - 复查测试 +6（事件回放/stage 分类/信封注册）；套件 344；E2E 16/16
Phase J v1（本轮，DONE）：
  - 后端：ReplayFeedbackService（§79 编排）：Decision → 链上最新已验证
    Prediction（无则 422 replay.chain_incomplete 显式拒绝，§50 不伪造预测）→
    RegressionReview（确定性归因）→ ExperienceCard v(n+1)（教训 append-only，
    method=review）→ StrategyVersion v(n+1)（同筛选运行重组，拾取新卡片）→
    ResearchExperience（§53 append-only）；review artifact registered
    generated_from 预测（直建预测补登记），策略 v2 generated_from 复盘
  - 前端：盯盘决策区「复盘回灌」动作（结果/拒绝显形）；monitor.replay* 本地化
  - E2E-16：诚实双路径（DRAFT→盯盘门槛拒绝；EXPERIMENTAL→决策→回灌拒绝
    显形——链上无成熟验证是事实）；完整回填由后端成熟预测测试覆盖
Phase I v1（本轮，DONE）：
  - 后端：GET /artifacts/graph（有界节点集 + 其间全部溯源边）；
    ArtifactService.edges_among —— Phase A 起积累的 Edge 账本成为可查询
    全库视图
  - 前端：/research-graph 页（类型分组节点 + Lineage Explorer：上游/下游
    关系行带跳数，业务语言；跨模块跳转走 artifact 自身 route）；
    nav 全库图谱；researchGraph.* 本地化
  - E2E-15：选报告节点 → lineage 上溯到 研究运行(产出) → 跨模块跳转
Phase H v1（本轮，DONE）：
  - 后端：industry_map_snapshots/global_context_snapshots 表
    （迁移 c7d8e9f0a1b2）；两视图由真实证据组装：产业链/主业来自
    eastmoney_industry 证据；相关公司=证据文本与注册表名称共现（真实
    共现，basis 显式标注，关系源未接入显式披露）；全球坐标=macro_policy
    证据主题（含官方机构提及标注），「官方宏观数值源未接入」显式披露；
    PIT as_of 取证据时间；artifact industry_map/global_context 注册并
    generated_from 报告；handoff 注册两视图 → workspace:open_with_context
  - 前端：/industry-map 与 /global-context 视图页（非孤立 Dashboard：
    open_with_context 回工作台带信封）；工作台头部入口链接；
    industryMap./globalContext. 全量本地化
  - E2E-14：工作台 → 产业地图（产业链或诚实未生成）→ 带上下文回到
    同一标的工作台 → 全球坐标披露断言
Phase G v1（本轮，DONE）：
  - 后端：strategy_monitors/observations/signals/decisions 四表
    （迁移 b6c7d8e9f0a1）；create_monitor 门槛=EXPERIMENTAL（§47 衔接，
    DRAFT → 422）；一次运行三分离：Observation（真实数据：最近两条含价
    行情证据的变化 + 自上次观察以来的新公司事件）→ Signal（强类型规则
    quote_move≥阈值/new_event，强度落库）→ DecisionRecord（§49 全字段：
    决策/置信度/理由/观察与信号与证据引用/as_of；§25 仅 Research
    Decision，rationale 显式注明，无任何下单对象）
  - Scheduler.tick 后台运行 due monitors（§23：不是页面打开才工作）
  - 前端：/monitoring 列表 + 详情（观察/信号/决策三个独立分区=§24 的
    UI 结构本身）；策略页「建立盯盘」CTA（门槛拒绝显形）；monitor.* 本地化
  - E2E-13：诚实双路径（EXPERIMENTAL→建立+运行+三分区可见；DRAFT→门槛
    拒绝显形）
Phase F v1（本轮，DONE）：
  - 后端：strategy_versions/strategy_backtest_runs 表（迁移 a5b6c7d8e9f0）；
    §46 组装（筛选候选=typed universe，理念=卡片机制，前向收益入场规则，
    同名版本号自增）；§47 跨标的回测（与工作流共用同一条真实日线 Data
    路径，逐标的指标+组合聚合，失败案例显形 §22，逐标的数据失败记录
    no_data）；验证门槛（无完成回测 → 422；验证后一律 EXPERIMENTAL，
    verdict 显式注明禁止进入正式盯盘）；strategy_version/backtest
    artifact generated_from 筛选运行与经验卡；handoff 注册
    screening→strategy:create_strategy；工作流服务抽取共享日线助手
  - 前端：/strategy 列表 + 详情（回测块：组合指标/逐标的/失败案例显形）；
    筛选页「做成策略」CTA 走信封；strategy.* 全量本地化；补
    workflow.status.* 词条（状态芯片此前裸显 key）
  - E2E-12：筛选 → 策略（信封溯源）→ 门槛拒绝显形 → 回测诚实终态 →
    完成路径验证标 EXPERIMENTAL
Phase E v1（本轮，DONE）：
  - 后端：screening_runs 表（迁移 f4a5b6c7d8e9）；§45 流程 ExperienceCard →
    强类型规则（has_report/thesis_direction/has_quote，全部由真实研究状态
    求值）→ 全市场评估 → 候选排序；每候选 rank/score/factor_scores/
    matched_rules/explanation（事实拼装，卡片标题引用，无裸 id）/risks（§20）；
    被排除原因按规则聚合 + 示例（为什么没选中）；screening_run artifact
    registered generated_from 卡片；RunEvent（stage SCREENING）可回放；
    handoff 注册 experience→screening:run_screening
  - 前端：/screening 列表 + /screening/:runId 详情（候选卡 + 排除聚合）；
    卡片页「按此经验筛选」CTA 走信封；screening.* 全量本地化
  - E2E-11：卡片 → 筛选（信封溯源）→ 候选带「命中全部…经验依据」解释 +
    排除聚合披露
Phase D v1（本轮，DONE）：
  - 后端：workflow_runs 表（迁移 e3f4a5b6c7d8）；最小强类型 DAG
    Data(真实日线 historical_data)→Rule(前向收益 h/阈值)→Validation(确定性
    指标：样本/命中率/收益分布，0 样本如实披露)→Output(quant validation
    写入卡片 + workflow_run artifact registered generated_from 卡片)；
    事件经 RunEvent 落库可回放（§37 通用 run_id）；handoff 注册
    experience→workflow:run_validation（§44）
  - 前端：卡片页验证工作流面板（期限选择→发起→节点进度→指标网格）；
    workflow.* 全量本地化
  - E2E-10：诚实终态契约（完成→指标+量化记录；失败→真实源错误显形于节点），
    今日 kline 源被网络阻断故走失败显形路径（完成路径由后端测试覆盖）
Phase C（本轮，DONE）：
  - 后端：experience_cards/versions/validations 表（迁移 d1e2f3a4b5c6）；
    ExperienceService 原→炼（确定性提炼，保留 report_id/version_id/claim_ids/
    evidence_ids，§43）→ 验（v1 Case validation：PIT 入场价→最新可见价，信息
    记录）→ 用（批准需 ≥1 验证，§13 门槛）；LLM 润色可选（无 provider 显式 422）；
    artifact experience_card 注册 + generated_from 报告；handoff 注册
    report→experience:create_experience_draft
  - 前端：/experience 列表 + /experience/:cardId 详情（来源显形/验证记录/
    验证/批准/否决动作）；报告页「炼成经验卡」CTA 走信封；经验卡状态全量本地化
  - E2E-09：报告 → 卡片（信封溯源）→ 拦截未验证批准 → 案例验证 → 批准通过
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
Research Capability Deep Port（R 线）：R0-R3 DONE；当前 R4 — Commander
Autonomous Loop（DOING）。
R4 要点：Intent Router 扩九类（company/industry/event/earnings/policy/
mainline/overseas_mapping/thesis_review/comparison）+ 结构化 Plan 扩展
（objective/questions/required_sources/completion_criteria）+ Missing Data
Loop（迭代重收集）+ Agent Profiles 白名单 + run 状态机扩展 + max iterations。
随后 R5 Products → R6/R7 → R8 Inbox/Thesis Diff → R9 Graph → R10-CLOSURE。

```

## Tests

```text
backend: 349 passed
frontend: 7 passed + build PASS
e2e: Playwright 产品 E2E 17/17 passed（E2E-01…17，真实浏览器+真实源，
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
Phase J（本轮真机，000831，E2E-16 + compose API 实测）：
  盯盘决策 → 复盘回灌：链上无成熟验证 → 422 显式拒绝（不假装闭环）PASS
  完整回填（成熟预测→归因→卡片 v2→策略 v2→教训记录）后端 3/3 覆盖 PASS
  review artifact generated_from 预测；策略 v2 generated_from 复盘 PASS
深度扩展（本轮真机，000831）：
  宏观数值层：rebuild 后 6 指标全通（上证 3952.18 / 道指 53559.99 /
  纳指100 29433.43 / 恒指 25584.79 / COMEX金 4503.37 / 布油 88.33，
  numeric_source=tencent_global_macro，各带市场时间）PASS
  产业地图：板块成员→related（basis 东财同业板块），回落路径披露 PASS
  quant_expression：DAG 表达式节点 verdict 诚实记录（成立/不成立）PASS
  盯盘多源观察：公告/新闻/宏观观察与独立信号 PASS
  E2E-03 亚秒运行竞态：§37 回放补全面板 PASS
验收复查（本轮真机，000831）：
  写后读竞态真机复现（create 201 → 立即 GET 404）→ 中间件修复 →
  立即读一致（create 200/validate 后 VALIDATING 即时可见）PASS
  回测事件回放（backtest_started→completed，stage BACKTESTING）PASS
  盯盘事件回放（monitor_started/completed，stage MONITORING）PASS
  strategy→monitor 信封注册（POST /handoffs 201）PASS
Phase I（本轮真机，000831，E2E-15 + compose API 实测）：
  /artifacts/graph 返回 5 节点 4 边（run/version/report/prediction 链）PASS
  Lineage Explorer：报告节点上溯 研究运行(产出) PASS
  跨模块跳转离开图谱页 PASS
Phase H（本轮真机，000831，E2E-14 + compose API 实测）：
  产业地图：industry_chain/主业由真实 industry_profile 证据组装，
  artifact generated_from 报告，二次读取复用快照 PASS（compose 实测
  imap_25abb0fd0fa4 + by-domain 解析 + handoff 201）
  全球坐标：政策主题含官方机构提及，数值源未接入显式披露 PASS
  视图 → open_with_context → 同标的工作台（上下文不丢失）PASS
Phase G（本轮真机，000831，E2E-13 + compose API 实测）：
  盯盘门槛：DRAFT 版本 422 拒绝显形 PASS
  三分离记录落库且互相引用（观察引用真实行情证据，决策引用全部观察/信号）PASS
  Scheduler.tick 后台拾取 due monitor 并完成一次运行 PASS
Phase F（本轮真机，000831，E2E-12 + compose API 实测）：
  筛选 → 组装策略（信封溯源 URL，universe=筛选候选）PASS
  §47 门槛：无回测时验证 422 拒绝显形 PASS
  回测诚实终态（kline 源仍断连 → 失败显形于回测块）PASS
  完成路径（下跌序列失败案例披露/EXPERIMENTAL 标记）后端 6/6 覆盖 PASS
Phase E（本轮真机，000831，E2E-11 + compose API 实测）：
  卡片 → 筛选运行（信封溯源 URL）→ 候选含 中国稀土（命中全部 3 规则，
  解释含完整研究报告/论点方向/可见行情证据）PASS
  排除聚合按规则披露（缺报告/方向不符/无可比价 + 示例标的）PASS
  screening_run artifact generated_from 经验卡 PASS
Phase D（本轮真机，000831，E2E-10 + compose API 实测）：
  工作流 DAG 真实执行：kline 源被网络断连 → Data 节点诚实失败显形
  （source_unavailable），DAG 终态 failed，无伪造指标 PASS（诚实路径）
  完成路径（确定性指标/quant 记录/artifact 链接/事件回放）由后端
  构造序列测试覆盖 PASS（5/5）
Phase C（本轮真机，000831，E2E-09 + compose API 实测）：
  报告 → 炼成经验卡（信封溯源 URL）→ 来源显形（11 主张/17 证据）
  → 未验证批准被拦截 → 案例验证（PIT 24.83 → 最新价）→ 批准 APPROVED PASS
  compose 卡片 exp_f840958ef18b：APPROVED v1，artifact generated_from 报告 PASS
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
1. 资金流/历史行情对部分标的仍失败（源层真实失败，UI ⚠ 显形 —— 符合红线8）。
   2026-08-29 实测：东方财富 kline 端点对本机网络直接断连（宿主机与容器一致，
   疑似 TLS 指纹拦截），验证工作流 Data 节点诚实失败显形；恢复后完成路径
   即在真机可用（后端测试已覆盖指标确定性）
2. [已解决 2026-08-29] 预测方向与区间异号 → 已显式披露（consistency 字段 +
   卡片警示）+ 输入口径修复（中报 EPS 年化）。剩余差异为真实的市场溢价 vs
   基本面锚：现价 60.18 对应 PE≈270×/PB≈12.6×，锚定模型（PE25/PB5/PS8 默认
   倍数）必然给出深度负 upside —— 待历史分位/同业校准接入后锚定会更贴近
3. 基准指数（IDX）行情未接入 → 超额收益显式 null
4. 法定节假日历未接入 → 预测到期日 ±1-3 天
5. 公网部署需认证/TLS；SQLite 单机规模；生产多用户需 PostgreSQL
6. Macro 官方原始源未接入；Cost Ledger 待真实化；scheduler claim 待原子化
8. [已承接 Phase D] 简单 Quant validation 由验证工作流前向收益规则实现；
   quant_expression 自定义表达式仍留待后续工作流节点扩展
9. [已解决 2026-08-29] 东财 push2 系端点对本机网络断连 → 宏观数值层改用
   腾讯行情源（容器内可达）；K线源仍断连（产业地图同业板块用 searchapi
   + clist 可达端点，K线恢复后回测/工作流自动恢复全量指标）
7. [已解决 2026-08-29] Docker Desktop 引擎故障 —— 用户修复后 compose 重建完成，
   全链真机验证通过（见 Live Verification）。经验：多后端并存时先确认
   :5173 代理目标（vite ASRO_API_PROXY），E2E 断言须锁定自身创建的对象
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
