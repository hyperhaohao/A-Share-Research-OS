# A-Share-Research-OS（ASRO）
# Research Deep Port 验收整改任务书

> 文档性质：**验收整改 / Correctness & Closure Remediation**
>
> 当前结论：**R10 Closure 验收驳回，Research Deep Port 不得标记为 COMPLETE**
>
> 当前阶段应调整为：
>
> **Research Deep Port — Correctness & Closure Remediation**
>
> 本轮目标不是继续横向增加功能，而是修复已经发现的研究正确性、Research State、产品闭环和验收失真问题，使系统真正满足 Research OS 的能力定义。

---

# 1. 当前验收结论

当前 `R0-R10 DONE / R10-CLOSURE PASS` **不予接受**。

原因不是当前实现“没有做东西”。

相反，当前已经完成了大量真实工程实现，包括：

- Source Trust
- Extraction / Citation Integrity
- Industry Semantic Domain
- Research Product Contract
- Experience
- Research Memory
- Research Inbox
- Thesis Diff 基础框架
- Signal Ladder 基础框架
- Research Graph / Artifact Provenance
- Commander Research Loop

这些成果保留，不允许回退或推翻。

但当前验收存在明显的：

```text
Infrastructure Ready
        ↓
被解释为
Capability Complete
```

以及：

```text
API 能调用
        ↓
被解释为
Research Correctness PASS
```

的问题。

本轮整改必须解决：

> **系统不仅“能跑”，而且研究语义、Evidence→Claim→Thesis 更新关系、事件分类、研究产品和最终验收必须正确。**

---

# 2. 本轮最高原则

本轮禁止以以下方式完成整改：

1. 只修改 `STATUS.md`、Manifest 或 Closure 文档；
2. 用测试数据硬塞出 PASS；
3. 用 `count > 0` 证明研究能力完成；
4. 用“未来有数据即可运行”代替真实能力验收；
5. 用“Contract 已定义”代替 Product 已实现；
6. 用 API 已存在代替 UI / Workflow 已产品化；
7. 因真实数据暂缺而伪造 Evidence；
8. 因 LLM Key 缺失而 Mock LLM 输出；
9. 为满足黄金场景而改变研究问题本身；
10. 在没有正确修复 Domain / Service 的情况下仅调整测试。

必须遵循：

```text
Correctness
    >
Research Integrity
    >
Traceability
    >
Product Completeness
    >
Test Pass
    >
Documentation
```

测试和 Closure 必须反映实现，而不是实现迎合 Closure。

---

# 3. 整改优先级

本轮按以下优先级执行。

---

## P0-01：重写 Thesis Diff 影响分析算法

### 3.1 当前问题

当前 `_thesis_diff()` 存在严重逻辑错误。

现有逻辑近似：

```python
new_ids = 最近窗口的新 Evidence

for claim in historical_claims:
    refs = claim.evidence_refs

    stale = [
        ref
        for ref in refs
        if ref not in new_ids
    ]
```

这意味着：

> 历史 Claim 所引用的 Evidence 只要不是“最近的新 Evidence”，就可能被判为 `possibly_stale`。

因此出现：

```text
20 条 New Evidence
→ 2289 affected Claims
→ 177 affected Theses
```

这不是合理的 Research Impact Analysis。

---

## 3.2 正确目标

重构为：

```text
New Evidence
    ↓
Evidence Semantic Classification
    ↓
Entity / Event / Topic / Claim Relation Matching
    ↓
Candidate Claims
    ↓
Claim Impact Evaluation
    ├─ supports
    ├─ strengthens
    ├─ weakens
    ├─ contradicts
    ├─ supersedes
    ├─ updates
    └─ irrelevant
    ↓
Affected Claims
    ↓
Affected Theses
```

禁止继续使用：

```text
old evidence not in new evidence
=
stale
```

---

## 3.3 最低实现要求

至少建立明确的数据结构：

```text
ClaimImpact
```

建议字段：

```text
impact_id
claim_id
new_evidence_id
relation

relation:
- supports
- strengthens
- weakens
- contradicts
- supersedes
- updates
- irrelevant

reason
confidence_basis
verdict_basis
created_at
```

