# Testing Strategy（任务书 §18/§71-§81）

> 更新：2026-08-28（M28）。

## 1. 测试分层与现状

| 层 | 位置 | 运行 | 现状 |
|----|------|------|------|
| 后端单元 | `backend/tests/` | `uv run pytest` | 239 passed |
| 后端集成/E2E | 同上（API 级） | 同上 | 覆盖 §66 全部 API 面 |
| Live Source | `test_tencent_quote.py::test_live_quote_real_network` 等 | 同上（网络不可达时 skip） | PASS（真实行情） |
| 前端单元/组件 | `frontend/tests/` | `npm test` | 8 passed |
| 前端构建 | `npm run build` | — | PASS |
| 浏览器验证 | 手工 + DevTools（M1/M2/M24/M25/M26/M27 记录于 ROADMAP） | — | PASS |
| UI E2E（Playwright） | M29 补充部署验证 | — | 待 M29 |

## 2. 关键不变量测试映射

| 任务书要求 | 测试 |
|-----------|------|
| §23/§74 PIT 强制 | `test_snapshot_pit.py`（未来证据不可见/边界可见） |
| §24 不可变快照 | `test_snapshot_pit.py::TestSnapshotImmutability` |
| §21 失败显式 | `test_source_contract.py`（success 必须有记录/no_data 必须有原因/失败禁带记录） |
| dedup | `test_evidence_repository.py::test_save_is_idempotent_by_source_and_content` |
| §43 审计 | `test_quality_gates.py` + `test_audit_revision.py` |
| §44 修订不可覆盖 | `test_manifest.py::TestReportVersionChain`（§78 V1.0 保留） |
| §50 预测不可变 | `test_prediction.py::TestImmutability` |
| §80 预测数学 | `test_prediction.py::TestValidationMath`（固定数值） |
| §72 四板回归 | `test_code_norm.py` + `test_instrument_resolution.py` |
| §90 双语一致性 | `test_reports.py::test_bilingual_reports_share_numbers_and_citations` |
| §71 多标的 E2E | `test_e2e_multiresearch.py`（四板全流程 + 报告隔离） |
| §49 调度保证 | `test_scheduler.py`（幂等/重试/恢复/并发互斥） |

## 3. Live Source 验证记录（Source Milestone 硬要求）

```text
M0  TideTrading /api/quote/realtime/000001 实时盘口 PASS（上游验证）
M3  自建腾讯 provider live：贵州茅台 1292.30（-0.81%）PASS
M4  live collect → evidence 入库 PASS
M23 pipeline live 事件序列 PASS
注：live 测试网络不可达时自动 skip（CI 不强依赖，符合 §18）。
```

## 4. 性能与成本

- 成本口径：每 run 记录 LLM 调用数（当前确定性管线为 0）、source 调用数、时长 —— `GET /api/v1/costs`；
- 性能基线：全量后端测试 239 个用例 < 10s；关键 API（health/instruments/quote）本机 P99 < 50ms（quote 受上游网络影响）；
- 缓存：market_data TTL 5s，重复读不重复出网。

## 5. 已知限制

- 节假日交易日历未接入（预测 due 用周末近似）；
- UI E2E（Playwright）在 M29 部署验证时补；
- PDF 导出在 M29 交付（Markdown/HTML 已可用）。


## 测试分类（整改 R0.7）

| 标记 | 含义 | 示例 |
|------|------|------|
| `api_integration` | TestClient 全流程 + monkeypatch 传输层 —— **是 API Integration E2E，不是 Live Research E2E** | test_e2e_multiresearch.py（pytestmark） |
| `live` | 真实网络/真实数据源验证（离线自动 skip） | test_tencent_quote.py::test_live_quote_real_network |
| `unit` | 纯逻辑 | 估值数学/材质域校验 |

> Live Research E2E（多标的真实全链，无 monkeypatch、无手工补链）在整改 R5 交付；
> 在此之前，任何「E2E」表述均指 API Integration E2E。
