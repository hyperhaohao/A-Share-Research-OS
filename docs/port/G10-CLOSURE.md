# G10 — Full Product Closure（Guanlan Experience Port 验收记录）

> 依据《A-Share-Research-OS-Guanlan-Direct-Port-最终迁植与集成方案》§41/§44/§45。
> 基线：donor jesson-hh/financial-analyst @ 98f1398；验收日 2026-08-30。
> 核对方式：每模块对照方案 §43 Checklist 逐项核对 + 真机（compose 栈，000831）
> + Playwright 30/30 + backend 368 + frontend vitest 30/30 + build PASS。

---

## §45 Parity 总表

| # | Parity 项 | 结论 | 证据 |
|---|---|---|---|
| 1 | AI Research Commander | **PASS** | G1 三栏工作台（墨痕计划链/多会话/真实行情速记卡/动态 Workbench）；E2E-08 全链；§32「研究中国稀土近期资产整合信号」对话驱动真机通过 |
| 2 | Industry Research | **PASS** | G2 三视图一体（链级列+环节详情+五轴全球坐标）；真实证据组装；驱动/传导/叙事/站位无源 → 诚实显形（§25）；E2E-14 |
| 3 | Experience | **PASS** | G3 原炼验用工作台（11 主张 cite/17 证据摘要/KB）；批准门槛后端强制；E2E-09 全链（未验证批准拦截→案例验证→批准） |
| 4 | Workflow | **PASS**（Editor）| G4 真 Editor：Node Library/Canvas 连线/Inspector/版本链/运行点灯/诚实错误；不再以 Run Viewer 宣布完成（方案 §15 红线）；图校验 422 矩阵测试 |
| 5 | Screening | **PASS** | G5 三面板（条件侧栏+逐规则排除/候选池评级/研究解释 Inspector）；E2E-11 why-selected；CTA 进入研究/加入关注/做成策略 |
| 6 | Strategy Lab | **PASS** | G6 策略配方（物料溯源 chips/政策三件套/股票池 chips）+ 版本并排比较 + §47 全套回测（regime split/sensitivity/失败样本）；E2E-12 |
| 7 | Strategy Monitor | **PASS**（区内）| G7 K线区（证据层日线+信号对位）+ 三分离面板 + 合并时序 Replay 滑块；E2E-13 诚实双路径 + E2E-16 复盘回灌 |
| 8 | Global Macro | **PASS** | G8 市场级工作台（四区 6 真实指标 + 宏观主题 + 风险偏好诚实显形）；与产业全球坐标正式分离（§12）；nav 双入口 |
| 9 | Research Graph integration | **PASS** | G9 注册审计：10 类产物在册；定义运行+盯盘缺口补齐（generated_from 策略版本）；153 节点/157 边真机；E2E-15 跨模块跳转 |
| 10 | Evidence/PIT integration | **PASS** | 全部数据经证据层（daily-bars/行业/宏观均 PIT 可见证据组装）；无直接源读取 |
| 11 | Artifact/Provenance | **PASS** | G9 审计 + 缺口补齐（上） |
| 12 | Auth | **PASS** | 既有 auth gate + Bearer 注入 + auth tests（302 行测试面保持全绿） |
| 13 | Scheduler | **PASS** | scheduler_worker compose 运行；盯盘 tick/任务/预测验证调度（M18/G 契约）全绿 |
| 14 | CI | **PASS**（本地全量） | 本仓库无 GitHub Actions；验收即全量本地三线（pytest 368 / vitest 30 / Playwright 30）+ build，全部绿 —— CI 流水线属部署线（PLANNED） |

## §44 端到端链（000831）

登录 → AI研究中枢 →「研究中国稀土近期资产整合」→ 产业研究三视图 → 报告 →
炼成经验 → 工作流验证 → 智能选股 → 策略实验室 → 策略盯盘 → Decision →
Prediction → Validation → 复盘 → Experience v2 → 全库图谱：

- 链路自动化覆盖 = E2E-01…17（真实浏览器 + 真实源）+ E2E-16 复盘回灌
  （链上无成熟验证时显式拒绝）+ 完整回填由后端确定性测试覆盖；
- **环境性限制（非代码缺口）**：本机 kline 端点断连（Open Issues #1/#9，
  2026-08-29 实测）→ 工作流 Data 节点/回测的完成路径以确定性 fixture 后端
  测试覆盖（368 passed），真机走诚实失败显形路径；源恢复后完成路径即真机可用。

## 诚实边界（donor 能力 − ASRO 现实，均 §25 显形、不编数）

1. 因子/ML/回测引擎节点目录（donor 25 类中 20 类）：待因子引擎接入
   （G4 目录=可执行 原则）。
2. 风险偏好温度计（PM/Kalshi 概率）：无预测市场源。
3. AI 研判 prompt 注入：决策保持确定性规则；LLM 待 ASRO_LLM_API_KEY。
4. 驱动/传导/叙事/全球站位：待产业链关系/叙事抽取源。
5. 官方宏观统计源：现数值层为腾讯行情（披露于视图）。

以上均登记于对应 PORT-MANIFEST（G0–G9）与 docs/known-limitations.md，
接入后界面自动补全（G2/G5/G8 诚实置空位即数据落点）。

---

## 结论

> **Guanlan Experience Port — PORT COMPLETE（9/9 模块迁植 + 整合验收 PASS）**
>
> 后端坚持 ASRO；前端观澜工作台形态 1:1 迁植（TSX 组件化/删 Mock/
> 删 localStorage/接 ASRO Read Model+Artifact+Handoff）； donor 依赖
> 外部数据源的展示单元按方案 §25 诚实显形，不伪造。
> Track B 与 Production Integrity（Track A）双轨边界全部满足
> （Auth/PIT/Artifact/Handoff）。
