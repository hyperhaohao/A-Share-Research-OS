# F2-MANIFEST — Research State Review Fix

> 阶段：F2（第三轮整改任务书 §11 F2 / §5 P0-B）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 基线失败修复（F0 登记）
- 根因：commit a3c6be4 在 apply 中途 `session.rollback()`，将刚 build 的
  PIT snapshot（pending insert）回滚丢弃 → 后续 save_claim 的
  `_require_snapshot_evidence` 查不到 snapshot → CrossSnapshotError。
- 修复：apply 逻辑整体移入 `app/services/thesis_revision.py`，
  移除两处破坏性 rollback；`r8 thesis-diff apply` 通过。

### 2. 静默丢 Claim 修复（§5.3.1）
- 删除 carry-forward 的 `try/except Exception: continue`；
- 任一 Claim 保存失败 → 异常上抛 → `apply_thesis_revision` 捕获 →
  **全事务回滚** → 显式 500 `thesis_revision.failed`；Current 不切换（§5.3.2/§5.3.5）。
- 旧 Thesis 引用的 Claim 缺失 → 显式 500 拒绝（不再静默跳过）。

### 3. Claim Version Lineage（§5.3.4）
- 新迁移 `c2d3e4f5a6b7`（claims 表）：`parent_claim_id`（索引）/
  `revision_kind` / `revision_reason` / `source_impact_relation` / `carried_forward`；
- Domain `Claim` 增同名显式字段；Repository save/get/list 全链路映射；
- 空库 → head 迁移链实测通过；本地 dev DB 升至 head。

### 4. 七关系 Apply 语义修复（§5.2）
- supersedes：旧版本标 superseded + **创建新 Claim Version**
  （parent chain：version.parent = carried.parent = old claim），旧实现只标旧行不建新行；
- updates：**创建 revised Claim Version**（带 refs + parent chain），
  旧实现只写 metadata 不落 Claim；
- strengthens：记录强度变化（revision_reason 落「+1 supporting evidence…」）；
- weakens/contradicts：进入 opposing 列表 + opposing refs + relation/reason 落库
  （contradicts 记录冲突原因）；
- irrelevant：**不制造 Claim** —— 修复旧实现「未命中 impact 的新证据被
  `[新发现]` 兜底建 Claim」的违规路径；
- supports：继承 + supporting evidence 追加。

### 5. 结构化 Claim Builder（§5.3.3）
- `build_evidence_claim`（evidence_claim_builder_v1）：
  statement = `[{kind}] {title} — {summary}`（不静默截断；超限显式截断并在
  `metadata.statement_basis.truncated` 披露），废除 `[新发现] + summary[:300]`；
- 置信度由信任层计算（`trust_numeric_confidence`：T0 0.85 → T4 0.30，
  basis 落 metadata），新路径不再写固定 0.6（F4 处理其余路径）。

### 6. 幂等 / 唯一 Current（§5.4）
- 已消费证据过滤（current thesis meta.added_evidence_ids）→ 重复提交 422，
  不无限重复建 Claim；
- **真实潜在缺陷修复**：`demote_other_currents` 原地改 JSON 回赋同一对象，
  SQLAlchemy 变更检测判无变化 → **Current 切换从不落库**（多 Current 腐化）。
  改为新 dict 赋值；并发/脏状态测试证实修复后唯一 Current。

## 测试（tests/test_f2_thesis_revision.py，10 用例，全部真实 API + 真实仓储）

| # | 场景（§5.4/§5.2） | 结果 |
|---|---|---|
| 1 | 10 supporting + 3 opposing + irrelevant → 新 Thesis 仍 10+3，不造 Claim | PASS |
| 2 | supports → 继承 + supporting 追加 + relation 落库 | PASS |
| 3 | contradicts → 移入 opposing（非 supporting-only）+ 冲突记录 | PASS |
| 4 | supersedes → 版本链完整可回溯，新版本生效 | PASS |
| 5 | updates → revised Claim Version 落库（非只写 metadata） | PASS |
| 6 | strengthens → 强度变化记录 | PASS |
| 7 | weakens → 移入 opposing，不保留纯 supporting | PASS |
| 8 | carry-forward 第 3 条失败 → 500，全回滚，Current 不切换，无半成品 | PASS |
| 9 | 脏状态（双 Current）→ 修订后唯一 Current | PASS |
| 10 | 重复提交相同证据 → 422 幂等，Claim/Thesis 数不变 | PASS |

## 全量回归

```text
backend pytest 全量：exit 0（414 collected 含本阶段 +10；0 FAILED）
alembic：空库 upgrade head PASS（→ c2d3e4f5a6b7）；dev DB 已升级
```

## 修改文件

- backend/app/services/thesis_revision.py（新增，apply/diff/builder 服务层）
- backend/app/services/current_thesis.py（demote ORM 变更检测修复）
- backend/app/api/research_inbox_api.py（apply 收薄为服务调用）
- backend/app/storage/research_orm.py / research_repo.py（lineage 列与映射）
- backend/app/domain/research.py（Claim lineage 字段）
- backend/alembic/versions/c2d3e4f5a6b7_f2_claim_lineage.py（新迁移）
- backend/tests/test_f2_thesis_revision.py（新增 10 用例）

## 状态

IMPLEMENTED / INTEGRATED / TESTED（全量 backend exit 0）。
F15 前将在 Golden E2E（F14）对真实栈复验。
