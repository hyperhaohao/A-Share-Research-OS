# DOMAIN-MAP — 现有领域对象 → V2 八域映射

> 只做映射与接口细化。原则（§9）：Research Domain 不因扩展重写。

## 1. Research Domain（现状即达标，保持）

| 对象 | 代码 | 状态 |
|---|---|---|
| Instrument / InstrumentProfile | `domain/instrument.py` + `storage/instrument_repo.py`（持久化 Registry，PW0） | ✅ |
| Source / EvidenceRecord / SourceManifest | `sources/*`、`domain/evidence.py`、`storage/repository.py` | ✅ |
| EvidenceSnapshot（PIT 不可变） | `domain/snapshot.py`、`storage/snapshot_repo.py` | ✅ |
| CorporateEvent / Claim / Thesis | `domain/research.py`、`storage/research_repo.py` | ✅ |
| AnalystBrief / MissingData / ResearchRequest | `domain/agents.py`、`storage/agent_repo.py` | ✅ |
| Debate / Scenario | `domain/debate.py`、`services/debate_engine.py` | ✅ |
| Valuation（十法确定性） | `domain/valuation.py`、`storage/valuation_repo.py` | ✅ |
| Risk（Thesis/Scenario 内嵌） | `domain/research.py` | ✅ |
| ResearchRun / RunManifest / ReportVersion | `domain/manifest.py`、`storage/manifest_repo.py`、`storage/snapshot_repo.py` | ✅ |
| ResearchReport / Revision | `domain/report.py`、`domain/audit.py`、`storage/revision_repo.py` | ✅ |
| Monitor / Materiality | `services/monitor.py`（DELTA/FULL/NO 三分支） | ✅ |
| Prediction / Validation / RegressionReview / Experience | `domain/prediction.py`、`services/validation_service.py`、`domain/regression.py` | ✅（归 Prediction & Review 域） |

> 注意：`domain/regression.py` 的 ResearchExperience（M20，append-only 文本沉淀）
> **不等于** V2 的 ExperienceCard（C 域，结构化 + 版本 + Validation）。
> C 阶段新建 `domain/experience/`，与 ResearchExperience 是演进而非复制关系。

## 2. 待建八域落点

| V2 域 | 落点 | 依赖现有 |
|---|---|---|
| Research | `domain/`（现文件保持） | — |
| Industry & Macro | `domain/industry/`、`domain/macro/`（Phase H：IndustryMap*/GlobalContextSnapshot） | IndustryAnalyst/MacroPolicyAnalyst 的采集能力（capability=industry/macro_policy） |
| Experience | `domain/experience/`（Phase C：ExperienceCard + Version + Validation + Case） | ReportVersion/Claim/Evidence 引用（强类型外键式 ref）；RegressionReview 做回灌来源 |
| Workflow | `domain/workflow/`（Phase D：强类型 DAG，§16 六类节点 + §17 NodeSpec） | quant/engine.py（因子公式）、sources、evidence 查询 |
| Screening | `domain/screening/`（Phase E：Screen/Run/Candidate+Explanation） | experience/workflow 产物 + 财务/因子数据 |
| Strategy | `domain/strategy/`（Phase F：StrategyVersion/Backtest/Validation） | screening/experience + quant engine 回测件 |
| Prediction & Review | 现有 prediction/regression 保持 | 新增 Decision→Prediction 等关系边（走 ProvenanceEdge） |
| Knowledge Graph | `domain/knowledge_graph/`（Phase I）= ArtifactRegistry+ProvenanceEdge 的读模型 | Phase A 地基 |

## 3. 跨域规则

- 跨域引用一律存 **ref（id + type）**，不复制对象；
- 关系写 ProvenanceEdge（Phase A 起），域内关系维持各表现有 JSON 列；
- LLM 参与的域（experience 提炼、industry 抽取）产物必须带 Evidence refs，
  未证实标记 `inferred`（§10/§65/§66，复用 `fact_status` 八态，不新造）。