如果不需要独立 ORM，也必须存在结构化 Domain Model，不能只返回模糊 `possibly_stale`。

---

## 3.4 Matching 第一阶段允许确定性实现

本轮不强制必须依赖 LLM。

可以采用：

### Entity Match

```text
instrument_id
company
shareholder
group
government entity
subsidiary
industry
asset
```

### Event Match

```text
restructuring
asset_injection
equity_transfer
share_reduction
acquisition
asset_transfer
trusteeship
related_party_transaction
policy
capacity
price
```

### Keyword / normalized event rules

用于筛选 Candidate Claims。

但：

> Candidate Match ≠ Claim Impact。

最终必须至少经过 deterministic relation 判断。

---

# 4. P0-02：重构 Thesis Revision / Apply

## 4.1 当前问题

当前 Thesis Diff Apply 实际行为近似：

```text
检测到 New Evidence
      ↓
找到旧 Thesis
      ↓
复制原 supporting_claims
复制原 opposing_claims
复制原 snapshot
复制 confidence
      ↓
修改 description
      ↓
生成新 Thesis
```

这不是真正的 Research State 更新。

---

## 4.2 正确目标

必须形成：

```text
Old Snapshot
    ↓
New Evidence arrives
    ↓
New Snapshot
    ↓
Claim Impact Analysis
    ↓
New Claims / Revised Claims
    ↓
Thesis Revision
    ↓
New Thesis Version
```

---

## 4.3 New Thesis 必须满足

新 Thesis 必须明确记录：

```text
parent_thesis_id
snapshot_id
revision_reason
added_claims
removed_claims
unchanged_claims
new_supporting_claims
new_opposing_claims
changed_invalidators
changed_risks
changed_catalysts
created_at
```

如果现有 Thesis Schema 不适合，可以通过：

```text
ThesisRevision
ThesisVersion
Artifact relation
meta_json
```

实现。

但最终必须可追踪。

---

## 4.4 Current Thesis 定义

禁止继续：

```python
select(ThesisORM).first()
```

来代表当前 Thesis。

必须建立明确规则，例如：

```text
instrument
+
thesis_type
+
status = current
+
latest version
```

或：

```text
root_thesis_id
version
is_current
```

必须保证系统可以回答：

```text
哪个是当前 Thesis？
上一版是什么？
为什么变化？
新 Evidence 是什么？
新增/删除了什么 Claim？
```

---

# 5. P0-03：重做 000831 黄金场景

黄金场景保持：

> **中国稀土（000831）近期资产整合 / 重组信号研究**

不得为了测试 PASS 改成：

```text
股东减持研究
```

---

## 5.1 当前错误

当前 Golden Scenario 使用：

```text
广晟控股减持中国稀土股份
```

并将：

```text
减持 + 披露
```

定义为资产整合 B 级信号。

这是研究语义错误。

---

## 5.2 Signal Ladder 必须恢复正确业务语义

### A 级正式信号

至少覆盖：

```text
停牌筹划重大资产重组

重组预案

重组报告书

发行股份购买资产

明确资产注入方案

标的资产明确

交易对手明确

聘请独立财务顾问

专项审计

资产评估

国资审批明确推进

监管审批明确推进
```

---

### B 级前置信号

至少覆盖：

```text
集团继续收购 / 归集地方稀土资产

地方国资股权无偿划转

地方国资产权变更

央地合作明显提速

上市平台定位变化

资产证券化措辞升级

同业竞争解决由原则性转为具体方案

托管结构变化

资产租赁结构变化

关联交易结构显著变化

中国稀土与中稀有色业务边界调整

资产归属调整

重点区域出现可能为后续注入准备的资产整合动作
```

重点区域：

```text
江西
广东
湖南
广西
四川
```

---

## 5.3 必须增加 Negative Rules

以下文本不得因为关键词出现而误判为 A/B：

```text
不存在重大资产重组计划

未筹划资产重组

没有资产注入计划

公司否认资产注入

终止重大资产重组

不存在应披露未披露事项

暂未考虑资产证券化
```

