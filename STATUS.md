# STATUS.md

# Current Execution Status — Remediation（整改）

> 本文件只描述当前状态。历史记录见 `docs/milestones/`。
> 整改阶段详情与任务清单见 `REMEDIATION.md`（整改状态唯一来源）。

---

## Current Phase

```text
Remediation — R5 Production Research E2E
```

## Current Milestone

```text
R5.1–R5.4：多标的 Live Research E2E → 长时运行测试 → 生产复验 →
Final Reviewer Pass
```

## Completed

```text
R0.1  REMEDIATION.md 建立（整改状态源，含 14 项真实缺口基线）
R0.2  STATUS 重写为整改态；旧状态归档 docs/milestones/M0-M29-initial-delivery-STATUS.md
```

## In Progress

```text
R0.5 RunManifest 真实值（git commit / SHA256 config digest / 真实 seed）
R0.6 QualityGate 绕过修复（report_compiler data_quality or True、估值假设占位）
R0.7 测试重分类（api_integration / live 标记）
```

## Next Action

```text
1. R0.5 修 app/services/pipeline.py RunManifest：git rev-parse HEAD、
   配置规范化 SHA256、uuid4 派生真实 random_seed
2. R0.6 修 app/services/report_compiler.py:245 or True 绕过 + :240 估值假设占位
   （数据质量 section 实际渲染内容；估值假设来自真实估值输入或留空 FAIL）
3. R0.7 pyproject 增加 pytest markers（api_integration/live）；docs/testing.md 分类说明
4. Build + 全量 pytest + checkpoint → 进入 R1
```

## Tests

```text
Baseline（整改前最后全量）：backend 240+ / frontend 8+ PASS
R0 验证：待 R0.5–R0.7 完成后全量重跑
```

## Live Verification

```text
腾讯行情 live 验证历史 PASS（M3/M4）。
R1 将扩展公告/财务/新闻 live 验证。
```

## Open Issues

```text
1. Provider 仅腾讯行情（R1 补齐）
2. Pipeline 主链不完整：仅 market→analyst(facts)→report（R2 重构）
3. 无 LLM Provider 进主流程（R3）
4. Quant 未进正式主链（R3 方案 A）
5. Scheduler 无后台服务进程（R3 compose 第三服务）
6. Workspace 信息架构不完整（R4）
7. 现有 E2E 为 API Integration（monkeypatch），非 Live Research E2E（R5）
```

## Branch / Commit

```text
Branch: main
Commit: 见 git log（整改起点 = d4c7cef 之后）
Remote: github.com/hyperhaohao/A-Share-Research-OS.git
```
