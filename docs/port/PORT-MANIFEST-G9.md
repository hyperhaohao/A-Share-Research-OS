# PORT-MANIFEST — G9 全库研究图谱整合

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/graph/graph.jsx + guanlan-bus（共享档案库/GL 信箱习语，
                   对应 ASRO ArtifactRegistry/ProvenanceEdge —— ASRO 侧
                   Phase A/H/I 已建成，本阶段为覆盖审计 + 缺口补齐）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  WorkflowDefinitionService.run_definition 注册
                   workflow_run Artifact（title=定义名·版本，route=/workflows/
                   {run_id}）+ StrategyMonitorService.create_monitor 注册
                   strategy_monitor Artifact 并 generated_from 策略版本
                   Artifact + ArtifactType.STRATEGY_MONITOR 枚举
                   frontend  ARTIFACT_TYPE_LABELS + strategy_monitor 业务名
audit results:     已注册（图谱在册）：research_run/report/report_version/
                   prediction/experience_card/workflow_run（卡路径）/
                   screening_run/strategy_version/industry_map/global_context；
                   缺口补齐：①定义运行此前不注册 → 现 registry 覆盖
                   ②盯盘此前无 Artifact → 现注册 + generated_from 策略版本
replaced APIs:     donor GL 共享档案库/window 信箱 → ASRO ArtifactRegistry
                   （已有 Phase A 基建；本阶段只补注册点）
removed mock:      无新增（G9 为整合审计阶段）
removed persistence: 无（donor localStorage 信箱本就不迁）
remaining drift:   1. WorkflowDefinition 本身不注册 Artifact（运行产物注册；
                      定义注册待版本 diff 图谱需求出现）
                   2. 图谱节点 → 原模块上下文跳转走 artifact.route
                      （E2E-15 既有契约）；G2/G8 新视图的节点路由沿用其
                      artifact route（/industry-map、/global-macro 待
                      视图注册入口后自然覆盖）
E2E contracts:     E2E-15（Graph lineage + 跨模块跳转）PASS；E2E-10/17
                   （workflow artifact 链）PASS
tests:             backend 368 passed（+1 G9：定义运行注册 Artifact 并可经
                   by-domain 检索，全量 exit 0）；frontend vitest 30/30 +
                   build PASS；Playwright 30/30；真机核验（定义运行 wr_*
                   出现于 /artifacts/graph 节点，153 节点/157 边）
next (G10):        Full Product Closure（§44 端到端验收 + §45 parity 全 PASS
                   才宣布 COMPLETE）
```
