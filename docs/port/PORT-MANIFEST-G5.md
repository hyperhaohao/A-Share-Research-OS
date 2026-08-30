# PORT-MANIFEST — G5 智能选股工作台

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/screen/screen-app.jsx（1897 行：XuanguApp 配置侧栏/候选榜/
                   逐候选展开/regime 徽章/模型工坊/一句话解析/再打分 overlay）
                   ui/screen/screen-data.jsx（后端桥）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       frontend features/screening-workbench/：
                   ScreeningWorkbench.tsx（三栏工作台编排）+
                   CandidateInspector（内嵌：研究解释 + CTA）+
                   screening-workbench.css；
                   ScreeningRunDetailPage 重定向至工作台（列表页保留）
ported behaviors:  三面板形态（左 因子/条件侧栏 + 逐规则排除计数 / 中 候选池
                   排名+评级徽标（rank≤3 → 评级 A，可从数据推导的展示）/
                   右 研究解释 Inspector）；候选行点击选中 → Inspector 显示
                   Why Selected（真实 explanation/命中规则/风险，方案 §16/
                   §45）；CTA：进入研究（workspace）+ 加入关注（POST
                   /watchlist）+ 做成策略（既有 §47 门 StrategyLaunchButton
                   置于头部）；「为什么没选中」逐规则排除 + 示例（donor 诚实
                   披露习语保留）
replaced APIs:     donor /screen/factors(56 因子·实测 IC)/screen/regime/
                   xgBuildBackend/v4 模型工坊 → ASRO screening run API
                   （规则=经验卡研究状态规则 has_report/thesis_direction/
                   has_quote，全部真实求值，方案 §45）
removed mock:      donor FACTOR_REASON/LLM 选因子 mock/regime 缺产物诚实不渲染
                   习语保留但 ASRO 无 regime 源 → 不渲染；因子 IC/模型评分
                   无引擎 → 不显示（不编数，方案 §25）
removed persistence: donor localStorage/GL 信箱 → ASRO HandoffEnvelope
                   （screening-launch 走信封，E2E-11 契约保留）
remaining drift:   1. 因子库/因子 IC/模型评分（v4 工坊/变体重训/regime 徽章）：
                      ASRO 暂无因子引擎 —— 待 M21 审计的因子库接入后
                      以 G4 Editor 同款「目录=可执行」原则扩充
                   2. ScreenDefinition/ScreenVersion 持久化：v1 筛选规则由
                      经验卡决定（研究状态规则），无自由配置面；
                      待因子引擎接入后按 G4 模式补定义/版本层
                   3. donor 一句话解析/再打分/行业重排 overlay 不迁
E2E contracts:     screening-launch（信封 URL）/ screening-detail /
                   screening-candidates（tbody tr）/ screening-candidate /
                   screening-excluded 全保留；E2E-11/12 PASS
tests:             backend 367 passed（无后端改动）；frontend vitest 27/27 +
                   build PASS；Playwright 30/30；真机核验（规则侧栏+排除计数+
                   候选表+Inspector 全真实数据：中国稀土 命中全部 3 条规则）
next (G6):         donor ui/seats/luozi-foundry.jsx + luozi-fleet.jsx +
                   luozi-panels.jsx → StrategyLab（物料装配 + 版本比较 +
                   失败样本，方案 §17/§37）
```
