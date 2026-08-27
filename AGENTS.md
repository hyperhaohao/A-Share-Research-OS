# AGENTS.md

# A-Share Research OS — Agent Execution Rules

> 本文件只规定 Coding Agent 如何执行。
>
> 不重复产品规格。
>
> 最终任务目标见 `TASK.md`。
> 详细产品规格见 `docs/A-Share-Research-OS-最终实施任务书.md`。

---

## 1. 规则优先级

发生冲突时：

```text
用户当前明确指令
↓
TASK.md
↓
AGENTS.md / CLAUDE.md
↓
PLAN.md / STATUS.md / ROADMAP.md
↓
实际项目架构和已有代码
↓
README / docs
```

不得修改低优先级文件来规避高优先级要求。

---

## 2. Canonical Repository

唯一正式仓库：

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

所有正式源码、测试、Migration、文档和部署配置最终必须进入该仓库。

上游项目必须位于正式仓库之外，只能作为：

```text
audit
reference
adapter source
licensed code source
```

不得把任一 upstream Fork 当作最终产品仓库。

---

## 3. 长时间自主执行

本项目是持续执行任务。

Agent 的目标不是给建议，而是：

```text
Implement
→ Build
→ Test
→ Verify
→ Fix
→ Update State
→ Git Checkpoint
→ Next Task
```

直到 `TASK.md` 的最终完成条件满足，或遇到真实外部阻塞。

完整执行协议：

```text
docs/01-长时间自主执行协议.md
```

---

## 4. 启动 / 恢复前必须执行

开始任何代码修改前：

```text
pwd
git status
git log --oneline -10
```

然后阅读：

```text
TASK.md
AGENTS.md
CLAUDE.md
PLAN.md
STATUS.md
ROADMAP.md
README.md
```

再按当前 Milestone 阅读相关 docs。

必须查真实代码、配置、数据库、接口、测试和构建状态。

禁止仅根据文档假设功能已完成。

---

## 5. 状态文件职责

```text
TASK.md
= 不可自行降低的最终任务契约

PLAN.md
= 可动态调整的执行计划

STATUS.md
= 跨上下文持久执行状态

ROADMAP.md
= 长期 Milestone 状态
```

PLAN 可以调整实现路径。

STATUS 必须持续更新。

TASK 不得为了适应实现而降级。

---

## 6. 实现原则

采用：

> 垂直闭环、增量交付、真实数据、真实调用、真实测试、真实验收。

优先：

```text
复用现有实现
>
扩展现有实现
>
局部重构
>
新建体系
```

禁止重复架构。

---

## 7. 当前范围

以：

```text
ROADMAP.md 当前 DOING Milestone
+
PLAN.md 当前 Phase
+
STATUS.md Next Action
```

共同确定当前工作。

除修复前置 blocker 外，不扩展到无关后续 Milestone。

---

## 8. 禁止空架构

禁止提前创建：

- 空目录；
- 空 Service / Repository / Adapter / Controller；
- 空 API；
- 空 UI 页面；
- 未使用 Schema；
- `pass`；
- `NotImplementedError`；
- TODO 代替当前必须功能。

未来能力到真实需要时再创建。

---

## 9. 禁止伪完成

不得用以下方式标记 DONE：

```text
Mock业务数据
固定JSON
随机行情
placeholder
按钮无行为
仅Schema
仅API
仅UI
测试只覆盖Mock
Source失败伪装成无数据
Report citation不可追溯
ReportVersion覆盖旧版本
Scheduler不执行真实研究
Prediction可以事后修改
```

Fixture 可以用于测试，但 Source Milestone 必须至少一次真实数据验证。

---

## 10. 修改范围

禁止顺便：

- 全项目格式化；
- 无关目录迁移；
- 无关重命名；
- 无关依赖升级；
- 无关框架迁移；
- 纯审美大重构。

发现技术债务记录，不扩大当前任务。

---

## 11. Build / Test / Verify

每个可验证阶段至少按实际技术栈执行：

```text
Build
Unit Test
Integration Test
必要的 Functional / Live Verification
Review
```

