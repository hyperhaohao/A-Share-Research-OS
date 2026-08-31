# A-Share Research OS（ASRO）
# Research Deep Port 第二轮验收整改任务书

> 文档性质：**正式验收整改 / Correctness & Product Closure Remediation**
>
> 适用仓库：`hyperhaohao/A-Share-Research-OS`
>
> 当前结论：**Research Deep Port 不得继续标记为 Correctness Remediation COMPLETE**
>
> 建议当前状态：
>
> ```text
> Research Deep Port
> Correctness Remediation — PARTIAL / REOPEN
> ```
>
> 本轮不是继续大规模扩功能，而是集中修复剩余的 Research State 正确性、Signal 生产集成、黄金场景语义真实性和产品闭环问题。
>
> 本文是 Claude Code 的正式持续执行任务书，不是咨询建议。除真实外部阻塞外，应持续执行、验证、修复，直至最终 Closure 满足全部验收条件。

---

# 0. 执行总指令

Claude Code 读取本文件后，必须：

```text
Inspect Current State
→ Reopen Closure
→ Fix P0 Correctness
→ Add Semantic Tests
→ Fix P1 Product Closure
→ Full Regression
→ Real Stack Verify
→ Final Reviewer
→ Regenerate Closure
```

禁止：

```text
只改文档
只改测试
用 count > 0 代替语义正确性
用 Contract Ready 代替 Product Complete
用 meta_json 记录新证据代替 Research State 真正更新
用兼容 API 绕开正式 Domain Rule
为了 Golden PASS 手工构造与研究问题无关的规则
```

本轮完成前，不得再次写：

```text
Correctness Remediation COMPLETE
R10 PASS
ALL DONE
```

---

# 1. 当前复审结论

本轮整改相比上一轮已经有明显进展，以下部分应保留并继续作为正式基础：

```text
ClaimImpact 七关系模型
SignalRule Domain
Source Trust
Citation Integrity
基础 Semantic Conflict Check
Research Product Compiler MVP
Research Inbox UI
Research Memory UI
Thesis Center 初版
Research Graph / Artifact
Experience / Memory Domain
```

但当前仍存在以下核心问题：

| 优先级 | 问题 | 当前判断 |
|---|---|---|
| P0 | Thesis Revision 仍未形成 New Evidence → New Snapshot → New Claims → New Thesis | FAIL |
| P0 | Apply 仍可能选择非 Current Thesis | FAIL |
| P0 | SignalRule Domain 与正式 API 未真正接通 | FAIL |
| P0 | Golden Scenario 仍存在“减持→B”与“减持≠整合”同时 PASS 的语义矛盾 | FAIL |
| P0 | Closure 中 DIFF-02/03/04/05 的 PASS 与实际代码不一致 | FAIL |
| P1 | Citation Semantic Entailment 仍是规则级冲突检查，不是完整主体/事件蕴含 | PARTIAL |
| P1 | Mainline Radar / Overseas Mapping / Daily Brief 仍是 MVP 编译器 | PARTIAL |
| P1 | Research Inbox 仍偏信息看板，缺 Delta Research / Open Thesis / Review Signal 动作 | PARTIAL |
| P1 | Thesis Center 更接近 Version Browser，缺完整 Thesis Diff | PARTIAL |
| P1 | Research Memory UI 缺 retired / provenance / scope / tags 等完整管理 | PARTIAL |
| P1 | `confidence=0.6` 仍存在于 Extraction → Claim 路径 | FAIL |
| P1 | Source Independence 未真正实现 | FAIL |
| 外部 | Transmission 无真实证据 | BLOCKED_REAL_EVIDENCE |
| 外部 | LLM Structured Refinement 无 API Key 实跑 | BLOCKED_EXTERNAL |

因此本轮目标不是重新设计 ASRO，而是：

> **把已经搭好的 Research OS 内核真正闭合。**

---

# 2. 本轮整改目标

最终必须实现：

```text
New Evidence
     ↓
Evidence Validation
     ↓
PIT Snapshot
     ↓
Claim Impact
     ↓
New / Revised Claim
     ↓
Current Thesis
     ↓
Thesis Revision
     ↓
New Thesis Version
     ↓
Research Product
     ↓
Monitor
     ↓
Research Inbox
     ↓
Next Delta Research
```

