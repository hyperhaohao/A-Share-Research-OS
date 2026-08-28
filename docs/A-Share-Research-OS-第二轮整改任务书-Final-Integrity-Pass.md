# A-Share Research OS 第二轮整改任务书
# Final Integrity Pass

> 适用仓库：
>
> `https://github.com/hyperhaohao/A-Share-Research-OS.git`
>
> 本文档用于 Claude Code / Coding Agent 直接执行第二轮整改。
>
> 本轮不是再次重构 R0–R5，也不是扩展大量新功能。
>
> 目标只有一个：
>
> > **修复当前已经存在但尚未真正闭合的关键调用链，让项目从“Research OS Beta”进入“可长期真实试用”的状态。**

---

# 1. 执行原则

本轮整改必须：

```text
保留现有有效实现
>
修复真实逻辑问题
>
补齐缺失调用链
>
重新验证
>
统一状态
```

禁止：

```text
重新设计一套新架构
大范围推翻现有 Source / Evidence / Pipeline / UI
继续堆新的空 Milestone
因为已有测试通过就忽略真实业务链
用文档修饰替代真实代码整改
```

开始前必须读取：

```text
TASK.md
AGENTS.md
CLAUDE.md
PLAN.md
STATUS.md
ROADMAP.md
REMEDIATION.md
README.md
A-Share-Research-OS-整改实施任务书.md
```

并执行：

```bash
pwd
git status
git log --oneline -10
```

确认当前正式仓库：

```text
hyperhaohao/A-Share-Research-OS
```

---

# 2. 当前整体结论

当前系统相比首轮整改前已经有明显实质提升：

```text
多 Source
→ Evidence
→ PIT Snapshot
→ 多 Analyst
→ Claims
→ Thesis
→ Debate
→ Valuation
→ Scenario
→ Risk
→ Report
```

同时已经具备：

```text
LLMProvider
Quant
Scheduler Worker
React Flow Research Graph
九 Tab Workspace
Copilot
Revision UI
Live Research E2E
Docker Compose
Backup / Restore
```

因此：

> **本轮不推倒重来。**

当前主要问题已经从“系统缺失能力”转变为：

> **关键业务链中仍有部分调用顺序错误、分支未闭环、功能存在但未真正接主流程，以及状态文件再次失真。**

---

# 3. 本轮整改阶段

本轮只设置 4 个阶段：

```text
F0 — Pipeline Integrity
F1 — Research Integration
F2 — Product Integrity
F3 — Final Verification
```

不再增加 M30 / M31 / R6 / R7 等长期编号。

---

# 4. F0 — Pipeline Integrity

## 4.1 修复 Continuous Research FULL 分支

### 当前问题

当前：

```text
MONITOR
→ MaterialityJudge
```

可以产生：

```text
NO_MATERIAL_CHANGE
DELTA_RESEARCH
FULL_RESEARCH
```

但是：

```text
FULL_RESEARCH
```

在 `run_monitor_task()` 中没有真正调用完整 `ResearchPipeline`。

同时：

```text
TaskType.PERIODIC_FULL_RESEARCH
```

目前仍绑定旧的：

```text
run_periodic_full_research()
```

而该函数只执行：

```text
market_data
→ snapshot
→ report
```

不是完整研究。

### 必须整改

最终统一为：

```text
FULL_RESEARCH
→ ResearchPipeline.run()
```

以及：

```text
PERIODIC_FULL_RESEARCH
→ ResearchPipeline.run()
```

推荐最终业务函数：

```python
def run_full_research_task(session, task):
    ResearchPipeline(session).run(task.instrument_id)
```

HANDLERS：

```python
HANDLERS = {
    TaskType.MONITOR: run_monitor_task,
    TaskType.PERIODIC_FULL_RESEARCH: run_full_research_task,
    TaskType.PREDICTION_VALIDATION: run_prediction_validation,
}
```

Monitor 中：

```text
NO_MATERIAL_CHANGE
→ return

DELTA_RESEARCH
→ affected research / new ReportVersion

FULL_RESEARCH
→ full ResearchPipeline
```

### 禁止

不得保留两套“Full Research”：

```text
旧 market→snapshot→report
新 full pipeline
```

正式业务必须只有一个 Full Research 实现。

---

## 4.2 修复 AnalysisQualityGate 执行时机

