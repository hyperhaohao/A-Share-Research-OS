# REMEDIATION.md

# A-Share Research OS — 整改状态源（唯一）

> 本文件是整改（R0–R5）的执行状态唯一来源。
> 旧 M0–M29 记录保留于 git 历史与 `docs/milestones/`（历史，不代表当前完成结论）。
>
> 整改依据：`A-Share-Research-OS-整改实施任务书.md`
> 原则：保留现有 Kernel，修正「对象存在 = 完成」的错误判定，
> 补齐真实数据 → 真实研究 → 真实调度 → 真实端到端闭环。

---

## 状态图例

```text
TODO      未开始
DOING     进行中（当前只能一个）
DONE      已通过该阶段 DoD
BLOCKED   真实外部阻塞
```

---

## 阶段总览

| 阶段 | 内容 | 状态 | DoD 摘要 |
|------|------|------|----------|
| R0 | State & Integrity Repair | DONE | 状态一致 / Manifest 无占位 / Gate 无绕过 / 测试分类真实 |
| R1 | Real Research Data | TODO | 公告/财务/新闻/资金/行业/宏观 provider + 行情 fallback，3-5 只真实股票形成 Evidence |
| R2 | Full Research Pipeline | TODO | Analyst 集 → ClaimCompiler → ThesisBuilder → Debate → Scenario → Valuation(证据输入) → Risk → Report 全链无手工补链 |
| R3 | AI / Quant / Continuous | TODO | LLMProvider（OpenAI-compatible）接入主链 + Copilot + Quant 实接 + 后台 scheduler 服务 + Monitor/Delta/Full |
| R4 | Research Workspace | TODO | Stock Workspace 九 Tab + Copilot + React Flow 图 + Interactive Report 补全（真实 API） |
| R5 | Production Research E2E | TODO | 4-6 只不同风格真实 A 股 Live Research E2E 全链 + 长时运行测试 + 生产复验 |

---

## R0 — State & Integrity Repair（DONE，2026-08-28）

### 任务清单

| # | 任务 | 状态 |
|---|------|------|
| R0.1 | 建立 REMEDIATION.md（本文件）作为整改状态源 | DONE |
| R0.2 | STATUS.md 重写为整改态（移除「全部完成」结论；历史移至 milestones） | DOING |
| R0.3 | ROADMAP.md 增加整改阶段表（保留 M0-M29 历史） | DONE |
| R0.4 | PLAN.md 纳入 R0-R5 阶段 | DONE |
| R0.5 | RunManifest 真实值：git commit / config digest SHA256 / 真实 random_seed | DONE |
| R0.6 | QualityGate 绕过修复（report_compiler `or True`、估值假设占位） | DONE |
| R0.7 | 测试重分类：pytest 标记 api_integration / live；docs/testing.md 更新 | DONE |
| R0.8 | Build + 全量测试 + checkpoint（backend 240 + frontend 8 PASS） | DONE |

### 已确认的真实缺口（整改基线）

```text
1. Provider 仅腾讯行情一个            → R1
2. 无公告/财务/新闻/资金/行业/宏观链  → R1
3. Pipeline 仅 market→analyst(facts)→report，无完整 Analyst→Claim→Thesis→
   Debate→Scenario→Valuation→Risk 链  → R2
4. MarketAnalyst 仅行情事实提取       → R2
5. Debate 为确定性拼装（保留为 fallback）→ R2/R3
6. 无 LLM Provider 进入主流程         → R3
7. Explain 为关键词匹配（保留为 baseline）→ R3
8. 英文报告部分内容直接复用中文原文   → R3（narrative layer）
9. RunManifest 占位值（pipeline.py）  → R0.5
10. Gate 绕过（report_compiler or True）→ R0.6
11. Quant 未进正式主链                → R3（方案 A: TideQuantAdapter）
12. Scheduler 仅手动 tick             → R3（后台 worker 服务）
13. Workspace 信息架构不完整          → R4
14. E2E 为 API Integration（monkeypatch）→ R0.7 重分类 + R5 Live E2E
```

### R0 DoD

```text
[x] STATUS / ROADMAP / README 状态一致（整改态）
[x] RunManifest 无 placeholder（真实 git commit / SHA256 config / 真实 seed）——
    pipeline 端到端验证：code_commit=d4c7cef…、config_digest=64位SHA256、seed≠0
[x] QualityGate 无绕过（新增 missing_data_undisclosed FAIL 规则；
    估值假设来自真实引擎输入；FAIL 阻止 publish 由既有测试覆盖）
[x] 测试分类真实（api_integration / live 标记 + docs/testing.md）
[x] Build PASS
[x] 全量 Tests PASS（backend 240 / frontend 8）
[x] Git checkpoint
```

---

## R1 — Real Research Data（TODO）

### 任务清单