并保证：

```text
Signal
必须来自正式 Rule
+
真实 Evidence
+
真实 Source Trust
+
真实 Evidence Type
```

不能再由调用方自己传：

```text
level
keywords
label
```

决定正式 Research Signal。

---

# 3. 状态回退要求

立即修改：

```text
STATUS.md
PLAN.md
docs/research-deep-port/R10-CLOSURE.md
```

## 3.1 STATUS.md

将当前 `Correctness Remediation COMPLETE` 回退为：

```text
Current Phase:
Research Deep Port — Correctness & Product Closure Remediation

Status:
PARTIAL / REOPEN

P0 Blockers:
1. Thesis Revision Research State correctness
2. Current Thesis selection correctness
3. SignalRule production API integration
4. Golden Scenario semantic consistency
5. Closure evidence mismatch
```

## 3.2 R10-CLOSURE.md

顶部改为：

```text
STATUS: REOPENED
```

或者将当前版本保存为：

```text
R10-CLOSURE-REVIEWED-REOPENED.md
```

禁止保留 `Correctness Remediation COMPLETE` 作为当前最终状态。


---

# 4. P0-A：真正完成 Thesis Revision Research State

这是本轮最高优先级。

## 4.1 当前错误

当前 Apply 仍近似：

```text
Old Thesis
   ↓
copy old snapshot
copy old supporting claims
copy old opposing claims
copy old confidence
   ↓
replace description
   ↓
new Thesis row
```

同时只在：

```text
meta_json.new_evidence_ids
```

记录新 Evidence。

这不是真正的 Research State 更新。

## 4.2 正确链路

必须改为：

```text
Current Thesis
     ↓
New Evidence
     ↓
Build New PIT Snapshot
     ↓
ClaimImpact
     ↓
Classify Affected Claims
     ↓
Create / Revise Claims
     ↓
Assemble New Thesis
     ↓
Set New Thesis Current
     ↓
Demote Old Thesis
```

---

# 5. P0-A1：Current Thesis 必须唯一且可确定

禁止继续：

```python
select(ThesisORM)
.where(instrument_id == ...)
.first()
```

作为 Current Thesis。

建立统一查询：

```python
get_current_thesis(
    session,
    instrument_id,
    thesis_type=None
)
```

规则：

```text
instrument_id
+
is_current = true
+
按 revision/version 最新
```

旧数据兼容：

```text
若无 is_current：
按 created_at 最新
并记录 legacy fallback
```

同一 `instrument_id + thesis_type` 原则上只能有一个 Current Thesis。

Apply 必须在单事务中：

```text
read current
→ re-check current
→ old current=false
→ new current=true
→ commit
```

防止并发产生两个 Current Thesis。

---

# 6. P0-A2：New Evidence 必须进入 New Snapshot

当前不允许：

```text
New Thesis.snapshot_id
=
Old Thesis.snapshot_id
```

作为正常 Revision。

当：

```text
new_evidence exists
AND
suggested_action = delta_research
```

必须构建新 `EvidenceSnapshot`：

```text
Old Snapshot 可见 Evidence
+
New Eligible Evidence
```

所有 Evidence 满足：

```text
available_time <= snapshot.as_of
```

新 Thesis 必须记录：

```text
old_snapshot_id
new_snapshot_id
added_evidence_ids
as_of
```

---

# 7. P0-A3：New Evidence 必须通过 Claim 进入 Thesis

禁止把：

```text
meta_json.new_evidence_ids
```

解释成：

```text
Thesis 已经引用 New Evidence
```

真正的 Research State 链必须是：

```text
Thesis
→ Claim
→ Evidence
```

## 7.1 ClaimImpact Apply 语义

### supports

```text
Create supporting Claim
或
Add support to equivalent existing Claim
```

### strengthens

```text
保留 Existing Claim
+
追加 supporting evidence
```

### weakens

```text
保留 Claim
+
追加 opposing / weakening evidence
```

### contradicts

```text
Create Opposing Claim
或
追加 opposing evidence
```

