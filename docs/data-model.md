# Data Model

> 权威定义在各 domain 模块与 ORM；此处为概览（任务书 §19-§51）。

## 领域对象

| 对象 | 模块 | 关键约束 |
|------|------|----------|
| InstrumentProfile | domain/instrument.py | 六位代码+交易所+板块；分析字段缺失显式 null |
| EvidenceRecord | domain/evidence.py | 四时钟（event/available/ingested/revision）；content_hash 寻址；visible_at = available_time ≤ as_of |
| EvidenceSnapshot | domain/snapshot.py | (instrument, as_of) 唯一；append-only；内容寻址 id |
| ResearchRun | domain/snapshot.py | 绑定 snapshot_id；状态机 pending/running/… |
| Claim | domain/research.py | ≥1 证据引用（写时校验存在） |
| InvestmentThesis | domain/research.py | ≥1 主张引用；risks/trigger/invalidate |
| CorporateEvent | domain/research.py | announced_at ≥ occurred_at；16 类事件 |
| AnalystBrief | domain/agents.py | 引用仅限快照内证据；missing_data 显式 |
| ResearchRequest | domain/agents.py | open/fulfilled/failed；驱动补采闭环 |
| DebateRound / ScenarioSet | domain/debate.py | 辩论只引用既有证据；概率总和=100 |
| ValuationResult | domain/valuation.py | 纯确定性；缺输入 = not computable |
| PredictionRecord | domain/prediction.py | frozen；5D/20D/60D 交易日 due |
| ValidationRecord | domain/prediction.py | 单次；取整后自洽的收益/方向/区间 |
| RegressionReview / ResearchExperience | domain/regression.py | 归因 ≥1 维；经验 append-only |
| ReportVersion | domain/manifest.py | (report, version_no) 唯一；V>1 须 parent+reason |
| RunManifest | domain/manifest.py | 复现清单（commit/config/provider/seed/…） |
| QualityGateResult | domain/quality.py | 三类门；FAIL 拦截发布 |

## 数据表（25）

见 `backend/alembic/versions/0f8802656fc2_initial_schema_m4_through_m23.py`
（由 `app/storage/all_models.py` 全量注册生成）。

## 关键唯一约束

- evidence: (source, content_hash) —— 采集幂等
- snapshot: (instrument_id, as_of) —— 快照不可变
- claim: (snapshot_id, statement)；thesis: (snapshot_id, title)
- validation: prediction_id 唯一 —— 验证一次性
- report_version: (report_id, version_no) —— 版本链 append-only
