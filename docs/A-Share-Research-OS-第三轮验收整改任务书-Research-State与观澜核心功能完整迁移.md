# A-Share Research OS 第三轮验收整改任务书

## Research State 正确性与观澜核心功能完整迁移

> 文档类型：可直接交给 Claude Code / Codex 持续执行的工程整改任务书  
> 编制日期：2026-09-01  
> ASRO 审查基线：`e9a57ac`  
> 观澜固定参考版本：`98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28`  
> 当前验收状态：**REJECT / REOPEN**  
> 适用仓库：`https://github.com/hyperhaohao/A-Share-Research-OS`

---

# 0. 执行总令

本任务不是继续增加页面，也不是补一轮说明文档。

本任务要求同时完成两条整改主线：

1. **Research OS 正确性闭环**：修复仍存在的 Golden 失败、固定置信度、来源独立性、主体语义校验和 Closure 失真。
2. **观澜核心功能完整迁移**：重新打开已经错误关闭的 Direct Port，首先补齐帷幄的统帅 Agent、事件流、审批门、动态 Workbench、后台任务和记忆机制，再逐项审查产业研究地图、经验卡、验证工作流、智能选股、策略实验室和策略盯盘。

执行 Agent 必须实际修改代码、运行测试、修复失败并生成可复核证据。除真实外部阻塞外，不得完成少量阶段后停止。

禁止使用以下完成口径：

- 路由存在；
- 页面能打开；
- 布局与观澜相似；
- 后端已有同名对象；
- 单元测试通过但生产 API 未接入；
- Manifest 声称完成但代码或 Golden 不支持；
- 外部阻塞被写成 PASS；
- Fixture、Mock 或手工构造数据冒充真实产品闭环；
- 将 donor 的核心行为降级成 `REFERENCE_ONLY` 后宣布迁移完成。

本轮唯一有效的完成定义是：

```text
Implementation
+ Production Integration
+ Correct Semantics
+ Real Data / Honest Empty State
+ User Workflow
+ Regression Tests
+ Golden E2E
+ Evidence
= PASS
```

---

# 1. 当前正式验收结论

当前仓库不得继续使用以下总状态：

```text
R10-CLOSURE-V2 VERIFIED
Correctness & Product Closure Remediation Complete
G0-G10 Direct Port Complete
```

原因包括但不限于：

1. `R10-EVIDENCE-V2.md` 明确记录：

   ```text
   汇总：24/25 PASS
   FAIL · 6b Production Signal API · status=500
   ```

   但 `R10-CLOSURE-V2.md` 同时宣称：

   ```text
   Golden E2E 26/26 PASS
   Signal Production API Final PASS
   STATUS VERIFIED
   ```

   这是直接的证据—Closure 冲突。

2. 新 Claim 路径仍存在：

   ```python
   confidence=0.6
   ```

   因而“confidence 不再固定 0.6”并未完成。

3. Source Independence 仍缺 `origin_url / publisher / source_group / content_hash / original_source` 等可用于判定独立性的事实字段，却在 DoD 中被勾选。

4. Subject Swap Detection 明确尚需 Entity Dictionary，却也在 DoD 中被勾选。

5. Market Research Product 的 UI 仍标记 `PLANNED`，却被写成 Final PASS。

6. 帷幄核心行为被差距矩阵降级为 `REFERENCE_ONLY`，现有 AI 研究中枢只迁移了三栏外观和简化计划展示，并未迁移全平台统帅能力。

因此必须执行：

```text
Research Deep Port Closure       REOPEN
Guanlan Direct Port Closure      REOPEN
Weiwo Core Migration             P0 FAIL
Final Product Verification       NOT READY
```

---

# 2. 审查基线与证据优先级

## 2.1 固定基线

整改开始时必须记录：

- ASRO 当前 commit SHA；
- donor 固定 commit SHA；
- Python、Node、数据库版本；
- 后端、前端、Playwright、Golden 的原始结果；
- 当前 dirty worktree；
- 外部数据源和 API Key 可用性；
- 所有已知阻塞。

不得在整改过程中切换 donor 版本后继续声称同一基线对等。

## 2.2 证据优先级

验收证据按以下顺序裁决：

```text
真实运行结果
> 自动化测试
> 生产 API 行为
> 代码实现
> Manifest
> Commit Message
> Closure 描述
```

当 Evidence 与 Closure 冲突时，以 Evidence 为准，并将 Closure 判为无效。

## 2.3 Donor 使用边界

观澜仓库无明确 LICENSE。必须遵守：

- 允许分析产品行为、交互模式、状态机和信息架构；
- 允许在 ASRO 架构上独立重写等价行为；
- 禁止复制 donor 源码、样式文件或大段实现；
- 所有新实现必须基于 ASRO 的 Evidence、PIT、Artifact、Provenance、Version 和权限体系；
- Manifest 必须写明“行为适配”，不得写成未经证明的“源码迁植”。

---

# 3. 本轮总验收矩阵

