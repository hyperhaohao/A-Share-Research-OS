# A-Share Research OS

面向 A 股研究的长期 Research OS。

系统维护每个研究标的持续演化的 **Research State**（Evidence → Claim → Thesis → Valuation → Report → Prediction → Validation），而不是每次重新生成互不关联的 Markdown。

## 当前状态

执行状态与进度见：

```text
TASK.md       最终任务契约（不可降级）
PLAN.md       动态执行计划
STATUS.md     当前持久执行状态（从 Next Action 恢复）
ROADMAP.md    Milestone 状态
docs/         架构、审计、ADR 与规格文档
```

当前阶段：**M0 — 上游/底座源码审计**（见 [ROADMAP.md](ROADMAP.md)）。

## Canonical Repository

```text
https://github.com/hyperhaohao/A-Share-Research-OS.git
```

所有正式代码、测试、部署配置只进入本仓库。上游项目仅作为审计/参考/Adapter 来源。

## 文档

- [docs/00-文档索引.md](docs/00-文档索引.md)
- [docs/A-Share-Research-OS-最终实施任务书.md](docs/A-Share-Research-OS-最终实施任务书.md)

## 开发

工程基线在 M0 审计完成、ADR-001 确定后建立。届时本节更新为实际的 Build/Test 命令。
