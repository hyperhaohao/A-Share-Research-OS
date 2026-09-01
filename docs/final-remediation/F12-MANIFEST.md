# F12-MANIFEST — Research Product Productization

> 阶段：F12（第三轮整改任务书 §11 F12 / §10 P1-C）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. Thesis Center（§10.1）
- `GET /theses/{id}/diff/{other}` 增强：**Claim 级 lineage**
  （revision_kind / parent_claim_id / source_impact_relation / carried_forward /
  confidence_level / confidence_basis / 证据引用）+ **修订元数据**
  （revision_reason/revision_at/parent/carried/revised/superseded/impacts）；
- ThesisCenterPage：修订元数据面板（carried/revised/superseded 计数）、
  「对比当前版」→ Claim Lineage 视图（revision_kind / relation / confidence
  level 徽章）、修订时间。

### 2. Research Inbox（§10.2）
- Inbox 聚合新增（后端 + 前端面板）：
  **Thesis Changes**（窗口内修订：thesis/instrument/revision_at/is_current）；
  **Signal Ladder Hits**（对窗口内有新证据的标的实时跑 BUILTIN_SIGNAL_RULES
  —— 按需评估非持久化假象）；**Predictions Due**（原有，显式命名面板）；
  **Upcoming Validations**（同源显式）；**Recommended Next Actions**
  （确定性：Delta 研究/复核信号/检查失败源/处理到期验证）；
- 行动入口：「在帷幄中继续研究」（Open in Commander）+ 各面板业务链接。

### 3. Research Memory（§10.3）
- 三态治理 UI：**candidate → active → retired**（active 行「退役」动作走
  既有 promote 状态机；retired 独立面板）；
- **来源与时间面板**：source_artifacts / source_experiences provenance +
  updated_at（API 字段既有，前端补渲染）。

### 4. 市场级产品（§10.4-10.6）
- **Daily Brief**（§10.6）：编译器扩至全节 —— 新证据 / 重要性预警 /
  待补研究请求 / **Thesis 变化** / **信号命中** / **即将到期验证** /
  **建议下一步**（确定性推荐）；一键进帷幄由 Inbox/前端路由承接；
- **Overseas（§10.5）诚实重命名**：`OVERSEAS_EVIDENCE_RADAR`
  （契约新增枚举）+ `mapping_depth=evidence_radar` + `missing_chain`
  四项映射链缺口显形 —— 关键词证据雷达不再冒充完整 Mapping；
- Mainline Radar：结构既有（叙事→证据→驱动→映射→反方），维持。

## 测试与验证

- backend 全量：**exit 0，0 FAILED**（459 collected，含 inbox 契约扩展）；
- frontend：tsc PASS + vitest 35/35 + build PASS；
- **Live Verify**（compose 全栈重建后实测）：
  ```text
  GET /research-inbox → thesis_changes=8 / signal_hits=0（BUILTIN 规则无命中=真实）
                        / predictions_due=8 / recommended_actions 3 条
  GET /research-products/daily-brief → 全节真实渲染
  GET /research-products/overseas-mapping → product_type=OVERSEAS_EVIDENCE_RADAR
                                          + missing_chain×4 显形
  ```

## 修改文件

- backend：app/services/research_inbox.py、research_products_compiler.py、
  app/domain/research_products.py、app/api/research_inbox_api.py
- frontend：features/research-center/ResearchCenterPages.tsx、i18n locales

## 状态

IMPLEMENTED / INTEGRATED / TESTED / REAL_VERIFIED。
