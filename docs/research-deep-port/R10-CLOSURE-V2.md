# R10-CLOSURE-V2

> **STATUS: REOPENED（第三轮验收整改 2026-09-01，F1 校准后的事实矩阵）**
> 依据 docs/A-Share-Research-OS-第三轮验收整改任务书-Research-State与观澜核心功能完整迁移.md
> 本文件在 F1（Closure Truth Gate）中重写：与 R10-EVIDENCE-V2.md 逐项对齐，
> 消除「Evidence 记 FAIL、Closure 写 PASS」冲突；所有未验证项恢复为
> FAIL / PARTIAL / BLOCKED，不得折算为 PASS（任务书 §4.2）。
> 历史 VERIFIED 版本已作废（git 历史 e9a57ac），不再代表当前验收状态。
> 一致性校验：`python scripts/check_closure_consistency.py`（F1 交付）。

---

## Capability Matrix（当前事实，F1 校准；F15 结束时重估）

| Capability | Implemented | Production Integration | UI | Real Verify | Golden | Final |
|---|---|---|---|---|---|---|
| Thesis Carry-forward | PASS | PASS | N/A | PARTIAL | PARTIAL | **PARTIAL** |
| ClaimImpact 七关系 | PASS | PASS | N/A | PARTIAL | PARTIAL | **PARTIAL** |
| Current Thesis 选择器 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Thesis Revision（快照/Claim/切换） | PASS | PASS | PASS | PARTIAL | PARTIAL | **PARTIAL** |
| Signal Rule Domain（BUILTIN_RULES） | PASS | FAIL | N/A | FAIL | FAIL | **FAIL** |
| Signal Production API | PASS | **FAIL（500）** | PASS | FAIL | FAIL | **FAIL** |
| Citation Integrity | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Semantic Entailment | PASS | PARTIAL | N/A | PARTIAL | PARTIAL | **PARTIAL** |
| Source Independence | PARTIAL | FAIL | N/A | FAIL | N/A | **PARTIAL** |
| Subject Swap Detection | PARTIAL | FAIL | N/A | FAIL | N/A | **PARTIAL** |
| Confidence Migration | PARTIAL | **FAIL（固定 0.6）** | PARTIAL | FAIL | FAIL | **FAIL** |
| Closure Truthfulness | FAIL → F1 修复 | N/A | N/A | PASS | N/A | **PARTIAL** |
| Thesis Center | PARTIAL | PASS | PARTIAL | PARTIAL | N/A | **PARTIAL** |
| Research Inbox | PARTIAL | PASS | PARTIAL | PASS | N/A | **PARTIAL** |
| Research Memory | PARTIAL | PASS | PARTIAL | PASS | N/A | **PARTIAL** |
| Mainline Radar | PASS | PASS | **PLANNED** | PASS | N/A | **PARTIAL** |
| Overseas Mapping | PASS | PASS | **PLANNED** | PASS | N/A | **PARTIAL** |
| Daily Research Brief | PASS | PASS | **PLANNED** | PASS | N/A | **PARTIAL** |
| Transmission（链级传导） | PASS | N/A | N/A | **BLOCKED_REAL_EVIDENCE** | N/A | **PARTIAL** |
| LLM Structured Refinement | PASS | N/A | N/A | **BLOCKED_EXTERNAL** | N/A | **PARTIAL** |
| 帷幄 UI Shell（三栏外观） | PARTIAL | PASS | PARTIAL | PASS | N/A | **PARTIAL** |
| 帷幄 Commander Orchestration | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| 帷幄 Event Protocol / SSE | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| 帷幄 Approval Gate | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| 帷幄 Dynamic Workbench | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| 帷幄 Background Runway | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| 帷幄 Memory / Recovery | **FAIL** | FAIL | FAIL | FAIL | FAIL | **FAIL** |

FAIL/PARTIAL 行的依据（对齐 R10-EVIDENCE-V2 与 F0 基线）：

- **Signal Production API = FAIL**：Evidence 步骤 6b `status=500`；F0 基线在
  compose 栈复现 HTTP 500（根因 `InstrumentProfile.get` 误用，
  `backend/app/api/research_inbox_api.py:557`）。修复与重验在 F3。
- **Confidence Migration = FAIL**：生产 Claim 路径仍产生固定 `confidence=0.6`
  （任务书 §1.2）；旧 Closure「confidence 不再固定 0.6」的 PASS 勾选作废。
- **Source Independence = PARTIAL**：缺 `publisher / origin_url / canonical_url /
  source_group / original_source / content_hash` 等事实字段；转载同稿、同通讯社
  稿件无法判独立。F4 实现。
- **Subject Swap Detection = PARTIAL**：缺 Entity Dictionary 与关系图；
  「中国稀土集团 ≠ 中国稀土股份」词面重叠误判风险未消除。F4 实现。
- **Thesis Carry-forward / ClaimImpact / Thesis Revision = PARTIAL**：happy path
  有 Evidence（7a/7b PASS），但七关系完整消费、事务回滚、并发唯一 Current、
  幂等重提交等未验证；F0 基线另有 1 个真实测试失败
  （`test_r8_inbox.py::test_thesis_diff_detects_and_applies` CrossSnapshotError）。F2 修复与验证。
