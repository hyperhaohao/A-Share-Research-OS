# C8-MANIFEST — Research Inbox UI + Research Memory UI + Thesis Center（整改 P1-03/04/05）

```text
frontend:
  - features/research-center/ResearchCenterPages.tsx：三页
    - ResearchInboxPage（/research-inbox）：新证据/重要性预警/研究请求/失败采集
    - ResearchMemoryPage（/research-memory）：candidate→promote→active + 类型过滤
    - ThesisCenterPage（/thesis-center）：Current Thesis + 版本链 + Diff
  - 路由 + nav 研究 group + i18n（zh/en）
  - 视觉基线重生成（侧栏新增 3 条目）
E2E: E2E-12 flaky（kline 环境限制，非 C8 引入）；其余 29 PASS
next: C9 LLM + Confidence Cleanup → C10 Full Regression → C11 Final Closure
```
