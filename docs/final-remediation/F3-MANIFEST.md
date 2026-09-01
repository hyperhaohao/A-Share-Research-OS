# F3-MANIFEST — Signal Production Fix

> 阶段：F3（第三轮整改任务书 §11 F3 / §6 P0-C）
> 日期：2026-09-02 | 基线：docs/final-remediation/F0-BASELINE.md

## 交付

### 1. 生产 API 500 修复（Golden 6b，F0 基线复现项）
- 根因：`evaluate_evidence_signals` 将 pydantic `InstrumentProfile` 当 dict 使用
  （`profile.get("name")`）→ AttributeError → 500；
- 修复：API 收薄，委托新服务 `app/services/signal_production.py`。

### 2. 正式 API 契约重构（§6.2/§6.3）
- 调用方只传 `instrument_id + evidence_ids`；自定义 level/keywords/ladder
  无入口（行为面测试断言规则集 ⊆ BUILTIN_SIGNAL_RULES）；
- **Instrument Ownership Gate**：跨标的证据显式 `rejected_evidence`
  （cross_instrument + 归属披露），不再静默 continue；
- **Trust Gate**：自动加载 trust_for_evidence；不满足 → 显式拒绝原因；
- **Type Gate**：required_evidence_types 逐证据真实执行；
- **Entity Gate**：实体来自 Instrument Registry（name + aliases 文本命中），
  解析状态显形（registry_entities_resolved）；无 000831 硬编码清单
  （全库 grep 复核：0 命中，仅 commander 示例文案）；
- **Negative / State Transition Gate**：否定标记逐规则记录
  `negative_pattern:<词>` 拒绝原因；state_transition 落结果；
- 返回含 §6.3 全部键：rule_id / signal_level / event_type /
  matched_evidence_ids / trust_gate / type_gate / entity_gate /
  state_transition / rejected_reasons（逐证据×逐规则拒绝迹，上限 200 显式截断披露）；
- 有界评估（MAX_EVIDENCE=50），超限显式 rejected_evidence 记录。

### 3. §6.4 Golden 语义 → 8 个 API 级测试（真实规则 + 真实仓储，无 Mock）

| # | 场景 | 断言 | 结果 |
|---|---|---|---|
| 1 | 股东减持披露 | restructuring/asset_injection 信号 = 无 | PASS |
| 2 | 否认筹划重大重组 | 无 A；negative_pattern 拒绝迹 | PASS |
| 3 | 正式停牌筹划重组公告 | A + §6.3 全键 + trust/type gate passed + B→A | PASS |
| 4 | T4 传闻「注入预案即将公布」 | 无 A；trust_gate 拒绝迹 | PASS |
| 5 | 同业竞争解决方案披露 | B（related_party_boundary_change） | PASS |
| 6 | 其他公司重组公告 | results=[]；rejected_evidence=cross_instrument | PASS |
| 7 | 终止重大资产重组 | 无 A；negative_pattern:终止 拒绝迹 | PASS |
| 8 | 默认加载 + 契约形状 + 规则集白名单 | PASS | PASS |

## 真实验证（Live Verify，compose 栈重建后实测）

```text
docker compose build backend && up -d
迁移：b8c9d0e1f2a4 → c2d3e4f5a6b7 于真实数据卷自动应用（现有 DB 可升级 ✓）
POST /api/v1/research-inbox/signal-ladder/evaluate-evidence?instrument_id=SZSE:000831
  → HTTP 200（修复前 500）
  → evaluated: evidence_count=50, rules=6, registry_entities_resolved=true
  → rejected trace 200 条（显式披露）
```

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（422 collected = 404 基线 + 10 F2 + 8 F3）
```

## 修改文件

- backend/app/services/signal_production.py（新增）
- backend/app/api/research_inbox_api.py（endpoint 收薄）
- backend/tests/test_f3_signal_production.py（新增 8 用例）

## 状态

IMPLEMENTED / INTEGRATED / TESTED / REAL_VERIFIED（live 栈 200 + 迁移自动应用）。
F14 将重跑完整 Golden 脚本（含 6a/6b）。