| 能力 | 当前判定 | 本轮目标 |
|---|---|---|
| Thesis Carry-forward | 基本实现，仍需状态与异常路径验证 | VERIFIED |
| ClaimImpact → Thesis 关系消费 | 基本实现，需七关系完整验证 | VERIFIED |
| Confidence Migration | FAIL，仍有固定 `0.6` | VERIFIED |
| Source Independence | PARTIAL | VERIFIED 或诚实 BLOCKED_SCHEMA |
| Subject Swap Detection | PARTIAL | VERIFIED |
| Signal Production API | Golden 记录 500 | VERIFIED |
| Signal Golden Semantics | 代码已改，真实链失败 | VERIFIED |
| Closure Truthfulness | FAIL | VERIFIED |
| 帷幄 UI Shell | PARTIAL | PASS |
| 帷幄 Commander Orchestration | FAIL | VERIFIED |
| 帷幄 Event Protocol / SSE | FAIL | VERIFIED |
| 帷幄 Approval Gate | FAIL | VERIFIED |
| 帷幄 Dynamic Workbench | FAIL | VERIFIED |
| 帷幄 Background Runway | FAIL | VERIFIED |
| 帷幄 Memory / Recovery | FAIL | VERIFIED |
| 产业研究地图（河图） | 页面级迁移，能力存在漂移 | 逐项 VERIFIED |
| 研究经验卡 | MVP，仍有关键漂移 | 逐项 VERIFIED |
| 验证工作流 | Editor MVP，执行器和类型系统不完整 | 逐项 VERIFIED |
| 智能选股 | MVP，因子/模型能力缺失 | 逐项 VERIFIED |
| 策略实验室（校场） | MVP，自由装配和风险结构不完整 | 逐项 VERIFIED |
| 策略盯盘（席位） | MVP，条件治理和统帅联动不足 | 逐项 VERIFIED |
| Thesis Center | Version Browser 增强版 | Product VERIFIED |
| Mainline / Overseas / Daily Brief | 编译器 MVP | Product VERIFIED |

---

# 4. P0-A：重新校准 Closure 与执行状态

## 4.1 目标

在继续开发前，先停止错误的 COMPLETE 状态传播。

## 4.2 必须修改

1. 将 `R10-CLOSURE-V2.md` 状态改为 `REOPENED`，或者生成明确替代它的新 Reopened 文档。
2. 将 `Golden 26/26 PASS` 修正为真实结果。
3. 所有 Capability 必须分别记录：

   - Implemented；
   - Production Integration；
   - UI；
   - Real Verify；
   - Golden；
   - Final。

4. 以下状态不得折算为 PASS：

   - `PLANNED`；
   - `PARTIAL`；
   - `BLOCKED_EXTERNAL`；
   - `BLOCKED_REAL_EVIDENCE`；
   - `BLOCKED_SCHEMA`；
   - `FLAKY`；
   - 未运行。

5. 更新项目 `PLAN.md / STATUS.md`，加入本任务 F0–F15，不得提前勾选。

## 4.3 DoD

- 文档状态与测试结果逐项一致；
- 不存在 Evidence 中 FAIL、Closure 中 PASS 的同一能力；
- 不存在 Checklist 勾选项的说明仍为“待实现”；
- CI 或本地脚本能够校验 Evidence 汇总数与 Closure 数字一致。

---

# 5. P0-B：Research State 正确性最终收口

## 5.1 Thesis Revision 目标状态

必须保持：

```text
Old Current Thesis
        ↓
New Evidence
        ↓
New PIT Snapshot
        ↓
Carry Forward Unaffected Claims
+ Revise Affected Claims
+ Add New Claims
+ Preserve Opposing Claims
        ↓
New Thesis Version
        ↓
Atomic Current Switch
```

## 5.2 必须验证的语义

| ClaimImpact | Apply 行为 |
|---|---|
| `supports` | 新证据进入 supporting evidence，Claim 仍为 supporting |
| `strengthens` | 新证据进入 supporting evidence，并记录强度变化 |
| `weakens` | 新证据进入 opposing evidence；不得悄悄保留为纯 supporting |
| `contradicts` | Claim 进入 opposing 或 disputed 状态，并记录冲突 |
| `supersedes` | 创建新 Claim Version，旧版本标记 superseded，保留 parent chain |
| `updates` | 创建或明确记录 revised Claim，不能只写 metadata |
| `irrelevant` | 不进入 Thesis，不制造 Claim |

## 5.3 必须修复或补足

1. Carry-forward 不得通过裸 `except Exception: continue` 静默丢 Claim。
2. 任一旧 Claim 重绑定失败必须：

   - 整个 revision 事务回滚；或
   - 明确失败并拒绝切换 Current Thesis。

3. 新 Claim 不得仅使用：

   ```text
   [新发现] + summary 截断
   ```

   作为最终研究陈述。必须经过类型化抽取或结构化 Claim Builder。

4. Claim Version 需要显式字段或可审计 metadata：

   - `parent_claim_id`；
   - `revision_kind`；
   - `revision_reason`；
   - `source_impact_relation`；
   - `carried_forward`；
   - `created_at`。

5. Current 切换必须在同一事务内满足：

   ```text
   新 Thesis 完整写入
   + Claim 引用完整
   + Artifact/Provenance 可生成
   + 旧 Current 降级
   + 新 Current 生效
   ```

6. 并发两个 revision 时，每个 instrument 最终只能有一个 Current Thesis。

## 5.4 必测场景

