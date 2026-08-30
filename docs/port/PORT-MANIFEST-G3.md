# PORT-MANIFEST — G3 研究经验卡（原炼验用工作台）

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/cards/validation.jsx（1186 行：原→炼→验→用 四阶段工作台）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  app/services/experience_view_service.py +
                   api/views.py GET /views/experience/{card_id}（方案 §24 命名）
                   frontend  features/experience-workbench/：
                   ExperienceWorkbench.tsx（编排 + 生命周期条 + 动作区）/
                   ExperienceSourcePane.tsx（原）/
                   ExperienceRefinePane.tsx（炼）/
                   ExperienceValidationPanel.tsx（验）/
                   ExperienceKnowledgeBase.tsx（用）+
                   experienceView.ts + experience-workbench.css
ported behaviors:  四阶段工作台形态（左 原·来源与主张 / 中 炼·机制与条件 /
                   右 验·裁决+记录 / 用·知识库）；donor cite 标记等价物 =
                   主张引用序号 [n]；verdict chip（通过/存疑/驳回/未验证，
                   donor VERDICT 配色语义：黛/金/印章红）；量化指标区
                   （无量化验证 → 诚实留空 —）；KB 面板（已批准卡片）
replaced APIs:     donor 引擎 /cards + markdown 三桶数据库 + localStorage
                   会话信箱 → ASRO ExperienceCard/Version/Validation
                   （/views/experience/{id} 只读装配 + 既有 POST validate/
                   approve/reject）；approve 门槛（≥1 验证）保持后端强制
removed mock:      donor SOURCES 写死素材库（研报/热帖/复盘 mock 全部）
                   + synthVal 占位指标（donor 自己已删，保留诚实约定）
                   → ASRO 全真实来源（报告/主张/证据，11 主张 17 证据真机核验）
removed persistence: donor localStorage handoff 信箱/卡记忆（ws= 参数隔离）
                   → ASRO HandoffEnvelope（服务端持久化）
remaining drift:   1. 量化指标 IC/ICIR/年化/胜率：待工作流量化验证接入卡片指标
                      （现仅案例验证摘要；quant_expression 字段已透传显示）
                   2. donor 因子组合（combos）/生成因子组合动作不迁
                      （ASRO 组合走 Strategy Lab，G6）
                   3. donor LLM 炼制交互（四段式 markdown 解析）不迁 ——
                      ASRO 炼制为后端确定性提炼（§43），LLM 润色待 KEY
E2E contracts:     experience-detail / experience-lifecycle / experience-actions /
                   experience-validate / experience-approve / experience-reject /
                   experience-create 全保留；E2E-09 来源断言更新为工作台
                   新文案（同语义：N 条主张 · M 条证据）；E2E-09/10/11 PASS
tests:             backend 367 passed（thesis 标题业务名化附加修复）；frontend
                   vitest 23/23 + build PASS；Playwright 30/30；真机截图核验
                   （原面板 cite 主张 + 事实状态本地化 + 生命周期条）
next (G4):         donor ui/factor/workflow.jsx（3275 行）→ WorkflowStudio
                   （真正 Editor：Node Library/Canvas/Inspector/Run/Metrics/
                   Version，方案 §15/§35）
```