### 当前问题

目前流程实际类似：

```text
Snapshot
↓
EvidenceQualityGate
+
AnalysisQualityGate
↓
Analysts
↓
Claims
```

即：

> AnalysisQualityGate 在 Claims 创建之前已经执行。

后续只是复用之前的 gate result，没有重新审查新生成的 Claims。

### 正确顺序

必须改成：

```text
EvidenceSnapshot
↓
EvidenceQualityGate
↓
Analyst Orchestrator
↓
Claims
↓
AnalysisQualityGate
↓
ThesisBuilder
↓
Debate
...
```

### 推荐拆分

不要继续使用一个同时执行两个 gate 的方法造成时序错误。

推荐：

```python
run_evidence_gate(snapshot_id)
run_analysis_gate(snapshot_id)
```

或至少：

```text
QualityService.run_evidence_gate(...)
QualityService.run_analysis_gate(...)
```

分别在正确阶段调用。

### 验收

新增测试：

```text
1. Pipeline 开始时 Claim 数 = 0
2. Analysts 生成 Claim
3. AnalysisQualityGate 必须看到这些新 Claim
4. 插入 dangling Evidence Claim 时必须 FAIL
```

---

## 4.3 修复 FinalReportQualityGate Citation 自证问题

### 当前问题

当前调用类似：

```python
known_evidence_ids = report.citations
citations = report.citations
```

导致检查：

```text
Citation 是否属于 Citation 自己
```

实际无法发现越界 Citation。

### 正确逻辑

必须使用：

```text
EvidenceSnapshot.evidence_ids
```

作为：

```text
known_evidence_ids
```

即：

```text
Report Citation
⊆
Snapshot Evidence
```

正确输入：

```python
known_evidence_ids = tuple(snapshot.evidence_ids)
citations = tuple(report.citations)
```

### 必须验证

新增：

```text
合法 Citation
→ PASS

伪造不存在 Evidence ID
→ FAIL

引用属于该股票但不属于当前 Snapshot
→ FAIL
```

必须保证：

```text
Report
→ Claim
→ Evidence
→ Current Snapshot
```

完全闭合。

---

## 4.4 RunManifest 继续加强

当前 placeholder 已基本修复，但最终仍需检查：

```text
git commit
config digest
random seed
provider version
model
prompt version
environment
snapshot
```

### 当前建议

如果实际使用 LLM：

必须在 RunManifest 写：

```text
model_versions
prompt_versions
```

不能只有：

```text
pipeline version
provider version
```

LLM 未配置时：

```text
model_versions = ()
```

可以接受。

但若 LLM 实际参与 ResearchRun：

> 必须记录真实模型和 Prompt 版本。

---

# 5. F0 DoD

只有同时满足：

```text
Scheduler FULL → Full ResearchPipeline
Periodic Full → Full ResearchPipeline
AnalysisQualityGate 时机正确
Citation Gate 使用 Snapshot Evidence
RunManifest 与真实执行一致
Backend Tests PASS
```

才进入 F1。

---

# 6. F1 — Research Integration

## 6.1 英文 Narrative 真正接入报告主链

### 当前问题

系统已经有：

```text
narrativize_report()
```

但实际 Report Pipeline 仍主要：

```text
ReportCompiler.compile
→ render_and_gate
```

Narrative Layer 未真正进入正常 Report 编译路径。

同时部分内容仍：

```python
text_zh = 中文
text_en = 同一段中文
text_language = "zh-CN"
```

而 narrative 只处理：

```text
text_en is empty
```

导致这些内容不会被翻译。

### 正确结构

建议：

```text
Structured Research State
↓
ReportCompiler.compile()
↓
Narrative Layer
├─ zh-CN
└─ en-US
↓
Quality Gate
↓
Renderer
```

英文请求：

```text
language=en-US
```

时：

```text
narrativize_report(report, provider)
```

必须真实执行。

### 数据结构建议

中文原始内容：

```text
text_zh = original Chinese
text_en = None
text_language = zh-CN
```

不要提前把：

```text
text_en = text_zh
```

写进去。

英文 narrative 生成后：

```text
text_en = generated English
text_language = None
```

LLM 不可用时：

```text
text_en = original Chinese
text_language = zh-CN
```

明确表示 fallback。

