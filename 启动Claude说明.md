# 给 Claude Code 的启动说明

把本包内容放入唯一正式仓库：

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

然后对 Claude Code 只发送：

> 这是一个长时间持续执行任务，不是一次性问答。请确认当前仓库为 `hyperhaohao/A-Share-Research-OS`，依次读取 `TASK.md`、`AGENTS.md`、`CLAUDE.md`、`PLAN.md`、`STATUS.md`、`ROADMAP.md`、`README.md` 和当前阶段相关 docs。首先执行 `pwd`、`git status`、`git log --oneline -10`，然后从 `STATUS.md` 的当前阶段和 Next Action 开始实际工作。不要重新生成方案，不要等待我逐步确认，不要提前创建未来空架构。持续执行 Implement → Build → Test → Verify → Fix → Update PLAN/STATUS → Git Checkpoint → Next Task。普通错误自行解决；只有真实外部阻塞才暂停。上下文即将结束时必须持久化 STATUS/PLAN/ROADMAP 并 Git checkpoint。只有 `TASK.md` 全部要求、完整 Build/Test/E2E、核心流程、PIT、Traceability、双语、System/Light/Dark、部署、备份恢复和最终 Reviewer Pass 全部通过后才允许宣布完成。

后续 Claude 会话不需要再次粘贴完整任务书。

只需：

> 读取 TASK / PLAN / STATUS / ROADMAP，从 STATUS 的 Next Action 继续。
