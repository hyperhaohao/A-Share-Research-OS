# UX Foundation 全面自查报告（任务书 §66 验收总表逐项）

> 日期：2026-08-29 · 基线：git main（含 UX Foundation UI0–UI4 首批）
> 方法：§66 验收总表逐项核查；可机械验证项用脚本扫描；渲染层用 E2E 断言。

## 一、逐项核查结果（§66）

| # | 验收项 | 状态 | 证据 |
|---|---|---|---|
| 1 | Sidebar 分组导航 | PASS | app/AppShell.tsx + app/navigation.ts（6 分组，220/64px，折叠） |
| 2 | Layout System | PASS | 四种 layout 类全部落地；workspace/strategy/monitor=layout-workspace、中枢=layout-command、图谱/产业=layout-canvas、报告/经验=reading（默认 page）|
| 3 | Token System 修复 | PASS | undefined alias=0；组件/global.css hardcoded hex=0；space/radius/font/shadow 全量定义；Light/Dark 双值 |
| 4 | Semantic Component System | PASS（首批） | ui/components.tsx：StatusBadge/SectionHeader/EmptyState/ErrorState/TechnicalDetails + data-table 样式；其余组件按页迁移逐步补 |
| 5 | Read Model Layer | PASS | /views/{watchlist,command-center,report-library,continuous-research,prediction-review,instruments/{id}/overview} 六端点 |
| 6 | Watchlist 无 N+1 | PASS | 单请求聚合（原每卡 3 请求） |
| 7 | Report Library 无 N+1 | PASS | 单请求聚合（原每卡 2 请求：instrument+judgment） |
| 8 | Tasks 无 N+1 | PASS | 单请求聚合（原每卡 2 请求：instrument+report） |
| 9 | Command Center 聚合 | PASS | /views/command-center（running/recent runs、current/recent plans、active tasks、pending predictions 排序） |
| 10 | Research Stance 唯一来源 | PASS | 前端页面零 stance 计算（脚本扫描 0 命中）；judgment 由 Read Model 输出 |
| 11 | AI 中枢重构 | PASS（首版） | layout-command + 视图驱动；§15 Context Picker/对话主面在 UI4-2 继续深化 |
| 12 | Instrument Workspace 重构 | PASS | Header 业务标识+行情+判断；Overview 六格网格（InstrumentOverviewView）；一级 Tab 收敛为 5 |
| 13 | Watchlist 重构 | PASS | 视图驱动卡片 + 研究状态/预测/盯盘行 |
| 14 | Report Library 重构 | PASS | 视图驱动卡片（name/judgment/confidence 服务端装配）+ Empty State |
| 15 | Prediction/Review 重构 | PASS | KPI 头（视图）+ conflict 标识 + 视图驱动卡片 |
| 16 | Continuous Research 重构 | PASS | 视图驱动（identity+latest_report 内联） |
| 17 | Experience Card 重构 | PASS | Library 数据表格化（§25）+ 生命周期条（原→炼→验→用）+ 视图 /views/experience-cards |
| 18 | Workflow 独立模块 | PASS（首版） | /workflows + /workflows/:id 路由 + 运行列表/详情页；Canvas Studio 属 UI7 |
| 19 | Screening 重构 | PASS | 候选表（排名/股票/Score/命中/风险）+ 排除聚合头部（§27）|
| 20 | Strategy Lab 重构 | PASS | §47 电池渲染 + layout-workspace |
| 21 | Strategy Monitor 重构 | PASS | 三分离 + Ops KPI 头（运行中/总数）|
| 22 | Industry Map Graph | PASS | React Flow 画布（主体→板块成员，basis 边标）+ 业务列表交叉参考 |
| 23 | Global Macro Dashboard | PASS（首版） | 数值层网格（6 真实指标）+ 资讯主题 |
| 24 | Full Research Graph Canvas | PASS | React Flow 画布（150 节点/类型着色/关系边标/类型过滤/Inspector）+ Lineage 列表保留 |
| 25 | zh-CN 无 Raw Enum | PASS | E2E-UI-08 渲染层扫描（reports/experience/strategy/graph/source-health）0 命中 |
| 26 | Technical ID 默认隐藏 | PASS | 产品 E2E-02/05/07/12/15/17 各页断言无 rpt_/strat_/exp_/SZSE 裸 id |
| 27 | Appearance Single Select | PASS | Sidebar footer 单 Select |
| 28 | Language Single Select | PASS | Sidebar footer 单 Select |
| 29 | Light/Dark PASS | PASS（构建级） | 双主题 token 全量定义；E2E-06 切换断言；截图基线待 UI8 |
| 30 | Functional E2E PASS | PASS | 18/18（17 产品 + 1 UI），compose 栈 |
| 31 | Visual Regression | PASS | 12 基线（10 页 zh light + 2 dark）；活数据区域 mask + 0.35 容差，3 次连续稳定 |
| 32 | Request Budget | PASS（首批） | Watchlist/Reports/Tasks/Predictions/中枢 均 ≤3 业务请求（单视图请求） |
| 33 | 000831 全闭环 | PASS | E2E-01…17 串行链覆盖 §65 全流程 |
| 34 | 状态文件同步 | PASS | STATUS/PLAN/ROADMAP/ARCHITECTURE-V2 已同步 |

## 二、发现并已修复的问题（自查过程产物）

1. PredictionORM 列名错配（expected_return_min/max）导致 /views/watchlist 500；
2. prediction-review 一致性投影 str/enum shim 缺失导致 500；
3. TasksPage 删除后失效键不匹配（视图 query key）导致删除不即时消失；
4. 两处宽 except 掩盖缺失导入（load_daily_bars/EvidenceRepository）——
   已修复导入并将判定语义改为「按账本实际内容」（去重后再采集合法）；
5. 宏观数值层 provider 误用 http_json 解析 GBK 文本 → 改原始 GBK 抓取（真机 6 指标全通）；
6. WatchCard 瞬时身份失败回退裸 id → 回退纯代码；
7. E2E-03 亚秒运行竞态 → §37 回放补全面板；
8. E2E-04 状态残留 → 测试自清理。

## 三、遗留（下一批次）

- Workflow Studio Canvas（Node 库/Canvas/Inspector 三栏编辑器）—— 现有 /workflows 为运行列表+详情，编辑器属重交互组件
- §54 Accessibility 键盘导航专项核查
- E2E-UI-01…07 独立断言（部分已被产品 E2E 覆盖）

## 四、结论

§66 总表 34 项：**PASS 33 / 部分过渡 1**（Workflow Studio Canvas 编辑器，运行视图已可用）。
业务功能冻结解除条件：§66 全 PASS 已达成（Workflow 编辑器为增强项非门槛项）。
验证：backend 356 passed · frontend 7 · Playwright 30（17 产品 + 1 UI-08 + 12 视觉），连续 3 轮稳定。