- 10 个 supporting + 3 个 opposing，新增一条 irrelevant Evidence：新 Thesis 仍为 10+3；
- 一条 supports：原 Claim 继承且增加 supporting evidence；
- 一条 contradicts：不得进入 supporting-only；
- 一条 supersedes：旧 Claim 可回溯，新 Claim 成为有效版本；
- Carry-forward 中第 N 条写入失败：Current 不得切换；
- 两个并发 revision：唯一 Current；
- 重复提交相同 Evidence：幂等，不制造无限重复 Claim。

---

# 6. P0-C：Signal Production API 与 Golden 修复

## 6.1 当前阻塞

`R10-EVIDENCE-V2.md` 已明确记录 Production Signal API 返回 500。只要该项仍失败，Signal 不能验收。

## 6.2 正式 API 契约

生产调用方只允许传：

```json
{
  "instrument_id": "SZSE:000831",
  "evidence_ids": ["ev_xxx"]
}
```

后端必须自动完成：

```text
Evidence Load
→ Instrument Ownership Gate
→ Source Trust
→ Evidence Type
→ Entity Resolution
→ Event Classification
→ BUILTIN_SIGNAL_RULES
→ Negative / State Transition Gate
→ Signal Result + Provenance
```

调用方不得传入自定义 `level / keywords / label` 决定生产 A/B。

## 6.3 必须修复

1. 定位并修复 Golden 中 `/evaluate-evidence` 的 500，加入回归测试。
2. Evidence 必须满足：

   ```text
   Evidence.instrument_id == requested instrument_id
   ```

3. `required_evidence_types` 必须真实执行。
4. Entity 不得使用 000831 专属硬编码清单；必须来自：

   - Instrument Registry；
   - 公司/集团/股东关系；
   - Evidence Extraction；
   - Entity Alias Dictionary。

5. 返回值必须包含：

   - `rule_id`；
   - `signal_level`；
   - `event_type`；
   - `matched_evidence_ids`；
   - `trust_gate`；
   - `type_gate`；
   - `entity_gate`；
   - `state_transition`；
   - `rejected_reasons`。

## 6.4 Golden 必测语义

| Evidence | 预期 |
|---|---|
| 股东减持披露 | `share_reduction`，资产整合 Signal = NONE |
| 否认筹划重大重组 | 不得为 A |
| 正式停牌筹划重组公告 | 满足 Trust、Type、Entity 后为 A |
| T4 传闻“即将注入” | 不得为 A |
| 同业竞争解决进入具体方案 | 可按内置规则评估 B |
| 其他公司重大重组公告 | 不得污染 000831 |
| 终止重大资产重组 | 独立负向事件，不得识别为正向 A |

---

# 7. P1-A：Confidence、Source Independence 与 Semantic Entailment

## 7.1 Confidence 真正迁移

禁止在生产 Claim 路径继续产生固定 `confidence=0.6`。

必须选择一种统一模型：

### 推荐模型

领域层保存：

```text
confidence_level = high | medium | low | insufficient
confidence_basis = {
  source_trust,
  corroboration,
  directness,
  semantic_consistency,
  freshness
}
```

若数据库仍需数值用于排序，数值必须由上述可解释因素计算，并明确：

- 数值不是概率；
- 计算版本可追溯；
- 不允许使用固定默认值掩盖缺失。

必须清理至少以下生产路径：

- Extraction → Claim；
- Thesis Diff Apply → New Claim；
- Replay / Prediction 的研究 Claim 创建路径；
- Strategy Monitor 中未经解释的固定置信度。

## 7.2 Source Independence

两个 Evidence 只有在来源链独立时才能计为两份 corroboration。

最低需要：

```text
publisher
origin_url
canonical_url
source_group
original_source
content_hash
published_at
```

独立性判定至少处理：

- 同一篇稿件不同站点转载；
- 同一通讯社稿件；
- 同一公告的多个镜像页；
- 标题变化但正文 hash 高相似；
- 二次报道引用同一个原始来源。

`>=2 T2/T3` 必须指 `>=2 independent source groups`，不是两行 Evidence。

## 7.3 Subject Swap Detection

必须建立实体词典与关系图，至少覆盖：

- 上市公司；
- 控股股东；
- 实际控制人；
- 集团公司；
- 子公司；
- 同行业公司；
- 监管机构；
- 地方国资主体。

Evidence：

```text
中国稀土集团正在研究资产整合方案
```

Statement：

```text
中国稀土股份正在筹划重大资产重组
```

不得仅因词面重叠而通过。

## 7.4 DoD

- 生产代码搜索不存在无解释的 Claim `confidence=0.6`；
- 两个转载源不能满足独立来源门槛；
- 主体偷换用例被拒绝或返回 uncertain；
- 每个裁决返回机器可读 reason code；
- UI 能显示“为什么是该置信度”，而不是只显示高/中/低标签。

---

# 8. P0-WEIWO：帷幄核心能力完整迁移

## 8.1 产品定义

帷幄不是三栏页面。

帷幄是 ASRO 的全局研究统帅层：用户通过一个会话入口编排研究、证据、Thesis、验证、筛选、策略、监控和报告；系统通过实时事件流展示执行过程；右侧 Workbench 根据 Artifact 自动打开真实业务页面；高风险写入经过人工确认；长任务可在后台运行并恢复。

