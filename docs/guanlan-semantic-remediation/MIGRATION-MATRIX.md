# G0 — MIGRATION-MATRIX（观澜研究能力语义迁移台账）

> 任务书：docs/观澜研究能力语义迁移整改任务书.md（REJECT，2026-09-02）
> 基线：ASRO `c66952e`（F0–F15 第三轮结束后 HEAD）；backend 459/0、vitest 35/35、tsc/build PASS
> 本台账按**当前代码实读**裁决（不沿用旧 Manifest 结论）；每行给代码证据。
> 状态：PASS / PARTIAL / FAIL / BLOCKED_*；「Structural PASS ≠ Semantic PASS」
> ——旧 60 项测试全过只证明结构可运行，不证明语义迁移（任务书 §二）。

## 1. 产业链研究（G1 目标：可计算、可引用、可 PIT 的产业图谱）

| 能力 | Original Intent | ASRO 现状（代码证据） | Executable Semantics | PIT | Status | Gap |
|---|---|---|---|---|---|---|
| IndustryChain/Segment | 产业链环节与传导 | industry_map_snapshots 由**行业分类字符串**组装（industry_view_service：classification→chain_levels） | 无边、无传导、不可计算 | as_of 有（快照时间） | **FAIL** | 分类树 ≠ 产业链；无 Segment Edge |
| IndustryEdge（9 类 relation/时滞/强度/方向） | 传导边可计算 | **不存在** | — | — | **FAIL** | 需新域模型 |
| IndustryProduct / CompanyIndustryPosition | 公司在链上的角色与暴露 | 无（related=板块成员共现） | — | — | **FAIL** | Peer 靠标题共现 |
| IndustryEdgeEvidence | 边引用证据可删改降级 | **不存在** | — | — | **FAIL** | — |
| 分类树浏览 | 继续可用 | ✅ | — | — | PARTIAL | 保留但不得命名为产业链 |

## 2. 产业语义（G2：节点-边-公司-证据闭环）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| Driver/Narrative/Transmission 对象 | industry_semantic 单表四类（R3），引用反查强制 | PARTIAL | 未关联 chain/segment/edge；无 contrary evidence 字段 |
| Evidence Ownership Gate（公司/产业关系+Trust+PIT） | 引用存在性校验有；**跨产业/公司归属门无** | **FAIL** | G2 新建 |
| Narrative Temperature 从已验证 Evidence 读 | 温度可复算但证据集可客户端提交 | PARTIAL | 需服务端锁定 |
| GET as_of 重放（不触发采集） | 视图读快照（无隐式写） | PARTIAL | 双 as_of 对比未验证 |
| Global Industry Position 五轴 | **固定空**（诚实置空） | **FAIL** | 资源/技术/产能/成本/政策无数据接入 |

## 3. Experience 原—炼—验—用（G3）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| 原（Report→Candidate） | from-report + claim/evidence 引用保留 | PARTIAL | — |
| 炼（Structured Revision） | 确定性提炼 + LLM 九字段（BLOCKED_EXTERNAL） | PARTIAL | preconditions/invalidators/signals 无独立字段承载 |
| 验（Case/Counterexample/History/Cross-company/Expert） | case+反例搜索+quant_expression；无历史/跨公司/专家 | PARTIAL | 验证方法面不全 |
| Confirm（Approval 需 PASS 验证 + Confirmation Gate） | 需 ≥1 验证；**未接 F7 Confirmation Gate/Audit** | PARTIAL | G3 接入 |
| 用（机器可消费规则组件） | **无输出规则组件**（卡片=标签） | **FAIL** | G5 编译承接 |
| Version Diff / 下游使用位置 | versions append-only；无 Diff 视图/使用反查 | PARTIAL | — |
| 真实 IC/ICIR/样本（INSUFFICIENT 显形） | **无**（禁量化回潮为红线，但「非量化验证指标」缺失） | PARTIAL | 以非量化指标（样本/跨度/一致性）落地 |

## 4. Workflow Studio（G4：Typed Dataflow DAG）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| Node Definition 端口/schema 声明 | 5 类可执行 kind，无 input_ports/output_ports/schema | **FAIL** | G4 新建 |
| Edge data_contract（source_port→target_port） | **Edge 不传数据**（`_node_output` 返回字符串标签；节点不消费上游输出） | **FAIL** | 已实读核实 |
| NodeInput/NodeOutput/NodeEvent/Artifact 不可变保存 | RunEvent 有；Node 级 I/O 无 | **FAIL** | — |
| 分支/合并/失败传播/重试/取消/暂停/恢复 | 拓扑执行 + 失败传播；无重试/暂停/恢复 | PARTIAL | G4 补 |
| Definition Run instrument/industry scope | run 有 instrument | PARTIAL | — |
| 图校验（孤立/不可达/端口类型/重复输出） | 环/双 output/未知 kind；无端口类型 | PARTIAL | — |

