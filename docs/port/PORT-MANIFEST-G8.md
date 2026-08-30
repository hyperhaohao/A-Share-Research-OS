# PORT-MANIFEST — G8 全球宏观 / 海外

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/macro/macro-app.jsx（421 行：全球情绪温度计 Gauge/Spark/
                   市场行 PM+Kalshi 预测市场概率）+ macro-data.jsx +
                   ui/overseas/overseas-app.jsx（115 行）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  industry_view_service.global_macro_view +
                   api/views.py GET /views/global-macro（市场级：最新
                   GlobalContextSnapshot 的指数/商品数值层 + 宏观主题）
                   frontend features/global-macro/：GlobalMacroWorkspace.tsx
                   （区域归组 中国/香港/美国/商品 + 宏观主题 + 风险偏好）+
                   global-macro.css；路由 /global-macro + nav 研究组新入口
                   （旧 /global-context 更名 产业研究·全球产业坐标，§12 分离）
ported behaviors:  市场状态分区（donor 双半球区域观 → 中/港/美/商品 四区，
                   MetricCell 复用）；宏观主题流（官方机构提及标注）；
                   单源失败/快照陈旧诚实显形（donor 习语 → 无快照显形
                   宏观快照未采集）
replaced APIs:     donor PM/Kalshi 预测市场概率 + 假温度 → ASRO
                   GlobalContextSnapshot（腾讯行情数值层 6 指标真实值 +
                   macro_policy 证据主题）
removed mock:      donor 预测市场概率/温度计数值无源不迁 —— 风险偏好区显形
                   「暂无风险偏好源……不编温度」（§25）；overseas-app 的
                   海外市场静态卡不迁（数据并入区域面板）
removed persistence: donor localStorage 快照缓存 → 服务端快照表
remaining drift:   1. 风险偏好温度计（donor Gauge/Spark）：待预测市场/波动率
                      源（VIX/PM 数据）接入后渲染真温度
                   2. donor 历史概率火花线（快照沉淀曲线）：随快照积累后可加
                   3. 利率/流动性专项目录：待官方宏观统计源（dis disclosures
                      已注明未接入）
E2E contracts:     global-context-page/-disclosure/-indicators（产业坐标侧）
                   不受影响；E2E-14/17 PASS；新 global-macro-page testid
tests:             backend 367 passed（+global-macro 视图，全量 exit 0）；
                   frontend vitest 30/30 + build PASS；Playwright 30/30；
                   真机核验（四区 6 指标全真实：上证 3952.18 / 道指 53559.99 /
                   纳指 29433.43 / 恒指 25584.79 / 金 4503.37 / 油 88.33）
next (G9):         全库研究图谱整合（全部 Workbench 注册 Artifact/Provenance/
                   Handoff；Graph 节点带上下文跳转，方案 §19/§40）
```
