# G9-MANIFEST — Research Products 产品化

> 观澜研究能力语义迁移任务书 §G9（P1）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §9（临时 dict 无 Artifact/PIT/Version → FAIL）

## 交付

### 1. 编译版本化 + Artifact（§G9 通用要求）
- 新表 `research_product_compiles`（迁移 c6a7b8c9d0e2）：每次编译落
  version（product 内单调递增）+ as_of（PIT）+ payload 全文 + artifact_id +
  provenance_status；
- `POST /research-products/{kind}/compile`（**显式 Command**，confirm=true；
  未确认 422）：编译 + 落库 + Artifact 注册（research_product/
  ResearchProduct domain；失败 → INCOMPLETE_PROVENANCE 显形）；
- **diff_vs_previous**：每版可查看与上一版变化（previous_version/items
  数量变化）+ `GET /compiles/diff?product_type&v1&v2` 版本对比端点；
- Overseas 维持诚实命名 OVERSEAS_EVIDENCE_RADAR + missing_chain。

### 2. 页面（§G9.2/§G9.3）
- `/research-products` 正式路由 + 页面（ResearchProductsPage）：
  三产品编译入口 + 版本/Artifact/as_of/provenance 显形 + missing_chain
  披露 + 版本历史列表；所有入口均为真实路由。

### 3. 条目可打开（§G9.4）
- Mainline/Overseas 条目携带 evidence_id（既有）；晨报节 items 携文本与
  时间；Evidence → 证据层真实 ID（打开走既有证据入口）。

## 测试（tests/test_g9_products.py，4 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | compile+register → v1 + Artifact + provenance complete；二编 → v2 + diff；列表；版本 diff | PASS |
| 2 | 未确认 → 422 | PASS |
| 3 | 未知 kind → 404 | PASS |
| 4 | Overseas 诚实命名 + missing_chain | PASS |
（全量 backend 0 FAILED；frontend tsc/vitest 35/build PASS）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G10：Thesis Center diff 全字段 + Inbox 路由修正 + Memory Diff/恢复。