### supersedes

```text
旧 Claim 保留
status = superseded
+
Create New Claim
```

### updates

```text
创建新版 Claim
或追加新 Evidence 并记录 revision
```

### irrelevant

```text
不得进入 affected_claims
不得进入 Thesis Revision
```

正式 Claim 不能覆盖历史。

建议增加：

```text
parent_claim_id
revision_reason
is_current
```

若暂时不新增列，可以使用 `meta_json + Artifact relation`，但必须可追踪。

---

# 8. P0-A4：Thesis Revision Contract

新 Thesis 至少保存：

```text
parent_thesis_id
root_thesis_id
is_current
revision_at
revision_reason

old_snapshot_id
snapshot_id

added_evidence_ids
added_claim_ids
removed_claim_ids
revised_claim_ids
unchanged_claim_ids

added_supporting_claims
added_opposing_claims

changed_risks
changed_catalysts
changed_invalidators

materiality_decision
```

可以采用：

```text
核心列
+
revision_meta_json
```

但必须：

```text
可查询
可展示
可进入 Graph
可测试
```

---

# 9. P0-A5：Thesis Revision API

建议正式提供：

```text
GET  /research-inbox/thesis-diff
POST /research-inbox/thesis-diff/prepare
POST /research-inbox/thesis-diff/apply
GET  /theses/current/{instrument_id}
GET  /theses/history/{instrument_id}
GET  /theses/{id}/diff/{other_id}
```

`prepare` 可选，但 Impact Analysis 与 Apply Revision 应保持边界清晰。

---

# 10. P0-A6：强制测试

### DIFF-NEW-01

```text
Current Thesis T1
Snapshot S1
+
New Evidence E2
→ New Snapshot S2 != S1
```

### DIFF-NEW-02

```text
E2 必须直接进入 New/Revised Claim 的 evidence refs
```

### DIFF-NEW-03

```text
New Thesis T2 必须引用该 New/Revised Claim
```

### DIFF-NEW-04

```text
T2.parent_thesis_id = T1
```

### DIFF-NEW-05

```text
T1.is_current = false
T2.is_current = true
```

### DIFF-NEW-06

两个并发 Apply 后：

```text
只能存在 1 Current Thesis
```

### DIFF-NEW-07

```text
share_reduction Evidence
不得修改：
earnings / policy / industry supply 等无关 Claim
```


---

# 11. P0-B：SignalRule 正式接入生产 API

当前 Domain Rule 已经改进，但正式 API 仍允许调用方自行传：

```text
ladder
keywords
level
label
```

这会绕过正式 Rule。

## 11.1 正式接口

推荐新增：

```text
POST /signal-ladder/evaluate-evidence
```

输入：

```json
{
  "instrument_id": "SZSE:000831",
  "evidence_ids": ["ev_xxx"]
}
```

后端自动：

```text
Load Evidence
↓
Load Source Trust
↓
Load Evidence Type
↓
Extract Entities
↓
Load BUILTIN_SIGNAL_RULES
↓
Evaluate
```

旧 `/signal-ladder/evaluate` 可保留，但必须标记：

```text
LEGACY / DEBUG / EXPERIMENTAL
```

不得再用于 Golden Scenario 和正式 Research Workflow。

---

# 12. P0-B1：Trust 自动加载

正式调用者不能提交“可信度”。

后端必须根据：

```text
Evidence.authority_level
+
Evidence.evidence_type
```

调用：

```text
trust_for_evidence(...)
```

计算。

---

# 13. P0-B2：Evidence Type Gate 真正实现

当前类似：

```python
if rule.required_evidence_types:
    pass
```

必须删除空实现。

例如 A 级：

```text
restructuring_formal_launch
```

要求：

```text
announcement
```

则 T3 新闻即使写“重大重组”，也不能触发 A。

---

# 14. P0-B3：Entity Gate

需要基于真实 Evidence：

```text
instrument
company
group
shareholder
regulator
asset
```

形成 Entity View。

至少要区分：

```text
中国稀土股份
中国稀土集团
中稀有色
广晟控股
国资委
```

---

# 15. P0-B4：Signal Result

正式结果增加：