---

# 6. P0-04：升级 Signal Ladder

当前：

```python
if keyword in text:
    hit
```

不得作为最终实现。

---

## 6.1 新 Rule Contract

至少调整为：

```text
SignalRule

rule_id
level
event_type

positive_patterns
negative_patterns

required_entities
required_source_trust

required_evidence_types
exclusions

state_transition

label
description
```

---

## 6.2 示例

```yaml
rule_id: restructuring_formal_launch
level: A
event_type: restructuring

positive_patterns:
  - 筹划重大资产重组
  - 重大资产重组预案
  - 发行股份购买资产

negative_patterns:
  - 不存在
  - 未筹划
  - 否认
  - 终止

required_source_trust:
  - T0_primary_disclosure

required_entities:
  - listed_company
```

---

## 6.3 每个 Signal 输出必须包含

```text
signal_id
level
rule_id
rule_name
event_type
matched_pattern
evidence_ids
source_trust
entities
reason
detected_at
```

不能只返回：

```text
level=B
rule=xxx
```

---

# 7. P0-05：Citation Verification 增加真正的 Entailment

## 7.1 当前能力

当前主要检查：

```text
support_span 是否存在于 Evidence

数字是否存在于 Evidence

Source Trust 是否允许升级
```

这些必须保留。

---

## 7.2 当前缺口

现有实现没有真正检查：

```text
Statement
是否由
support_span
语义蕴含
```

例如：

原文：

```text
公司正在筹划重大资产重组。
```

错误 Statement：

```text
公司明确否认存在重大资产重组计划。
```

只进行字符定位和数字检查不足以阻止该错误。

---

## 7.3 新 Verification Pipeline

改成：

```text
Extract
  ↓
Locate Support
  ↓
Citation Integrity Check
  ↓
Number Consistency
  ↓
Source Trust Gate
  ↓
Semantic Entailment
  ↓
accepted / rejected / uncertain
```

---

## 7.4 至少检查以下语义维度

```text
主体是否一致

正向 / 否定是否一致

时间是否一致

计划 / 已完成是否一致

可能 / 明确是否一致

数量是否一致

条件是否一致

因果是否被夸大

范围是否扩大

主体是否偷换
```

---

## 7.5 Verdict

由：

```text
accepted
rejected
```

升级为：

```text
accepted
rejected
uncertain
```

`uncertain` 不得自动进入正式 Research State。

---

# 8. P0-06：重写 Golden Test 验收口径

不得再主要依赖：

```python
count > 0
len(items) > 0
artifact exists
markdown exists
```

这些只能作为 Plumbing Test。

---

## 8.1 Golden Test 至少分四层

### Layer 1：Infrastructure

```text
API 可调用
Run completed
Artifact 创建
Graph 可达
```

### Layer 2：Research Integrity

```text
Citation 可反查

PIT 正确

Source Trust 正确

Evidence → Claim 正确
```

### Layer 3：Semantic Correctness

```text
减持 ≠ 资产整合信号

否认重组 ≠ A 级信号

终止重组 ≠ 正向 A 级信号

新增减持公告不得影响数千无关 Claims
```

### Layer 4：Research State Update

```text
New Evidence
→ New Snapshot
→ Claim Impact
→ Thesis Diff
→ New Thesis Version
```

---

# 9. P0 Golden Test 强制新增断言

至少加入以下测试。

---

## TEST-R10-SEM-01

输入：

```text
广晟控股拟减持中国稀土不超过 1%
```

断言：

```text
不得因为“减持”自动成为资产整合 A/B 信号。
```

除非以后存在专门的：

```text
ownership_structure_change
```

研究事件类型。

---

## TEST-R10-SEM-02

输入：

```text
公司不存在重大资产重组计划。
```

断言：

```text
A Signal = false
```

---

## TEST-R10-SEM-03

输入：

```text
公司正在筹划重大资产重组。
```

T0 Evidence。

断言：

```text
A Signal = true
```

---

## TEST-R10-SEM-04

输入：

```text
公司终止重大资产重组。
```

断言：

