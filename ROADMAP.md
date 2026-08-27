# ROADMAP.md

# A-Share Research OS — Milestone Roadmap

> 本文件是长期 Milestone 状态的唯一状态源。
>
> 每完成一个 Milestone（通过其 DoD）更新状态。
> 同一时间只允许一个 `DOING`。
> Milestone 细节以 `docs/A-Share-Research-OS-最终实施任务书.md` 为准。

---

## 状态图例

```text
PLANNED   未开始
DOING     进行中（当前只能有一个）
DONE      已通过 DoD
BLOCKED   真实外部阻塞（需在 STATUS.md 记录 blocker）
NOT_REQUIRED   经审计后证明不需要（仅 M22 允许）
```

---

## Milestones

| # | Milestone | 状态 | 交付核心 |
|---|-----------|------|----------|
| M0 | 上游/底座源码审计 | DONE | upstream audit workspace、评估矩阵、架构审计、ADR-001 |
| M1 | 工程基线 + i18n + theme | DONE | 可运行的 backend/frontend 基线、zh-CN/en-US、system/light/dark |
| M2 | Instrument | DONE | InstrumentProfile、A 股代码/名称解析、四板回归 |
| M3 | Source Layer | DONE | capability-based Provider、fallback、SourceResult、source health |
| M4 | Evidence | DONE | EvidenceRecord、authority/fact_status、dedup、SourceManifest |
| M5 | PIT / Snapshot | DONE | 四时钟、available_time <= as_of 强制、不可变 EvidenceSnapshot |
| M6 | Research Domain | DONE | CorporateEvent、Claim、InvestmentThesis |
| M7 | Quality | DOING | EvidenceQualityGate、AnalysisQualityGate、FinalReportQualityGate |
| M8 | Structured Agents | PLANNED | AnalystBrief、missing_data → ResearchRequest 闭环 |
| M9 | Debate / Scenario / Risk | PLANNED | Thesis-based Bull/Bear、Bear/Base/Bull Scenario、Risk trigger |
| M10 | Valuation | PLANNED | 确定性估值引擎（PE/PB/PS/EV/EBITDA/DCF/DDM/SOTP/NAV/percentile/comps） |
| M11 | ResearchReport bilingual | PLANNED | 结构化报告、zh/en renderer、共享 Research State |
| M12 | Manifest / Versions | PLANNED | ResearchRun、RunManifest、不可变 ReportVersion |
| M13 | Report Q&A | PLANNED | Explain（无新数据）与 Refresh（允许新数据）严格区分 |
| M14 | Audit / Revision | PLANNED | sentence/claim/thesis audit、RevisionProposal、Diff、Accept |
| M15 | Delta / Materiality | PLANNED | Monitor、Evidence delta、MaterialityJudge 三分支 |
| M16 | Timeline | PLANNED | 统一事件时间线 |
| M17 | Research Graph | PLANNED | 溯源图、upstream/downstream 遍历 |
| M18 | Tasks / Scheduler | PLANNED | ResearchTask、scheduler、worker、retry、idempotency、recovery |
| M19 | Prediction / Validation | PLANNED | 不可变 PredictionRecord、5D/20D/60D、ValidationRecord |
| M20 | Regression / Experience | PLANNED | RegressionReview 归因、ResearchExperience 沉淀 |
| M21 | Quant audit | PLANNED | 主工程 quant 能力客观审计，决定是否需要 Qlib |
| M22 | Qlib（若需要） | PLANNED | 若需要：真实 A 股 Data→Factor→Model→Backtest→Metrics 闭环；否则 NOT_REQUIRED |
| M23 | Research API / SSE | PLANNED | 稳定 Research API、SSE 事件流、source health API |
| M24 | Workspace | PLANNED | Dashboard、Watchlist、Stock Workspace |
| M25 | Research visual UI | PLANNED | Timeline UI、Research Graph UI、Thesis Board、Evidence UI |
| M26 | Interactive Report | PLANNED | TOC、Citation viewer、Explain/Audit/Refresh/Revalue/Revision Diff |
| M27 | Tasks / Prediction UI | PLANNED | Tasks UI、Prediction Dashboard、完整双语主题回归 |
| M28 | E2E / Performance / Cost | PLANNED | 多标的 E2E、性能、成本核算、安全审查 |
| M29 | Production Delivery | PLANNED | Docker Compose、migration、health check、backup/restore、最终 Reviewer Pass |

---

## 当前 DOING：M7 — Quality

### 范围（任务书 §31）

