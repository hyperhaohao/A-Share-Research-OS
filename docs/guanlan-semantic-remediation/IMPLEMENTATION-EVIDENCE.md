# G14 — IMPLEMENTATION-EVIDENCE（观澜语义迁移实施证据）

> 每项含：Requirement ID / Code Path / Production API / Migration / Test /
> Result / Real Artifact / Remaining Limitation / Status。

## E-G1 真实 Industry Graph

| 项 | 值 |
|---|---|
| Requirement | 任务书 §G1（产业链/环节/传导边/产物/公司位置/边证据） |
| Code Path | app/domain/industry_graph.py · app/services/industry_graph_service.py · app/storage/industry_graph_orm.py · app/api/industry_graph.py |
| Production API | /industry-graph/chains · /chains/{id}/graph?as_of · /segments · /edges · /edges/{id}/evidence(POST/DELETE) · /positions · /instruments/{id}/positions · /instruments/{id}/peers · /seed/rare-earth |
| Migration | b9c0d1e2f3a6（六表） |
| Test | tests/test_g1_industry_graph.py（7 用例全 PASS） |
| Real Artifact | 稀土链 seed → industry_graph Artifact（chain domain） |
| Remaining Limitation | 边证据需研究运营持续挂载；自动抽取待 LLM/NLP 线 |
| Status | **PASS** |

## E-G2 产业语义 PIT/证据治理

| 项 | 值 |
|---|---|
| Requirement | §G2（Ownership Gate / 服务端温度 / as_of 重放 / 五轴 / 显式采集 / INCOMPLETE_PROVENANCE） |
| Code Path | app/services/industry_graph_service.py（global_position）· app/application/industry_semantic.py · app/api/industry_semantics.py · app/services/industry_view_service.py |
| Production API | /industry-semantics/*（as_of）· /industry-graph/chains/{id}/global-position · /views/industry（去隐式写） |
| Migration | c0d1e2f3a6b7（chain/segment/edge/contrary 列） |
| Test | tests/test_g2_semantics_pit.py（7 用例全 PASS） |
| Remaining Limitation | 五轴「技术/政策」依赖语义对象积累；五轴「资源/产能/成本」由图谱位置与边派生 |
| Status | **PASS** |

## E-G3 Experience 原—炼—验—用

| 项 | 值 |
|---|---|
| Code Path | app/services/experience_service.py（rule_component/approve/ version_diff/validation_metrics）· app/api/experience.py |
| Production API | /experience-cards/{id}/rule-component · /metrics · /versions/diff · approve/reject（审计事件） |
| Migration | c1d2e3f4a6b7（signals/scope/usage_guidance/counterexamples/validation_method/verdict） |
| Test | tests/test_g3_experience.py（10 用例全 PASS） |
| Real Artifact | experience_card Artifact（既有）+ 规则组件（机器可消费） |
| Remaining Limitation | LLM 精炼 BLOCKED_EXTERNAL；directional_ic 待 G8 因果方向记录 |
| Status | **PASS** |

## E-G4 Typed Dataflow Workflow

| 项 | 值 |
|---|---|
| Code Path | app/services/workflow_typed.py · app/storage/workflow_io_orm.py · app/api/workflow_typed.py |
| Production API | /workflows-typed/definitions · /runs · /runs/{id} · /runs/{id}/control |
| Migration | c2e3f4a5b6c8（workflow_node_io） |
| Test | tests/test_g4_workflow_typed.py（6 用例全 PASS） |
| Remaining Limitation | 15 类节点执行器深度不一（prediction 节点待 G8 因果方向）；UI 画布接线为 v1 复用 |
| Status | **PASS** |

## E-G5 Experience-driven Screening

| 项 | 值 |
|---|---|
| Code Path | app/services/experience_screening.py（ScreenCompiler/ExperienceScreenService）· app/api/screening_v2.py |
| Production API | /screening-v2/definitions · /definitions/{id}/publish · /definitions/{id}/run · /runs/{id} |
| Migration | c3f4a5b6c8d9（screen_definitions/screen_definition_runs） |
| Test | tests/test_g5_screening.py（6 用例全 PASS） |
| Real Artifact | ScreenRun Artifact（universe+结果） |
| Remaining Limitation | 因子值受证据层限制（无因子引擎）；uncompiled 自由文本显形 |
| Status | **PASS** |

## E-G6 Executable Strategy Lab

| 项 | 值 |
|---|---|
| Code Path | app/services/backtest_engine.py · app/api/strategies.py（backtest-v2） |
| Production API | POST /strategies/{id}/backtest-v2 |
| Test | tests/test_g6_backtest.py（9）+ tests/test_g6_strategy_api.py（4）全 PASS |
| Real Artifact | strategy_backtest Artifact |
| Remaining Limitation | 涨跌停/停牌规则覆盖典型场景；分红除权未建模 |
| Status | **PASS** |

## E-G7 Strategy-aware Monitor

| 项 | 值 |
|---|---|
| Code Path | app/services/strategy_monitor_service.py（run_monitor G7 升级） |
| Production API | /strategy-monitors/{id}/status（状态机）· /monitor/run（执行） |
| Migration | c4a5b6c7d8e0（status/cursors/last_error + signal direction/idempotency_key） |
| Test | tests/test_g7_monitor.py（4 用例全 PASS） |
| Remaining Limitation | Evidence Rule 执行随证据种类扩展 |
| Status | **PASS** |

## E-G8 Causal Replay

| 项 | 值 |
|---|---|
| Code Path | app/services/replay_service.py（因果过滤 + rule_error 反馈）· app/domain/regression.py（七类归因）· app/api/predictions.py（from-decision） |
| Production API | POST /predictions/from-decision · POST /reviews/feedback |
| Migration | c5b6c7d8e9f1（predictions.decision_id） |
| Test | tests/test_g8_causal_replay.py（3 用例全 PASS） |
| Remaining Limitation | Outcome 评估粒度随验证方法扩展 |
| Status | **PASS** |

## E-G9 Research Products 产品化

| 项 | 值 |
|---|---|
| Code Path | app/services/research_products_compiler.py（compile_and_register/diff）· app/storage/research_product_orm.py · app/api/research_products_api.py · frontend/src/pages/ResearchProductsPage.tsx |
| Production API | /research-products/{kind}/compile（POST，显式）· /compiles · /compiles/diff |
| Migration | c6a7b8c9d0e2（research_product_compiles） |
| Test | tests/test_g9_products.py（4 用例全 PASS） |
| Real Artifact | research_product Artifact（每版本） |
| Remaining Limitation | Mainline 状态机随叙事数据深化 |
| Status | **PASS** |

## E-G10/G11/G12

| 项 | 值 |
|---|---|
| G10 | Thesis Diff strengthened/weakened/meta_changes（research_inbox_api.py）；Memory promote 幂等+审计+diff（memory.py）—— test_g10 |
| G11 | research_state_check 工具（freshness/PIT/missing/blockers/INSUFFICIENT_RESEARCH_STATE）—— test_g11 |
| G12 | 后台任务 pause/resume/heartbeat/dead-letter（background_runway.py）—— test_g12 |
| Status | **PASS**（3+1+3 用例） |