```text
不得作为“重组正式启动”信号。

必须识别为：
restructuring_terminated
```

---

## TEST-R10-DIFF-01

给系统增加一条：

```text
股东减持公告
```

断言：

```text
affected_claims
只能是和：
股东结构 / 股份供给 / 股东行为
相关的有限 Claims。

不得影响完全无关的：
盈利
稀土价格
政策
资产注入
行业供需
Claims。
```

---

## TEST-R10-DIFF-02

新增真正的资产整合 T0 Evidence。

断言：

```text
生成 New Snapshot
```

---

## TEST-R10-DIFF-03

断言新 Thesis：

```text
snapshot_id != old snapshot

parent_thesis_id = previous current thesis
```

---

## TEST-R10-DIFF-04

断言：

```text
new thesis
必须直接或通过新 Claim
引用此次 New Evidence
```

---

## TEST-R10-DIFF-05

断言：

```text
旧 Thesis 保留
新 Thesis 成为 Current
Version History 可查询
```

---

# 10. P1-01：Transmission 不得继续判 PASS

当前正确状态：

```text
Transmission Domain / API:
DONE

Transmission Real Data:
NOT VERIFIED

R3:
PARTIAL
```

---

## 10.1 要求

寻找至少一组真实 Transmission Evidence。

目标结构例如：

```text
政策 / 供给变化
       ↓
稀土供给
       ↓
稀土价格 / 加工费
       ↓
上游资源企业
       ↓
冶炼分离
       ↓
下游磁材
       ↓
公司经营影响
```

所有路径必须有真实 Evidence。

---

## 10.2 如果无法找到真实材料

允许最终标记：

```text
BLOCKED_BY_REAL_EVIDENCE
```

但：

```text
不得 PASS。
```

---

# 11. P1-02：完成三个市场级 Research Product Compiler

以下目前不能只停留在 Contract：

```text
MAINLINE_RADAR

OVERSEAS_MAPPING

DAILY_RESEARCH_BRIEF
```

---

## 11.1 Mainline Radar

必须真正生成类似：

```text
Narrative
↓
Evidence
↓
Industry Driver
↓
Transmission
↓
Industry / Company Mapping
↓
Contrary Evidence
↓
Monitor
```

不是行情涨幅榜。

---

## 11.2 Overseas Mapping

必须实现：

```text
Overseas Event
↓
Global Industry Impact
↓
China Industry Mapping
↓
A-share Company Mapping
↓
Evidence
↓
Transmission
↓
Risks
```

---

## 11.3 Daily Research Brief

必须来源于：

```text
Research Inbox
Thesis Changes
Material Evidence
Signal Ladder
Open Research Requests
Failed Collection
Upcoming Validation
```

而不是：

```text
指数上涨多少
热门股票排行
```

---

# 12. P1-03：Research Inbox 正式 UI

新增正式入口，例如：

```text
/research-inbox
```

至少展示：

```text
New Evidence

Materiality Alerts

Open Research Requests

Predictions Due

Failed Collections

Thesis Changes

Signal Ladder Hits
```

---

## 12.1 每项应支持 Handoff

例如：

```text
Open in Commander

Open Evidence

Open Thesis

Start Delta Research

Review Signal
```

---

# 13. P1-04：Research Memory UI

新增：

```text
/research-memory
```

至少支持：

```text
Candidate

Active

Retired
```

过滤：

```text
company
industry
event_playbook
research_method
known_failure
research_checklist
user_preference
```

---

## 13.1 晋升动作

UI 至少支持：

```text
candidate
→ promote
→ active

active
→ retire
```

并显示：

```text
source experience
version
scope
tags
created_at
updated_at
```

---

# 14. P1-05：建立真正的 Thesis Center

当前 Instrument Workspace 中的 Thesis Tab 保留。

另外增加真正的：

```text
Thesis Center
```

建议路径：

```text
/thesis
```

或：

```text
/thesis-center
```

---

## 14.1 至少包含

```text
Current Thesis

Current State

Confidence Basis

Supporting Claims

Opposing Claims

Evidence

Assumptions

Catalysts

Risks

Invalidators

Open Questions

Related Narratives

Related Drivers

Current Monitor Rules

Version History

Thesis Diff
```