```text
signal_id
level
event_type
rule_id
rule_name
matched_pattern
blocked_patterns
evidence_ids
evidence_types
source_trust
entities
state_transition
reason
detected_at
```

---

# 16. P0-B5：终止重组独立事件

`终止重大资产重组` 不应只表现为“不命中 A”。

应输出：

```text
event_type = restructuring_terminated
```

并进入：

```text
Research Inbox
Thesis Impact
Risk / Invalidator
```

---

# 17. P0-C：重做 000831 Golden Scenario

研究问题保持：

> **中国稀土近期资产整合 / 资产注入 / 同业竞争解决信号。**

禁止使用“减持”作为资产整合 B Signal 的正式 PASS。

## 17.1 正确行为

```text
广晟控股减持
↓
event_type = share_reduction
↓
asset_integration_signal = NONE
```

它可以进入 Ownership / Share Supply Research，但不能成为资产整合 B。

---

# 18. P0-C1：Golden 必须使用 BUILTIN_SIGNAL_RULES

禁止 Golden 自己传：

```text
keywords
level
label
```

必须走正式 Rule Library。

---

# 19. P0-C2：真实 B / A

尽量从真实语料寻找：

```text
资产整合
资产证券化
同业竞争解决方案
托管
资产租赁
业务边界调整
无偿划转
股权划转
集团资产归集
央地合作
```

如果没有：

```text
B = BLOCKED_REAL_EVIDENCE
```

比伪造 B 更正确。

如果当前没有真实 A：

```text
A = NONE
```

也是正确结果。

Golden 的目标不是“必须有 A/B”，而是**当前结论必须正确**。

---

# 20. P0-C3：Golden Semantic Assertions

### GOLD-SIGNAL-01

```text
减持
→ asset integration signal = NONE
```

### GOLD-SIGNAL-02

```text
不存在重大资产重组计划
→ A = NONE
```

### GOLD-SIGNAL-03

```text
筹划重大资产重组
+
T0 announcement
→ A = restructuring_formal_launch
```

### GOLD-SIGNAL-04

```text
终止重大资产重组
→ restructuring_terminated
→ 不属于 formal launch
```

### GOLD-SIGNAL-05

```text
T4 传闻“重大重组”
→ A = NONE
```

### GOLD-SIGNAL-06

```text
T3 新闻转述重组
无 T0 announcement
→ A = NONE
```

---

# 21. P0-D：Closure Evidence 必须与实现一致

最终每项必须区分：

| Capability | Implemented | Unit | Integration | Golden | Real Stack | Final |
|---|---:|---:|---:|---:|---:|---:|

禁止：

```text
Unit Test PASS
→ 直接写 Golden PASS
```

也禁止：

```text
meta 记录了 new evidence
→ 写 Thesis 引用了 new evidence
```


---

# 22. P1-A：Citation Semantic Entailment 完善

现有：

```text
方向冲突
计划/完成
范围扩大
```

应保留。

继续补：

```text
主体一致性
事件主体一致性
时间一致性
条件一致性
归属关系
```

## 22.1 主体偷换

必须阻止：

Evidence：

```text
中国稀土集团正在研究资产整合方案。
```

Statement：

```text
中国稀土股份正在筹划重大资产重组。
```

在无其他支持 Evidence 时自动 accepted。

第一阶段可采用：

```text
Organization Token Extraction
+
Instrument Mapping
+
Known Entity Dictionary
```

## 22.2 Verdict 三态

正式启用：

```text
accepted
rejected
uncertain
```

`uncertain` 不得自动 promote。

---

# 23. P1-B：Confidence 真正迁移

当前虽然已有：

```text
high
medium
low
insufficient
```

但新 Claim 路径仍不得继续写固定：

```python
confidence = 0.6
```

建议：

```text
confidence_level
confidence_basis
```

成为正式展示字段。

旧 float 可以保留兼容，但：

```text
禁止新写固定 0.6
```

Confidence Basis 至少：

```text
source_quality
supporting_source_count
contrary_evidence_count
missing_data
uncertainty
reason
```

---

# 24. P1-C：Source Independence

当前“≥2 T2/T3”还不足够。

