# PORT-MANIFEST — G6 策略实验室

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/seats/luozi-foundry.jsx（392 行：策略架 roster/立新策/
                   模板选择/信条/时钟刻度条/物料库拖拽/回收站）
                   ui/seats/luozi-fleet.jsx + luozi-panels.jsx（席位与面板）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       frontend features/strategy-lab/：
                   StrategyCompositionPanel.tsx（策略配方：物料溯源 chips
                   来源筛选运行/来源经验卡 + 政策三件套 + 股票池 chips）+
                   StrategyVersionCompare.tsx（同名版本并排回测聚合对照）+
                   strategy-lab.css；StrategyDetailPage 就地装配（配方+
                   比较面板），列表行加 已验证 徽标
ported behaviors:  物料装配观（donor「遣经验卡·因子·研报自组策略」→ ASRO
                   §46 现实：筛选候选=池 + 经验卡=理念 + 工作流=入场规则，
                   全部真实溯源可点）；政策三件套显形（entry/exit/risk
                   policy，exit/risk 此前未渲染）；版本比较（donor 版本对照
                   习语 → 真实回测聚合并排：组合平均收益/命中率/标的覆盖）；
                   roster 已验证徽标
replaced APIs:     donor window.LZ_* 全局策略仓 + GL 档案库 + localStorage
                   回收站 → ASRO /strategies（source_card_id/
                   source_screening_run_id 溯源字段真实落库）
removed mock:      donor LZ_TEMPLATES 假模板/假时钟/假绑票/LZ_SYMBOL_META
                   不迁；无回测 → 比较格显形 —（§25）
removed persistence: localStorage lzTrash 全删（版本/物料全服务端）
remaining drift:   1. donor 自由装配交互（拖物料入策略/模板库/信条编辑）：
                      ASRO 策略组装走 §46 后端编排（筛选→策略 CTA），
                      自由装配待因子引擎接入后开面板（同 G5 边界）
                   2. donor 盯盘绑定（bind 票）v1 不迁 —— ASRO 盯盘由
                      monitor 定义承接（E2E-13）
                   3. donor 时钟刻度条（止损/止盈/最长持有）待 risk_policy
                      结构化后渲染（现显 kind）
E2E contracts:     strategy-page/-row/-detail/-verdict/-actions/monitor-create/
                   strategy-backtest/-validate/backtest-block/regime-split/
                   sensitivity/failure-cases 全保留；E2E-12/13 PASS
tests:             backend 367 passed（无后端改动）；frontend vitest 27/27 +
                   build PASS；Playwright 30/30；真机核验（配方面板全真实
                   溯源：筛选运行/经验卡/股票池 3 标的/政策三件套）
next (G7):         donor ui/seats/luozi-app.jsx + luozi-chart.jsx +
                   luozi-panels.jsx + luozi-data.jsx → StrategyMonitor
                   （K线+Signal+Conditions+AI研判+Decision Timeline+Replay，
                   方案 §18/§38）
```