---

## 14.2 Version History

至少展示：

```text
V1
↓
V2
↓
V3
```

每次明确：

```text
新增 Evidence

新增 Claims

删除 Claims

反方变化

Invalidator 变化

Conclusion Change

Reason
```

---

# 15. P1-06：LLM Structured Refinement 做一次真实验证

当前：

```text
Pipeline Ready
但 ASRO_LLM_API_KEY 缺失
```

不得作为“能力已验证”。

---

## 15.1 正确状态

未配置时：

```text
IMPLEMENTED
BLOCKED_BY_CONFIGURATION
```

---

## 15.2 配置可用 Key 后至少真实验证一次

输入：

```text
真实 Experience Card
```

输出九字段：

```text
observation

mechanism

preconditions

expected_outcome

counter_example

failure_conditions

applicable_scope

invalidators

research_checklist
```

---

## 15.3 必须验证

```text
LLM 没新增原始 Research State 中不存在的事实。

Original 和 Refined 双存。

Schema 验证通过。

不可追溯字段不得自动晋升 Memory。
```

---

# 16. P2-01：修复 Claim Confidence 伪精确值

禁止：

```python
confidence = 0.6
```

这种没有计算基础的固定值直接作为研究置信度。

---

## 16.1 第一阶段建议

改为：

```text
confidence_level:
- high
- medium
- low
- insufficient
```

以及：

```text
confidence_basis:

source_quality
source_count
contrary_evidence
missing_data
uncertainty
reason
```

---

## 16.2 如果保留数字

必须提供：

```text
confidence_contract
```

明确如何计算。

否则 UI 不得直接展示伪精确小数。

---

# 17. P2-02：加强 Source Trust Independence

当前：

```text
≥2 T2/T3
```

可能支持事实升级。

必须增加：

```text
Independent Source
```

约束。

不能：

```text
同一篇原稿
→ 被三家媒体转载
→ 当成 3 个独立 Source
```

至少考虑：

```text
origin_url
publisher
source_group
content_hash
original_source
```

---

# 18. 测试整改

本轮不得只补 happy-path 测试。

必须增加：

---

## Unit Test

覆盖：

```text
Thesis Impact Relation

Signal Negative Pattern

Citation Entailment

Source Independence

Current Thesis Selection

Version Chain
```

---

## Integration Test

覆盖：

```text
Evidence
→ Snapshot
→ Claim
→ Thesis

New Evidence
→ Claim Impact
→ Thesis Revision
```

---

## E2E

至少：

```text
000831 Asset Integration Golden Scenario

Research Inbox → Delta Research

Thesis Center → Version Diff

Research Memory Promote

Signal Ladder Evidence Drilldown
```

---

# 19. Golden Scenario 最终应证明什么

完成后必须可以回答：

### Q1

当前对中国稀土资产整合的结论是什么？

### Q2

当前处于：

```text
无信号
B 前置信号
A 正式信号
```

哪一级？

### Q3

为什么？

必须列：

```text
Rule
Evidence
Source Trust
Event
Entity
```

### Q4

哪些信息不是整合信号？

例如：

```text
减持
普通行情上涨
无关行业新闻
```

### Q5

新 Evidence 相对上一版 Thesis 改变了什么？

### Q6

哪些 Claims：

```text
新增
加强
削弱
冲突
失效
```

### Q7

新 Thesis 为什么成为 Current？

### Q8

上一版 Thesis 是否完整保留？

### Q9

未来重点监控什么？

### Q10

有哪些信息仍缺失？

---

# 20. Closure 状态规则

本轮必须引入更严格的状态。

禁止只使用：

```text
PASS
DONE
```

建议：

```text
NOT_STARTED

IN_PROGRESS

IMPLEMENTED

VERIFIED

BLOCKED_EXTERNAL

BLOCKED_REAL_EVIDENCE

PARTIAL

PASS

FAIL
```

---

## 20.1 定义

### IMPLEMENTED

代码已经完成。

但：