### 必须新增真实集成测试

不要只测试独立 `narrativize_report()`。

必须：

```text
真实 StructuredReport
→ compile en-US
→ narrative
→ render
→ English Report
```

至少断言：

```text
Thesis 中文原文 != English narrative
Claim 中文原文 != English narrative
Evidence IDs 完全一致
Numbers 完全一致
Valuation 完全一致
```

---

## 6.2 Macro / Policy 正式进入 Analyst Loop

### 当前问题

当前 Pipeline 已采：

```text
macro_policy
```

但没有对应：

```text
MacroPolicyAnalyst
```

因此：

```text
Source → Evidence
```

存在，

但：

```text
Evidence → AnalystBrief → Claim → Thesis
```

没有完成。

### 必须二选一

#### 方案 A — 推荐

增加：

```text
MacroPolicyAnalyst
```

其输出至少：

```text
AnalystBrief
Claim
Evidence refs
Risks / Questions
```

规则：

```text
媒体报道政策
=
media_report

官方原文政策
=
regulatory_document / confirmed official
```

不能混淆。

#### 方案 B

如果本阶段暂时不做 Macro 分析：

必须明确：

```text
macro_policy = collection_only
```

并从“完整 Analyst Set 已完成”的表述中移除。

不能：

```text
采了数据
=
分析完成
```

---

## 6.3 宏观数据源质量提升

当前 MacroProvider 本质上是：

```text
Eastmoney 搜索
+
官方机构关键词识别
```

这仍然属于：

```text
media_report
```

不是直接官方原始政策。

### 建议

至少增加 1～2 类真实直接官方 Source，例如：

```text
中国人民银行
国家统计局
证监会
国务院
工信部
发改委
```

第一版不要求全接。

但至少要证明：

```text
Official Source
→ Evidence
→ authority B1 / A1
```

与媒体报道明确区分。

---

## 6.4 QuantBrief 真正影响正式 Research State

### 当前问题

Quant 当前已经有：

```text
Kline
→ Factor
→ Backtest
→ Metrics
→ QuantBrief
```

这是有效实现。

但 QuantBrief：

```text
claim_refs
```

通常为空。

所以：

```text
claim_ids.extend(quant_brief.claim_refs)
```

对 Thesis 基本没有影响。

### 必须整改

Quant 应至少创建 1～N 个：

```text
FactStatus.ANALYST_INFERENCE
```

的 Quant Claim。

例如：

```text
5日动量为正
过去N日动量策略回测收益为X
当前20日波动率为Y
```

必须引用：

```text
historical_data Evidence
```

但注意：

```text
回测结果
≠ confirmed_fact
```

推荐：

```text
claim_type = quantitative_signal
fact_status = analyst_inference
confidence = 根据样本长度/稳定性约束
```

### Thesis 使用规则

Quant Claim：

```text
不能自动压过正式公告/财务事实
```

只作为：

```text
supporting context / market signal
```

---

## 6.5 LLM Research 能力边界重新定义

当前 LLM 主要应用于：

```text
Copilot
Narrative
```

这是可以接受的。

不要为了“AI Research”强行把所有 Analyst 都改成 LLM。

建议采用：

```text
Deterministic Fact Analysts
+
Optional Evidence-grounded Reasoning Layer
```

例如：

```text
Evidence-backed Claims
↓
LLM Thesis Challenge
↓
LLM Bull/Bear Reasoning
↓
Citation Validation
```

第一阶段先用于：

```text
Thesis refinement
Counterargument
Risk interpretation
Research Copilot
```

不要让 LLM 创建原始事实。

---

# 7. F1 DoD

必须真实证明：

```text
English Report 经过 Narrative Layer
Macro 能力状态真实
Quant 产生可追溯 Claim
LLM 边界保持 Evidence First
Backend Tests PASS
```

---

# 8. F2 — Product Integrity

## 8.1 Research Graph 补完整 Research Lifecycle

### 当前问题

当前 Graph 已覆盖：

```text
Source
Evidence
Snapshot
Claim
Thesis
ResearchRun
Report
ReportVersion
```

但系统完整 Research State 还包括：

```text
CorporateEvent
Valuation
Prediction
Validation
RegressionReview
```

### 建议补齐节点

