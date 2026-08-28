# ARTIFACT-PROTOCOL — ArtifactRegistry / ProvenanceEdge 接口细化

> §27/§28/§29/§62。Artifact 只是**跨领域索引/导航/溯源/搜索/Handoff** 的总线，
> 绝不取代强类型 Domain（红线 2）。

## 1. ArtifactRecord（表 `artifacts`）

```python
class ArtifactType(str, Enum):
    # 第一批（Phase A 就注册的现有对象）
    RESEARCH_RUN = "research_run"
    REPORT = "report"
    REPORT_VERSION = "report_version"
    PREDICTION = "prediction"
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    CLAIM = "claim"
    THESIS = "thesis"
    # 后续 Phase 渐进追加（experience_card / workflow_run / screening_run /
    # strategy_version / observation / signal / decision / review / …）

class ArtifactORM(Base):
    __tablename__ = "artifacts"
    artifact_id: str          # "art_<hex16>"
    artifact_type: str        # ArtifactType
    domain_type: str          # 强类型对象类型名（ReportVersion/Prediction/...）
    domain_id: str            # 强类型主键（report_id/prediction_id/run_id/...）
    title: str                # 业务标题（如 中国稀土 · 完整研究报告 v3）
    summary: str | None
    instrument_ids: JSON      # [ "SZSE:000831" ]
    as_of_time: DateTime      # PIT 语义（继承自对象的 as_of/created）
    version: int | None
    status: str               # active/superseded
    created_by: str           # "pipeline" / "prediction_builder" / "user"
    route: str                # 前端路由（/reports/<id>、/instrument/<id>…）
    metadata_json: JSON
    created_at: DateTime
    # 唯一性：UniqueConstraint(domain_type, domain_id)
```

## 2. ArtifactService（`app/application/artifacts/service.py`）

```python
class ArtifactService:
    def register(self, *, artifact_type, domain_type, domain_id, title,
                 summary=None, instrument_ids=(), as_of_time=None,
                 version=None, created_by, route, metadata=None) -> str
    # 幂等：(domain_type, domain_id) 已存在 → 更新 title/status 后原样返回

    def get(self, artifact_id) -> dict | None
    def search(self, query, *, artifact_type=None, instrument_id=None,
               limit=20) -> list[dict]            # title/summary LIKE + 过滤
    def by_domain(self, domain_type, domain_id) -> dict | None
    def lineage(self, artifact_id, *, direction="upstream", max_depth=10) -> dict
```

## 3. ProvenanceEdge（表 `provenance_edges`）

```python
class RelationType(str, Enum):
    DERIVED_FROM = "derived_from"      # 报告 ← 快照
    SUPPORTED_BY = "supported_by"      # claim ← evidence
    GENERATED_FROM = "generated_from"  # prediction ← report
    VALIDATED_BY = "validated_by"      # prediction ← validation
    SUPERSEDES = "supersedes"          # version ← 旧 version
    TRIGGERED_BY = "triggered_by"      # run ← monitor decision
    PRODUCED = "produced"              # run → report
    USED_BY = "used_by"
    # Phase C+ 追加：contradicted_by / selected_by / monitored_by /
    # decided_from / predicted_from / reviewed_by

class ProvenanceEdgeORM(Base):
    __tablename__ = "provenance_edges"
    edge_id: str                 # "pe_<hex16>"
    from_artifact_id: str        # FK→ artifacts.artifact_id
    to_artifact_id: str
    relation_type: str
    created_at: DateTime
    metadata_json: JSON
    # UniqueConstraint(from_artifact_id, to_artifact_id, relation_type)
```

ProvenanceEdge 写入只经 `ArtifactService.link(from, to, relation, metadata)`。
禁止前端拼关系（§30）；图谱读模型（Phase I）只读这两张表。

## 4. 第一批注册映射（§85）

| 现有对象 | artifact_type | 注册点（写入路径） | as_of_time | route |
|---|---|---|---|---|
| ResearchRun | research_run | `ResearchPipeline.run()` 完成/失败时 | run.as_of | `/instrument/<iid>` |
| ReportVersion | report_version | `ResearchPipeline.run()` 保存版本后 | snapshot.as_of | `/reports/<report_id>` |
| Prediction | prediction | `PredictionRepository.save` 后（两个 API 路径） | prediction.as_of | `/predictions` |
| Validation | validation | `ValidationService.validate` 后 | validated_at | `/predictions` |

首批 Provenance 边：
`research_run --produced--> report_version`、
`report_version --generated_from--> prediction`、
`prediction --validated_by--> validation`、
`report_version --derived_from--> research_run`。

## 5. API（§62 增量）

```
GET  /artifacts?query=&artifact_type=&instrument_id=&limit=
GET  /artifacts/{artifact_id}
GET  /artifacts/{artifact_id}/upstream?max_depth=
GET  /artifacts/{artifact_id}/downstream?max_depth=
GET  /artifacts/{artifact_id}/lineage
```

验收（Phase A 完成定义）：从一条 Prediction 的 lineage 可回溯
report_version → research_run，且 `GET /artifacts` 支持按 000831 检索；
全部经产品级测试（Playwright 扩一条 E2E-07：报告页技术详情 → lineage）。
