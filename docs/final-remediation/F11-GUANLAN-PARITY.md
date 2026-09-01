# F11-GUANLAN-PARITY — 观澜核心能力逐行为对等复审

> 阶段：F11（第三轮整改任务书 §9 P1-B / §9.7 矩阵模板）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md
> donor 固定 commit 98f1398；license=None → 全程 BEHAVIORAL ADAPTATION（不复制源码）。
> 本矩阵**不沿用** G2–G7 Manifest 的旧 PASS 结论；每行按当前代码 + 本轮
> live 实测（compose 栈 2026-09-02，见各 Evidence 列）重新裁决。
> 图例：✅ PASS · ⚠️ PARTIAL · 🚫 BLOCKED_*（不计 PASS，§13.3）· ✖️ 不迁（登记）

## 9.1 产业研究地图（河图 → Industry Research Map）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| 产业链阶段/环节/上下游 | 三视图一体（阶段列+环节 tile） | ✅ | ✅ | ✅ live: `/views/industry/SZSE:000831` chain_levels+map_id | E2E-14 | **PASS** | 本轮 curl 实测 |
| 环节详情（链外拒绝） | 环节详情 + 404 显形 | ✅ | ✅ | ✅ live: 链外 segment → `segment_not_found` | — | **PASS** | 本轮 curl 实测 |
| Driver/Transmission/Narrative | R3 语义对象 + 诚实置空 | ✅ | ✅ | ⚠️ 无真实链级证据 → 诚实置空 | — | **BLOCKED_REAL_EVIDENCE** | R3 试点 2+2 条真实引用；任务书 §9.1 允许标记 |
| 全球需求/涨价/国产替代/主题 | 全球坐标五轴 + 宏观主题 | ✅ | ✅ | ✅ live: global-macro 6 指标真实数值 | E2E-14 | **PASS**（数值层）；五轴 BLOCKED_REAL_EVIDENCE | 本轮 curl 实测 |
| 行业→公司映射 | 相关公司=东财板块成员（真实 basis） | ✅ | ✅ | ⚠️ 深度扩展 a 已接；本轮未逐标的复测 | — | **PARTIAL** | 深度扩展 a 记录 |
| PIT as-of | map/context snapshot 携 as_of | ✅ | ✅ | ✅ live: as_of 字段 | — | **PASS** | 本轮 curl 实测 |
| 地图→公司研究/Evidence/Thesis | open_with_context 回工作台 | ✅ | ✅ | E2E-14（G7 轮） | E2E-14 | **PASS** | E2E-14 |
| 帷幄自动打开携带上下文 | F8 workbench industry-map 映射 | ✅ | ✅ | ✅ ARTIFACT_PAGE_MAP（本轮代码+测试） | F8 测试 | **PASS** | test_f8_workbench |

**Final：PARTIAL**（数据面 BLOCKED_REAL_EVIDENCE：链级传导/五轴证据未接入；
任务书 §9.1 明确允许此标记组合）。

## 9.2 研究经验卡（原 → 炼 → 验 → 用）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| 原：来源报告+Claims+Evidence | 只读装配来源显形 | ✅ | ✅ | ✅ live: `/views/experience/exp_90ffe…` stages 全 | E2E-09 | **PASS** | 本轮 curl 实测 |
| 炼：机制/条件/反例/范围 | 确定性提炼 + LLM 结构化九字段 | ✅ | ✅ | ⚠️ LLM 精炼 🚫 BLOCKED_EXTERNAL（KEY 缺） | — | **PARTIAL**（LLM 面） | R6；无 KEY 422 显形 |
| 验：案例/反例/量化/裁决 | case+反例搜索+quant_expression | ✅ | ✅ | E2E-09 + 深度扩展 c | E2E-09 | **PASS** | E2E-09 |
| 用：筛选/工作流/策略/Memory/Tool | 批准门 + 全下游 CTA + F6 工具 | ✅ | ✅ | F6 工具实测（create_experience_card） | E2E-09/11/12 | **PASS** | test_f6 |
| 版本链 append-only | versions 表 + 版本号 | ✅ | ✅ | Phase J 回灌 v(n+1) | — | **PASS** | Phase J |
| Approve/Reject 确认门+审计 | 批准门（≥1 验证）+ 留档 | ✅ | ✅ | E2E-09 拦截未验证批准 | E2E-09 | **PASS** | E2E-09 |
| 量化指标来自真实 Workflow Run | 指标区 — 显形 | ✅ | ✅ | G3 真机 | — | **PASS** | PORT-G3 |
| 「未见反例」≠「不存在反例」 | 反例搜索文案锁死 | ✅ | ✅ | R6 文案断言 | — | **PASS** | R6 |

