# G1-MANIFEST — 真实 Industry Graph

> 观澜研究能力语义迁移任务书 §G1（P0）| 日期：2026-09-02
> 基线：docs/guanlan-semantic-remediation/MIGRATION-MATRIX.md §1（G1 FAIL 项）

## 交付

### 1. 六个新域模型 + 迁移（与行业分类分表分路由）
- `industry_chains / industry_segments / industry_edges / industry_products /
  industry_edge_evidence / company_industry_positions`（迁移 b9c0d1e2f3a6）；
- **IndustryEdge 最低字段全数落地**：source/target_segment_id、relation_type
  （9 类：material_flow/price/cost/profit/demand_transmission/
  supply_constraint/policy/substitution/competition）、input/output_product_ids、
  transmission_metric、direction、lag_min/max_days、strength、confidence_level、
  valid_from/valid_to、evidence_ids（经链接表）、snapshot_id、version；
- 分类树（industry_view_service）保留可用，路由/UI 不再命名为产业链。

### 2. Evidence Ownership Gate（§G1/G2 复用）
- 证据挂边三重门：存在性 + **PIT（available_time ≤ as_of）** +
  **产业归属**（证据标的有链上 Company Position，或证据文本提及链名/环节名）；
  跨产业证据注入 → 422 `evidence_ownership_rejected`；未来证据 → 422
  `evidence_not_yet_available`。

### 3. 置信派生与降级（§G1 DoD）
- strength/confidence/status 由支撑证据**独立来源组**派生
  （F4 source_independence 复用：同源转载不加分）；
- 状态机：insufficient（0 支撑，不可发布）→ degraded（有支撑未达门槛/
  存在反对/置信未达 high）→ active（≥2 独立组 + high）；
- **删除关键证据自动降级**（active→degraded→insufficient 全链测试）。

### 4. Company Industry Position
- 一家公司可位于多个产业链/环节；角色五类（producer/processor/consumer/
  supplier/recycler）+ 收入/利润暴露 + 产能依据 + 证据；
- **位置证据归属**：证据标的必须=被定位公司（他司披露 → 422）；
- 000831/600259 位置隔离测试。

### 5. Peer 关系
- Peer = 同链同环节共位（明确关系语义）；非关键词共现；
- 测试锁定：不同环节不成为 peer。

### 6. 稀土 Golden 种子（显式 Command，幂等）
- 5 环节（资源开采→冶炼分离→金属/合金→永磁材料→电机/新能源应用）+
  5 条传导边（material_flow×2 + price_transmission + demand_transmission +
  supply_constraint），9 类 relation 校验通过；
- **不伪造证据**：种子只建结构，边初始 insufficient；证据由研究运营经
  Ownership Gate 挂载；
- 图谱 Artifact 注册（industry_graph/IndustryChain domain）+
  `provenance_complete` 显形。

### 7. API（/industry-graph/*）
chains / chains/{id}/graph?as_of / segments / edges / edges/{id}/evidence
(POST+DELETE) / positions / instruments/{id}/positions?as_of /
instruments/{id}/peers / seed/rare-earth（需 confirm:true）。

### 8. as_of 可重放（PIT）
- 未来创建的环节/边不进入历史 as_of 状态；
- 证据按 available_time ≤ as_of 过滤（测试：历史 as_of 证据为空、当前可见、
  新环节对历史不可见）。

### 9. 修复
- related_instruments 持久化去重（按 instrument_id 保留首现，
  防跨 run 重复膨胀 —— 任务书 §G1.7）。

### 10. UI
- 产业研究工作区新增第三 tab「产业链图」（IndustryGraphView）：
  环节 stage 卡片（含公司数）+ 传导边表（source→target 方向箭头（负向 ↛）、
  relation、传导度量、时滞、状态徽章、证据入口）+ 公司链上位置面板 +
  as_of 标注；i18n zh/en；行业分类 tab 保留。

## 测试（tests/test_g1_industry_graph.py，7 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 稀土链结构（≥5 环节/≥4 跨环节边/relation 覆盖/无证据=insufficient/幂等） | PASS |
| 2 | 边校验（非法 relation 422/自环 422/跨链环节 422） | PASS |
| 3 | Ownership Gate（相关证据挂载 OK；跨产业 422） | PASS |
| 4 | 未来证据 PIT 拒绝 | PASS |
| 5 | 置信派生与降级（2 独立组→high/active；删 1→degraded；删空→insufficient） | PASS |
| 6 | 多链位置 + 位置证据归属 + 000831/600259 隔离 | PASS |
| 7 | Peer 同环节共位语义 + as_of 双态重放 | PASS |
（#7 拆两用例；全量 backend 467 collected / 0 FAILED）

## 状态

IMPLEMENTED / INTEGRATED / TESTED（后端全量绿；前端 tsc/vitest/build 绿）。
Gap→G2：语义对象（Driver/Narrative/Transmission）关联 chain/segment/edge。
