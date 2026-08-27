# Upstream Evaluation — M0 评估矩阵与采用结论

> 生成：2026-08-28（M0）。证据见 `current-architecture-audit.md`。
> 打分 0–5（migration-cost 反向：低分=迁移成本低）。

---

## 1. 评估矩阵

| 维度 | TideTrading | OpenAlpha CN | 觀瀾 | Qlib | RD-Agent | TradingAgents |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| a-share-data-coverage | **5**（live 验证：mootdx/腾讯/akshare/tushare/baostock） | 3（语义内建，provider 靠外部服务） | 4（引擎内建，数据在作者机器） | 4（cn 数据管线，需自有格式数据） | 2（经 qlib 间接） | 0（无 A 股） |
| engineering-completeness | **5**（102 端点 API+SSE+前端+Docker+CI） | 4（6.5k 行精炼工程，25 端点） | 3（薄壳+fork 引擎，无构建前端） | 4（成熟库形态） | 4 | 3（CLI 形态） |
| maintainability | 4（126k 行大体量但模块清晰） | **5**（小而严，frozen 契约+34 测试文件） | 2（fork 内嵌+无构建 JSX） | 4（十年老库） | 3 | 4 |
| license | **5**（MIT） | **5**（MIT） | 0（**无 LICENSE，禁止复制**） | **5**（MIT） | **5**（MIT） | 4（Apache-2.0） |
| tests | 4（252 文件，本环境 2 个路径问题） | **5**（105/105 全绿） | 2（有 tests/，未全跑） | 3（本环境环境性失败） | 3（未全跑） | 4（27/27 绿） |
| backend-api | **5** | 4 | 3 | n/a（库） | 3 | 2 |
| frontend | **5**（React19+Vite+TS+i18n+ECharts，build PASS） | 1（12 文件原型） | 4（信息密度设计最佳，但无构建） | 0 | 2（streamlit） | 1（TUI） |
| i18n | **5**（react-i18next zh-CN 默认 + en，5 locale 文件） | 1 | 2（中文硬编码为主） | 0 | 1 | 0 |
| theme | 3（Tailwind .dark 基础存在） | 0 | **5**（明暗 tokens + A股语义色最佳实践） | 0 | 1 | 0 |
| agent-orchestration | **5**（swarm runtime + SSE + scheduled） | 3（committee/deliberation） | 3（buddy + recipes） | 0 | **5**（Co-STEER 自动研发闭环） | 4（LangGraph 辩论状态机） |
| quant-backtest | 4（factors zoo + backtest engines/optimizers） | 4（事件研究/组合/Replay/CAR 检验） | 3（因子评测+回测） | **5**（业界标准） | 4（自动化因子研发） | 1（backtrader 壳） |
| pit | 0（无 PIT 概念） | **5**（四时钟+is_visible_at+batch 校验） | 0 | 4（data/pit.py 财报时点） | 1 | 0 |
| evidence-provenance | 1（卡片级，无证据链） | **5**（内容寻址快照+digest+Manifest） | 2（citation 展示级） | 0 | 1 | 1 |
| task-scheduling | **5**（scheduled_research executor/store，本机验证启动） | 3（批量队列+重启恢复） | 2（alerts/watch） | 0 | 2 | 0 |
| deployment | **5**（docker-compose.prod + entrypoint + healthcheck） | 4（compose + recovery 验证脚本） | 1（个人机路径） | 3（Dockerfile） | 3 | 4 |
| migration-cost（低=好） | 2（126k 行需裁剪通道/租户/交易向功能） | **1**（契约小而独立，易移植） | n/a（只读设计） | 4（重依赖+自有数据格式） | 5（现不接入） | 4 |

---

## 2. 采用结论

```text
TideTrading     ADOPT     主工程基线：增量演进为 A-Share Research OS
OpenAlpha CN    ADAPT     领域契约移植：四时钟 PIT / 不可变 EvidenceSnapshot /
                          RunManifest / Provider 结构化失败语义（MIT，注明出处）
觀瀾             REFERENCE_ONLY   仅 UX/设计模式参考（无 LICENSE，禁止复制任何源码）
Qlib            REFERENCE_ONLY（M21 再评）  若主工程量化能力审计不足，M22 经 Adapter 接入
RD-Agent        REJECT（当前范围，M20 后可重评）  学习闭环成熟后再议
TradingAgents   REFERENCE_ONLY    辩论编排设计参考；无 A 股数据层，不接入运行时
```

---

## 3. 分层选型（M1 起按此实施）

| 系统层 | 选择 | 来源 |
|--------|------|------|
| 工程基线（backend/frontend/i18n/theme/SSE/Docker） | TideTrading 增量演进 | ADOPT |
| Research Core 领域模型（Instrument/Evidence/Claim/Thesis/Run/Report/Version） | 自建（正式仓库内），契约蓝本来自 OpenAlpha CN | ADAPT |
| Source Layer（capability provider + 结构化失败 + PIT 校验） | 自建骨架，契约蓝本 OpenAlpha CN；loader 实现复用 TideTrading 数据矩阵 | ADAPT |
| Agent 编排（Analyst/Bull-Bear/Risk） | TideTrading swarm 为底座，辩论轮次控制参考 TradingAgents | ADOPT+REFERENCE |
| 定时研究/调度 | TideTrading scheduled_research 扩展（retry/idempotency/recovery 按任务书补齐） | ADOPT |
| 估值引擎 | 自建确定性代码（任务书 §36），无一 upstream 提供 | 自建 |
| 报告审查/修订/版本 | 自建（任务书 §42-44），无一 upstream 提供 | 自建 |
| Prediction/Validation | 自建（任务书 §50-52）；统计检验方法参考 OpenAlpha CN outcome validator | ADAPT |
| Quant/Factor/Backtest | 先用 TideTrading factors+backtest；M21 审计后决定是否 Qlib Adapter | ADOPT→M21 |
| UI/UX 设计语言 | 原创实现，交互与视觉规范参考觀瀾（tokens/信息密度/经验卡/研究图谱交互） | REFERENCE |

---

## 4. 主工程差距清单（进入 M1+ 的正式 backlog 输入）

```text
G1  Research Core 领域模型（Evidence 四时钟/Claim/Thesis/Scenario）—— 全新自建
G2  PIT 强制与不可变 EvidenceSnapshot —— 契约移植 openalpha-cn
G3  报告结构化 + 双语渲染 + 不可变 ReportVersion —— 全新自建
G4  Report Q&A（Explain vs Refresh 分离）/ Audit / RevisionProposal —— 全新自建
G5  MaterialityJudge 三分支监控 —— scheduled_research 之上自建
G6  Prediction/Validation 台账 —— 全新自建
G7  Quality Gates（Evidence/Analysis/FinalReport）—— 全新自建
G8  i18n 补齐 en 完整性 + theme 三态（system 默认）强化 —— 在 TideTrading 基础上完善
G9  A股语义色（红涨绿跌）Design Tokens —— 参考觀瀾模式自建
G10 裁剪 TideTrading 交易向重量（IM 通道/租户/实盘 runner 不进正式交付核心）
```
