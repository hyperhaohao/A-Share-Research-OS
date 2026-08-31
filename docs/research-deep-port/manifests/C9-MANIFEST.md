# C9-MANIFEST — LLM Real Verification + Confidence Cleanup（整改 P1-06/P2-01）

```text
C9a LLM Real Verification:
  status: BLOCKED_EXTERNAL — ASRO_LLM_API_KEY 缺失
  pipeline + schema + 422 显形已就绪（R6）；有 KEY 后设 .env 即生效
  不可冒充验证完成（§15.1 IMPLEMENTED + BLOCKED_EXTERNAL）

C9b Confidence Cleanup:
  - confidence_level() 函数：high/medium/low/insufficient 四级定性
    （确定性规则：T0/T1→high；2×T2/T3→medium；contrary→low；无证据→insufficient）
  - 替代伪精确 0.6 小数；后续 UI 展示 confidence_level 替代数字
deviations: 前端展示切换留待 R9 图谱扩展（当前 UI 已显示 confidence
  但不展示为精确研究结论——只是数据字段）
next: C10 Full Regression
```
