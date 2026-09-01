# F14-MANIFEST — Golden E2E

> 阶段：F14（第三轮整改任务书 §11 F14 / §12 Golden 场景）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md
> 执行栈：live compose（backend+frontend 重建至 F12/F13 代码，真实数据卷）

## 1. Golden A：000831 Research State（backend/tests/test_r10_golden.py，live 25 步）

- **25/25 PASS，连续两次**（证据：[F14-R10-GOLDEN-RUN.txt](F14-R10-GOLDEN-RUN.txt)）：
  - 6b Production Signal API：**status=200 count=0**（F3 修复后由 500 → 200；
    BUILTIN 规则对当前 50 条窗口证据 0 命中 = 真实评估结果）；
  - 7b Thesis Diff apply：**append-only 新版本成功**（ths 链继续增长，
    Current 切换保留=True；F2 原子修订服务在真实数据上运行）；
  - 1-14 全链：意图/管线/证据/引用反查/产业语义/图谱/PIT/报告渲染全 PASS。
- **修复过程如实记录**：首轮 25/25 后，第二次运行 7b 失败 ——
  定位为 **updates 版本 Claim 的 (snapshot_id, statement) 唯一约束冲突**
  （多轮 Golden 后同证据更新两条同文 Claim 产生同语句版本行）。
  修复：版本语句携带证据 id 尾码 + 同语句预检复用（幂等）；
  修复后连续 25/25 ×2。这正是 Golden 重复执行要暴露的问题（§5.4 幂等族）。

## 2. Golden C：帷幄跨模块闭环（backend/tests/test_f14_golden_weiwo.py，live 13 步）

- **13/13 PASS，两次**（证据：[F14-WEIWO-GOLDEN-EVIDENCE.md](F14-WEIWO-GOLDEN-EVIDENCE.md)）：
  G1 一句话 → 跨模块计划；G2 计划完成（期间对话照常）；G3 事件流实时 +
  工具链 + sequence 单调；G4 Tool Call↔Result correlation；G5 Artifact 自动
  打开 Workbench；G6 Snapshot 刷新恢复；G7 **拒绝确认 → 无副作用**
 （422 + Thesis 数不变）；G8 批准 → 修订执行 + confirm consumed；
  G9 requested/decided 审计事件；G10 经验卡（card=exp_4aec31b03194）；
  G11 后台任务 queued→pump→succeeded 100%；G12 任务事件通知；
  G13 会话隔离（第二会话 Workbench 为空）。
- G10 修正：create_experience_card 结构化结果补真实 card_id（原返回 None —
  结构化 Result 契约修复）。

## 3. Golden B：Signal Semantics

- §6.4 七语义 = F3 的 8 个 API 级测试（test_f3_signal_production.py，全 PASS）；
- 6a/6b 由 Golden A live 复验（25/25 中 6a/6b PASS）。

## 4. Golden D：观澜核心产品链

- E2E-09…16（报告→经验卡→工作流→筛选→策略→盯盘→三分离→回灌）由 F13
  Playwright **30/30 PASS** 覆盖；失败路径诚实显形（E2E-10/12/13/16 双路径
  契约）；无 localStorage 事实源。

## 5. 真实失败路径 Golden

- 引用编造拒绝（4b rejected number_not_in_source）PASS；
- kline 断连 → 工作流/回测诚实失败显形（BLOCKED_ENVIRONMENT 登记于
  F11 矩阵 + known-limitations）；
- 无新证据重复提交 → 422（F2 测试 10）；高风险工具未批准 → 422（F6/F7）。

## 状态

GOLDEN_VERIFIED：Golden A 25/25 ×2、Golden C 13/13 ×2、Golden B/D 覆盖如上。