- EvidenceQualityGate：PIT 合规 / 来源权威度 / 新鲜度 / 关键数据覆盖 /
  冲突证据 / source failures —— 真实业务规则，不是字数检查
- AnalysisQualityGate：Claim 是否有证据 / 事实越界 / 事实-预测混用 /
  冲突证据是否说明 / missing_data 是否披露
- FinalReportQualityGate：无效 citation / unsupported claim / 估值无假设 /
  风险缺失 / 数据质量未披露 / disclaimer 缺失 —— FAIL 不得发布正式报告
- Gate 结果持久化 + API 可见

### M7 DoD

```text
[ ] 三类 Gate 实现为真实业务校验
[ ] Gate 拦截测试（FAIL 场景确实拦截）
[ ] snapshot 级评估入口 + API
[ ] Git checkpoint
```

---

## 已完成 Milestone

### M6 — Research Domain（DONE，2026-08-28）

```text
backend/app/domain/research.py    CorporateEvent（§27 事件类型全集/announce>=occur 校验）、
                                  Claim（§28 字段全集 + 至少一条证据引用的域约束）、
                                  InvestmentThesis（§29 字段全集 + 至少一条主张引用）
backend/app/storage/research_orm.py + research_repo.py
                                  ORM/仓储 + 写时引用完整性（引用不存在的
                                  evidence/claim → ReferenceNotFoundError 拒绝）
backend/app/api/research.py       POST/GET claims、theses、corporate-events
backend/alembic                   m6 迁移（三表真实建表）
验证: backend pytest 121 passed
      追溯链测试：Thesis → Claim → Evidence → source 全链存在
      假引用 422（claim.evidence_not_found / thesis.claims_not_found）
```

## 已完成 Milestone

### M5 — PIT / Snapshot（DONE，2026-08-28）

```text
backend/app/domain/snapshot.py     EvidenceSnapshot（frozen 语义、内容寻址 snapshot_id、
                                   §24 字段全集）、SnapshotItem、ResearchRun 最小骨架
backend/app/storage/snapshot_repo.py
                                   build = PIT gate（available_time <= as_of 双重强制）+
                                   get-or-create 幂等（同 (instrument, as_of) 永不改写历史）
backend/app/api/snapshots.py       POST /snapshots + GET /snapshots/{id} + POST /research-runs
backend/alembic                    m5 迁移（evidence_snapshots + research_runs 真实建表）
验证: backend pytest 112 passed
      §74 强制测试：未来证据不可见（> as_of）、边界 == as_of 可见、
      幂等重建同快照、后续新数据不改历史快照、不同 as_of 产生新快照
      LIVE: collect(1) → snapshot snap_c5d14844(1 item) → run 绑定 PASS
```

### M4 — Evidence（DONE，2026-08-28）

```text
backend/app/domain/evidence.py     EvidenceRecord（§22 字段全集 + 内容寻址 evidence_id +
                                   content_hash）、AuthorityLevel（§25 A1-D）、
                                   FactStatus（§26 八态）、EvidenceType、SourceManifest
backend/app/storage/orm.py         SQLAlchemy 2 ORM（evidence_records + source_manifests，
                                   唯一约束 (source, content_hash) 实现去重）
backend/app/storage/repository.py  幂等 save（同源同内容 → created=False）、
                                   PIT 可见性过滤 list、manifest 台账
backend/app/services/evidence_collector.py
                                   SourceResult → Evidence 采集服务（失败记录 manifest，
                                   不伪造数据）
backend/app/api/evidence.py        POST /api/v1/evidence/collect + GET /api/v1/evidence
backend/alembic/                   初始迁移（真实建表 asro_dev.db，autogenerate 生成）
验证: backend pytest 100 passed（含 live 采集入库回归）
      失败采集 → manifest 记录 network_error、evidence 为空（不伪装）
```

---

### M3 — Source Layer（DONE，2026-08-28）

```text
backend/app/sources/base.py          SourceResult 契约（八态 status、错误分类、retryable、
                                     as_of/attempted_at；成功必须带记录、no_data 必须带原因；
                                     契约蓝本 OpenAlpha CN providers/base.py，MIT 已注明）
backend/app/sources/provider.py      BaseProvider 显式结果构造器
backend/app/sources/registry.py      capability registry + 有序 fallback（异常防护，
                                     耗尽后合成 SOURCE_UNAVAILABLE，永不静默空返回）
backend/app/sources/health.py        source health 状态机（连续失败→unavailable）
backend/app/sources/cache.py         分能力 TTL 缓存（market_data 5s … instrument 24h）
backend/app/sources/runtime.py       进程级 runtime（resolve_cached）
backend/app/sources/providers/tencent_quote.py
                                     腾讯实时行情 provider（GBK 报文解析、真实字段布局）
backend/app/api/market_data.py       GET /api/v1/market-data/quote?instrument=…
backend/app/api/source_health.py     GET /api/v1/source-health
验证: backend pytest 83 passed（契约不变量/fallback/health/缓存/mock 报文/live）
      LIVE: 茅台 1292.30(-0.81%) 总市值 1.615万亿 event_time 2026-08-27T16:14:55
            平安银行 11.59 按名称解析 → SZSE:000001；health available=true
```

