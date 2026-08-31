# C4-MANIFEST — Citation Semantic Entailment（整改 P0-05）

```text
problem:  Citation Verification 只做 span 包含 + 数字一致，不检查语义方向
fix:      verify_extraction 增加 _semantic_entailment（§7.4 四维度确定性检查）:
  1. 方向一致性：statement「筹划」+ evidence「否认」→ semantic_direction_conflict
  2. 计划/完成：statement「计划」+ evidence「已完成」→ modality_conflict
  3. 范围扩大：statement「全部」+ evidence「部分」→ scope_inflation
  4. 主体偷换：v1 通过 entity overlap 间接覆盖
verdict:  accepted/rejected（uncertain 留给 LLM entailment 接入后启用）
live:     evidence「筹划」+ statement「否认」→ rejected semantic_direction_conflict
tests:    R2 套件 + 全量 backend exit 0（含 C4 语义冲突真实用例）
next:     C5 Golden Semantic Test
```
