# R2-MANIFEST — Source Trust + Evidence-backed Extraction

```text
donor basis:      98f1398（REFERENCE_ONLY / BEHAVIORAL ADAPTATION —— License Gate 未通过）
ASRO base:        3c319ac（R0）→ 本 commit
backend:
  - app/domain/source_trust.py：T0-T4 业务信任层（authority A1-D → 业务层，
    读时派生，不建平行字段）；check_fact_support（confirmed_fact 门槛：
    ≥1 T0/T1 或 ≥2 独立 T2/T3，否则 TrustEscalationError）；
    trust_for_evidence：market_quote 经 A2/B2 持牌转载 = 交易所原始数据 T0
    （方案 §8.2 T0 语义），叙述性证据不升级
  - app/domain/extraction.py：Extraction 契约（statement/source_evidence_id/
    support_span/fact_status/claim_type/confidence_basis/extractor/
    prompt_version）+ CitationVerifier 确定性内核：
    ① support_span 归一化包含于原文 ② statement 数字 ⊆ 原文数字（防编造）
    ③ T4 升格 confirmed_fact 拒绝；verdict_basis=deterministic 诚实标注
  - app/application/extraction.py + extraction_records 表（migration
    b1c2d3e4f5a6）：rejected 留档审计、accepted 可晋升
  - POST /extractions / GET /extractions / POST /extractions/{id}/promote
    （promote 走既有 Claim domain → 引用完整性/PIT 继承）
  - 质量门 AnalysisQualityGate 新增 analysis.source_trust_escalation（FAIL）
frontend:
  - formatSourceTrust（authority → T0-T4 业务名，zh/en）+
    ExperienceSourcePane 证据行信任徽章（data-testid=evidence-trust）
injection boundary: 指令样源文本 = 纯数据（verdict 仅内容裁决）；
  T4 上 confirmed_fact 一律拒绝 —— 单测锁定
live verify:      docs/research-deep-port/manifests/R2-LIVE-VERIFY.md
  （真实 000831 证据：T3 政策原句抽取 accept / T3 单源升格 confirmed_fact
  reject trust_escalation / 行情真实数字 accept / 编造数字 61.99 reject
  number_not_in_source —— 8 条抽取落档可查）
tests:            tests/test_r2_source_trust.py 5/5；全量 backend exit 0；
  既有 quality gate 测试按新契约补 authority 桩（意图不变）
next: R3 Industry Semantic Engine（稀土真实框架跑通）
```