**Final：PARTIAL**（唯一缺口 = LLM 精炼 BLOCKED_EXTERNAL，显形不冒充）。

## 9.3 研究验证工作流（Workflow Studio）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| 强类型 Node/Port + DAG 校验 | 图校验矩阵（未知 kind/环/双 output→422） | ✅ | ✅ | G4 真机拦截 | — | **PASS** | PORT-G4 |
| Definition + Version append-only | workflow_definitions+versions | ✅ | ✅ | ✅ live: definitions count≥1 | — | **PASS** | 本轮 curl 实测 |
| Undo/Redo | **未实现，显式列为未完成** | ✖️ | — | — | — | **PARTIAL（登记）** | 任务书 §9.3 允许 |
| 导入/导出 | **未实现（登记）** | ✖️ | — | — | — | **PARTIAL（登记）** | 同上 |
| 逐节点事件 | RunEvent 落库可回放 | ✅ | ✅ | §37 回放 | E2E-10 | **PASS** | E2E-10 |
| 真实数据源 | 日线 Data 节点真实源 | ✅ | ✅ | 🚫 kline 断连（本机网络）→ 诚实失败显形 | E2E-10 诚实路径 | **BLOCKED_ENVIRONMENT** | F0 基线 §3 |
| 结果写回 Experience Validation | quant validation 写卡片 | ✅ | ✅ | E2E-10 完成路径（后端确定性覆盖） | — | **PASS** | E2E-10 |
| 帷幄发起/查看/取消/恢复 | F6 start_validation_workflow + F9 跑道 | ✅ | ✅ | test_f6/f9 | — | **PASS** | test_f6/test_f9 |
| 节点类型覆盖对等（donor 20 类） | 5 类可执行 + 目录诚实 | ⚠️ | ✅ | — | — | **PARTIAL** | 任务书 §9.3：不得以 Editor 闭环冒充 |

**Final：PARTIAL**（登记：undo/redo、导入导出、15 类 donor 节点未接引擎）。

## 9.4 智能选股（Screening Workbench）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| Screen Definition/Version | **待因子引擎（G5 登记）** | ✖️ | — | — | — | **PARTIAL（登记）** | 任务书 §9.4 允许 |
| 因子和条件真实执行 | 研究状态规则（has_report/thesis_direction/has_quote） | ✅ | ✅ | ✅ live: run 13 universe 全规则 | E2E-11 | **PASS**（研究状态规则面） | 本轮 curl 实测 |
| 候选 + Why Selected | 逐候选 explanation + 命中规则 | ✅ | ✅ | E2E-11 中国稀土全真实 | E2E-11 | **PASS** | E2E-11 |
| Why Not Selected | 按规则聚合排除 + 示例 | ✅ | ✅ | E2E-11 | E2E-11 | **PASS** | E2E-11 |
| 行业/市场状态 | regime 无引擎 → 不编数显形 | ✅ | ✅ | — | — | **PARTIAL（登记）** | §25 |
| 重评分与排序依据 | rank/score/factor_scores 真实 | ✅ | ✅ | E2E-11 | — | **PASS**（规则面） | E2E-11 |
| Candidate → Instrument Research/Strategy | CTA 信封（§44/§47 门） | ✅ | ✅ | E2E-12 | E2E-12 | **PASS** | E2E-12 |
| 帷幄 NL 发起 + 打开结果 | F6 run_screening + F8 自动开 Tab | ✅ | ✅ | test_f6/f8 | — | **PASS** | test_f6 |

**Final：PARTIAL**（因子引擎/模型评分缺失 = 任务书承认的 MVP 边界，显形登记）。