```text
没有真实运行验证。
```

---

### VERIFIED

已在真实栈中验证。

---

### BLOCKED_EXTERNAL

例如：

```text
缺 LLM API Key。
```

---

### BLOCKED_REAL_EVIDENCE

例如：

```text
Transmission 无真实 Evidence。
```

---

### PASS

只有：

```text
Implementation
+
Correctness
+
Real Verification
+
DoD
```

均满足时才允许。

---

# 21. R10 Closure 重新生成要求

当前：

```text
docs/research-deep-port/R10-CLOSURE.md
```

不得继续作为最终 Closure。

先改为：

```text
R10-CLOSURE-REJECTED.md
```

或在顶部明确：

```text
STATUS: REOPENED
```

直到本轮整改完成。

---

## 21.1 新 Closure 必须逐项区分

例如：

| Capability | Implemented | Real Verified | UI | Golden | Final |
|---|---:|---:|---:|---:|---:|
| Source Trust | PASS | PASS | PASS | PASS | PASS |
| Citation Integrity | PASS | PASS | PASS | PASS | PASS |
| Semantic Entailment | PASS | PASS | N/A | PASS | PASS |
| Transmission | PASS | PASS | PASS | PASS | PASS |
| Thesis Diff | PASS | PASS | PASS | PASS | PASS |
| Research Memory | PASS | PASS | PASS | PASS | PASS |
| Research Inbox | PASS | PASS | PASS | PASS | PASS |
| Mainline Radar | PASS | PASS | PASS | PASS | PASS |

不得再用：

```text
框架就绪
```

作为：

```text
Final PASS
```

---

# 22. 本轮禁止行为

Claude / Agent 在执行本任务期间禁止：

1. 遇到失败后修改测试以适配错误实现；
2. 删除失败测试；
3. Mock Golden Scenario；
4. 人工往数据库插入不存在的正式事实；
5. 把 API Ready 写成 Product Complete；
6. 把 UI 缺失写成非关键偏差；
7. 把真实 Evidence 缺失写成 PASS；
8. 把 Contract 定义写成 Compiler Complete；
9. 用“后续再做”同时又标记当前 Closure PASS；
10. 在 P0 未解决时新增无关功能。

---

# 23. 执行顺序

必须严格按以下顺序执行。

```text
Phase C0
验收状态回退
R10 REOPEN
        ↓
Phase C1
Thesis Diff Correctness
        ↓
Phase C2
Thesis Revision / Version Model
        ↓
Phase C3
Signal Ladder 重构
        ↓
Phase C4
Citation Semantic Entailment
        ↓
Phase C5
000831 Semantic Golden Test
        ↓
Phase C6
Transmission Real Verification
        ↓
Phase C7
Three Research Product Compilers
        ↓
Phase C8
Research Inbox UI
Research Memory UI
Thesis Center
        ↓
Phase C9
LLM Real Verification
Confidence Cleanup
        ↓
Phase C10
Full Regression
        ↓
Phase C11
Final R10 Closure
```

---

# 24. 每个 Phase 完成要求

每阶段完成后必须：

```text
1. 修改代码

2. 新增 / 修改测试

3. 运行阶段测试

4. 运行相关 Regression

5. 真实栈验证

6. 写 Manifest

7. 明确：
   DONE / PARTIAL / BLOCKED

8. 再进入下一阶段
```

禁止：

```text
一次性把所有 STATUS 打勾
最后统一补验证
```

---

# 25. 最终 Definition of Done

只有满足以下全部条件，才允许：

```text
Research Deep Port
=
COMPLETE
```

---

## Research Correctness

- [ ] Thesis Diff 不再大面积错误标记无关 Claim；
- [ ] Claim Impact 有明确 relation；
- [ ] 新 Evidence 真正进入新 Research State；
- [ ] Current Thesis 可确定；
- [ ] Thesis Version 可追踪；
- [ ] Signal Ladder 具备正向和否定规则；
- [ ] “减持”不再被错误当成资产整合 B 信号；
- [ ] Citation Verification 可识别基本语义矛盾。

---

## Research Integrity