### M2 — Instrument（DONE，2026-08-28）

```text
backend/app/domain/instrument.py   InstrumentProfile（任务书 §19 字段全集）
backend/app/domain/code_norm.py    A 股代码规范化 + 板块分类
                                   （沪主板60/科创板688-689/深主板000-003/创业板300-302/北交所43-92）
backend/app/domain/catalog.py      seed 目录（12 只真实标的，覆盖四板 + 五大研究风格）
backend/app/api/instruments.py     GET /api/v1/instruments?query= / GET /instruments/{id}
frontend                           标的搜索卡片（真实 API 调用）
验证: backend pytest 49 passed（四板回归/前缀变体/矛盾提示拒绝/名称别名/缺数据契约）
      浏览器实测: 600519→按代码 / 茅台→按名称 / CATL→按别名 / 未知→空
```

### M1 — 工程基线 + i18n + theme（DONE，2026-08-28）

正式仓库内建立（非搬迁 TideTrading，见 ADR-001 D1/D4）：

```text
backend/   FastAPI + Pydantic v2；/api/v1/health；稳定 error_code 信封
           （common.not_found/validation_error/internal_error…）；
           message_code + Accept-Language normalize（zh*→zh-CN）
frontend/  Vite + React 19 + TS；TanStack Query 接真实后端；react-i18next
           （zh-CN/en-US 资源、system 解析、手动覆盖持久化）；三态主题
           （data-theme + prefers-color-scheme 跟随 + 手动覆盖）；
           Design Tokens（tokens.css light/dark 双套，语义色与主题解耦，
           A股红涨绿跌 CN 默认 + data-updown=intl 可配置）
```

真实验证（浏览器实测）：

```text
后端连通 PASS（/api/v1/health → ok · v0.1.0）
三态主题切换 PASS；OS 深浅跟随 PASS；手动覆盖不被系统覆盖 PASS
语言三态（system/zh-CN/en-US）切换 PASS（h1/lang 属性/localStorage）
涨跌语义色实测：light up=#c23a2f(红) down=#2e7d54(绿)；dark 同语义提亮；intl 惯例翻转 PASS
frontend build PASS（vite）
```

### M0 — 上游/底座源码审计（DONE，2026-08-28）

六个候选完成源码级审计（结构/运行/测试/许可证）：

```text
TideTrading    ADOPT  主工程基线（live A股行情验证 PASS，102 端点，frontend build PASS）
OpenAlpha CN   ADAPT  领域契约蓝本（105 tests PASS，25 端点验证）
觀瀾            REFERENCE_ONLY（无 LICENSE，仅 UX 参考）
Qlib           REFERENCE_ONLY（import PASS，闭环验证 defer M21/M22）
RD-Agent       REJECT（import PASS，M20 后可重评）
TradingAgents  REFERENCE_ONLY（27 tests PASS，无 A 股数据层）
```

产出：`docs/current-architecture-audit.md`、`docs/upstream-evaluation.md`、
`docs/adr/ADR-001-main-engine-baseline.md`。

---

## Milestone 依赖关系

```text
M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12
M12 → M13 → M14
M12 → M15 → M16 → M17 → M18
M18 → M19 → M20
M18 → M21 → (M22 | NOT_REQUIRED)
M12 → M23 → M24 → M25 → M26 → M27
M27 + M20 + M22 → M28 → M29
```

M13/M14 与 M15–M18 可交错推进，但各自 DoD 独立成立。

---

## 长期不变量（所有 Milestone 必须遵守）

- 所有正式交付物只进入 `hyperhaohao/A-Share-Research-OS`；
- 不允许伪完成（TODO/placeholder/mock 冒充真实业务）；
- i18n（zh-CN/en-US/system）与 theme（system/light/dark）从 M1 起是一级能力；
- PIT 与 Traceability 约束从 M4 起强制；
- Prediction 一旦创建不可修改；
- ReportVersion 永不覆盖旧版本；
- 每个 Milestone 的代码、测试、migration、文档同一阶段闭环。