- **帷幄六项 = FAIL**：现有 AI 研究中枢只迁移了三栏外观与简化计划展示；
  无统帅 Tool Orchestration、无 append-only 事件协议与 SSE snapshot/replay/live、
  无服务端 Approval Gate、右栏为固定信息卡非 Dynamic Workbench、
  无后台任务跑道、无会话/长期记忆。F5–F10 迁移。
- **Mainline / Overseas / Brief = PARTIAL**：编译器与 API 就绪，UI 仍为 PLANNED，
  不得折算 Final PASS。

## 未决失败登记（Evidence FAIL ↔ Closure）

| Evidence 步骤 | 现象 | 修复阶段 |
|---|---|---|
| 6b Production Signal API | POST /research-inbox/signal-ladder/evaluate-evidence → 500 | F3 |
| r8 thesis-diff apply（基线新增） | CrossSnapshotError: snapshot not found | F2 |
| 生产固定 confidence=0.6 | Extraction→Claim / Diff Apply→New Claim 等路径 | F4 |
| Source Independence 字段缺失 | 无 origin_url/publisher/source_group/content_hash | F4 |
| Subject Swap 实体词典缺失 | 词面重叠即可通过，无 uncertain reason code | F4 |
| 帷幄核心六项 | 见上表 FAIL 行 | F5–F10 |

## §50 Definition of Done（F1 校准后的勾选状态）

### P0 Research State
- [x] Current Thesis 唯一且正确（get_current_thesis）
- [x] Apply 使用 Current Thesis
- [ ] New Evidence 建 New Snapshot（happy path PASS；异常路径未验证，F2）
- [ ] New Evidence 进入 New/Revised Claim（七关系 Apply 测试未补全，F2）
- [x] New Thesis 引用 New/Revised Claims
- [x] Old Thesis 保留（append-only）
- [x] Parent Chain 正确（meta_json.parent_thesis_id）
- [x] Current 切换正确（demote_other_currents）
- [ ] Thesis Diff 真实反映变化（并发/幂等/回滚测试未补全，F2）

### P0 Signal
- [x] 正式 API 使用 BUILTIN_SIGNAL_RULES（代码在，但见下条——生产链 500）
- [ ] 生产 API 可用（**500，F3 修复**）
- [ ] Trust 自动加载端到端验证（生产链 500 阻塞，F3）
- [ ] Evidence Type Gate 端到端验证（生产链 500 阻塞，F3）
- [ ] Negative Pattern 端到端验证（生产链 500 阻塞，F3）
- [x] 减持不再是资产整合 B（GOLD-SIGNAL-01 PASS，6a）
- [x] 终止重组独立事件（unit test）
- [ ] T3/T4 不能冒充 A（生产链 500 阻塞端到端验证，F3）

### P0 Golden
- [x] 000831 研究问题保持资产整合
- [x] Golden 无语义自相矛盾（SEM-01/02 PASS）
- [ ] Signal 与真实 Evidence 对应（6b 500，F3）
- [ ] DIFF-02/03/04/05 全过（r8 apply 当前失败，F2）
- [x] Golden Evidence 文档与代码行为一致

### P1 Integrity
- [ ] Subject Swap：**未实现**（需 Entity Dictionary，F4）
- [x] uncertain verdict：方向/计划/范围冲突检查已实现（主体一致性待 F4）
- [ ] confidence 不再固定 0.6（**FAIL：生产路径仍有固定 0.6，F4**）
- [ ] source independence：**未实现**（待 origin_url/publisher 字段，F4）

### P1 Product
- [x] Thesis Center 基础（current + version history + diff detail）
- [ ] Thesis Center 完整产品化（§10.1 全字段 + provenance，F12）
- [ ] Research Inbox 操作入口补全（§10.2 各类动作，F12）
- [ ] Memory 完整治理 UI（retired/provenance，F12）
- [ ] Mainline Radar / Overseas Mapping / Daily Brief UI（**PLANNED，F12**）
- [x] 三市场 Research Product 有 API

## 外部阻塞

| 项 | 状态 | 说明 |
|---|---|---|
| Transmission real evidence | BLOCKED_REAL_EVIDENCE | 语料无稀土链级传导证据句 |
| LLM Structured Refinement | BLOCKED_EXTERNAL | ASRO_LLM_API_KEY 缺失 |
| kline 日线源 | BLOCKED_ENVIRONMENT | 本机网络对东财 kline 端点断连（F0 基线 §3） |

## 测试（F0 基线，2026-09-01）

| 线 | 结果 |
|---|---|
| backend pytest | 404 collected / **403 passed / 1 FAILED**（r8 thesis-diff apply）exit 1 |
| frontend vitest | 30/30 PASS |
| TypeScript build | PASS |
| Playwright | NOT RUN（F13 全量回归执行） |
| Golden E2E | **24/25 PASS（6b FAIL：Production Signal API 500，基线复现）** |

## 结论

> **Research Capability Deep Port — Correctness & Product Closure Remediation：REOPEN**
>
> Evidence（R10-EVIDENCE-V2，24/25）与 Closure 冲突已在 F1 校准：
> 本文件不再包含任何与 Evidence 冲突的 PASS 声明；
> `python scripts/check_closure_consistency.py` exit 0 为每轮门槛。
> 修复顺序：F2 Research State → F3 Signal Production → F4 Integrity →
> F5–F10 帷幄 → F11 Parity → F12 Productization → F13–F15 回归与最终 Closure。