当前 AI 研究中枢只能评为：

```text
Three-column UI Shell       PARTIAL
Commander Orchestration     FAIL
Event Stream                FAIL
Approval Gate               FAIL
Dynamic Workbench           FAIL
Background Runway           FAIL
Memory / Recovery           FAIL
```

## 8.2 禁止的伪等价

以下替代关系全部无效：

```text
Plan Step 状态行        ≠ Tool Call / Tool Result Event Chain
Artifact 链接列表       ≠ Dynamic Workbench
定时 GET 轮询           ≠ Snapshot + Replay + Live SSE
独立后台线程            ≠ Commander Background Task Runway
Research Memory 页面    ≠ Commander 会话/长期记忆
普通按钮                ≠ Server-authoritative Approval Gate
固定意图解析            ≠ 跨模块 Tool Orchestration
```

## 8.3 Commander Event Protocol

新增统一、append-only、可回放的事件协议。建议最小 Envelope：

```json
{
  "event_id": "evt_xxx",
  "session_id": "ses_xxx",
  "sequence": 42,
  "event_type": "tool_result",
  "created_at": "2026-09-01T12:00:00Z",
  "correlation_id": "corr_xxx",
  "plan_id": "plan_xxx",
  "task_id": "task_xxx",
  "status": "completed",
  "payload": {},
  "artifact_ids": ["art_xxx"],
  "provenance": {}
}
```

最低事件类型：

```text
user_message
assistant_delta
assistant_message
plan_created
plan_updated
step_started
step_updated
tool_call
tool_result
tool_error
artifact_created
workbench_open_requested
confirmation_requested
confirmation_decided
task_started
task_progress
task_completed
task_failed
memory_compacted
run_completed
run_failed
```

要求：

- 每个 Session 内 `sequence` 单调递增；
- 事件只能追加，不能覆写历史；
- Tool Call 与 Tool Result 通过 correlation 关联；
- Artifact 必须可反查产生它的事件和工具；
- 事件 payload 使用版本化 schema；
- 敏感字段不得进入明文事件日志；
- 重放事件不得重复执行副作用。

## 8.4 Snapshot → Replay → Live SSE

Command Center 必须提供真实 SSE，而不是前端轮询模拟。

建议接口：

```text
GET /api/v1/command/sessions/{session_id}/events?after_sequence=N
GET /api/v1/command/sessions/{session_id}/stream?after_sequence=N
```

连接行为：

```text
Connect
→ Session Snapshot
→ Replay after_sequence
→ Live Events
→ Heartbeat
→ Reconnect with last sequence
```

必须验证：

- 刷新页面后对话、工具链、计划、审批、任务和 Workbench 状态恢复；
- SSE 断开重连不丢事件、不重复展示；
- 同一 Session 多个连接保持一致；
- 不同 Session 严格隔离；
- 慢客户端有明确背压或截断策略；
- 事件保留和归档策略明确。

## 8.5 Tool Registry 与跨模块编排

不得使用任意函数名执行或 `eval`。建立白名单 Tool Registry，每个工具声明：

```text
name
description
input_schema
output_schema
risk_level
requires_confirmation
timeout
idempotency_policy
artifact_contract
executor
```

首批必须覆盖：

- 创建/运行研究计划；
- 搜索和打开 Evidence；
- 构建 PIT Snapshot；
- 打开 Current Thesis；
- 分析 Thesis Diff；
- 发起 Delta Research；
- 提交 Thesis Revision；
- 打开产业研究地图；
- 从报告提炼经验卡；
- 发起验证工作流；
- 发起智能选股；
- 组装策略并运行回测；
- 创建和运行策略监控；
- 生成 Mainline Radar、Overseas Mapping、Daily Brief；
- 打开指定产品页面；
- 读取/写入经治理的 Memory。

每个工具都必须返回结构化 Result，失败必须显形，不能用自然语言“已完成”替代真实结果。

## 8.6 Approval / Confirmation Gate

以下操作默认需要服务端确认门：

- 切换 Current Thesis；
- 批准/拒绝经验卡；
- 晋升 Research Memory；
- 创建、修改或启用监控；
- 启动高成本长任务；
- 导出或对外发送产物；
- 任何不可逆或高影响写操作。

状态机至少包含：

```text
pending
→ approved | rejected | expired | revoked
→ consumed
```

要求：

- 前端卡片只展示服务端真实状态；
- 确认内容带参数摘要和 digest，批准后参数不得被替换；
- 支持 lease/timeout，避免旧批准被后续请求复用；
- 重复点击幂等；
- 拒绝后不得发生副作用；
- 所有决定写入 Audit Event。

## 8.7 Dynamic Workbench 与 Handoff

右栏必须从固定信息卡重构为动态 Tab Workbench。

Artifact / Tool Result 返回受控 Handoff：

```json
{
  "page": "thesis-center",
  "route": "/thesis-center",
  "title": "中国稀土 · Thesis Diff",
  "payload": {
    "instrument_id": "SZSE:000831",
    "thesis_id": "ths_xxx",
    "snapshot_id": "snap_xxx"
  },
  "artifact_ids": ["art_xxx"],
  "open_mode": "workbench_tab"
}
```

要求：

