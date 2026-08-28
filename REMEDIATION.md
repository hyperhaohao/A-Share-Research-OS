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
| R1 | Real Research Data | DONE | 公告/财务/新闻/资金/行业/宏观 provider + 行情 fallback，3-5 只真实股票形成 Evidence |
| R2 | Full Research Pipeline | DONE | Analyst 集 → ClaimCompiler → ThesisBuilder → Debate → Scenario → Valuation(证据输入) → Risk → Report 全链无手工补链 |
| R3 | AI / Quant / Continuous | DONE | LLMProvider（OpenAI-compatible）接入主链 + Copilot + Quant 实接 + 后台 scheduler 服务 + Monitor/Delta/Full |
| R4 | Research Workspace | DONE | Stock Workspace 九 Tab + Copilot + React Flow 图 + Interactive Report 补全（真实 API） |
| R5 | Production Research E2E | DONE | 4-6 只不同风格真实 A 股 Live Research E2E 全链 + 长时运行测试 + 生产复验 |

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

## R1 — Real Research Data（DONE，2026-08-28）

### 任务清单

| # | 任务 | 状态 |
|---|------|------|
| R1.1 | 行情 fallback provider：EastmoneyQuoteProvider（腾讯→东财链） | DONE |
| R1.2 | Announcements：CninfoAnnouncementsProvider（A2 主）→ EastmoneyAnnouncementsProvider（B2 备） | DONE |
| R1.3 | Financials：EastmoneyFinancialsProvider（ZYZB 指标+zcfzb 资产负债，NOTICE_DATE 锚定 PIT） | DONE |
| R1.4 | News：EastmoneyNewsProvider（C2，低于公告） | DONE |
| R1.5 | Capital Flow：EastmoneyCapitalFlowProvider（量/额/换手；主力资金显式 unavailable） | DONE |
| R1.6 | Industry：EastmoneyIndustryProvider（EM2016 三级行业链；peers 显式 pending） | DONE |
| R1.7 | Macro/Policy：EastmoneyMacroPolicyProvider（官方机构白名单标注） | DONE |
| R1.8 | Live 验证：4 只（沪主板/深主板/创业板/科创板）× 4 能力全链 Evidence+Manifest | DONE |

### R1 DoD

```text
[x] 七能力 provider 全部接入统一 SourceResult 语义（http.py 显式失败映射；
    禁止 异常→[] / 失败→no_data；CNINFO 实测 504 → 链内 fallback 生效）
[x] Live 验证通过（test_r1_live.py，@live 标记，离线自动 skip）：
    4 只不同板块真实 A 股 × market/announcement/financial/news →
    真实 Evidence（公告=official_disclosure A2/B2；新闻=media_report C2；
    财务 NOTICE_DATE 锚定 PIT）+ SourceManifest 可追溯
[x] Git checkpoint
```

---

## R2 — Full Research Pipeline（DONE，2026-08-28）

### 任务清单

| # | 任务 | 状态 |
|---|------|------|
| R2.1 | Analyst 集：Industry/Financial/Event/News/CapitalFlow（BaseSnapshotAnalyst 模板方法，快照钉住证据） | DONE |
| R2.2 | ClaimCompiler：claims 由分析师创建（引用强制），pipeline 聚合去重 | DONE |
| R2.3 | ThesisBuilder：官方披露/确认事实→supporting，媒体→context；confidence=均值 | DONE |
| R2.4 | Debate 入主链（确定性 baseline 一轮，引用现有 Claim/Evidence） | DONE |
| R2.5 | ScenarioEngine：Bear 30/Base 45/Bull 25（和=100），假设+触发条件 | DONE |
| R2.6 | ValuationInputBuilder：PE/PB/PS 输入全部来自证据（价格/市值/EPS/BVPS/营收），目标倍数为显式记录假设；DCF/DDM/分位显式 not-computable | DONE |
| R2.7 | RiskManager：thesis_risk/invalidation/data_availability 三类，携带 supporting claims/evidence | DONE |
| R2.8 | Pipeline 全链改造 + SSE 新阶段（snapshot_built/claims_compiled/thesis_ready/debate_ready/scenario_ready/risk_ready） | DONE |
| R2.9 | Live 验证：真实贵州茅台全链（无手工补链）PASS；claim→报告正文可验证 | DONE |

---

## R3 — AI / Quant / Continuous（DONE，2026-08-28）

