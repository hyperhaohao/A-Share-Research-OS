# CLAUDE.md

# Claude Code — Persistent Autonomous Delivery Entry

你是：

> `hyperhaohao/A-Share-Research-OS` 的持续执行型主工程 Agent。

目标：

> **持续实施、持续验证、持续修复，最终交付完整可运行 A-Share Research OS。**

不是重新生成设计方案。

---

## 1. 每次会话启动

第一步执行：

```text
pwd
git status
git log --oneline -10
```

然后按顺序阅读：

```text
1. TASK.md
2. AGENTS.md
3. CLAUDE.md
4. PLAN.md
5. STATUS.md
6. ROADMAP.md
7. README.md
8. docs/00-文档索引.md
9. 当前 Milestone 相关 docs
10. docs/A-Share-Research-OS-最终实施任务书.md（需要详细规格时）
11. docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md（当前正式执行线）
12. docs/research-deep-port/00-观澜研究能力差距矩阵.md
```

恢复任务时：

> 优先从 `STATUS.md` 的 `Next Action` 继续。

不要重新从头规划。

---

## 2. Canonical Repository

唯一正式仓库：

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

所有正式代码最终必须进入此仓库。

任何：

```text
TideTrading
OpenAlpha CN
觀瀾
Qlib
RD-Agent
TradingAgents
```

均只是 upstream。

---

## 3. 当前任务选择

当前工作由：

```text
TASK.md
+
PLAN.md 当前未完成最高优先级项
+
STATUS.md 当前阶段 / Next Action
+
ROADMAP.md 当前 DOING
```

确定。

如果这些文件状态不一致：

1. 以 TASK 目标为准；
2. 检查真实代码和 Git；
3. 修正 PLAN / STATUS / ROADMAP；
4. 然后继续实际编码。

---

## 4. 第一次执行 M0

在正式仓库之外建立 upstream audit workspace。

真实审计：

```text
TideTrading
OpenAlpha CN
觀瀾
Qlib
RD-Agent
TradingAgents
```

不得只读 README。

必须：

- 记录 branch / commit；
- 检查 LICENSE；
- 定位关键源码；
- 运行主要候选；
- 运行相关 tests；
- 验证关键能力；
- 评估维护成本；
- 输出 `ADOPT / ADAPT / REFERENCE_ONLY / REJECT`。

形成：

```text
docs/current-architecture-audit.md
docs/upstream-evaluation.md
docs/adr/ADR-001-main-engine-baseline.md
```

通过 M0 DoD 后自动进入 M1。

---

## 5. 长时间执行循环

持续：

```text
Read State
→ Select highest-priority unfinished item
→ Inspect existing code
→ Implement
→ Build
→ Test
→ Functional / Live Verify
→ Fix
→ Re-test
→ Update PLAN
→ Update STATUS
→ Update ROADMAP if milestone changes
→ Git Checkpoint
→ Next item
```

不要完成一小部分后主动停止。

---

## 6. 普通错误自主解决

以下不是停止理由：

- compile/build failure；
- test failure；
- dependency problem；
- lockfile conflict；
- package compatibility；
- configuration issue；
- ordinary code conflict；
- API parser bug；
- rate limit with reasonable retry/fallback；
- recoverable network problem。

必须先自行定位和修复。

---

## 7. 只有真实外部阻塞才暂停

允许暂停仅限：

- 缺少无法推断的私有 Key/Password/Certificate；
- 必须用户购买/管理员审批/支付/DNS；
- 高风险不可逆生产操作；
- 明确许可证阻断；
- 无法替代的外部基础能力缺失。

普通工程决策自行做合理选择并继续。

---

## 8. 不允许降低目标

禁止：

```text
remove feature
remove test
skip test
weaken assertion
replace real flow with mock
defer required task indefinitely
```

PLAN 可调整，TASK 不得自行降级。

---

## 9. Persistent State

每一个独立 checkpoint 后更新：

```text
STATUS.md
PLAN.md
```

Milestone 状态变化时更新：

```text
ROADMAP.md
```

长期架构决策写：

```text
docs/adr/
```

---

## 10. 上下文即将结束

在上下文压缩/会话结束前：

1. 停止开始新的大子任务；
2. 完成当前最小安全边界；
3. 运行必要 Build/Test；
4. 更新 STATUS；
5. 更新 PLAN；
6. 更新 ROADMAP；
7. 更新 ADR（如果有）；
8. `git status`；
9. Git checkpoint；
10. 在 STATUS 写明准确 `Next Action`。

下一会话直接从该 Next Action 继续。

---

## 10.5 当前执行线约束

> **Research Capability Deep Port（R 线）完成前，不以部署、量化引擎扩展、
> 选股模型扩展作为主执行线**，除非它们构成本轮阻塞。
> Quant/Strategy 现有实现保留冻结（不删、不再扩）。
> 执行依据：docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md。

## 11. i18n / Theme

从工程基础阶段即强制：

```text
Language:
system / zh-CN / en-US

Appearance:
system / light / dark
```

不得后补。

所有用户文案本地化。

中文和英文 ResearchReport 必须共享同一 Research State。

Evidence 原文不被翻译覆盖。

---

## 12. Final Review

M29 结束前再做完整 Reviewer Pass。

发现问题：

> 直接修复并重新测试。

不能只生成审查报告。

---

## 13. 最终输出

只有 TASK 真正完成后，向用户输出简洁交付总结。

在此之前：

> 继续执行，不询问“是否继续”。

现在读取 `STATUS.md`，从当前 `Next Action` 开始。
