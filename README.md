# A-Share Research OS

面向 A 股研究的长期 Research OS。系统维护每个研究标的持续演化的
**Research State**（Evidence → Claim → Thesis → Valuation → Report →
Prediction → Validation），而非一次性生成的互不关联的报告。

## 当前状态

**Research OS Beta — Final Integrity Pass 完成。**

已完成：多源真实数据（公告/财务/新闻/资金/行业/宏观）、完整研究管线（8 分析师 → Claim → Thesis → Debate → Scenario → Valuation → Risk → Report）、LLM Provider + Copilot + Narrative Layer、确定性 Quant 引擎（Kline → 因子 → 回测 → 指标）、后台调度器（Monitor/Materiality/Delta/Full 三分支）、九 Tab Workspace + React Flow 图谱 + Copilot 侧栏 + Revision Diff、Live Research E2E（4 板块）。

进行中/增强项：基准指数数据源、节假日历、公网认证/TLS。

- 状态文件：[STATUS.md](STATUS.md)
- 整改历史：[REMEDIATION.md](REMEDIATION.md)
- 首轮 M0–M29：`docs/milestones/`
- 历史 M0–M29 交付记录：`docs/milestones/`（保留，不代表当前完成结论）
详见 [ROADMAP.md](ROADMAP.md) 与 [STATUS.md](STATUS.md)。

## 快速开始

### Docker Compose（推荐）

```bash
cp .env.example .env
docker compose up --build
# 打开 http://localhost:8080
```

### 本地开发

```bash
# 后端（backend/ 目录）
cd backend
uv sync
ASRO_DATABASE_URL=sqlite:///./asro_dev.db uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000

# 前端（frontend/ 目录）
cd ../frontend
npm install
npm run dev      # http://localhost:5173（/api 代理到 8000）
```

### 测试

```bash
cd backend  && uv run pytest          # 239 个测试（含 live，网络不可达自动 skip）
cd frontend && npm test && npm run build
```

## 核心能力

| 能力 | 入口 |
|------|------|
| A 股标的解析（四板 + 名称/别名） | `GET /api/v1/instruments?query=` |
| 实时行情（真实数据源，无 key） | `GET /api/v1/market-data/quote?instrument=` |
| 证据采集（来源/权威度/事实状态全溯源） | `POST /api/v1/evidence/collect` |
| PIT 快照（未来数据不可见） | `POST /api/v1/snapshots` |
| 主张 / 论点（写时引用完整性） | `/api/v1/claims`、`/api/v1/theses` |
| 确定性估值（PE/PB/DCF/DDM/…） | `POST /api/v1/valuations/compute` |
| 质量门（证据/分析/发布三道） | `POST /api/v1/quality-gates/run` |
| 双语研究报告（zh-CN/en-US 一致） | `POST /api/v1/reports/compile` |
| 报告问答（Explain 零采集 / Refresh 采集） | `POST /api/v1/reports/{id}/ask` |
| 审查与修订（旧版本永不覆盖） | `/api/v1/reports/{id}/audits`、`/revisions` |
| 监控与实质性判定 | `POST /api/v1/monitor/run` |
| 预测验证（5D/20D/60D） | `/api/v1/predictions` |
| 任务调度（幂等/重试/恢复/互斥） | `/api/v1/tasks`、`/tasks/scheduler/tick` |
| 时间线 / 溯源图谱 | `/api/v1/timeline`、`/api/v1/graph` |
| 界面 | 双语（zh-CN/en-US）+ 三态主题（system/light/dark）+ 红涨绿跌可切换 |

## 文档

全部文档见 [docs/00-文档索引.md](docs/00-文档索引.md)，包括：

- [architecture.md](docs/architecture.md) · [data-model.md](docs/data-model.md)
- [source-layer.md](docs/source-layer.md) · [evidence-and-pit.md](docs/evidence-and-pit.md)
- [report-and-review.md](docs/report-and-review.md) · [research-workflow.md](docs/research-workflow.md)
- [i18n.md](docs/i18n.md) · [theming.md](docs/theming.md) · [tasks.md](docs/tasks.md)
- [quant-audit.md](docs/quant-audit.md) · [testing.md](docs/testing.md) · [security.md](docs/security.md)
- [deployment.md](docs/deployment.md) · [backup-restore.md](docs/backup-restore.md) · [migration.md](docs/migration.md)
- [known-limitations.md](docs/known-limitations.md)

## License

MIT