- `page` 必须来自注册表，禁止任意 URL 注入；
- 页面收到 payload 后加载真实数据并复算；
- Artifact 自动打开对应页面，而不是只生成链接；
- 支持多个 Tab、关闭、固定、切换和恢复；
- 每个 Session 有独立 Workbench 状态；
- 可“在独立页面打开”，但不能丢失上下文；
- Workbench 操作可继续产生事件和 Artifact；
- 页面刷新后恢复 active tabs。

至少支持：

```text
Evidence Detail
Instrument Workspace
Thesis Center / Diff
Industry Research Map
Research Report
Experience Card
Workflow Run
Screening Result
Strategy Lab
Strategy Monitor
Daily Brief
```

## 8.8 Background Task Runway

长任务必须与对话解耦：

```text
Confirm
→ Background Task
→ Progress Events
→ User Continues Chatting
→ Complete / Fail / Retry
→ Notification
→ Artifact Auto-open
→ Archive
```

必须提供：

- Session 级和全局任务列表；
- 当前步骤、进度、开始时间、耗时、重试次数；
- 可取消任务的安全取消；
- Worker 重启后的 lease recovery；
- 同一昂贵任务的幂等或合并策略；
- 失败原因和恢复入口；
- 任务完成后自动进入会话事件流。

不得仅依赖 Web 进程内 daemon thread 作为生产级持久任务机制。

## 8.9 会话、记忆与压缩

必须实现：

### 会话治理

- 新建、重命名、归档；
- 状态和最后活动时间；
- 关联 Instrument / Thesis / Plan / Task；
- 每会话独立 Workbench；
- 可恢复最近执行上下文。

### 双层记忆

- Session Memory：当前目标、已确认参数、关键结论、未决问题；
- Research Memory：经过治理的长期经验、方法和来源经验。

### 长对话压缩

- 达到消息数或字符阈值后生成结构化摘要；
- 摘要保留关键实体、计划、决定、Artifact 和未决问题；
- 原始事件仍可审计；
- 摘要版本可追溯；
- Memory 注入必须在事件中披露来源，不能暗中影响结论。

## 8.10 帷幄核心 UI

中栏必须真实展示：

- User / Assistant Message；
- Plan Approval Card；
- Tool Call Card；
- Tool Result Card；
- Confirmation Card；
- Background Task Card；
- Recommendation Card；
- Artifact Card；
- Error / Retry Card。

左栏至少展示：

- 会话；
- 当前计划；
- 后台任务；
- 未处理确认；
- 最近研究上下文。

右栏为动态 Workbench，不再是固定 Artifact List。

## 8.11 帷幄 DoD

以下全部满足才能标记 PASS：

- 一句话跨至少三个 ASRO 模块形成真实计划；
- Tool Call/Result 以事件形式实时出现；
- 写操作经过真实确认门；
- 长任务期间可以继续发送新消息；
- Artifact 自动打开真实 Workbench 页面；
- 刷新后完整恢复；
- 断线重连不丢事件；
- 多会话不串线；
- 失败显形且可重试；
- 每个产物可追溯到 Evidence/PIT/Tool/Event；
- 生产链不依赖 Mock、Fixture 或手工插库。

---

# 9. P1-B：观澜其他核心能力逐项功能对等复审

不得沿用现有 G2–G7 Manifest 的“ported behaviors”直接判 PASS。必须重新建立 `Donor Behavior → ASRO Behavior → Integration → Real Verify` 矩阵。

## 9.1 产业研究地图（河图 → Industry Research Map）

必须复核：

- 产业链阶段、环节、上下游关系；
- Driver、Transmission、Narrative；
- 行业到公司的映射；
- 全球需求、涨价周期、国产替代、技术路线、主题映射；
- 环节详情和证据；
- PIT as-of；
- 从地图进入公司研究、Evidence、Thesis；
- 从帷幄自动打开并携带上下文。

当前以“没有真实边数据所以不画”为诚实空态是允许的，但不得把对应能力写成已完成。应分别标记：

```text
UI READY
DATA SOURCE MISSING
REAL VERIFY BLOCKED_REAL_EVIDENCE
Final PARTIAL
```

## 9.2 研究经验卡

必须完成“原 → 炼 → 验 → 用”：

- 原：来源报告、Claims、Evidence、PIT Snapshot；
- 炼：机制、适用条件、失效条件、反例、范围；
- 验：案例、反例搜索、量化指标、裁决；
- 用：筛选、工作流、策略、Memory、Commander Tool。

要求：

- 版本链 append-only；
- Approve/Reject 有确认门和审计；
- 量化指标必须来自真实 Workflow Run；
- “未见反例”不得展示为“不存在反例”；
- 帷幄可打开、验证、批准和使用经验卡；
- LLM 不可用时允许确定性提炼，但必须显式披露。

## 9.3 研究验证工作流

必须复核：

- 强类型 Node/Port；
- DAG 校验；
- Definition + Version；
- Undo/Redo 或明确列为未完成；
- 导入/导出；
- 逐节点事件；
- 真实数据源；
- 可重复执行；
- 结果写回 Experience Validation；
- 帷幄发起、查看、取消和恢复。

若仅有 5 类节点，而 donor 关键分析/因子/回测节点未接入，最终状态必须是 PARTIAL，不得用“Editor 核心已闭环”替代完整产品对等。

