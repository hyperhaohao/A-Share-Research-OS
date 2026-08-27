# ADR-001 — 主工程基线决策

- 状态：Accepted
- 日期：2026-08-28
- 阶段：M0（上游/底座源码审计）
- 依据：`docs/current-architecture-audit.md`、`docs/upstream-evaluation.md`

---

## 背景与问题

A-Share Research OS 需要决定：**每一层采用、适配或参考哪个成熟实现**，以及在哪个基线上增量建设正式系统。

约束（来自 TASK.md / 任务书）：

1. 正式产品只进入 `hyperhaohao/A-Share-Research-OS`，任何上游不得替代；
2. 不允许一次性预建空架构，目录随 Milestone 生长；
3. i18n（zh-CN/en-US）与 theme（system/light/dark）从 M1 起是一级能力；
4. Evidence/PIT/可追溯是领域硬约束；
5. 不得为了偏好硬选某候选，必须基于源码、运行、测试、许可证客观决策。

## 决策

### D1 — 主工程基线：TideTrading（ADOPT）

以 TideTrading 为正式系统主工程基线，在正式仓库内增量演进（非 fork-替换式重写）：

- A 股数据能力真实可用（本机 live 验证：000001 实时行情+五档盘口，无 key）；
- FastAPI + React19/Vite/TS + i18next + ECharts + SSE + Docker，与任务书技术原则一致；
- 已具备 scheduled_research、swarm 编排、governance、因子库与回测引擎；
- MIT 许可，活跃维护。

其缺失（Research Core 领域模型、PIT、报告版本化、预测验证、质量门）由本仓库自建，见 D2/D3。

### D2 — Research Core 领域契约蓝本：OpenAlpha CN（ADAPT）

四时钟 `Timeline` 与 `is_visible_at` PIT 规则、frozen 内容寻址 `EvidenceSnapshot`、`RunManifest`（code/config/provider/model/prompt/seed/checkpoints）、Provider 结构化失败语义（成功/no_data 严格区分、batch 级 PIT 校验、payload digest）——按 MIT 许可移植进正式仓库并在源码头注明出处，再按任务书扩展 Claim/Thesis/Scenario/Report/Version 等基本面研究领域对象。

### D3 — 其余候选

- 觀瀾：REFERENCE_ONLY。**无 LICENSE，禁止复制任何源码**；仅借鉴 UX 模式（明暗 Design Tokens + A 股红涨绿跌语义解耦、研究闭环信息架构、经验卡、研究图谱交互）；明确否定其 localStorage 事实源与无构建 JSX 前端。
- Qlib：REFERENCE_ONLY，M21 重新审计。仅当主工程 factors+backtest 审计不足时，M22 经 Adapter 接入并完成真实 A 股闭环。
- RD-Agent：REJECT（当前范围）。任务书明确基础系统稳定前禁止接入；M20 后可重评。
- TradingAgents：REFERENCE_ONLY。无 A 股数据层（grep 证实）；其 LangGraph 辩论轮次控制是 Debate 实现参考。

### D4 — 裁剪边界

TideTrading 中与 Research OS 无关的交易产品向重量（IM 消息通道、多租户体系、实盘 runner、影子账户）不进入正式交付核心路径；正式仓库按 Milestone 引入所需模块，不做整体搬迁。

## 备选方案（否决理由）

1. **全自建最小基线**：放弃 TideTrading 的 A 股数据矩阵、API/SSE/前端工程与调度设施，重复建设量巨大；任务书明确「若审计通过则增量建设，不再重立空架构」。否决。
2. **OpenAlpha CN 为基线**：领域契约最佳，但产品形态是 signal/decision/回放引擎，缺报告体系/估值/审查闭环/工作台前端，改造其 6.5k 行工程的代价不低于在 TideTrading 上新建领域层，且其社区极小。否决为基线，采纳为契约蓝本。
3. **TradingAgents 为基线**：无 A 股数据、CLI 形态、重 langchain 栈。否决。
4. **觀瀾 为基线**：无 LICENSE（法律阻断复制）、数据绑定作者个人磁盘、前端无构建。否决。

## 影响

- M1（工程基线+i18n+theme）在 TideTrading 基础上开展：先最小化裁剪出可运行 baseline，再强化 i18n 完整性与三态主题；
- M3 Source Layer 的 provider 骨架按 OpenAlpha CN 契约实现，loader 实现桥接 TideTrading 数据矩阵；
- 估值引擎、报告审查、预测验证、质量门为全新自建模块；
- 上游仓库永远留在 `upstreams/`，正式仓库只收录自建代码与注明出处的适配代码。

## 验证记录

```text
TideTrading   backend 启动 PASS / 102 端点 / live A股行情 PASS / frontend build PASS /
              定向测试切片（scheduled_research+research_protocol+research_card+backtest
              security）78 passed；全量套件环境性错误（沙箱缺 HOME）已定位，抽样验证通过
OpenAlpha CN  105 tests PASS / 25 端点 API 启动 PASS
觀瀾           engine import PASS
Qlib          import PASS（完整闭环 defer 至 M21/M22）
RD-Agent      import PASS
TradingAgents 27 tests PASS
```