```text
Source
→ Evidence
→ CorporateEvent
→ Claim
→ Thesis
→ Valuation
→ ReportVersion
→ Prediction
→ Validation
→ RegressionReview
```

不要求所有对象都必须串成单一直线。

但要保证真实引用关系存在。

### 至少增加

```text
valuation
prediction
validation
corporate_event
```

节点与边。

---

## 8.2 Overview 补齐真正研究摘要

当前 Overview 主要：

```text
latest price
evidence count
```

还不像真正 Research Workspace 首页。

至少补：

```text
Research Confidence
Data Quality
Top Thesis
Top Catalysts
Top Risks
Valuation Status
Latest Material Change
Latest Prediction
Latest Research Run
```

数据全部来自真实 API。

禁止前端硬编码。

---

## 8.3 Workspace 状态展示

当 Source 出现：

```text
partial
network_error
source_unavailable
```

UI 必须显示：

```text
degraded
```

而不是：

```text
No Data
```

Research Workspace 应至少给用户看到：

```text
数据是否完整
哪个 Source 失败
什么时候采集
是否走 fallback
```

---

## 8.4 Production Database

### 当前状态

当前 Docker Compose 默认仍：

```text
SQLite
```

对于：

```text
单用户
内网试用
低并发
```

可以继续使用。

但如果目标是：

```text
多用户
长期 scheduler
并发 ResearchRun
持续积累 Evidence
```

建议升级：

```text
PostgreSQL
```

### 本轮建议

不强制立刻删除 SQLite。

建议：

```text
Development:
SQLite

Production:
PostgreSQL
```

完善：

```text
.env.example
docker-compose.production.yml
migration test
backup/restore
```

如果暂时不做：

必须在：

```text
known-limitations.md
```

明确说明 SQLite 仅适合当前试用规模。

---

# 9. 状态治理必须彻底修复

这是必须做的，不是文档美化。

当前：

```text
REMEDIATION.md
STATUS.md
ROADMAP.md
README.md
```

再次出现互相冲突。

### 最终规则

只保留一个当前状态源：

```text
STATUS.md
```

建议职责调整：

```text
TASK.md
= 最终任务

PLAN.md
= 当前工作计划

STATUS.md
= 当前唯一执行状态

ROADMAP.md
= 长期历史路线

REMEDIATION.md
= 已完成整改历史记录
```

## 9.1 STATUS.md

必须只保留当前事实：

```text
Current Phase
Completed
In Progress
Next Action
Tests
Live Verification
Open Issues
Branch
Commit
```

禁止 append 历史。

## 9.2 REMEDIATION.md

如果 R0–R5 已结束：

改为：

```text
Historical Remediation Record
```

不要继续作为“唯一当前状态源”。

每个阶段真实状态重新确认。

## 9.3 ROADMAP.md

整改阶段如果完成：

```text
R0 DONE
R1 DONE
...
```

如果本次 Final Integrity 还没完成：

新增一个简单章节：

```text
Final Integrity Pass — DOING
```

但不要再拆成十几个长期 Milestone。

## 9.4 README

README 只能写用户当前真实状态。

例如：

```text
Current:
Research OS Beta — Final Integrity Pass

Completed:
multi-source evidence
full research pipeline
workspace
scheduler

In progress:
final pipeline integrity / English narrative / graph lifecycle
```

不能继续写：

```text
R0
```

如果实际已经到了最后阶段。

---

# 10. F2 DoD

必须：

```text
Graph 生命周期更完整
Overview 成为真正 Research Summary
Source degraded 状态可见
Production DB 策略明确
STATUS / ROADMAP / README / REMEDIATION 一致
Frontend Build PASS
Frontend Tests PASS
```

---

# 11. F3 — Final Verification

## 11.1 Full Research E2E

至少 4 个标的：

```text
600519
000001
300750
688981
```

本轮建议：

> **4 个全部成功。**

不要再只要求：

```text
completed >= 3
```

如果某 Source 短暂失败：

允许：

```text
partial / degraded
```

但 Pipeline 本身必须：

```text
正常结束
并显式披露缺失
```

除非所有必要 Source 都不可用。

---

## 11.2 Continuous Research E2E

必须真实测试：

```text
Monitor
→ NO_MATERIAL_CHANGE
```

以及：

```text
Monitor
→ DELTA_RESEARCH
→ New ReportVersion
```