## 9.4 智能选股

必须复核：

- Screen Definition / Version；
- 因子和条件真实执行；
- 候选及 Why Selected；
- Why Not Selected；
- 行业/市场状态；
- 重评分与排序依据；
- Candidate → Instrument Research；
- Candidate → Strategy；
- 帷幄自然语言发起和打开结果。

没有因子引擎、模型评分和可配置 ScreenDefinition 时，只能称 Research-state Screening MVP。

## 9.5 策略实验室（校场）

必须复核：

- Experience Card、Screening、Workflow、Factor 等物料装配；
- Entry / Exit / Risk Policy 强类型结构；
- 策略 Definition / Version；
- 回测真实执行；
- 跨标的、跨时间、跨市场状态验证；
- 版本对比；
- 失败案例和敏感性分析；
- Strategy → Monitor；
- 帷幄创建、运行、比较、打开。

仅显示来源 chips 和回测汇总不等于完成策略装配能力。

## 9.6 策略盯盘（席位）

必须复核：

- Observation / Signal / Decision 三分离；
- 策略条件真实运行；
- 信号与 K 线对位；
- 决策时间线；
- Replay；
- Scheduler、lease、失败恢复；
- 通知和人工决策门；
- 监控结果回灌 Research Memory / Experience；
- 帷幄创建、暂停、运行、查看和复盘。

## 9.7 逐项 Parity Matrix 模板

每个模块必须提交：

| Donor Behavior | ASRO Target | Implemented | Production Integrated | Real Verify | Golden | Final | Evidence |
|---|---|---:|---:|---:|---:|---|---|
| 示例行为 | 对应 ASRO 能力 | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/PARTIAL/BLOCKED | 测试/API/截图 |

禁止整页只给一个 PASS。

---

# 10. P1-C：Thesis Center 与市场研究产品产品化

## 10.1 Thesis Center

必须展示：

- Current Thesis；
- Supporting Claims；
- Opposing Claims；
- Assumptions；
- Risks；
- Catalysts；
- Invalidators；
- Open Questions；
- Related Narratives；
- Evidence；
- Previous / Current Version；
- Added / Removed / Strengthened / Weakened Claims；
- Changed Risks / Catalysts / Invalidators；
- Revision Reason；
- Claim 与 Evidence provenance。

版本号列表加 revision metadata 仍不足以叫完整 Thesis Diff UI。

## 10.2 Research Inbox

除当前聚合项外，至少增加：

- Predictions Due；
- Thesis Changes；
- Signal Ladder Hits；
- Upcoming Validation；
- Open Evidence；
- Open Thesis；
- Start Delta Research；
- Review Signal；
- Open in Commander。

## 10.3 Research Memory

UI 必须覆盖：

- Candidate / Active / Retired；
- source experience；
- scope；
- tags；
- version；
- created_at / updated_at；
- provenance；
- promote / retire 的人工治理。

## 10.4 Mainline Radar

目标结构：

```text
Narrative
→ Evidence
→ Driver
→ Transmission
→ Industry Mapping
→ Company Mapping
→ Contrary Evidence
→ Monitor
```

## 10.5 Overseas Mapping

目标结构：

```text
Overseas Event
→ Global Industry
→ China Industry
→ A-share Company
→ Transmission Evidence
→ Risk / Opportunity
→ Monitor
```

仅按“海外/美国/欧盟/美元/关税”关键词筛选 Evidence，应命名为 Overseas Evidence Radar，不能冒充完整 Mapping。

## 10.6 Daily Brief

至少包含：

- New Evidence；
- Materiality；
- Thesis Changes；
- Signal Ladder Hits；
- Open Research Requests；
- Failed Collections；
- Upcoming Validation；
- Recommended Next Actions；
- 一键进入帷幄继续研究。

---

# 11. 实施阶段 F0–F15

## F0 — Reopen 与基线冻结

- 修正 STATUS/PLAN/Closure；
- 保存全量测试原始结果；
- 固定 ASRO/donor commit；
- 建立本任务 Manifest 目录。

## F1 — Closure Truth Gate

- 修复 Evidence/Closure 冲突；
- 增加汇总一致性校验；
- 所有未验证项恢复为 PARTIAL/BLOCKED。

## F2 — Research State Review Fix

- 修复静默丢 Claim；
- 完善 Claim version lineage；
- 补七关系 Apply 测试；
- 补事务、并发、幂等测试。

## F3 — Signal Production Fix

- 修复生产 API 500；
- 完成 Instrument/Trust/Type/Entity Gates；
- 重跑真实 Golden。

## F4 — Integrity Migration

- 移除生产固定 `confidence=0.6`；
- 实现来源独立性；
- 实现 Entity Dictionary 和主体偷换；
- 完善 uncertain reason codes。

## F5 — Weiwo Event Foundation

- Event schema；
- append-only repository；
- sequence/correlation；
- events API；
- snapshot/replay/live SSE。

## F6 — Weiwo Tool Orchestration

- Tool Registry；
- input/output schema；
- risk classification；
- 首批跨模块 tools；
- tool call/result events。

## F7 — Weiwo Approval Governance

- confirmation state machine；
- plan approval card；
- digest/lease/idempotency；
- audit events。

## F8 — Weiwo Dynamic Workbench

