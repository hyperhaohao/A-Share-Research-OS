# R3-MANIFEST — Industry Semantic Research Engine

```text
donor basis:      98f1398（REFERENCE_ONLY：只迁概念/结构，不复制 ai_chain.yaml 语料）
ASRO base:        0b94e40（R2）
backend:
  - app/domain/industry_semantic.py：方向/叙事状态/五轴/温度 枚举
    （direction: positive|negative|mixed|uncertain；温度=可复算定性四态，
    方案 §9.5 禁造数值）
  - app/application/industry_semantic.py + industry_semantic_objects 单表
    （migration c3d4e5f6a7b8）：四类语义对象统一存储（object_type/
    object_key/version append-only）；创建/更新强制 引用反查（复用 R2
    归一化包含；无引用/反查失败 → 422 citation_failed，不进正式研究状态）
  - GET /industry-semantics/{type}（最新版本聚合）/ POST upsert /
    GET /{type}/{key}（全版本历史）/ GET /narrative/{key}/temperature
  - /views/industry 并入 semantics（driver/transmission/narrative/position
    按链级集合聚合——稀土级条目与有色金属级条目同属本行业视图）
frontend:
  - IndustryChainView 驱动/传导/叙事面板消费真实语义（方向徽章/状态徽章），
    空时保持 暂无观点 显形
live verify (rare-earth pilot, manifests/R3-LIVE-VERIFY.md):
  - Driver「广晟控股减持计划带来股份供给压力」(negative) —— 引用 2 条真实
    新闻证据（人民财讯/中证报 2026-08-20 广晟减持 ≤1061.22 万股/≤1%），
    引用反查通过，201 v1
  - Narrative「稀土板块股东减持：广晟控股拟减持中国稀土不超过1%」(active) ——
    引用 2 条真实证据，201 v1
  - 伪造 span → 422 industry_semantic.citation_failed ✓
  - 视图并读 drivers=1 narratives=1 ✓；UI 真机显示真实条目 ✓
  - 温度：证据点 <3 → insufficient 显形 ✓（不造数字）
deviations from DoD（如实）:
  - Transmission ≥1 未达成：当前语料无稀土链级传导的真实证据句，
    按 §23（禁 Mock/禁 LLM 填空）保持诚实置空；引擎已就绪，证据出现即可入
  - 五轴真实定位：无证据 → 诚实空（同上）
tests:            tests/test_r3_industry_semantic.py 4/4；全量 backend exit 0
next: R4 Research Commander Autonomous Loop
```