以及：

```text
Monitor
→ FULL_RESEARCH
→ ResearchPipeline
→ New ResearchRun
→ New Report
```

三条分支。

---

## 11.3 Analysis Gate Test

必须证明：

```text
Analyst creates Claims
↓
AnalysisQualityGate sees Claims
↓
Bad Claim → FAIL
```

不能只测 Gate 类。

---

## 11.4 Citation Gate Test

必须证明：

```text
Snapshot Evidence = {A,B,C}
Report Citation = {A,B}
→ PASS
```

以及：

```text
Report Citation = {A,X}
X not in Snapshot
→ FAIL
```

---

## 11.5 English Report E2E

必须：

```text
Real Snapshot
→ Real Claims
→ Real Thesis
→ compile en-US
→ Narrative Layer
→ English Report
```

至少检查：

```text
中文 Claim
≠ 英文 rendered narrative
```

同时：

```text
Evidence IDs same
Numbers same
Valuation same
```

---

## 11.6 Quant Integration Test

必须：

```text
historical_data
→ QuantBrief
→ Quant Claim
→ Thesis/Report visible
```

不能只证明 QuantBrief 存在。

---

## 11.7 Scheduler Long-running Test

验证：

```text
periodic full research
monitor
prediction validation
retry
restart recovery
idempotency
same-instrument lock
```

---

## 11.8 Prediction Validation

当前 immediate mark-to-market：

```text
return = 0
```

可以保留为 smoke。

但不要把它描述为真正 5D Validation。

文档明确区分：

```text
mark_to_market validation
vs
matured horizon validation
```

真正 5D/20D/60D 等待时间型验证由 scheduler 后续持续运行完成。

测试可以使用：

```text
historical frozen fixture / controlled clock
```

验证数学逻辑。

---

# 12. Final Reviewer Pass

最终再次检查：

```text
FULL_RESEARCH 是否唯一实现
Analysis Gate 是否在 Claim 后执行
Citation Gate 是否真实
Narrative 是否进入生产路径
Macro 是否真实进入研究或明确 collection-only
Quant 是否形成 Claim
Graph 是否缺关键 lifecycle 节点
STATUS 是否再次失真
TODO
FIXME
placeholder
Mock business data
swallowed exception
PIT violation
broken citations
```

发现问题直接修复。

---

# 13. 最终完成条件

只有以下全部满足：

```text
F0 PASS
F1 PASS
F2 PASS
F3 PASS
```

以及：

```text
Backend Build PASS
Frontend Build PASS
Unit Tests PASS
Integration Tests PASS
Live Research E2E 4/4 PASS
Continuous Research 3 branches PASS
AnalysisQualityGate integration PASS
Citation Gate integration PASS
English Narrative E2E PASS
Quant Claim integration PASS
Scheduler PASS
PIT PASS
Traceability PASS
i18n PASS
Theme PASS
Backup/Restore PASS
Final Reviewer PASS
State Files Consistent
```

才允许写：

```text
Final Integrity Pass COMPLETE
```

---

# 14. Claude 直接执行指令

现在开始：

1. 读取当前仓库和现有任务文件；
2. 不重新输出新的架构方案；
3. 将本文件纳入当前 PLAN；
4. 从 `F0 — Pipeline Integrity` 开始实际修改；
5. 先修 Scheduler FULL、AnalysisQualityGate、Citation Gate；
6. 然后修英文 Narrative 主链；
7. 再处理 Macro / Quant 正式入链；
8. 最后补 Graph / Overview / 状态治理；
9. 每个阶段必须 Build / Test / Integration Verify；
10. 上下文即将结束时更新 STATUS 并 Git checkpoint；
11. 除真实外部阻塞外继续执行；
12. 只有本文件所有 DoD 全部通过后才能结束。

---

# 15. 最重要的判断标准

不要再判断：

```text
类存在了吗？
接口存在了吗？
测试文件存在了吗？
```

只判断：

```text
这个能力是否真的在正式业务链中被调用？
↓
输入是否真实？
↓
输出是否进入 Research State？
↓
是否有真实引用关系？
↓
异常是否真实可见？
↓
是否被集成测试证明？
```

最终目标：

> **让现有 A-Share Research OS 从“功能很多”变成“调用链真实、状态可信、长期可运行”。**
