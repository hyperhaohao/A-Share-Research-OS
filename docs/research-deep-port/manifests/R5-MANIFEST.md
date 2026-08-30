# R5-MANIFEST — Research Product System

```text
donor basis:      98f1398（REFERENCE_ONLY）
backend:
  - app/domain/research_products.py：7 类产品契约（P0 四类 + P1 三类），
    每契约显式 required_sections/intent/missing_data_behavior=disclose/
    monitor_behavior/market_wide/notes（方案 §11.2 拒绝纯 Prompt 隐式约定）
  - reports.product_type 列（migration e5f6a7b8c9d1）——复用既有 Report/
    Version/Artifact 基座（§11 不建平行报告系统）
  - pipeline.run(product_type=...)：编译期契约校验（validate_product →
    缺 Required Section → data_quality_notes 显形，不编造；阻断仍由
    既有 FinalReportQualityGate 决定）；报告 Artifact 标题随契约类型化
    （「中国稀土 · 事件调查」）
  - commander：焦点 → 产品类型映射（event→EVENT_INVESTIGATION 等；
    黄金问题落 EVENT_INVESTIGATION）
frontend: 报告卡片标题经既有报告页呈现（类型在标题中显形）
live verify (manifests/R5-LIVE-VERIFY.md):
  黄金问题 → plan meta product_type=EVENT_INVESTIGATION → plan completed →
  report artifact 标题「中国稀土 · 事件调查」
sequencing note（如实）:
  MAINLINE_RADAR / OVERSEAS_MAPPING / DAILY_RESEARCH_BRIEF 三类市场级产品
  的编译器在 R8（Research Inbox 数据就绪后）实现——其数据源（Inbox 聚合）
  属 R8 交付面；契约已在本阶段定义并校验。此为顺序依赖而非能力推迟出轮。
tests:            tests/test_r5_research_products.py 4/4；全量 backend exit 0
next: R6 Experience 非量化改造
```