必须识别是否同源转载。

优先复用现有 Source / Manifest，并增加或派生：

```text
publisher
origin_url
canonical_url
content_hash
source_group
original_source_id
```

以下不能计为独立来源：

```text
同 URL
同 canonical URL
同 content hash
同原始稿源
同一发布主体镜像
```

---

# 25. P1-D：Thesis Center 真正产品化

当前可视为：

```text
Thesis Version Browser v1
```

需要升级为正式 Thesis Center。

## 25.1 Current Thesis

展示：

```text
Title
Conclusion
Status
Confidence Basis
Last Reviewed
Snapshot AsOf
```

## 25.2 Claims

展示：

```text
Supporting Claims
Opposing Claims
Weakened Claims
Superseded Claims
```

点击 Claim：

```text
→ Evidence Inspector
```

## 25.3 Thesis Diff

真正展示：

```text
Added Evidence
Added Claims
Removed Claims
Strengthened Claims
Weakened Claims
Contradicted Claims
Changed Risks
Changed Catalysts
Changed Invalidators
```

## 25.4 Timeline

```text
V1
↓
V2
↓
V3 Current
```

每版展示：

```text
why changed
what changed
evidence changed
```

## 25.5 Open Questions

增加：

```text
Open Research Questions
```

并支持：

```text
Start Delta Research
```

---

# 26. P1-E：Research Inbox 变成工作入口

继续保留现有：

```text
New Evidence
Materiality
Open Requests
Failed Collections
```

新增：

```text
Predictions Due
Thesis Changes
Signal Hits
```

Actions：

```text
Open Evidence
Open Thesis
Open Event
Review Signal
Start Delta Research
Open in Commander
Resolve Request
```

---

# 27. P1-F：Research Memory UI 补全

增加：

```text
Retired
```

并展示：

```text
source_experience
source_artifacts
scope
tags
version
created_at
updated_at
```

Memory Detail：

```text
Content
Why saved
Where from
Applicable scope
Known failures
Version history
```

---

# 28. P1-G：Mainline Radar 深化

当前已有真实 Compiler，保留。

目标升级为：

```text
Narrative
↓
Supporting Evidence
↓
Driver
↓
Transmission
↓
Industry Mapping
↓
Company Mapping
↓
Contrary Evidence
↓
Monitor
```

主线必须是 Research Object，而不是 recent evidence list。

---

# 29. P1-H：Overseas Mapping 深化

当前更接近：

```text
Overseas Evidence Radar
```

目标：

```text
Overseas Event
↓
Global Impact
↓
China Industry Mapping
↓
A-share Company Mapping
↓
Transmission
↓
Risks
↓
Evidence
```

---

# 30. P1-I：Daily Research Brief 深化

至少包括：

```text
New Material Evidence
Thesis Changes
Signal Hits
Open Research Requests
Failed Collection
Upcoming Catalyst
Predictions Due
Validation Results
```

---

# 31. P1-J：Research Product UI

增加统一入口：

```text
/research-products
```

Tabs：

```text
主线雷达
海外映射
每日研究简报
```

---

# 32. 外部阻塞：Transmission

继续保持：

```text
BLOCKED_REAL_EVIDENCE
```

必须区分：

```text
Engine Implemented
UI Implemented
Real Evidence Verification Blocked
```

不得写 `Transmission Complete`。

---

# 33. 外部阻塞：LLM Structured Refinement

无 `ASRO_LLM_API_KEY` 时：

```text
IMPLEMENTED
BLOCKED_EXTERNAL
```

不得 VERIFIED。

---

# 34. 代码质量顺手修复

检查并修复：

```python
return dt if dt.tzinfo is None or True else dt
```

这类恒真逻辑。

删除未使用变量，如：

```text
old_meta
```

新实现完成后同步清理旧注释，避免代码仍声称：

```text
新 Thesis 钉在旧 Snapshot
```


---

# 35. 测试战略

最终至少四层。

## 35.1 Unit

覆盖：

```text
ClaimImpact
SignalRule
Source Trust
Source Independence
Semantic Entailment
Current Thesis Selector
Confidence
```

## 35.2 Integration

覆盖：