## 9.5 策略实验室（校场）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| 物料装配（卡片/筛选/工作流/因子） | §46 组装（筛选=池+卡片=理念+工作流=入场） | ✅ | ✅ | ✅ live: strategies version 62 真实 philosophy | E2E-12 | **PASS**（三类物料）；因子物料无引擎 | 本轮 curl 实测 |
| Entry/Exit/Risk 强类型三件套 | 政策三件套渲染+落库 | ✅ | ✅ | G6 真机 | — | **PASS** | PORT-G6 |
| Definition/Version | strategy_versions append-only | ✅ | ✅ | ✅ live version_no=62 | — | **PASS** | 本轮 curl 实测 |
| 回测真实执行 | 与工作流共用真实日线 | ✅ | ✅ | 🚫 kline 断连 → 失败显形；确定性路径后端覆盖 | — | **BLOCKED_ENVIRONMENT** | F0 基线 |
| 跨标的/跨时间/市场状态验证 | §47 全套（regime split+sensitivity） | ✅ | ✅ | 深度扩展 d | — | **PASS**（数据源恢复即全通） | 深度扩展 d |
| 版本对比 | 同名版本并排聚合 | ✅ | ✅ | G6 真机 | — | **PASS** | PORT-G6 |
| 失败案例/敏感性 | 逐标的失败显形 + 9 组合邻域 | ✅ | ✅ | 深度扩展 d | — | **PASS** | 深度扩展 d |
| Strategy → Monitor | §47 门槛 + create_monitor 信封 | ✅ | ✅ | E2E-13 | E2E-13 | **PASS** | E2E-13 |
| 帷幄创建/运行/比较/打开 | F6 assemble_strategy + F8 strategy-lab 映射 | ✅ | ✅ | test_f6/f8 | — | **PASS** | test_f6 |
| donor 自由装配面板 | **不迁（§46 后端编排替代，登记）** | ✖️ | — | — | — | **PARTIAL（登记）** | PORT-G6 |

**Final：PARTIAL**（回测 live 面 BLOCKED_ENVIRONMENT；自由装配面板登记不迁）。

## 9.6 策略盯盘（席位）

| Donor Behavior | ASRO Target | Impl | Prod | Real Verify | Golden | Final | Evidence |
|---|---|---|---|---|---|---|---|
| Observation/Signal/Decision 三分离 | 四表 + 三独立分区 | ✅ | ✅ | E2E-13 真机 | E2E-13 | **PASS** | E2E-13 |
| 策略条件真实运行 | 强类型规则（quote_move/new_event…） | ✅ | ✅ | G7 真机 | — | **PASS** | PORT-G7 |
| 信号与 K 线对位 | 证据层真实日线 + 对位标记 | ✅ | ✅ | 🚫 kline 断连时诚实 has_data=false | — | **BLOCKED_ENVIRONMENT** | F0 基线 |
| 决策时间线 + Replay | 观察→信号→决策合并回放 | ✅ | ✅ | G7 真机 | — | **PASS** | PORT-G7 |
| Scheduler/lease/失败恢复 | due_monitors + tick + **F9 lease 恢复** | ✅ | ✅ | test_f9 | — | **PASS** | test_f9 |
| 通知/人工决策门 | 决策为 Research Decision（§25）+ 事件通知（F9） | ✅ | ✅ | test_f9 事件 | — | **PASS** | test_f9 |
| 结果回灌 Memory/Experience | Phase J 全链（预测→归因→卡片 v2→策略 v2） | ✅ | ✅ | E2E-16 诚实双路径 | E2E-16 | **PASS** | E2E-16 |
| 决策置信度可解释 | F4：信号证据信任层+组数 basis（原固定 0.6 移除） | ✅ | ✅ | test_f4 全量 | — | **PASS** | F4-MANIFEST |
| 监控条件治理（创建/暂停） | DRAFT 门槛 422 显形 | ✅ | ✅ | E2E-13 | E2E-13 | **PASS** | E2E-13 |
| donor AI 研判/盘口/条件单编辑 | **不迁（LLM KEY 缺；登记）** | ✖️ | — | — | — | **PARTIAL（登记）** | PORT-G7 |
| 帷幄创建/暂停/运行/查看 | F6 create_strategy_monitor（high+确认）+ F8 Tab | ✅ | ✅ | test_f6/f8 | — | **PASS** | test_f6 |

**Final：PARTIAL**（K 线对位 live 面 BLOCKED_ENVIRONMENT；AI 研判登记不迁）。

## 汇总

| 模块 | Final | 关键缺口（全部显形登记） |
|---|---|---|
| 产业研究地图 | PARTIAL | 链级传导/五轴证据（BLOCKED_REAL_EVIDENCE） |
| 研究经验卡 | PARTIAL | LLM 精炼（BLOCKED_EXTERNAL） |
| 验证工作流 | PARTIAL | undo/redo、导入导出、15 类节点、kline（BLOCKED_ENV） |
| 智能选股 | PARTIAL | 因子引擎/模型评分/ScreenDefinition 版本层 |
| 策略实验室 | PARTIAL | 回测 live（BLOCKED_ENV）+ 自由装配面板（登记不迁） |
| 策略盯盘 | PARTIAL | K 线对位 live（BLOCKED_ENV）+ AI 研判（登记不迁） |

> 红线自检：本轮矩阵无任何「整页一个 PASS」；所有 PARTIAL/BLOCKED 均给出
> 具体行为与证据；BLOCKED_* 不计入 PASS（§13.3）。
