# Architecture

> 对应任务书 §0.4/§5/§86；决策记录见 adr/ADR-001。

## 总体结构

```text
frontend/  React 19 + Vite + TS（TanStack Query + zustand；i18next；Design Tokens）
backend/   FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic（SQLite 开发 / PostgreSQL 生产）
    app/api/         REST 端点（按域分路由）
    app/domain/      领域模型（不可变契约，纯逻辑可测）
    app/services/    编排服务（采集/分析/编译/验证/管线/审计）
    app/sources/     Source Layer（capability provider + fallback + health + cache）
    app/scheduler/   任务与调度（§48/§49）
    app/storage/     ORM + 仓储（写时引用完整性）
    app/core/        错误信封 / i18n / 事件总线
```

## 分层选型（ADR-001）

| 层 | 实现 | 来源 |
|----|------|------|
| 工程基线 | 自建（技术栈对齐 TideTrading） | ADOPT（增量演进） |
| Research Core 契约 | 自建，蓝本 OpenAlpha CN（MIT） | ADAPT |
| 量化底层 | 主工程 factors/backtest（china_a 引擎等） | ADOPT（M22 NOT_REQUIRED） |
| UI 设计语言 | 原创实现，交互参考觀瀾 | REFERENCE |

## 核心研究闭环

```text
Source（capability provider，结构化失败）
→ Evidence（四时钟，内容寻址，dedup）
→ EvidenceSnapshot（as_of 冻结，PIT gate）
→ Claim（≥1 证据引用）→ Thesis（≥1 主张引用）
→ Debate/Scenario（概率=100）→ Valuation（确定性代码）
→ ResearchReport（双语渲染，gate 拦截发布）→ ReportVersion（append-only）
→ Prediction（不可变）→ Validation（确定性数学）→ RegressionReview/Experience
```

每一跳都有引用完整性校验；追溯链 `Report → Thesis → Claim → Evidence → Source`
由写时约束保证（AGENTS §14「Source before Evidence」）。
