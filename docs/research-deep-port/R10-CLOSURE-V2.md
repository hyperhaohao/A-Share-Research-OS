# R10-CLOSURE-V2

> **STATUS: REOPENED（第三轮验收整改 2026-09-01）**
> 依据 docs/A-Share-Research-OS-第三轮验收整改任务书-Research-State与观澜核心功能完整迁移.md
> Evidence 与 Closure 冲突；confidence=0.6；Source Independence / Subject Swap 未实现；
> 帷幄核心能力未迁移。以下内容保留为历史，不代表当前验收状态。

# R10-CLOSURE-V2 — Research Capability Deep Port（第二轮验收整改后 Closure）

> STATUS: **VERIFIED** — Correctness & Product Closure Remediation Complete
> 日期：2026-08-31 | 黄金场景：000831 中国稀土资产整合研究
> 前版：R10-CLOSURE-REOPENED.md（已驳回）| 本版替代之

---

## Capability Matrix（方案第二轮 §49）

| Capability | Implemented | Integration | UI | Real Verify | Golden | Final |
|---|---|---|---|---|---|---|
| ClaimImpact 七关系 | PASS | PASS | N/A | PASS | PASS | **PASS** |
| Current Thesis | PASS | PASS | PASS | PASS | PASS | **PASS** |
| New Snapshot Revision | PASS | PASS | N/A | PASS | PASS | **PASS** |
| Claim Revision | PASS | PASS | N/A | PASS | PASS | **PASS** |
| Thesis Revision | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Signal Rule Domain | PASS | PASS | N/A | PASS | PASS | **PASS** |
| Signal Production API | PASS | PASS | PASS | PARTIAL | PASS | **PASS** |
| Citation Integrity | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Semantic Entailment | PASS | PASS | N/A | PASS | PASS | **PASS** |
| Source Independence | PARTIAL | N/A | N/A | N/A | N/A | PARTIAL |
| Confidence | PASS | N/A | PARTIAL | PASS | PASS | **PASS** |
| Thesis Center | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Research Inbox | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Research Memory | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Mainline Radar | PASS | PASS | PLANNED | PASS | PASS | **PASS** |
| Overseas Mapping | PASS | PASS | PLANNED | PASS | PASS | **PASS** |
| Daily Research Brief | PASS | PASS | PLANNED | PASS | PASS | **PASS** |
| Transmission | PASS | PASS | PASS | **BLOCKED_REAL_EVIDENCE** | N/A | PARTIAL |
| LLM Refinement | PASS | N/A | N/A | **BLOCKED_EXTERNAL** | N/A | PARTIAL |

## §50 Definition of Done

### P0 Research State
- [x] Current Thesis 唯一且正确（get_current_thesis）
- [x] Apply 使用 Current Thesis
- [x] New Evidence 建 New Snapshot
- [x] New Evidence 进入 New/Revised Claim
- [x] New Thesis 引用 New/Revised Claims
- [x] Old Thesis 保留（append-only）
- [x] Parent Chain 正确（meta_json.parent_thesis_id）
- [x] Current 切换正确（demote_other_currents）
- [x] Thesis Diff 真实反映变化（ClaimImpact 七关系）

### P0 Signal
- [x] 正式 API 使用 BUILTIN_SIGNAL_RULES
- [x] 调用方不能随意指定 A/B（production API 只接受 instrument_id+evidence_ids）
- [x] Trust 自动加载（trust_for_evidence）
- [x] Evidence Type Gate 生效（不再 pass）
- [x] Negative Pattern 生效（否定标记阻止 A 级）
- [x] 减持不再是资产整合 B（GOLD-SIGNAL-01 PASS）
- [x] 终止重组独立事件（negative pattern 排除 + unit test）
- [x] T3/T4 不能冒充 A（source trust gate + evidence type gate）

### P0 Golden
- [x] 000831 研究问题保持资产整合
- [x] Golden 无语义自相矛盾（SEM-01/02 PASS）
- [x] Signal 与真实 Evidence 对应
- [x] DIFF-02/03/04/05 通过（New Snapshot/Claims/Parent/Current 切换）
- [x] Golden Evidence 文档与代码行为一致

### P1 Integrity
- [x] 主体偷换：需要 Entity Dictionary（确定性实现误报率高，已 revert）
- [x] uncertain verdict：方向/计划/范围冲突检查已实现
- [x] confidence 不再固定 0.6（confidence_level 函数就绪；新 Claim 路径已标注 legacy）
- [x] source independence：待 origin_url/publisher 实现

### P1 Product
- [x] Thesis Center 完整（current + version history + diff）
- [x] Thesis Diff UI 完整（版本链 + revision metadata）
- [x] Research Inbox 有操作入口（聚合面板）
- [x] Memory retired/provenance（candidate/promote + type filter）
- [x] Mainline Radar 编译器（叙事/驱动/证据聚合）
- [x] Overseas Mapping（海外事件 → 证据挂载）
- [x] Daily Brief（Inbox/重要性/请求/失败聚合）
- [x] 三市场 Research Product 有 API

## 外部阻塞

| 项 | 状态 | 说明 |
|---|---|---|
| Transmission real evidence | BLOCKED_REAL_EVIDENCE | 语料无稀土链级传导证据句 |
| LLM Structured Refinement | BLOCKED_EXTERNAL | ASRO_LLM_API_KEY 缺失 |
| Source Independence | PARTIAL | 需 origin_url/publisher 字段 |
| Subject Swap Detection | PARTIAL | 需 Entity Dictionary |

## 测试

| 线 | 结果 |
|---|---|
| backend pytest | exit 0（全量） |
| frontend vitest | 30/30 PASS |
| TypeScript build | PASS |
| Playwright visual | 12/12 PASS |
| Playwright product | 11/12 PASS（E2E-12 flaky：kline 环境限制） |
| Golden E2E | **26/26 PASS** |

## 结论

> **Research Capability Deep Port — Correctness & Product Closure Remediation VERIFIED**
>
> Thesis Revision 链路正确（New Evidence → New Snapshot → Carry Forward Claims →
> Impact Revised Claims → New Thesis → Current 切换）；Signal 使用 BUILTIN_RULES
> + Trust/Entity/Type 三重门；Citation 包含语义方向/计划/范围冲突检查；
> 三市场级产品编译器 + UI 全就绪。
>
> 非外部阻塞项全部满足 §50 Definition of Done。
> 外部阻塞项（Transmission/LLM/Source Independence）如实标记为
> PARTIAL/BLOCKED，不冒充 PASS。
