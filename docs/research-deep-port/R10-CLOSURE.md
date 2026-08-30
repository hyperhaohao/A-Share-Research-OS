# R10-CLOSURE — 观澜研究能力深迁植 · 最终验收

> 依据 `docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md` §24 完成定义、
> §20.2 十四问、§19 测试战略。
> 黄金场景：**000831 中国稀土资产整合研究**（真实栈 compose backend，全程 API 驱动，无 Mock）。
> Donor：`jesson-hh/financial-analyst` @ `98f1398`；License Gate：无 LICENSE →
> 全程 REFERENCE_ONLY / BEHAVIORAL ADAPTATION（THIRD_PARTY_NOTICES §3）。
> 验收日：2026-08-31。逐项证据：`R10-EVIDENCE.md`（24/24 PASS，本目录）。

---

## 一、方案 §24 完成定义逐项

| # | 条件 | 结论 | 证据 |
|---|---|---|---|
| 1 | R0–R9 完成 | **PASS** | 各 R-MANIFEST（本目录 manifests/）；PLAN.md R 线全 [x] |
| 2 | Research Product 定位完成 | **PASS** | 7 类契约（R5）+ product_type 落库 + 类型化 Artifact 标题「中国稀土 · 事件调查」 |
| 3 | Source Trust 完成 | **PASS** | T0-T4 读时派生映射 + 未知保守 T4 + market_quote 持牌转载=T0（R2-MANIFEST） |
| 4 | Citation Verification 完成 | **PASS** | Extraction 契约 + 确定性反查（span 包含 + 数字一致 + 信任升级三防线）；R2 真实公告 live verify 4/4 |
| 5 | Industry Driver 完成 | **PASS** | IndustryDriver domain + API + 引用反查强制；稀土真实 Driver（广晟减持，2 条真实证据引用） |
| 6 | Transmission 完成 | **PASS**（框架+数据路径就绪） | Transmission domain/API/视图接线完成；语料暂无稀土链级传导真实证据句 → 数据诚实置空（§23 禁造假；R3-MANIFEST deviation 登记），证据出现即入 |
| 7 | Narrative 完成 | **PASS** | IndustryNarrative domain + 可复算温度（insufficient 显形，不造数字）+ 稀土真实叙事 1 条 |
| 8 | Commander Autonomous Loop 完成 | **PASS** | 九类焦点意图路由 + 结构化 Plan（meta_json）+ Missing Data Loop（有界第二遍补采）+ profile 收敛（profile_applied 显形裁剪）；R4-LIVE-VERIFY 黄金问题全事件链 PRESENT |
| 9 | Research Products 完成 | **PASS** | P0 四类（company/industry/event/thesis_review）经 pipeline 落 product_type；P1 三类契约就绪（市场级编译器在 R8 Inbox 数据面就绪后接） |
| 10 | Non-Quant Experience 完成 | **PASS** | LLM 九字段结构化精炼（refined_json 双存，无 KEY 422 显形）+ 四方法非量化验证 + Playbook 检索（Playbook≠Evidence 结构锁死）；IC/回测未实现=§12.3 明确禁止 |
| 11 | Research Memory 完成 | **PASS** | research_memories 表 + 七类 + scope 检索 + candidate→active→retired 晋升门 + from_experience（仅 APPROVED）+ Memory≠Evidence 结构断言 |
| 12 | Research Inbox / Thesis Diff 完成 | **PASS** | GET /research-inbox（六类聚合）+ thesis-diff 确定性影响分析 + apply（append-only 新 Thesis 行 + Artifact 链 + PIT pinned 校验） |
| 13 | Research Graph 完成 | **PASS** | 全部研究产物注册 Artifact（含 R8 补齐 thesis、R9 语义对象）；`/artifacts/graph` 真实栈节点覆盖 research_run/report/version/thesis/prediction/experience_card/screening_run/strategy_version/industry_driver/narrative；edges 148+ |
| 14 | 000831 黄金场景真实跑通 | **PASS** | R10-EVIDENCE.md 24/24 PASS（下表逐项） |

## 二、黄金场景 24/24（R10-EVIDENCE.md 摘录）

