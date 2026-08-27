# Evidence & PIT（任务书 §22-§26/§73-§75）

## 四时钟

| 时钟 | 含义 |
|------|------|
| event_time | 底层事件发生时间 |
| available_time | 市场首次可知时间 —— PIT 可见性以此为准 |
| ingested_time | 本系统入库时间 |
| revision_time | 数据最后一次修订时间 |

校验：全部 timezone-aware；ingested/revision 不得早于 available。

## PIT 强制点

1. **域层**：`EvidenceRecord.visible_at(as_of)` = available_time ≤ as_of；
2. **快照构建**：`SnapshotRepository.build` 只纳入可见证据，并对每条再做
   `visible_at` 双重确认；naive as_of 直接拒绝；
3. **不可变性**：同 (instrument, as_of) 重建返回已存快照 —— 后来数据永不改写历史；
4. **查询**：`EvidenceRepository.list_for_instrument(visible_at=…)` SQL 级过滤。

测试：`test_snapshot_pit.py`（§74 场景：未来证据不可见、边界 == as_of 可见、
幂等重建、新增数据不改历史）。

## 内容寻址

`content_hash = sha256(instrument|type|source|title|summary|excerpt|event_time|
available_time|metadata_canonical_json)`；`evidence_id = "ev_" + hash[:24]`。
采集幂等：同源同内容只存一行（唯一约束 + 仓储级查重）。

## 权威度 / 事实状态

- authority_level（§25）：A1 监管/公司一手 → A2 法定披露平台 → B1 官方 →
  B2 主要媒体/大型行情转发 → C1 专业研究 → C2 二级媒体 → D 传闻；
- fact_status（§26）：confirmed_fact / official_disclosure / regulatory_document /
  management_statement / media_report / market_expectation / analyst_inference / rumor。

映射示例：行情快照 = confirmed_fact + B2（交易所是一手，腾讯是大型转发商）。