| # | 任务 | 状态 |
|---|------|------|
| R3.1 | LLMProvider：OpenAICompatibleProvider（generate_structured/text/stream/model_info/usage 累计）+ DeterministicStubProvider | DONE |
| R3.2 | LLM 边界落地：explain_with_llm 仅叙述层；引用越界 → invalid_citations 标记；LLM 路径零 Claim/Evidence 写入（测试断言） | DONE |
| R3.3 | Copilot：ask API 增加 copilot=true（LLM 配置时走 narrative，未配置走确定性 baseline） | DONE |
| R3.4 | Narrative Layer：narrativize_report（LLM 翻译 zh→en 填充 text_en；失败/未配置 → 原文+语言标记，绝不伪造） | DONE |
| R3.5 | Quant：EastmoneyKlineProvider（historical_data）+ 确定性 quant 引擎（5d 动量信号 t-1 无前视、long/flat 回测、年化/Sharpe/回撤/胜率固定数值测试）+ QuantBrief 进 Research State（pipeline quant 阶段） | DONE |
| R3.6 | 后台 scheduler 服务：backend/scheduler_worker.py（SIGTERM 优雅退出）+ compose 第三服务（ASRO_SCHEDULER_INTERVAL） | DONE |
| R3.7 | Continuous：monitor handler 接 Materiality → DELTA 时以新快照重编译并追加 delta change_reason 的 ReportVersion；scheduler 集成测试 | DONE |

---

## R4 — Research Workspace（DONE，2026-08-28）

| # | 任务 | 状态 |
|---|------|------|
| R4.1 | Stock Workspace 九 Tab 补齐（Overview/Timeline/Graph/Thesis/Financials/Valuation/Evidence/Reports/Predictions，双栏布局+Copilot 侧栏） | DONE |
| R4.2 | Research Copilot 侧栏（最新报告 ask + copilot=true；LLM 未配置走确定性 baseline；引用/主张展示） | DONE |
| R4.3 | Thesis UI 全字段（status/confidence/supporting+opposing/catalysts/risks/triggers/invalidate/时间） | DONE |
| R4.4 | Financial UI（最近期指标卡 + 多期 ROE/营收 SVG 趋势图，真实财务证据数据） | DONE |
| R4.5 | Valuation UI（方法/隐含价格/空间/输入缺失显式/场景绑定） | DONE |
| R4.6 | React Flow Research Graph（@xyflow/react：zoom/pan/minimap/kind 过滤/节点详情/upstream+downstream 追溯/tokens 主题） | DONE |
| R4.7 | Interactive Report 补全：RevisionPanel（版本历史/propose diff/accept/reject） | DONE |

---

## R5 — Production Research E2E（DONE，2026-08-28）

| # | 任务 | 状态 |
|---|------|------|
| R5.1 | Live Research E2E：4 只（沪/深主板、创业板、科创板）× 全链（pipeline→报告→monitor→预测→验证），仅经公开 API，无手工补链 | DONE |
| R5.2 | 长时运行：scheduler 连续 tick/retry 退避/restart 恢复/幂等/同标的互斥（test_scheduler 6 场景） | DONE |
| R5.3 | 生产复验：三容器（backend/frontend/scheduler）构建+启动全 healthy；备份恢复演练完成（发现并修复 WAL 残留恢复缺陷——restore.sh 现移除 -wal/-shm） | DONE |
| R5.4 | Final Reviewer Pass：TODO/FIXME/占位/Manifest/Gate 绕过/吞异常/mock 全扫描 —— 仅剩合法抽象基类标记；修复 restore.sh WAL 缺陷 | DONE |

---

## 最终结论（2026-08-28）

```text
R0 PASS — 状态一致/Manifest 真实值/Gate 无绕过/测试分类真实
R1 PASS — 七能力真实数据源 + 行情/公告双 fallback + 4 标的 live 证据链
R2 PASS — 8 分析师 + Claim/Thesis/Debate/Scenario/Valuation(证据输入)/Risk 全链，
          live 全链无手工补链
R3 PASS — LLMProvider(OpenAI-compatible)+引用边界+Copilot+双语 Narrative+
          确定性 Quant 引擎(kline→因子→回测→指标→QuantBrief)+后台 scheduler
          服务+Delta→新版本
R4 PASS — 九 Tab Workspace+Copilot 侧栏+Thesis/Financial/Valuation UI+
          React Flow 图谱(主题/i18n)+Revision Diff/Accept/Reject
R5 PASS — 4 标的 live E2E+长时运行测试+三容器生产部署（全 healthy）+
          备份恢复演练（修复 WAL 残留缺陷）+Reviewer 全扫
全量验证：backend 277 tests PASS；frontend 8 tests + build PASS；
生产栈 live：贵州茅台 1290-1294 实时行情/公告/财务/新闻经 API 与 UI 全通。
已知限制：docs/known-limitations.md（节假日历近似、基准指数序列、认证首版未含）。
```

---

## 决策记录

- R1 数据源优先级：公告=巨潮（法定披露平台，authority A2）；财务=公开财报接口；
  新闻=主流财经源（authority B2/C2，不得与公告同级）。
- LLM 边界：Evidence First, LLM Reasoning Second；LLM 输出一律携带 evidence 引用，
  引用完整性校验对 LLM 产物同等生效。
- Quant：采用方案 A（TideQuantAdapter），完成后维持 M22 NOT_REQUIRED 结论。
- 调度：第一版单进程 scheduler 服务（compose 第三服务），量大后再引入队列。