## 5. 智能选股（G5：Experience-driven）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| Experience → ScreenDefinition 编译 | **DEFAULT_RULES 常量**（has_report/thesis_direction/has_quote）——卡片内容不进规则 | **FAIL** | 已实读核实 |
| ScreenDefinition Vn（source_experience_version/universe/rules/factors/ranking/missing_policy） | 无 Definition 层 | **FAIL** | G5 新建 |
| 未批准 Experience → 4xx | 批准门在 create（§45）；无 Definition 发布门 | PARTIAL | — |
| Ranking Formula 版本化 | rank 按 score 排序（固定权重拼装） | PARTIAL | — |
| 逐规则解释/因子值/缺失项 | explanation 有；因子值无引擎 | PARTIAL | — |
| 排除计数 instrument 去重 | 已去重 | PASS | — |

## 6. Strategy Lab（G6：Executable Backtest）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| Entry/Exit/Position/Risk 可执行规则 | entry=forward_return 阈值；**exit=horizon_end 固定**；position/risk 无 | **FAIL** | 已实读核实 |
| 真实交易路径（仓位/成本/滑点/停牌/涨跌停） | **无**——对全部滚动窗口算未来收益 | **FAIL** | G6 重写回测内核 |
| 禁止重叠未来收益冒充独立样本 | 窗口重叠未处理 | **FAIL** | — |
| benchmark/超额/回撤/换手/暴露/样本数 | 超额 null（基准未接）；回撤/换手无 | **FAIL** | — |
| In-sample/Validation/OOS 分离 | 无 | **FAIL** | — |
| Regime 可复现定义 | 按退出年分域（§47 承认过轴标签粗糙） | PARTIAL | G6 修正 |
| 回测可重放 + Artifact | Artifact 已注册；参数级重放 PARTIAL | PARTIAL | — |

## 7. Strategy Monitor（G7：Strategy-aware）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| 执行所引用 Strategy 的 Entry/Exit/Risk/Invalidator | **通用 quote_move 阈值 + 新事件**，不执行策略规则 | **FAIL** | 已实读核实 |
| 状态机 DRAFT→ACTIVE↔PAUSED→RETIRED（+FAILED） | enabled 布尔 | PARTIAL | G7 改状态机 |
| pause/resume/retire/retry + Confirmation/Audit | 无独立动作 API | **FAIL** | — |
| Quote/Evidence Cursor + 幂等键 | 无 cursor（重复运行重复观察） | **FAIL** | — |
| 历史回填 vs 实时新信号区分 | 无 | **FAIL** | — |
| 同源 Signal 不作独立佐证 | 无 source_group 判定 | **FAIL** | F4 独立性服务可复用 |
| 负向信号保持负向 | 信号 kind 有区分 | PARTIAL | — |
| 失败持久化 | run 失败落事件 | PARTIAL | — |

## 8. Replay（G8：Causal）

| 能力 | 现状（代码证据） | Status | Gap |
|---|---|---|---|
| Prediction 引用 Decision/Signal/MonitorRun | **candidate 按 universe 任选**（instrument_id in universe，与 decision 无因果引用） | **FAIL** | 已实读核实 |
| Outcome 按 horizon/metric/target/PIT | validation 按方向+区间 | PARTIAL | — |
| Attribution 七类（thesis/evidence/timing/rule/execution/regime/insufficient） | 确定性归因单类 | PARTIAL | G8 扩 |
| 反馈改变**可执行** Definition | 卡片/策略版本 +1，但规则体不变（仅拾取新卡片） | **FAIL** | 已实读核实 |
| 启发式置信度（0.50+count×0.05） | 已移除（F4 归因数 basis） | PASS | — |

## 9. Research Products（G9）

| 能力 | 现状 | Status | Gap |
|---|---|---|---|
| Mainline 状态机（EMERGING→…→INVALIDATED）+ State Change | items+evidence_count 平铺 | PARTIAL | G9 补状态机 |
| Overseas Mapping 链 | 已诚实命名 Evidence Radar + missing_chain（F12） | PARTIAL | 链级接入前维持 Radar 命名 |
| Daily Brief 全节 | §10.6 全节（F12） | PASS | — |
| **Artifact/Version/PIT/Provenance** | 编译器返回临时 dict，**无 Artifact 注册** | **FAIL** | G9 关键缺口 |
| /research-products 正式路由与页面 | API 有；无独立页面（挂在研究组） | PARTIAL | — |

