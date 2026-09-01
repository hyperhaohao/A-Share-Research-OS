# F4-MANIFEST — Integrity Migration

> 阶段：F4（第三轮整改任务书 §11 F4 / §7 P1-A）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 可解释置信度模型（§7.1）—— 生产路径固定置信度全部移除
- 新模块 `app/domain/confidence.py`（`claim_confidence_v1`）：
  `compute_claim_confidence(supporting_trusts, corroboration_groups,
  directness, semantic_consistency, evidence_age_days, missing_data)` →
  {value, level, basis, model_version}；数值仅用于排序、非概率、
  因素映射版本可追溯；无支撑 → insufficient（不用默认值掩盖）；
- 清理的生产路径（grep 复核：生产 Claim/决策路径不再有固定值）：
  | 路径 | 原值 | 现值 |
  |---|---|---|
  | Extraction → Claim promote | 固定 0.6 | 信任层+引用反查(direct_quote)+新鲜度 |
  | Thesis Diff Apply → New Claim（F2 已做） | 固定 0.6 | 信任层 |
  | 分析师 ClaimSpec（8 处 0.95/0.9/0.55） | 硬编码 | 按证据信任层/独立组/直接性（fact_status 推导）/新鲜度 |
  | MarketAnalyst 行情事实 | 固定 0.99 | 行情 T0 + direct_quote |
  | QuantBrief 表达式 Claim | 0.65/0.5 条件 | 信任层 + directness（样本不足→inference，样本数入 basis） |
  | Debate bull/bear | 0.55+0.05×round / 0.55 | 信任层 + 轮次 adjust（入 basis） |
  | Strategy Monitor 决策 | min(0.9,0.5+0.1n) / 固定 0.6 | 信号证据信任层 + 信号组数；rationale 附 basis 说明 |
  | Replay ResearchExperience 教训 | 固定 0.6 | 0.50+0.05×min(归因数,4)，归因数入披露 |
- `claims` 表新增 `confidence_basis_json` + `confidence_level`
  （迁移 d3e4f5a6b7c8）；`/claims` API 透出 level+basis（§7.4 UI 可显示
  「为什么是该置信度」的后端就绪；UI 渲染在 F12 产品化落地）。

### 2. Source Independence（§7.2）
- 迁移 d3e4f5a6b7c8：`evidence_records` 新增 publisher / origin_url /
  canonical_url / source_group / original_source / published_at
  （content_hash 已有）；EvidenceRecord 域字段 + 仓储映射；
- 新服务 `app/services/source_independence.py`：
  - 独立组判定 6 规则（Union-Find，可审计）：同 content_hash（同稿转载）/
    规范化正文哈希（标题变化正文相似的转载；刻意不含标题）/
    canonical_url·origin_url 互指（多镜像）/ 同 source_document_id（同一公告）/
    同 original_source（二次报道引用同一原始来源）/ 同 source_group（同通讯社）；
  - `corroboration_check`：「≥2」指 **≥2 independent source groups**，
    不是两行 Evidence；降级披露 reason_code=degraded_fields
    （provenance 字段缺失时不得冒充通过）；
  - reason codes：satisfied / insufficient_independent_sources / degraded_fields。

### 3. Subject Swap Detection（§7.3）
- 新模块 `app/domain/entity_dictionary.py`：EntityEntry（canonical/entity_type/
  aliases/instrument_ids）+ 八类实体类型（上市公司/控股股东/实际控制人/
  集团公司/子公司/同行业/监管机构/地方国资）+ 最长别名匹配 resolve +
  运行时 extend（关系源接入登记入口）；
- 接入 `_semantic_entailment` 第 4 步（原 stub）：
  statement 与 evidence 解析到不同 canonical 实体且为混淆对
  （名称互为前后缀，如「中国稀土股份」vs「中国稀土集团」）→
  **uncertain + `subject_entity_mismatch:<A>(type)|<B>(type)`**；
  不再因词面重叠通过（§7.3 反例测试覆盖）；保守触发防误报回潮（§22.1）；
- `verify_extraction` 支持 uncertain 裁决 → 不进正式 Research State
  （promote 422 显形）。

## 测试（tests/test_f4_integrity.py，6 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | 置信度模型因素映射（信任层/独立组加成/无支撑 insufficient） | PASS |
| 2 | promote：T0 与 T3 证据 → 不同置信度；≠0.6；basis 落库含 model_version | PASS |
| 3 | 来源独立性分组（同稿/标题变化/独立/同通讯社/二次引用）+ ≥2 独立组裁决 | PASS |
| 4 | provenance 缺失 → degraded_fields 显式降级 | PASS |
| 5 | 主体偷换（中国稀土股份 vs 中国稀土集团）→ uncertain + reason code；主体一致 → accepted | PASS |
| 6 | uncertain 抽取 promote → 422（不进正式 Research State） | PASS |

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（428 collected = 404 基线 +10 F2 +8 F3 +6 F4）
alembic：c2d3e4f5a6b7 → d3e4f5a6b7c8 应用（空库链 + dev DB 实测）
```

## 修改/新增文件

- 新增：app/domain/confidence.py、app/domain/entity_dictionary.py、
  app/services/source_independence.py、alembic/versions/d3e4f5a6b7c8_*.py、
  tests/test_f4_integrity.py
- 修改：app/domain/extraction.py（uncertain + subject swap）、
  app/domain/evidence.py、app/domain/research.py、app/storage/orm.py、
  app/storage/research_orm.py、app/storage/research_repo.py、
  app/storage/repository.py、app/application/extraction.py（promote 置信度）、
  app/services/analysts.py、market_analyst.py、quant_brief.py、
  debate_engine.py、strategy_monitor_service.py、replay_service.py、
  app/api/research.py（claims 透出 basis）

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
已知边界：Entity Dictionary 种子仅含通用监管机构 + 000831 黄金链，
其余标的随关系源接入经 extend() 登记（机制通用，非 000831 专属）。