```text
Evidence
→ Snapshot
→ Claim
→ Thesis
```

以及：

```text
New Evidence
→ New Snapshot
→ ClaimImpact
→ Claim Revision
→ Thesis Revision
```

## 35.3 Product E2E

覆盖：

```text
Research Inbox
Thesis Center
Research Memory
Research Products
Commander
Evidence Inspector
```

## 35.4 Golden Semantic E2E

固定：

```text
000831 中国稀土资产整合
```

验证真实研究语义。

---

# 36. Golden 禁止只检查数量

不得仅：

```text
count > 0
artifact exists
markdown exists
```

必须检查：

```text
具体 Event Type
具体 Signal Level
具体 Rule
具体 Evidence
具体 Source Trust
具体 Claim relation
具体 Thesis parent
具体 Snapshot change
```

---

# 37. 黄金场景最终链

```text
Research Question
↓
Commander
↓
Event Plan
↓
Evidence Collection
↓
Source Trust
↓
Signal Evaluation
↓
Claims
↓
Current Thesis
↓
New Evidence
↓
New Snapshot
↓
ClaimImpact
↓
New/Revised Claims
↓
New Thesis
↓
Thesis Diff
↓
Research Product
↓
Monitor
↓
Research Inbox
↓
Research Memory
↓
Research Graph
```

---

# 38. 黄金场景最终十四问

系统必须真实回答：

1. 当前中国稀土资产整合结论是什么？
2. 当前有没有 A 级正式信号？
3. 当前有没有 B 级前置信号？
4. 每个信号由哪条正式 Rule 命中？
5. 每个信号对应哪些 Evidence？
6. Evidence 的 Source Trust 是什么？
7. 减持为什么不属于资产整合信号？
8. 哪些是 Confirmed Fact？
9. 哪些是 Analyst Inference？
10. 新 Evidence 相比上一版改变了哪些 Claims？
11. 新 Thesis 使用了什么新 Snapshot？
12. 新 Thesis 为什么成为 Current？
13. 哪些 Risk / Invalidator 发生变化？
14. 下一步 Monitor 什么？

---

# 39. 执行阶段

建议：

```text
F0  Reopen Closure
F1  Current Thesis Correctness
F2  New Snapshot Revision
F3  Claim Revision Apply
F4  Signal Production Integration
F5  Golden Semantic Rewrite
F6  Semantic Entailment + Confidence + Source Independence
F7  Thesis Center Full Product
F8  Inbox / Memory Closure
F9  Research Product Depth + UI
F10 Full Regression
F11 Golden Real Verify
F12 Final Closure
```

---

# 40. F0 — Reopen

完成：

```text
STATUS
PLAN
R10 Closure
```

DoD：

```text
Current Phase = REOPEN
P0 Blockers 明确
```

---

# 41. F1–F3 — Research State Correctness

必须整体完成：

```text
Current Thesis
New Snapshot
New Claims
New Thesis
Version Chain
```

不能中途宣布核心整改完成。

---

# 42. F4 — Signal Production Integration

DoD：

```text
正式 API 不接受自定义 A/B keywords
自动加载 Evidence trust/type/entities
required_evidence_types 真执行
Golden 使用 builtin rules
```

---

# 43. F5 — Golden Rewrite

DoD：

```text
减持不再 B
negative statements 不误判
真实 B 如无数据则 BLOCKED
真实 A 如无数据则 NONE
```

---

# 44. F6 — Research Integrity

DoD：

```text
主体偷换检测
uncertain verdict
confidence 不再固定 0.6
source independence
```

---

# 45. F7–F9 — Product Closure

完成：

```text
Thesis Center
Research Inbox Actions
Research Memory Complete UI
Research Product UI
Mainline/Overseas/Daily depth
```

---

# 46. F10 — Full Regression

必须：

```text
backend pytest
frontend vitest
TypeScript build
product E2E
visual E2E
```

任何失败不得写 PASS。

环境性失败：

```text
BLOCKED_EXTERNAL
```

---

# 47. F11 — Golden Real Verify

生成：

```text
docs/research-deep-port/R10-EVIDENCE-V2.md
```

每条 PASS 必须列：

