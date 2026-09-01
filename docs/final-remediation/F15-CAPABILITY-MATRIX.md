# F15-CAPABILITY-MATRIX — 第三轮整改最终能力矩阵

> 阶段：F15（第三轮整改任务书 §11 F15 / §17 签署条件）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md
> 与 F1 校准矩阵逐行对照后的最终状态；每个 Final 均链接证据
> （Manifest / 测试文件 / live 记录）。

## P0 Research State 正确性

| Capability | Final | 证据 |
|---|---|---|
| Closure Truthfulness | **PASS** | F1（一致性门 exit 0：R1/R2/R3/R4/R5） |
| Thesis Revision（原子链：新快照→carry→七关系→新 Thesis→Current 切换） | **PASS** | F2 test_f2 #1-10（事务/并发/幂等）；Golden A 7b live ×2 |
| Claim Version Lineage（§5.3.4 显式字段） | **PASS** | F2 迁移 c2d3e4f5a6b7 + test_f2 #4 |
| Current Thesis 唯一选择器 | **PASS** | F2（demote 落库修复）+ test_f2 #9 |
| ClaimImpact 七关系 Apply 语义 | **PASS** | F2 test_f2 #2-7（七关系全覆盖） |
| 结构化 Claim Builder（§5.3.3） | **PASS** | F4（builder v1 + basis 落库）+ F12 lineage |

## P0 Signal

| Capability | Final | 证据 |
|---|---|---|
| Signal Production API（§6.2 契约 + §6.3 门迹） | **PASS** | F3 test_f3 8 用例；Golden A 6b live 200 ×2 |
| Instrument/Trust/Type/Entity/Negative 全门迹 | **PASS** | F3（拒绝原因逐规则落盘） |
| §6.4 七语义（减持≠整合 / 否认≠A / 停牌公告=A / T4≠A / 同业竞争=B / 跨标的隔离 / 终止≠正向A） | **PASS** | F3 test_f3 #1-7；Golden A 6a live |
| 状态机（state_transition 落结果） | **PASS** | F3（B→A 等断言） |

## P1 Integrity（§7）

| Capability | Final | 证据 |
|---|---|---|
| Confidence Migration（无解释固定值全部移除） | **PASS** | F4（9 条生产路径接线 claim_confidence_v1；grep 0 命中）；test_f4 #2 |
| Confidence Basis UI 就绪（后端透出） | **PASS** | F4（/claims 透出 level+basis）；UI 渲染随 F12 页面 |
| Source Independence（§7.2 字段+六规则+独立组裁决） | **PASS** | F4 test_f4 #3/4；迁移 d3e4f5a6b7c8 |
| Subject Swap Detection（Entity Dictionary §7.3） | **PASS** | F4 test_f4 #5/6（uncertain + reason code） |
| uncertain 机器可读 reason codes（§7.4） | **PASS** | F4（subject_entity_mismatch:<A>(type)\|<B>(type)） |

## P0-WEIWO 帷幄核心（§8）

| Capability | Final | 证据 |
|---|---|---|
| Event Protocol（§8.3 append-only/sequence/correlation/脱敏） | **PASS** | F5 test_f5 #1/4/5 |
| Snapshot → Replay → Live SSE（§8.4） | **PASS** | F5 test_f5 #2/3/6（EventSource 前端消费 F10） |
| Tool Registry（§8.5 白名单+schema+risk+幂等策略） | **PASS** | F6 test_f6 #1/2/3（13 工具） |
| Approval Gate（§8.6 状态机/digest/lease/幂等/审计） | **PASS** | F7 test_f7 #1-8 |
| Dynamic Workbench（§8.7 页面注册表/自动打开/会话独立/恢复） | **PASS** | F8 test_f8 #1-4 + 前端 3 用例 |
| Background Runway（§8.8 持久化/lease 恢复/重试/取消/合并） | **PASS** | F9 test_f9 #1-4 |
| Session Governance（§8.9 重命名/归档/概览） | **PASS** | F9 test_f9 #5 |
| 双层记忆 + 长对话压缩（§8.9） | **PASS** | F9 test_f9 #6/7 |
| Product Cards UI（§8.10 中栏卡片/左栏状态） | **PASS** | F10 event-thread.test 2 用例 + live bundle |
| 帷幄跨模块 Golden（§12.3） | **PASS** | F14 13/13 ×2 live |

## P1 观澜核心对等（§9）—— 诚实边界

| 模块 | Final | 未决（全部显形登记，不计 PASS） |
|---|---|---|
| 产业研究地图 | **PARTIAL** | 链级传导/五轴：BLOCKED_REAL_EVIDENCE |
| 研究经验卡 | **PARTIAL** | LLM 精炼：BLOCKED_EXTERNAL（ASRO_LLM_API_KEY 缺失） |
| 验证工作流 | **PARTIAL** | undo/redo、导入导出、15 类节点未接引擎；kline：BLOCKED_ENVIRONMENT |
| 智能选股 | **PARTIAL** | 因子引擎/模型评分/ScreenDefinition 版本层（登记） |
| 策略实验室 | **PARTIAL** | 回测 live：BLOCKED_ENVIRONMENT；自由装配面板（登记不迁） |
| 策略盯盘 | **PARTIAL** | K 线对位 live：BLOCKED_ENVIRONMENT；AI 研判（登记不迁） |

## P1-C 产品化（§10）

| Capability | Final | 证据 |
|---|---|---|
| Thesis Center（版本链+修订元数据+Claim lineage diff） | **PASS** | F12（diff 增强 + 前端）|
| Research Inbox（全聚合 + 行动入口） | **PASS** | F12（thesis_changes/signal_hits/predictions_due/recommended + live） |
| Research Memory 三态治理 + provenance | **PASS** | F12（candidate/active/retired + 来源/时间面板） |
| Daily Brief（§10.6 全节） | **PASS** | F12（live sections 实测） |
| Overseas 诚实命名（§10.5） | **PASS** | F12（OVERSEAS_EVIDENCE_RADAR + missing_chain×4） |
| Mainline Radar（§10.4 结构） | **PASS** | live mainline-radar items（R8 既有 + 本轮复核） |

## 回归与 Golden（§12-§13）

| 线 | Final | 证据 |
|---|---|---|
| backend 全量 459 / vitest 35 / tsc / build | **PASS** | F13-MANIFEST |
| Playwright 30/30（产品 17 + 视觉 12 + 校准记录） | **PASS** | F13-MANIFEST |
| Golden A 25/25 ×2（live，6b=200） | **PASS** | F14-R10-GOLDEN-RUN.txt |
| Golden C 帷幄闭环 13/13 ×2（live） | **PASS** | F14-WEIWO-GOLDEN-EVIDENCE.md |
| 迁移三态（空库/现有库/downgrade） | **PASS**（历史迁移 downgrade 缺陷登记） | F13-MANIFEST §迁移 |