- [ ] Evidence 可反查；
- [ ] PIT 正确；
- [ ] Source Trust 正确；
- [ ] Claim 引用真实；
- [ ] Thesis 引用真实；
- [ ] 新 Thesis 绑定正确 Snapshot；
- [ ] Memory 不冒充 Evidence；
- [ ] Playbook 不冒充事实。

---

## Research Product

- [ ] Company Deep Dive；
- [ ] Industry Deep Dive；
- [ ] Event Investigation；
- [ ] Thesis Review；
- [ ] Mainline Radar；
- [ ] Overseas Mapping；
- [ ] Daily Research Brief。

七类必须不只是 Contract。

---

## Product UX

- [ ] Research Inbox；
- [ ] Research Memory；
- [ ] Thesis Center；
- [ ] Research Graph；
- [ ] Commander；
- [ ] Evidence Drilldown；
- [ ] Thesis Diff UI。

---

## Golden Scenario

- [ ] 000831 真实 Evidence；
- [ ] A/B Signal 研究语义正确；
- [ ] Negative Event 不误判；
- [ ] New Evidence → New Snapshot；
- [ ] Claim Impact 正确；
- [ ] Thesis Revision 正确；
- [ ] Version Chain 正确；
- [ ] Report 正确；
- [ ] Monitor 正确；
- [ ] Research Graph 完整。

---

## Validation

- [ ] Backend Full Tests PASS；
- [ ] Frontend Tests PASS；
- [ ] TypeScript Build PASS；
- [ ] E2E PASS；
- [ ] Golden Semantic Tests PASS；
- [ ] Real Stack Verification PASS。

---

# 26. 最终验收原则

本轮最终验收不再问：

> 系统有没有这个 API？

而是问：

> **这个系统是否真的能够维护一个长期、可验证、可更新、不会因为错误算法而污染的 Research State？**

最终必须实现：

```text
Evidence
   ↓
Citation Verification
   ↓
Claim
   ↓
Claim Impact
   ↓
Thesis
   ↓
Thesis Revision
   ↓
Research Product
   ↓
Monitor
   ↓
New Evidence
   ↓
Research Update
```

并形成持续闭环：

```text
Research
→ Evidence
→ Thesis
→ Monitoring
→ Change
→ Revision
→ Memory
→ Better Research
```

---

# 27. 当前状态修改要求

立即将：

```text
Research Capability Deep Port R0-R10
全部 DONE
R10-CLOSURE PASS
```

修改为：

```text
Research Capability Deep Port
主体实现完成

R10 Closure:
REOPENED

Current Phase:
Correctness & Closure Remediation

Primary Blockers:
1. Thesis Diff correctness
2. Thesis revision semantics
3. Signal Ladder research semantics
4. Citation entailment
5. Golden semantic verification
6. Product/UI closure
```

直到本整改任务书全部完成，禁止再次写：

```text
PORT COMPLETE

DEEP PORT COMPLETE

R10 PASS

ALL DONE
```

---

# 28. 给执行 Agent 的最终指令

你不是来重新分析这些问题。

你需要：

> **直接检查当前仓库实现，按照本任务书持续修改、测试、运行、验证和修复。**

不要只输出整改建议。

不要完成一两个问题后停止。

普通的：

```text
编译失败
测试失败
接口错误
Migration 错误
类型错误
E2E 失败
```

都属于应自行解决的问题，不属于外部阻塞。

只有真正无法自行解决的：

```text
缺少外部 API Key

真实数据源不存在

需要用户提供账号 / 权限 / Secret

外部服务不可用
```

才允许标记 BLOCKED。

最终目标不是：

> “测试全绿”。

最终目标是：

> **让 ASRO 的 Research State 在真实研究场景中具备正确性、可解释性、可追踪性和长期演化能力。**

完成所有整改后，再重新执行一次完整 R10 验收。

最终必须重新生成：

```text
R10-EVIDENCE.md
R10-CLOSURE.md
STATUS.md
```

其中所有 PASS 都必须有真实代码、真实测试和真实运行证据支撑。

**在此之前，Research Deep Port 不得关闭。**