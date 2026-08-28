# STATUS.md

# Current Execution Status

> 本文件只描述当前事实。历史记录见 `docs/milestones/`。

---

## Current Phase

```text
PW0–PW3 全部 DONE（git 6e4c285…e90002e，E2E 6/6 绿）
当前执行线：V2 总纲 Phase A —— 先产出 §84 四份映射文档（docs/v2/），
再实现 Artifact/Provenance/Context/Handoff/RunEvent 地基
```

## Completed

```text
首轮 M0–M29（历史，docs/milestones/）
首轮整改 R0–R5（历史，REMEDIATION.md）
二轮 Final Integrity Pass F0–F3（历史，git 5a0cec7–b96d3ab）
三轮 Repository Integrity Closure P0–P3（历史，git b96d3ab–13f7346）
四轮产品整改（首页去 demo/动态解析/Pipeline 中英阶段名，git 13f7346）
五轮 PW0–PW2（DONE，本次）：
  - 持久化 Instrument Registry + 统一 InstrumentService（远程解析/离线降级/重启持久）
  - Presentation Layer（交易所/板块/能力/分析师/任务/门禁/预测 全量本地化）
  - 外观/语言单 Select；研究管线 SSE 真实时（采集 8 能力/分析 8 分析师逐项）
  - Watchlist/Task/Report/Prediction 业务卡片化 + 生成预测/删除任务/立即运行
  - 修复 14 个测试文件的 as_of 定时炸弹（动态 PIT 时间戳）
```

## In Progress

```text
V2 Phase A —— ARCHITECTURE-V2 / DOMAIN-MAP / ARTIFACT-PROTOCOL / HANDOFF-PROTOCOL
```

## Next Action

```text
Phase A 批次 1（§85 第一批代码）：
ArtifactRecord + ProvenanceEdge 表与仓储、ArtifactService、ResearchContext、
HandoffEnvelope、RunEvent 持久化（SSE 事件落库可回放），
并把 ReportVersion/Prediction/ResearchRun 注册为 Artifact 验证跨模块；
四份映射文档见 docs/v2/（ARCHITECTURE-V2/DOMAIN-MAP/ARTIFACT-PROTOCOL/
HANDOFF-PROTOCOL）。
```

## Tests

```text
backend: 301 passed（含 PW0 registry/tasks/prediction-builder/reports 新测试）
frontend: 7 passed + build PASS
e2e: Playwright 用例就绪（product.spec.ts E2E-01…06），待 chromium 完成后执行
```

## Live Verification（本轮实测）

```text
000831 搜索 → 中国稀土 · 深交所 · 主板（无裸枚举）PASS
中文名「中国稀土」远程解析 PASS
Watchlist 000831 直接添加 → Workspace PASS
docker restart 后 registry/watchlist 持久 PASS
SSE 实时：数据采集 8/8 逐能力 + 分析 8/8 逐分析师 PASS
报告库业务卡片 + 报告页生成预测（真实 000831 研究状态推导）PASS
预测页业务卡片（无 SZSE、无 600519 hardcode）PASS
研究总控台四区（最近研究/任务/预测/报告）PASS
```

## Open Issues

```text
1. 资金流/历史行情对部分标的仍失败（源层真实失败，UI ⚠ 显形 —— 符合红线8）
2. 预测区间由估值隐含价导出，000831 当前呈深度负区间（诚实推导，方向与区间
   可能异号 —— 来自论点与估值口径差异，待 Phase C 经验卡/策略线处理）
3. 基准指数（IDX）行情未接入 → 超额收益显式 null
4. 法定节假日历未接入 → 预测到期日 ±1-3 天
5. 公网部署需认证/TLS；SQLite 单机规模；生产多用户需 PostgreSQL
6. Macro 官方原始源未接入；Cost Ledger 待真实化；scheduler claim 待原子化
```

## Branch / Commit

```text
Branch: main
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