失败必须分析并修复。

禁止：

```text
删除测试
skip测试
降低断言
注释失败代码
用Mock替代真实失败
```

---

## 12. 错误处理

Build/Test/Dependency/Third-party 普通错误都默认自行处理。

只有 `docs/01-长时间自主执行协议.md` 定义的真实外部阻塞才允许暂停请求用户。

普通工程选择不是 BLOCKED。

---

## 13. 上游源码复用

M0 必须真实审计：

- TideTrading；
- OpenAlpha CN；
- 觀瀾；
- Qlib；
- RD-Agent；
- TradingAgents。

每个必须给出：

```text
ADOPT
ADAPT
REFERENCE_ONLY
REJECT
```

复制任何源码前：

1. 检查 LICENSE；
2. 检查文件级许可；
3. 记录来源；
4. 只使用许可证允许内容；
5. 不明确时只参考，不复制。

TideTrading 是优先审计对象，不是预设最终底座。

---

## 14. Research Discipline

正式研究必须：

```text
Source before Evidence
Evidence before Claim
Claim before Thesis
Thesis before Opinion
Valuation before Recommendation
Every conclusion traceable
```

历史研究强制 PIT。

LLM 不得凭模型记忆创造正式事实。

缺失数据必须显式展示。

---

## 15. i18n

正式 UI 必须支持：

```text
system
zh-CN
en-US
```

所有用户可见文案必须可本地化。

后端业务协议优先稳定 code / enum，不把中文文本当协议值。

中文/英文报告共享同一 Research State。

Evidence 原文永久保留。

---

## 16. Theme

必须支持：

```text
system
light
dark
```

默认：

```text
system
```

使用 Design Tokens / CSS Variables。

图表、Graph、Markdown、Dialog、Tooltip、Table 等都必须完成 Light/Dark 验证。

---

## 17. Git Safety

修改前必须 `git status`。

保护用户未提交修改。

未经明确授权禁止：

```text
git reset --hard
git clean -fd
git checkout .
force push
```

---

## 18. Git Checkpoint

推荐：

```text
一个独立可验证阶段
=
一个 checkpoint
```

Checkpoint 前：

- 对应 Build/Test 完成；
- PLAN 更新；
- STATUS 更新；
- ROADMAP 在 Milestone 状态变化时更新。

避免每几行一个 commit，也避免数小时只有一个巨大 commit。

---

## 19. Context Persistence

每个阶段、重要修复、上下文压缩前、会话结束前必须更新：

```text
STATUS.md
```

至少：

- current phase；
- current milestone；
- branch；
- commit；
- completed；
- in progress；
- next action；
- tests；
- live verification；
- issues；
- decisions；
- modified files。

然后更新 PLAN / ROADMAP。

---

## 20. Milestone DONE

只有同时满足：

- 真实业务入口；
- 真实业务逻辑；
- 真实输出；
- 自动测试；
- 必要真实验证；
- 无 Mock 冒充；
- 无当前必须占位；
- 无已知关键回归；
- 文档与实现一致；

才能标记 DONE。

---

## 21. Final Reviewer Pass

全部实现完成后必须再次 Reviewer 视角检查并直接修复：

- unfinished code；
- swallowed exception；
- missing error handling；
- null/concurrency/resource issue；
- security；
- auth；
- injection；
- XSS；
- secrets；
- API mismatch；
- i18n遗漏；
- theme遗漏；
- PIT violation；
- traceability gap；
- recovery gap；
- test gap。

不能只输出 Review Report。

---

## 22. 最终结束条件

只有：

```text
TASK.md 全部完成
AND
PLAN 必要阶段完成
AND
ROADMAP 必要Milestone完成
AND
Build PASS
AND
Tests PASS
AND
E2E PASS
AND
Core Flows PASS
AND
Production Delivery PASS
AND
Final Reviewer PASS
```

才允许宣布任务完成。

不得说：

```text
“剩余可以以后实现”
“建议下一步”
“如果愿意我可以继续”
```

只要属于 TASK，直接继续执行。
