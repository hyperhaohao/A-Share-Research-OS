# F15-CLOSURE — 第三轮验收整改最终 Closure

> **STATUS: SUPERSEDED（观澜语义维度）— 2026-09-02**
> docs/观澜研究能力语义迁移整改任务书.md 复审确认：第三轮任务书范围内的
> F0–F15 口径（帷幄迁移 + 研究状态正确性）成立，但观澜研究能力的**语义
> 真实性**（产业链图/Typed Workflow/经验编译选股/可执行回测/策略感知监控/
> 因果 Replay/产品 Artifact 化）未达成 —— 见
> docs/guanlan-semantic-remediation/MIGRATION-MATRIX.md（G0 代码实读裁决）。
> 本文件保留为第三轮范围历史，不作为观澜语义迁移的验收依据。

> 任务书：docs/A-Share-Research-OS-第三轮验收整改任务书-Research-State与观澜核心功能完整迁移.md
> 执行区间：F0（2026-09-01）→ F15（2026-09-02）
> ASRO 基线：4c2e506（整改开始 HEAD）→ 本 Closure（git log 见下）
> donor 固定：98f1398（全程未切换，license=None → BEHAVIORAL ADAPTATION）

---

## §17 签署条件逐条核对

| # | 条件 | 状态 | 证据 |
|---|---|---|---|
| 1 | Production Signal API Golden 通过 | ✅ 25/25 ×2（6b=200） | F14-R10-GOLDEN-RUN.txt |
| 2 | Evidence 与 Closure 统计一致 | ✅ 一致性门 exit 0 | scripts/check_closure_consistency.py（R1-R5） |
| 3 | 生产 Claim 路径无解释固定 0.6 | ✅ 0 命中 | F4 grep 复核 + 9 路径接线 |
| 4 | Source Independence 真实实现 | ✅ | F4（字段迁移 + 六规则 + 独立组裁决 + 4 测试） |
| 5 | Subject Swap Detection 真实实现 | ✅ | F4（Entity Dictionary + uncertain reason codes + 2 测试） |
| 6 | Thesis Revision 事务/并发/幂等 | ✅ | F2 test_f2 #8/9/10 + Golden 7b ×2 |
| 7 | 帷幄六核心（事件流/编排/审批/工作台/跑道/记忆） | ✅ | F5–F10 各 Manifest + 459 测试中的 46 个新用例 |
| 8 | 帷幄 Golden 跨模块闭环 | ✅ 13/13 ×2 | F14-WEIWO-GOLDEN-EVIDENCE.md |
| 9 | 观澜核心模块逐行为矩阵 | ✅ | F11-GUANLAN-PARITY.md（六模块逐行，无整页 PASS） |
| 10 | 非外部阻塞项全部通过 | ✅ | F15-CAPABILITY-MATRIX（全部 PASS 行链接证据） |
| 11 | 外部阻塞项诚实标记且不计 PASS | ✅ | F11/BLOCKED 登记 + F15 矩阵 PARTIAL 行 |
| 12 | 后端/前端/构建/Playwright/Golden 原始结果 | ✅ | F13-MANIFEST + F14 证据文件 + F0 原始 pytest |
| 13 | Closure 每个 PASS 链接代码/测试/真实证据 | ✅ | F15-CAPABILITY-MATRIX 证据列 |

## 最终状态

```text
FINAL REMEDIATION VERIFIED
（全部 P0 通过；P1 外部阻塞项诚实标记为 BLOCKED_*/PARTIAL，不计 PASS；
 无任何「Evidence FAIL / Closure PASS」冲突残留 —— 一致性门为常设关口）
```

### 外部阻塞登记（不计入 PASS，恢复即自动补全的项已注明）

| 项 | 状态 | 影响 | 恢复条件 |
|---|---|---|---|
| LLM Structured Refinement / AI 研判 | BLOCKED_EXTERNAL | 经验卡 LLM 精炼、盯盘 AI 复核 | 设 ASRO_LLM_API_KEY |
| 链级传导 / 五轴证据 | BLOCKED_REAL_EVIDENCE | 产业地图 Transmission/Narrative 深度 | 真实语料接入 |
| 东财 kline 日线端点 | BLOCKED_ENVIRONMENT | 回测/K 线对位的 live 面（确定性路径有测试） | 网络恢复（本轮已间歇恢复，E2E-12 即证） |
| 因子引擎 / ScreenDefinition 版本层 | 登记未实现 | 智能选股因子面 | 后续因子线（保持冻结，恢复需用户明示） |
| Undo/Redo、导入导出、15 类节点、自由装配面板、条件单 | 登记不迁/未实现 | 对等工作流补全 | 后续阶段 |

### 已知问题（非阻塞）

- 历史迁移（r6 时代）downgrade 存在 drop_index 参数错误（正向迁移不受影响）；
- visual 基线对活数据敏感（strategy 页已改视口截图；其余活数据 mask + 容差）。

---

## 结论

两条整改主线完成：

1. **Research OS 正确性闭环**：Golden 失败（6b 500）修复；固定置信度全部
   移除并替换为可解释模型；来源独立性与主体偷换检测真实落地；
   Thesis 修订具备原子事务、版本链、幂等与并发保证；Closure 与 Evidence
   的一致性由常设脚本把关。
2. **观澜核心功能完整迁移（帷幄）**：append-only 事件协议 + 真实 SSE
   （snapshot/replay/live）+ 13 工具白名单编排 + 服务端审批状态机 +
   动态 Workbench（Artifact 自动打开、会话独立、刷新恢复）+ 持久化后台
   任务跑道（lease 恢复/重试/取消/合并）+ 会话治理与双层记忆压缩；
   帷幄跨模块 Golden 13/13 现场闭环。

> 不复制 donor 源码；观澜工作流深度 × ASRO Evidence/PIT/Provenance/
> Version/Governance = 可真实使用、可审计、可持续演化的 A 股智能投研
> 操作系统（任务书 §19）。
