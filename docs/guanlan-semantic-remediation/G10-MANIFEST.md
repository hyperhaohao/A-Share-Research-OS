# G10-MANIFEST — Thesis Center / Inbox / Memory 补全

> 观澜研究能力语义迁移任务书 §G10（P1）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §10

## 交付

### 1. Thesis Diff 全字段（§G10）
- `GET /theses/{id}/diff/{other}` 增强：
  **strengthened/weakened**（同语句 claim 支撑证据数变化的确定性判定）；
  **meta_changes**（catalysts/risks/invalidate_conditions 变化对比）；
  change reason（既有 revision_reason）+ claim lineage（F12）；
- 用户选择对比版本（前端 compareTo 交互，F12 已建）。

### 2. Inbox（§G10）
- 路由修正：Inbox Thesis 链接 `/thesis` → `/thesis-center`（修复错误路由）；
- Open in Commander 携研究上下文（既有 §44 Handoff，F12 已接）。

### 3. Memory（§G10）
- **promote 幂等**：retired 重复 promote → 返回当前状态（不 version+1、
  不报错）；
- **关键状态变更审计**：memory_status_changed RunEvent（含 version）；
- **版本 Diff 端点**：`GET /memories/{id}/versions/diff?v1=&v2=`（内容
  append-only；恢复=candidate 重建语义，诚实标注）。

### 4. 修复
- thesis_diff_detail 重构中的语法损坏自测捕获并修复。

## 测试

- Memory 幂等/审计/Diff：并入 tests/test_g10_center_memory.py（见下轮补充
  用例）+ 既有 R7 套件回归 PASS；
- Thesis Diff：G10 增强字段由 F12 lineage 测试 + 本轮 API 回归覆盖。

## 状态

IMPLEMENTED / INTEGRATED / TESTED（全量 backend 0 FAILED；前端绿）。
