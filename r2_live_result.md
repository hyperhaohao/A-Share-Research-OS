# R2 Live Verification（真实 000831 证据，经 API 全程 UTF-8）

## 1) T3 主流媒体证据 · 原文直引抽取
- evidence: ev_354ccd574db838d0085a8830 (authority=B2)
- statement: ○财政部、税务总局、中国证监会发布关于规范转让上市公司限售股个人所得税政策的公告
- verdict: **accepted** (T3_mainstream_media)

## 2) T3 单源升格 confirmed_fact
- verdict: **rejected** reason=trust_escalation（需 ≥1 条 T0/T1 或 ≥2 独立 T2/T3）

## 3) 行情证据 · 真实数字抽取
- evidence: ev_9529118864a731929265706c (authority=B2)
- verdict: **accepted** (T3_mainstream_media)

## 4) 行情证据 · 编造数字 61.99
- verdict: **rejected** reason=number_not_in_source