```text
input
API
result
semantic assertion
artifact / id
```

---

# 48. F12 — Final Closure

生成：

```text
docs/research-deep-port/R10-CLOSURE-V2.md
```

状态只允许：

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
VERIFIED
PARTIAL
BLOCKED_EXTERNAL
BLOCKED_REAL_EVIDENCE
PASS
FAIL
```

PASS 只有：

```text
Implemented
+
Unit
+
Integration
+
Real Verify
+
DoD
```

全部满足。

---

# 49. 最终 Capability Matrix

最终必须逐项填写：

| Capability | Implemented | Integration | UI | Real Verify | Golden | Final |
|---|---:|---:|---:|---:|---:|---:|
| ClaimImpact | | | | | | |
| Current Thesis | | | | | | |
| New Snapshot Revision | | | | | | |
| Claim Revision | | | | | | |
| Thesis Revision | | | | | | |
| Signal Rule Domain | | | | | | |
| Signal Production API | | | | | | |
| Citation Integrity | | | | | | |
| Semantic Entailment | | | | | | |
| Source Independence | | | | | | |
| Confidence | | | | | | |
| Thesis Center | | | | | | |
| Research Inbox | | | | | | |
| Research Memory | | | | | | |
| Mainline Radar | | | | | | |
| Overseas Mapping | | | | | | |
| Daily Research Brief | | | | | | |
| Transmission | | | | | | |
| LLM Refinement | | | | | | |


---

# 50. 最终 Definition of Done

只有以下全部满足，才允许：

```text
Research Deep Port
Correctness Remediation
COMPLETE
```

## P0 Research State

- [ ] Current Thesis 唯一且正确；
- [ ] Apply 使用 Current Thesis；
- [ ] New Evidence 建 New Snapshot；
- [ ] New Evidence 进入 New/Revised Claim；
- [ ] New Thesis 引用 New/Revised Claims；
- [ ] Old Thesis 保留；
- [ ] Parent Chain 正确；
- [ ] Current 切换正确；
- [ ] Thesis Diff 真实反映变化。

## P0 Signal

- [ ] 正式 API 使用 BUILTIN_SIGNAL_RULES；
- [ ] 调用方不能随意指定 A/B；
- [ ] Trust 自动加载；
- [ ] Evidence Type Gate 生效；
- [ ] Negative Pattern 生效；
- [ ] 减持不再是资产整合 B；
- [ ] 终止重组独立事件；
- [ ] T3/T4 不能冒充 A。

## P0 Golden

- [ ] 000831 研究问题保持资产整合；
- [ ] Golden 无语义自相矛盾；
- [ ] Signal 与真实 Evidence 对应；
- [ ] DIFF-02/03/04/05 真正通过；
- [ ] Golden Evidence 文档与代码行为一致。

## P1 Integrity

- [ ] 主体偷换可识别；
- [ ] uncertain verdict 生效；
- [ ] confidence 不再固定 0.6；
- [ ] source independence 生效。

## P1 Product

- [ ] Thesis Center 完整；
- [ ] Thesis Diff UI 完整；
- [ ] Research Inbox 有操作入口；
- [ ] Memory retired/provenance 完整；
- [ ] Mainline Radar 深化；
- [ ] Overseas Mapping 真正形成映射；
- [ ] Daily Brief 包含 Thesis/Signal/Validation；
- [ ] 三市场 Research Product 有 UI。

## External

允许：

```text
Transmission = BLOCKED_REAL_EVIDENCE
LLM Refinement = BLOCKED_EXTERNAL
```

但最终 Closure 必须明确：

> 它们不是 PASS。

---

# 51. 禁止事项

本轮禁止：

```text
1. 修改测试来适配错误实现。
2. 删除失败语义测试。
3. Golden 手工传“减持→B”规则。
4. 用 old snapshot 做正式 Thesis Revision。
5. 用 meta new_evidence_ids 冒充 Thesis 引用了 New Evidence。
6. 用 select().first() 获取 Current Thesis。
7. 正式 Signal API 允许客户端自定义 A/B Rule。
8. required_evidence_types 留 pass。
9. T3/T4 直接触发 A。
10. count > 0 作为 Research Correctness。
11. Market Product API 存在就写 Product Complete。
12. Thesis Center 有 Version List 就写 Diff Complete。
13. confidence helper 存在就继续写 0.6。
14. 两条同源转载当作独立 T2/T3。
15. BLOCKED_REAL_EVIDENCE 写 PASS。
16. BLOCKED_EXTERNAL 写 VERIFIED。
17. P0 未完成前新增无关 Quant/Strategy 功能。
```

---

# 52. Git Checkpoint

建议每阶段一个 checkpoint：

```text
docs(remediation): reopen research closure v2
fix(thesis): current thesis selector and single-current invariant
feat(thesis): new snapshot and claim revision apply
fix(signal): wire builtin rules into production evaluation
test(golden): rewrite 000831 semantic scenario
feat(extraction): entity-aware uncertain entailment
fix(confidence): remove fixed claim confidence
feat(source): independent corroboration identity
feat(thesis-ui): full thesis diff center
feat(inbox): research actions and signal changes
feat(products): deepen market research products and UI
test(research): full regression and golden v2
docs(research): final R10 closure v2
```

---

# 53. 给 Claude Code 的启动提示词

```text
读取并严格执行：
docs/A-Share-Research-OS-第二轮验收整改任务书.md

