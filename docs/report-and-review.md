# Report & Review（任务书 §38-§44）

## 结构化报告（§38）

`StructuredReport` 的 section 与任务书 §38 字段一一对应：
metadata（id/instrument/snapshot/as_of/language）、executive_summary、
market_and_capital、key_theses、corporate_events、valuation、scenarios、
bull_bear、risks、data_quality、source_manifest、disclaimer。
无数据的 section 显式渲染「暂无数据」。

## 编译与门禁

`ReportCompiler.compile(snapshot_id)` 从冻结研究状态只读编译；
`render_and_gate` 渲染 markdown/html 并运行 FinalReportQualityGate ——
FAIL 时 `published=false`（不安全报告不可发布）。

## 双语（§10/§41/§90）

zh-CN 与 en-US 渲染器读同一结构化状态：数字、claim/thesis 标识、引用集合
完全一致；claim/thesis 的原始语句逐字保留，跨语言显示时附加语言标记
（原文不被翻译覆盖）；证据摘要永远展示原文。

## 审查闭环

```text
Explain  POST /reports/{id}/ask  mode=explain —— 冻结态作答，零采集
Refresh  POST /reports/{id}/ask  mode=refresh —— 旁路缓存采集 → 新快照 → 影响差集
Audit    POST /reports/{id}/audits —— unsupported/outdated/conflicting/数值不可追溯
Revision POST /reports/{id}/revisions —— Proposal（original/proposed/reason/…）
Accept   POST /revisions/{id}/accept —— 生成 V(n+1)；V(n) 永久保留（§78）
Reject   POST /revisions/{id}/reject —— 仅记录
```