- page registry；
- Handoff contract；
- dynamic tabs；
- artifact auto-open；
- payload-driven real page；
- per-session persistence。

## F9 — Weiwo Background / Session / Memory

- durable background tasks；
- progress/retry/recovery；
- session governance；
- dual memory；
- long conversation compaction。

## F10 — Weiwo Product Cards 与 UI

- tool/approval/task/recommendation/artifact/error cards；
- left rail state；
- middle event thread；
- right dynamic workbench；
- accessibility/responsive states。

## F11 — Guanlan Core Parity Audit

- 产业研究地图；
- 经验卡；
- 验证工作流；
- 智能选股；
- 策略实验室；
- 策略盯盘；
- 每模块完整 Matrix 和 Review Fix。

## F12 — Research Product Productization

- Thesis Center；
- Inbox；
- Memory；
- Mainline Radar；
- Overseas Mapping；
- Daily Brief；
- 与帷幄互通。

## F13 — Full Regression

- backend 全量；
- frontend Vitest；
- TypeScript build；
- Playwright；
- migrations from empty DB and existing DB；
- concurrency / reconnect / idempotency；
- security and authorization。

## F14 — Golden E2E

- 000831 Research State Golden；
- Signal Golden；
- Weiwo cross-module Golden；
- Guanlan core product Golden；
- 真实失败路径 Golden。

## F15 — Final Evidence 与 Closure

生成：

```text
docs/final-remediation/F15-EVIDENCE.md
docs/final-remediation/F15-CAPABILITY-MATRIX.md
docs/final-remediation/F15-GUANLAN-PARITY.md
docs/final-remediation/F15-CLOSURE.md
```

只有所有非阻塞红线通过后才能写 VERIFIED。

---

# 12. Golden 场景

## 12.1 Golden A：000831 Research State

```text
Current Thesis
→ New Real Evidence
→ New PIT Snapshot
→ ClaimImpact
→ Carry Forward
→ Revised/New/Opposing Claims
→ New Thesis
→ Atomic Current Switch
→ Thesis Diff UI
```

断言：

- 旧 Thesis 仍可查询；
- 新旧 Snapshot 不同；
- 未受影响 Claims 全部保留；
- contradicts 不进入 supporting-only；
- 新 Evidence 可沿 Thesis → Claim → Evidence 反查；
- 旧 Current 降级，新 Current 唯一；
- 任一步失败则事务不产生半成品。

## 12.2 Golden B：Signal Semantics

```text
广晟/股东减持
→ share_reduction
→ asset_integration_signal = NONE
```

再使用真实资产整合 B Evidence 验证 B，并使用满足条件的正式公告验证 A。

生产 API 必须返回 2xx，不得 500。

## 12.3 Golden C：帷幄跨模块闭环

用户输入：

```text
研究中国稀土资产整合的新证据，比较当前 Thesis，
生成 Delta Research；如果需要修订 Thesis，先让我确认；
完成后提炼经验卡并建立后续信号监控。
```

必须出现：

```text
Plan Created
→ Evidence Tool Call/Result
→ PIT Snapshot
→ Thesis Diff
→ Confirmation Requested
→ User Approved
→ Thesis Revision
→ Artifact Auto-open in Workbench
→ Experience Candidate
→ Monitor Confirmation
→ Background Monitor Created
→ Final Summary + Provenance
```

同时验证：

- 用户在后台任务运行时可继续对话；
- 刷新页面后事件和 Workbench 恢复；
- 拒绝 Thesis 修订时不切换 Current；
- 第二会话不会看到第一会话的 Workbench；
- Artifact 均打开真实页面。

## 12.4 Golden D：观澜核心产品链

```text
Research Report
→ Experience Card
→ Validation Workflow
→ Screening
→ Strategy Lab
→ Backtest
→ Strategy Monitor
→ Observation / Signal / Decision
→ Replay / Memory
```

每一步都必须：

- 使用真实服务端对象；
- 有 Artifact；
- 有 Provenance；
- 可从帷幄发起或打开；
- 失败时诚实失败；
- 不依赖 localStorage 事实源。

---

# 13. 测试要求

## 13.1 后端

必须新增或补足：

- Command Event repository tests；
- sequence/concurrency tests；
- SSE replay/reconnect tests；
- Tool Registry schema/risk tests；
- Approval digest/lease/idempotency tests；
- background recovery tests；
- Workbench handoff validation tests；
- cross-instrument isolation tests；
- Claim revision transaction tests；
- source independence tests；
- subject swap tests；
- Signal Production API tests。

## 13.2 前端

必须覆盖：

- Event Thread 渲染；
- SSE reconnect；
- Tool/Result/Approval/Task cards；
- approval/reject interactions；
- dynamic Workbench tabs；
- session isolation；
- refresh recovery；
- honest empty/error/loading states；
- keyboard and accessibility basics。

## 13.3 E2E

不得只测试 DOM 是否存在。必须操作真实链路，并断言服务端状态。

失败的 Playwright 用例不得以 flaky 为由计入 PASS。若确属环境阻塞，应记录：

```text
BLOCKED_ENVIRONMENT
reproduction
scope
evidence
remaining risk
```

---

# 14. 数据库与迁移要求

若新增 Event、Approval、Task、Workbench State、Memory Summary 等表：