这是正式 Correctness & Product Closure Remediation 任务。

先执行 F0：
1. 检查当前 git status / latest commit；
2. 阅读 STATUS.md / PLAN.md / 当前 R10-CLOSURE.md；
3. 将 Closure 状态回退为 REOPEN；
4. 注册 P0 Blockers；
5. 跑 backend/frontend 当前基线；
6. Git checkpoint。

然后按 F1 → F12 连续执行。

本轮最高优先级：
P0-1 Current Thesis / New Snapshot / New Claim / New Thesis Research State Correctness
P0-2 SignalRule 正式生产 API 集成
P0-3 000831 Golden Scenario 研究语义修正
P0-4 Closure Evidence 与真实实现一致

明确禁止：
- 用 meta_json.new_evidence_ids 代替 Thesis 真正引用 New Evidence；
- 用 old snapshot 创建正式 Revision；
- 用 select().first() 代表 Current Thesis；
- 正式 Signal API 允许调用方自己传 A/B keywords；
- Golden 用“减持→B”凑资产整合链；
- 修改测试来迎合错误实现；
- Contract Ready 写成 Product Complete；
- BLOCKED 项写成 PASS。

每阶段执行：
Implement
→ Unit Test
→ Integration Test
→ Real Stack Verify
→ Fix
→ Manifest
→ Git Checkpoint

最终重新生成：
docs/research-deep-port/R10-EVIDENCE-V2.md
docs/research-deep-port/R10-CLOSURE-V2.md

只有全部非外部阻塞的 DoD 真正满足，才允许把：
Correctness Remediation
标记 COMPLETE。
```

---

# 54. 最终架构目标

```text
                       Research Commander
                              │
                ┌─────────────┼─────────────┐
                ↓             ↓             ↓
             Company       Industry        Event
                │             │             │
                └─────────────┼─────────────┘
                              ↓
                         Evidence Layer
                              ↓
                    Citation / Trust Gate
                              ↓
                         PIT Snapshot
                              ↓
                            Claim
                              ↓
                         ClaimImpact
                              ↓
                     Current Thesis
                              ↓
                        Thesis Diff
                              ↓
                     New Thesis Version
                              ↓
                     Research Products
                              ↓
                          Monitoring
                              ↓
                       Research Inbox
                              ↓
                       Delta Research
                              ↓
                      Experience / Memory
                              │
                              └────→ 下一轮研究
```

最终原则：

> **ASRO 的竞争力不在于 Agent 数量，也不在于页面数量。**
>
> 真正核心是：
>
> **每一条新 Evidence 都能被正确判断它影响什么、为什么影响、如何改变 Claim、如何改变 Thesis，并且整个变化过程可以被回溯、验证和持续研究。**
>
> 当前项目已经非常接近这个方向，但剩余的 P0 Research State 与 Signal Integration 问题必须真正修完，才能宣布 Research Deep Port 完成。
