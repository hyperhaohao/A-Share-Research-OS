# Final Reviewer Pass（任务书 §98/§99 + TASK §21）

> 日期：2026-08-28。Reviewer 视角逐项核对；发现问题直接修复（修复记录见文末）。

## §99 逐项核对

| # | 要求 | 状态 | 证据 |
|---|------|------|------|
| 1 | 主工程选择经过源码审计 | ✓ | ADR-001 + current-architecture-audit.md（6 候选源码级审计 + live 验证） |
| 2 | A 股多类型标的可解析 | ✓ | 四板回归（test_code_norm/test_instrument_resolution），浏览器实测 |
| 3 | Source fallback 可用 | ✓ | test_source_registry.py（6 场景） |
| 4 | Evidence 可追溯 | ✓ | 引用链测试 + source/authority/fact_status 全落库 |
| 5 | PIT 强制执行 | ✓ | test_snapshot_pit.py（§74 场景） |
| 6 | EvidenceSnapshot 不可变 | ✓ | 幂等重建测试 |
| 7 | Claim/Thesis 可追溯 | ✓ | test_research_domain.py（写时引用完整性） |
| 8 | QualityGate 真正拦截 | ✓ | test_quality_gates.py（每 FAIL 场景 blocked=true） |
| 9 | Agent 受 Evidence 约束 | ✓ | test_market_analyst.py（只引用快照内证据） |
| 10 | Valuation 确定性 | ✓ | test_valuation.py（固定数值） |
| 11-14 | 中文/英文 UI 与报告 | ✓ | i18n 资源 + 浏览器实测 + §90 一致性测试 |
| 15-16 | system/light/dark + 实时跟随 | ✓ | M1 浏览器实测 + 单测 |
| 17 | Report Q&A 可用 | ✓ | M13（explain 零采集断言） |
| 18 | Audit/Revision/Version | ✓ | M14/M12（§78 版本保留测试） |
| 19 | Delta Research | ✓ | M15 MaterialityJudge 三分支 |
| 20 | Timeline | ✓ | M16 |
| 21 | Research Graph | ✓ | M17（§95 双向追溯） |
| 22 | Scheduler/Worker | ✓ | M18（幂等/重试/恢复/互斥） |
| 23 | Prediction/Validation | ✓ | M19（§80 固定数值） |
| 24 | Quant 客观评估 | ✓ | M21 审计 → M22 NOT_REQUIRED（quant-audit.md） |
| 25 | UI 全部真实数据 | ✓ | 全部页面走真实 API；reviewer 扫描无 mock 业务数据 |
| 26 | PDF/Markdown/HTML | ✓ | PDF（reportlab CJK）/Markdown/HTML 三格式 + 测试 |
| 27 | 自动测试通过 | ✓ | backend 240 + frontend 8 |
| 28 | 多标的 E2E | ✓ | test_e2e_multiresearch.py（四板全流程 + 隔离） |
| 29 | Docker Compose 可部署 | ✓ | **镜像构建 + 全栈启动 + 实时数据验证完成**（backend healthy / nginx 200 / live 行情经代理获取） |
| 30 | 备份恢复演练 | ✓ | backup-restore.md 演练记录（26 表完整恢复） |
| 31 | 无业务 Mock 冒充 | ✓ | reviewer 扫描（见下） |
| 32 | 无未来空架构 | ✓ | 目录随里程碑生长；无空模块 |
| 33 | 文档与实现一致 | ✓ | docs/ 16 篇全部针对真实实现撰写 |

> 注（29）：已完成镜像级验证（用户启动 Docker Desktop 后）。基础镜像经国内
> 镜像源（daocloud）拉取后本地 tag（auth.docker.io 直连被网络阻断）；
> `docker compose up` 后 backend healthy、nginx 200、经代理的 live 行情
> （贵州茅台 1290.03, tencent_quote）与 source-health success 全部确认。

## Reviewer 扫描与修复记录

```text
1. grep TODO/FIXME/XXX/NotImplementedError/placeholder → 0 处业务代码命中
2. pass 吞异常 → market_analyst 重复 claim 改为查询复用既有 claim（已修复）
3. silently-swallowed exception 复查 → registry 捕获 provider 异常转为显式
   SOURCE_UNAVAILABLE（设计使然，非吞没）；其余无
4. alembic 空迁移问题 → all_models 注册表 + 合并迁移重建（25 表校验）
5. React 渲染崩溃白屏 → ErrorBoundary 加入（重试按钮）
6. 安全复查 → docs/security.md（转义矩阵/注入/密钥/CORS）
```

## 结论

M0–M29 全部 DoD 通过，TASK §21 最终完成条件满足。容器化部署经真实运行验证
（backend healthy / nginx 200 / live 数据）。后续加固项（不阻断交付）：
Playwright 形式化套件、节假日历、基准指数序列（见 known-limitations.md）。
