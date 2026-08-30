# PORT-MANIFEST — G4 Workflow Studio（真正 Editor）

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/factor/workflow.jsx（3275 行：SPECS 25 类节点目录/CATALOG/
                   建图模板/克隆/undo-redo/保存历史/JSON 导入导出/拓扑执行器/
                   逐节点点灯/结果抽屉）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  app/application/workflow_defs.py（Definition+Version
                   ORM/仓储）+ migration a9b8c7d6e5f4（两表）+
                   app/services/workflow_definition_service.py（图校验/
                   拓扑序/run 展开）+ app/api/workflow_defs.py
                   （GET/POST /workflow-definitions, /{id}, /{id}/versions,
                   /{id}/run 202 后台）+ workflow_service 泛化（节点级参数，
                   card 运行回退全局参数——向后兼容）
                   frontend  features/workflow-studio/：WorkflowStudio.tsx
                   （编排+Toolbar：命名/存版本/运行）/ WorkflowNodeLibrary.tsx
                   （分组目录，点击加节点）/ WorkflowInspector.tsx（按 schema
                   编辑参数+删除）/ WorkflowRunPanel.tsx（运行列表+逐节点
                   点灯+指标区）/ spec.ts（节点目录 schema+图校验）+
                   workflow-studio.css
ported behaviors:  Node Library（donor CATALOG 分组习语）/ Canvas 增删节点+连线
                   （React Flow 交互连线+Delete 删除）/ Inspector 按 type 编辑
                   （text/number+hint，donor SPECS params 形态）/ Toolbar 保存
                   +运行 / 版本链（donor 历史列表的服务端版，append-only）/
                   运行列表+逐节点状态点灯（donor runState）+ 结果指标区 +
                   错误显形（节点级 error + run 级 error）
replaced APIs:     donor localStorage 工作流存储（WF_KEY/WF_REP_KEY/WF_LAST_KEY）
                   + 引擎 _post/_get → ASRO workflow_definitions 版本化 API +
                   workflow_runs 持久化 + RunEvent 事件
removed mock:      donor SPECS 中未接 ASRO 引擎的 20 类节点（ML 模型/因子分析/
                   回测/组合/风险/GARCH/归因/时变β 等）不进目录 —— 目录与
                   NODE_KINDS 强对应（能执行什么就摆什么，方案 §25）；
                   donor 假结果数据/报告库 mock 不迁
removed persistence: localStorage 全删（定义/版本/运行全服务端持久化）
remaining drift:   1. donor 20 类执行器（特征工程/ML/因子/回测等）待后端引擎
                      逐类接入后进目录（M21 审计的 TideTrading 因子库为候选源；
                      接入属后端引擎工作，非本 Editor 单元）
                   2. donor 端口类型化（inputs/outputs dt）v1 简化为节点级连线
                      （5 类 kind 的 DAG 语义足够；端口级类型检查随引擎扩展）
                   3. donor undo/redo/克隆/JSON 导入导出/LLM 一句话建图/
                      模板建图（CARD_GRAPH）留待后续迭代（画布编辑核心已闭环）
E2E contracts:     CardWorkflowPanel 的 workflow-horizon/-launch/-expression/
                   workflow-run/-metrics 全保留（E2E-10/17 PASS）；
                   studio-canvas / workflow-studio 保留
tests:             backend test_phase_d_workflow.py 10/10（+3 G4：CRUD+版本链+
                   图校验 422 矩阵 / 拓扑执行+per-node 参数生效+无卡诚实落库 /
                   表达式节点裁决）；全量 367 passed；frontend vitest 27/27
                   （+4 studio）+ build PASS；Playwright 30/30
live verification: 真机全链：节点库加 4 节点 → 保存被图校验正确拦截（未连线
                   → output 不可达 422 显形）→ API 建图 → UI 载入定义
                   （4 节点 3 边 + v1 徽标）→ Run → 逐节点点灯（日线源诚实
                   失败——本机 kline 源断连为已知问题，引擎行为正确）
next (G5):         donor ui/screen/screen-app.jsx（1897 行）+ screen-data.jsx →
                   ScreeningWorkbench（因子/条件侧栏 + 候选池 + 研究解释三面板，
                   方案 §16/§36）
```