- 提供向前 migration；
- 空数据库可一次升级；
- 现有数据库可升级；
- migration 可重复检测；
- 索引覆盖 session/sequence/status/created_at；
- 明确事件与任务保留策略；
- 不删除用户已有研究数据；
- 不使用 destructive reset 解决 migration 问题。

---

# 15. 安全与治理

必须验证：

- Session、Artifact、Evidence、Thesis、Task 的权限边界；
- Handoff 页面白名单；
- Tool 输入 schema 校验；
- 高风险工具强制确认；
- SSE 不泄漏其他会话；
- 日志不写入 API Key 或敏感内容；
- Replay 不重新执行副作用；
- 批准 digest 防止 TOCTOU；
- 后台任务有超时和资源上限；
- LLM 输出永远不能绕过 Domain Gate。

---

# 16. 每阶段交付规范

每个 F 阶段完成后必须：

1. 更新 `PLAN.md`；
2. 更新 `STATUS.md`；
3. 生成 `Fxx-MANIFEST.md`；
4. 记录修改文件；
5. 记录运行命令和原始结果；
6. 记录仍有的 drift；
7. 提交单一主题 commit；
8. 继续下一阶段，不等待人工提示。

Manifest 必须使用：

```text
IMPLEMENTED
INTEGRATED
TESTED
REAL_VERIFIED
GOLDEN_VERIFIED
BLOCKED_*
PARTIAL
```

不得使用模糊词：

```text
基本完成
主体完成
大致可用
已支持
已就绪
```

除非后面紧跟可验证定义和证据。

---

# 17. 最终签署条件

只有同时满足以下条件才能写：

```text
FINAL REMEDIATION VERIFIED
```

条件：

- Production Signal API Golden 通过；
- Evidence 与 Closure 统计一致；
- 生产 Claim 路径不再产生无解释固定 0.6；
- Source Independence 真实实现；
- Subject Swap Detection 真实实现；
- Thesis Revision 事务、并发、幂等通过；
- 帷幄具备真实事件流、Tool Orchestration、Approval、Dynamic Workbench、Background Runway 和 Memory；
- 帷幄 Golden 跨模块闭环通过；
- 观澜其他核心模块逐行为矩阵完成；
- 所有非外部阻塞项均通过；
- 所有外部阻塞项诚实标记且不计入 PASS；
- 后端、前端、构建、Playwright、Golden 全部有原始结果；
- Closure 中每个 PASS 都能链接到代码、测试和真实证据。

任一 P0 未通过时，最终状态只能是：

```text
REOPEN
或
PARTIAL
```

---

# 18. 可直接复制给 Claude Code 的启动提示词

```text
你现在作为 A-Share Research OS 的持续执行型工程 Agent 工作。

请完整阅读：
A-Share-Research-OS-第三轮验收整改任务书-Research-State与观澜核心功能完整迁移.md

当前任务不是提出建议，而是从 F0 开始持续修改、测试、修复并提交，直到 F15。

必须遵守：

1. 先核对当前仓库 HEAD、dirty worktree、PLAN、STATUS、Closure 和真实测试结果。
2. 不覆盖用户已有修改，不使用 destructive reset。
3. 观澜固定参考 commit 为 98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28。
4. 观澜无明确 LICENSE，只能独立实现行为对等，禁止复制 donor 源码。
5. 不得以路由、页面、三栏布局或 Mock 作为迁移完成依据。
6. 每个阶段必须实际修改代码、运行测试、生成 Manifest、提交 commit，然后继续下一阶段。
7. 普通编译、测试、依赖、数据库和代码问题必须自行修复，不得因此停止。
8. 只有缺少外部凭证、真实外部数据不可得、权限被拒绝等无法自行解决的问题，才允许 BLOCKED；BLOCKED 不得写成 PASS。
9. 当前 R10-CLOSURE-V2 的 VERIFIED 状态无效，首先按 F0/F1 重新打开并校准。
10. P0-WEIWO 是本轮核心：必须实现统帅事件协议、SSE snapshot/replay/live、Tool Registry、Approval Gate、Dynamic Workbench、后台任务跑道、会话恢复和双层记忆。
11. 完成帷幄后，按逐行为矩阵重新审查产业研究地图、经验卡、验证工作流、智能选股、策略实验室和策略盯盘。
12. 不要完成一部分后等待我说“继续”。除真实外部阻塞外，持续执行到 F15。

开始前输出简短基线摘要和执行计划，随后立即执行 F0，不要只复述任务书。
```

---

# 19. 本轮最终目标

本轮不是把 ASRO 做得“更像观澜”。

最终目标是：

> 在不复制 donor 源码的前提下，将观澜成熟的研究工作台行为真正重建到 ASRO 的可信研究架构上；让帷幄成为可编排、可审批、可恢复、可追溯的全局研究统帅，让产业研究、经验、验证、筛选、策略和监控形成一条真实闭环，同时保证 Research State、Signal、Citation、Confidence 与 Source Independence 的研究语义正确。

完成后的 ASRO 应满足：

```text
观澜的产品工作流深度
+ ASRO 的 Evidence / PIT / Provenance / Version / Governance
= 可真实使用、可审计、可持续演化的 A 股智能投研操作系统
```