| # | 任务 | 状态 |
|---|------|------|
| R1.1 | 行情 fallback provider（腾讯 → 东财/其他稳定源） | TODO |
| R1.2 | Announcements provider（巨潮 CNINFO） | TODO |
| R1.3 | Financials provider（三大报表 + 规范化指标） | TODO |
| R1.4 | News provider（至少一个真实财经源） | TODO |
| R1.5 | Capital Flow provider（成交/换手/主力资金，缺失显式） | TODO |
| R1.6 | Industry provider（行业/概念/同业，结构化基础版） | TODO |
| R1.7 | Macro/Policy provider（官方源，topic/keyword/date） | TODO |
| R1.8 | Live 验证：3-5 只不同类型真实 A 股 × 4 能力 → Evidence + Manifest 可追溯 | TODO |

### R1 DoD

```text
[ ] 七能力 provider 全部接入统一 SourceResult 语义（禁止 异常→[] / 失败→no_data）
[ ] Live 验证通过并记录
[ ] Git checkpoint
```

---

## R2 — Full Research Pipeline（TODO）

### 任务清单

| # | 任务 | 状态 |
|---|------|------|
| R2.1 | AnalystOrchestrator + Financial/Event/News/Industry/Macro/CapitalFlow/Risk Analyst（按数据能力逐个闭环） | TODO |
| R2.2 | ClaimCompiler（Brief[] → Claim[]，强制引用） | TODO |
| R2.3 | ThesisBuilder（Claim[] → Thesis[]，强制引用） | TODO |
| R2.4 | Debate 接入主链（保留确定性 fallback；输出引用现有 Claim/Evidence） | TODO |
| R2.5 | ScenarioEngine（Bear/Base/Bull + valuation_result） | TODO |
| R2.6 | ValuationInputBuilder（Financial Evidence → 规范化指标 → 引擎输入，可追溯） | TODO |
| R2.7 | RiskManager（结构化 risk 对象，非模板） | TODO |
| R2.8 | ResearchManager 汇编 + Pipeline 全链改造 | TODO |
| R2.9 | Live 验证：至少一只真实股票全链执行（无手工 POST 补链） | TODO |

---

## R3 — AI / Quant / Continuous（TODO）

| # | 任务 | 状态 |
|---|------|------|
| R3.1 | LLMProvider（OpenAI-compatible：generate_structured/text/stream/model_info/usage） | TODO |
| R3.2 | LLM 边界落地（Evidence First；禁造事实；引用强制） | TODO |
| R3.3 | Copilot Explain/Refresh 接入 LLM（保留确定性 baseline） | TODO |
| R3.4 | 双语 Narrative Layer（en-US 不再直接复用中文原文；引用仍指原文） | TODO |
| R3.5 | Quant：TideQuantAdapter（历史→因子→模型→回测→指标→QuantBrief 进 Research State） | TODO |
| R3.6 | 后台 scheduler 服务（compose 第三服务，periodic tick） | TODO |
| R3.7 | Continuous Research：Monitor→Materiality→Delta（受影响 Claim/Thesis/Analyst→Revalue→NewVersion）/Full 接主 Pipeline | TODO |

---

## R4 — Research Workspace（TODO）

| # | 任务 | 状态 |
|---|------|------|
| R4.1 | Stock Workspace 九 Tab 补齐（Overview/Timeline/Graph/Thesis/Financials/Valuation/Evidence/Reports/Predictions） | TODO |
| R4.2 | Research Copilot 侧栏 | TODO |
| R4.3 | Thesis UI 全字段 | TODO |
| R4.4 | Financial UI（报表+趋势图 ECharts） | TODO |
| R4.5 | Valuation UI（方法/情景/假设/同业/分位/缺失） | TODO |
| R4.6 | React Flow Research Graph（zoom/pan/filter/节点详情/主题/i18n） | TODO |
| R4.7 | Interactive Report 补全（Counter Evidence/Revalue/Revision Diff/Accept/Reject/Version History） | TODO |

---

## R5 — Production Research E2E（TODO）

| # | 任务 | 状态 |
|---|------|------|
| R5.1 | Live Research E2E：4-6 只不同风格真实 A 股全链（含预测/验证/增量） | TODO |
| R5.2 | 长时运行测试（scheduler 连续/retry/restart/idempotency/source failure recovery） | TODO |
| R5.3 | 生产复验（compose/migration/health/backup/restore drill） | TODO |
| R5.4 | Final Reviewer Pass（按整改清单 §36 重扫） | TODO |

---

## 决策记录

- R1 数据源优先级：公告=巨潮（法定披露平台，authority A2）；财务=公开财报接口；
  新闻=主流财经源（authority B2/C2，不得与公告同级）。
- LLM 边界：Evidence First, LLM Reasoning Second；LLM 输出一律携带 evidence 引用，
  引用完整性校验对 LLM 产物同等生效。
- Quant：采用方案 A（TideQuantAdapter），完成后维持 M22 NOT_REQUIRED 结论。
- 调度：第一版单进程 scheduler 服务（compose 第三服务），量大后再引入队列。
