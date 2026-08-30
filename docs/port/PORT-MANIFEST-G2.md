# PORT-MANIFEST — G2 产业研究三视图

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/industry/industry-app.jsx（749 行，River 类三视图）
                   ui/industry/industry-data.jsx（fetch 层）
                   ui/industry/gl-ds.css
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  app/services/industry_view_service.py +
                   api/views.py GET /views/industry/{id}（方案 §24 命名）+
                   GET /views/industry/{id}/segment/{segment_id}
                   frontend  features/industry-research/：
                   IndustryResearchWorkspace.tsx（三视图一体编排 + 双 tab +
                   open_with_context）/ IndustryChainView.tsx（阶段列 + 环节
                   tile + 股票池 + 驱动/传导/叙事面板）/
                   GlobalIndustryPositionView.tsx（β/Δ/Ω/Θ/Ψ 五轴 + 宏观主题 +
                   指标网格）/ IndustrySegmentDetail.tsx（环节详情）+
                   industryView.ts + industry-research.css
ported behaviors:  三视图一体（§7：产业链+全球坐标+环节详情共享同一视图数据，
                   不再是两个孤立页面）；阶段分组列 + 环节 tile（悬停/点击进入
                   详情 + 返回）；股票池面板（真实东财同业板块成员）；五条逻辑轴
                   β 全球需求/Δ 涨价周期/Ω 国产替代/Θ 技术路线/Ψ 映射主题
                   （内部 key 按 §10：global_demand/pricing_cycle/
                   domestic_substitution/technology_route/theme_mapping）；
                   环节详情面板结构（定义/产业位置/驱动/传导/股票池/证据/研报）；
                   open_with_context 回工作台（Phase H 行为保留，E2E-14 锁定）
replaced APIs:     donor /industry/board(YAML) + glFetchSegment + STOCK_DB →
                   ASRO /views/industry/*（真实证据组装只读投影，复用
                   industry_map_snapshots + global_context_snapshots，
                   不建第二 Domain）
removed mock:      donor YAML 板库（写死的 SEGS/DRIVERS/EDGES/NARRS + quant
                   读数）不迁；ASRO 侧无证据源的象限诚实置空（§25，donor
                   自身「研报侧未抽取则显 —/暂无观点」同款约定）
removed persistence: 无 localStorage；dc 运行时（support.js/x-dc）不迁
remaining drift:   1. Driver/Transmission/Narrative/站位（mrow/mcol）/动量/温度/
                      研报计数：ASRO 尚无对应证据源 → 面板显形「暂无观点/
                      暂无定位」，不画假边不造假象限（后续接入对应源后自动补全，
                      PLAN 已登记关系源扩展）
                   2. donor 传导边 SVG 几何引擎/RAF 流动动画/坐标修正演示动画
                      不迁（无真实边数据；引擎随边源接入再评）
                   3. 环节缩放动效以轻量淡入替代（donor getBoundingClientRect
                      zoom 动画简化）
                   4. 证据列表显示真实摘要（donor 显示研报观点行——ASRO 以
                      证据共现代之，basis 显式披露）
E2E contracts:     industry-map-page / industry-chain / industry-map-open-workspace /
                   global-context-page / global-context-disclosure / global-indicators
                   （含 .pct-up/.pct-down）全部保留；E2E-14 + E2E-17 PASS
tests:             backend test_phase_h_research_map.py +2（三视图装配真实证据/
                   环节证据共现 + 404 显式拒绝）；backend 全量 367 passed；
                   frontend vitest 23/23 + build PASS；Playwright 30/30
next (G3):         donor ui/cards/validation.jsx（1186 行）→ ExperienceWorkbench
                   （原→炼→验→用 完整迁植，方案 §14/§34）
```