## 10. Thesis Center / Inbox / Memory（G10）

| 能力 | 现状 | Status | Gap |
|---|---|---|---|
| Thesis Diff（strengthened/weakened/新证据/risk 变化/reason） | lineage+修订元数据（F12）；strengthened/weakened 判定缺 | PARTIAL | — |
| Inbox Open Evidence/Open Thesis/Start Delta/携上下文 | 面板有；**/thesis 路由错误**；Commander 携上下文弱 | PARTIAL | G10 修 |
| Memory promote/retire 独立 API + 幂等 + Confirmation | promote 单端点三态推进；无 Confirmation/Audit | PARTIAL | — |
| Memory 内容版本 append-only + Diff/恢复 | version+1；无 Diff | PARTIAL | — |

## 11. 帷幄全链整合（G11）

| 能力 | 现状 | Status | Gap |
|---|---|---|---|
| 结论不前端拼装 + 引用 Artifact Version | 事件驱动（F10）；建议无 Artifact 引用 | PARTIAL | — |
| 高影响动作 Confirmation Gate | F7 已接（工具面） | PASS | — |
| INSUFFICIENT_RESEARCH_STATE 显形 | 无 | **FAIL** | G11 新增 |
| 打开产业链/主线/Experience/Strategy/Signal | workbench 20 页白名单 | PASS | — |

## 12. 长任务/并发/失败恢复（G12）

| 能力 | 现状 | Status | Gap |
|---|---|---|---|
| Workflow/Screening/Backtest/Monitor/Replay/Compile 持久化 Job | **后台跑道仅帷幄工具用**；pipeline 用 daemon thread；monitor 用 scheduler（有 lease） | PARTIAL | G12 统一跑道 |
| QUEUED/RUNNING/PAUSED/SUCCEEDED/FAILED/CANCELLED/BLOCKED_EXTERNAL | 六态有，PAUSED/BLOCKED_EXTERNAL 无 | PARTIAL | — |
| heartbeat/lease/retry/idempotency/dead-letter | lease/retry/merge 有；heartbeat/dead-letter 无 | PARTIAL | — |
| Current/Approval/Publish/Monitor 版本锁 | Current 唯一约束 + demote；Publish/Monitor 无 | PARTIAL | — |

## 13. 汇总

FAIL 核心（语义缺失）：产业链图（G1）、五轴（G2）、Experience 规则输出（G3/5）、
Typed Workflow（G4）、Screening 编译（G5）、可执行回测（G6）、策略感知监控（G7）、
因果 Replay（G8）、产品 Artifact 化（G9）。
PASS 基础设施：Evidence/PIT/Claim/Thesis/Artifact/Provenance/Confirmation Gate/
事件协议/审批门/后台跑道（保留，不重建 —— 任务书 §三.2）。

---

## 附：G0→G14 整改后的最终状态（逐模块）

| 模块 | G0 状态 | G 线整改后 | 关键证据 |
|---|---:|---:|---|
| 产业链研究 | FAIL | **PASS** | G1 六表图谱 + 传导边 + 位置（G1-MANIFEST） |
| 产业语义 | PARTIAL | **PASS** | G2 Ownership Gate/服务端温度/五轴（G2-MANIFEST） |
| 全球产业定位 | FAIL | **PASS** | G2 五轴端点（缺轴 insufficient 显形） |
| 经验提炼 | PARTIAL | **PASS** | G3 规则组件/FAIL 门/审计/Diff/指标 |
| Workflow Studio | FAIL | **PASS** | G4 端口/schema/data_contract/节点 I/O 账本 |
| 智能选股 | FAIL | **PASS** | G5 经验编译 Definition + 发布门 + PIT 运行 |
| Strategy Lab | FAIL | **PASS** | G6 事件引擎（Entry/Exit/Risk/成本/滑点/停牌） |
| Strategy Monitor | FAIL | **PASS** | G7 策略规则执行 + Cursor 幂等 + 状态机 |
| Replay | FAIL | **PASS** | G8 因果引用 + rule_error → 可执行规则修改 |
| Research Products | PARTIAL | **PASS** | G9 版本化编译 + Artifact + 页面 |
| Thesis Center/Inbox/Memory | PARTIAL | **PASS** | G10（strengthened/weakened/幂等/审计/Diff） |
| 帷幄全链 | PARTIAL | **PASS** | G11 research_state_check + 既有确认审计 |
| 长任务/恢复 | PARTIAL | **PASS** | G12 pause/resume/heartbeat/dead-letter |
| 语义测试/Golden | — | **PASS** | G13 Golden A/B/C + 否定测试矩阵 |
