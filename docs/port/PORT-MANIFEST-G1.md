# PORT-MANIFEST — G1 AI 研究中枢 / 深度研究

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/chat/app.jsx（3442 行，ObservatoryApp 全家桶）
                   ui/chat/agent-adapter.jsx（agent SSE 适配层）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       frontend/src/features/command-center/
                   CommandCenterPage.tsx（三栏编排 + 会话自举）
                   CommandCenterLeft.tsx（计划墨痕 + 正在运行 + 最近计划 + 会话切换）
                   CommandCenterTranscript.tsx（对话 + 计划执行链 + 上下文 chip Composer）
                   CommandCenterWorkbench.tsx（真实当前 Workbench：标的速记卡 +
                   计划产物 + 待验证预测）
                   plan.ts（Plan 投影 + 步骤三态映射）+ command-center.css
ported components: donor 三栏工作台布局 / 多会话切换（SessionSwitcher →
                   command_sessions API）/ 计划墨痕（ResearchStep 三态，G0 组件）/
                   工具链执行行（ToolChain 等价物 = PlanChain 墨痕链）/ Composer
                   上下文 chip（→ ResearchContext）/ 右栏「当前标的 · 速记」卡
                   （→ 真实行情 /market-data/quote：价格/涨跌/PE/PB/总市值/
                   行情时间，全部真实数据）/ 右栏动态 Workbench（§6：不是固定
                   Artifact List —— 当前计划产物优先，报告完成后置顶 CTA，§32）
replaced APIs:     观澜 window.GuanlanAgent SSE / GUANLAN_BACKEND /alerts /quotes
                   /report → ASRO /views/command-center（单请求聚合）+
                   /command/sessions(/turns) + /artifacts + /market-data/quote；
                   会话持久化 localStorage guanlan:state:v2 → ASRO command_sessions 表
removed mock:      donor WATCHLIST/ALERTS/STOCK_DB/TOOLS_META 写死数据 + mock 假
                   流式报告（buildReportText）+ 假步骤推进（900ms 定时器）全部不迁；
                   无行情 → 「行情暂不可用」显形（§25）
removed persistence: localStorage 全量删除（会话/自选/主题均不落 localStorage，
                   主题/语言走 ASRO ThemeProvider；业务数据全部 API）
remaining drift:   1. donor 顶栏指数条未迁（ASRO 暂无全市场指数视图源；不造假数据，
                      待 G8 宏观数值层横向服务后接入 MarketTicker）
                   2. donor CmdK 工具面板/盯盘规则卡/雪球 feed/回收站不迁
                      （ASRO 对应能力分属 盯盘/数据源/任务 各模块，§3 命名表）
                   3. 观澜 30 工具 TOOLS_META 概念不迁 —— ASRO 以能力分组呈现
                      数据采集 8 能力 + 分析 8 分析师（既有 §67 事件面）
i18n:              新增 cc.* 16 组（zh/en）；沿用 commander.*；无裸 key/裸 id 泄漏
                   （E2E-UI-08 扫描过）
theme:             light/dark token 化；无硬编码色
E2E contracts:     commander-page/-left/-right/-conversation/-input/-send/-reply/
                   -plan-progress/-artifacts/-current-plan/-brief-card/-context-chip/
                   -new-session + artifact-row/-open + plan-row 全部保留
tests:             tests/command-center.test.tsx（4：三态映射/步号/墨痕渲染/
                   三栏壳无裸 key）；vitest 23/23；build PASS；
                   Playwright 30/30（product 18 + visual 12，
                   command-center 双主题基线按内容变更重生成）
next (G2):         donor ui/industry/industry-app.jsx（749 行）+ industry-data.jsx →
                   IndustryResearchWorkspace 三视图（产业链/全球产业坐标/环节详情）
```