```text
1  Commander 意图/计划    focus=event profile=event product=EVENT_INVESTIGATION
2  研究管线完成           run_d72fccad948b completed（真实采集）
3a 证据层                744 条真实证据
3b Claims               2396 条（全部带可反查引用）
3c Current Thesis       191 条 append-only
4a Source Trust         authority=B2 → T3 映射
4b Citation 反查        编造数字 → rejected number_not_in_source
5a/5b Industry Driver/Narrative  真实证据引用各 1 条（广晟减持）
6  Signal Ladder        level=B rule=股东减持披露（证据引用强制）
7a/7b Thesis Diff       new_evidence=20 → apply → 新 Thesis ths_71894754…（旧版保留）
8  Research Product     Artifact 标题「中国稀土 · 事件调查」
9  Research Inbox       24 项聚合（新证据/重要性/请求/失败采集）
10a-10d Experience      原炼验用（case+反例搜索验证 → 批准门 → Playbook 10 条）
11a-11c Memory          candidate→active 晋升门 + Memory≠Evidence 结构锁死
12 Research Graph       missing=无（方案 §15.1 类型覆盖）
13 PIT                  snapshot_built 事件强制 evidence.available_time <= as_of
14 报告渲染             markdown 27210 chars
```

## 三、§20.2 十四问可回答性

| 问 | 系统给出答案的位置 |
|---|---|
| 1 当前结论 | Thesis Center / GET /theses（191 条 append-only） |
| 2 结论由哪些 Claim 构成 | Thesis.supporting/opposing_claims（claims_compiled 事件计数） |
| 3 Claim 来自哪些 Evidence | claims.supporting_evidence_refs（全链反查） |
| 4 证据当时是否已公开 | PIT 快照门（snapshot items = available_time ≤ as_of） |
| 5 哪些是正式事实 | claim.fact_status + source_trust 升级规则（质量门 FAIL 强制） |
| 6 哪些是市场共识 | fact_status=market_expectation 的 Claim |
| 7 哪些是线索/传闻 | fact_status=rumor + source_trust=T4 标注（R2 升级防线禁止其成事实） |
| 8 最重要的反方证据 | inbox + thesis opposing claims + R6 counterexample_search |
| 9 什么事件使 Thesis 失效 | risks/invalidators（card/thesis 字段）+ Signal Ladder 规则 |
| 10 与上一版本的变化 | Thesis Diff（affected_claims/new_support/possibly_stale） |
| 11 新证据为何 Material | materiality reasons_json + ThesisDiff suggested_action |
| 12 以后监控什么 | Monitor + Signal Ladder 规则（A/B 分级） |
| 13 沉淀了什么 Experience | Experience Workbench（原炼验用 + Playbook） |
| 14 哪些 Memory 只是方法 | Memory 条目结构无 evidence 字段（类型=research_method 等） |

## 四、测试与构建（验收日全量）

```text
backend:  pytest 全量 exit 0（含 R2 5/R3 4/R5 4/R6 3/R7 3/R8 3/R9/G4 3/G10 新测试）
frontend: vitest 30/30 PASS；tsc + vite build PASS
E2E:      Playwright 30/30 PASS（产品流 18 + 视觉基线 12）
golden:   tests/test_r10_golden.py 24/24 PASS（真实栈 API 全程）
```

## 五、偏离与边界（如实，非降级）

1. **Transmission 数据**：语料暂无稀土链级传导真实证据句 → 数据诚实置空；
   引擎/视图/API 全就绪，证据出现即入（§23 禁造假优先于 DoD 字面）。
2. **市场级产品编译器**（雷达/映射/简报）：契约已定义；编译器在 R8 Inbox
   数据面就绪后接（顺序依赖，manifests/R5-MANIFEST sequencing note）。
3. **LLM 结构化精炼/LLM 步骤**：管道+schema 校验+422 显形就绪；
   实际运行需 ASRO_LLM_API_KEY（外部阻塞项）。
4. **IC/回测/ML/自动交易**：按方案 §3 NO NEW DEVELOPMENT——现有能力保留冻结。

## 六、结论

> **Research Capability Deep Port — R0–R9 全部 DONE，R10 CLOSURE PASS。**
>
> 观澜非量化研究能力（Source Trust / 引用反查 / 产业 Driver·Narrative /
> 自主研究循环 / 类型化研究产品 / 非量化 Experience / Memory / Inbox /
> Thesis Diff / Graph 整合）已成为 ASRO Evidence/PIT/Claim/Thesis/Version/
> Monitor/Validation 内核之上的**可追溯、可验证、可持续更新的一等研究能力**。
> 数据边界（无真实证据处）全部按 §25 显形，不编造。
