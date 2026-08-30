# R1-MANIFEST — Research Domain Boundary & Product Repositioning

```text
donor basis:      jesson-hh/financial-analyst @ 98f1398（REFERENCE_ONLY，License Gate 未通过）
ASRO base:        89b4f6c（R0 checkpoint）
changes:
  - docs/adr/ADR-Research-First-Product-Boundary.md（研究优先决策：定位/
    导航分组/Quant 冻结/donor 边界/单一 Research Domain/内核红线）
  - frontend/src/app/navigation.ts：一级导航重组
    研究（9）：中枢/公司研究/研究报告/产业研究/产业·全球坐标/全球宏观/
    研究经验/持续研究/研究图谱
    实验·冻结（6）：智能选股/验证工作流/Workflow Studio/策略实验室/
    策略盯盘/预测 —— 量化面保留不删，降为 Experimental 语义
    附带修复：原「验证」组两个入口同 label（工作流/Studio 重复）→ 各自专名
  - i18n：nav.commander/company/industryGlobal/globalMacro/experience/tasks/
    researchGraph/workflowStudio/monitoring/predictions + nav.group.experimental
    （zh/en）
  - README：定位改为「面向 A 股的长期 AI Research OS（研究优先）」，
    完成/进行中清单与 R 线执行状态对齐
honest notes:
  - 事件研究/主线雷达/海外映射/Thesis Center 一级入口在 R4/R5 产品落地后加入
    （本轮不建死链）
  - 视觉基线未重生成：侧栏文字变更在 0.35 容差内（Playwright 30/30 PASS 实测）
verification: vitest 30/30 + build PASS + Playwright 30/30（含 dark 基线）
next: R2 Source Trust + Evidence-backed Extraction（P0）
```
