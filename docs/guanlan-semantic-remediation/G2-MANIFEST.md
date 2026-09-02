# G2-MANIFEST — 产业语义 PIT/证据治理/五轴

> 观澜研究能力语义迁移任务书 §G2（P0）| 日期：2026-09-02
> 台账缺口：MIGRATION-MATRIX.md §2

## 交付

### 1. Evidence Ownership Gate（§G2.2）
语义对象 upsert 强制三重门（新增）：
- 证据存在性（citation verify 已有）+ **PIT**：`available_time > as_of` → 422；
- **产业归属**：证据文本提及产业/环节名，或标的在含该产业名的链上有
  Company Position；跨产业注入 → 422（Deterministic，错误含归属判定说明）。

### 2. 图谱链接（§G2.1）
- 迁移 c0d1e2f3a6b7：语义对象新增 chain_id/segment_id/edge_id（索引）+
  contrary_evidence_refs_json；
- upsert 接受链接参数：edge 存在性校验 + **chain 自动回填**
  （edge_id 给定而 chain_id 缺省时从 edge 反查）；contrary 证据独立列表。

### 3. Narrative Temperature 服务端复算（§G2.3）
- **从证据表读 available_time**（客户端 observed_at 提交被忽略——测试以
  observed_at=2099 伪造验证）；
- **信任门**：仅 T0/T1 证据计入已验证观察；低信任证据单独披露
  （lower_trust_obs），不进温度；basis=server_evidence_table 落响应。

### 4. GET as_of 重放（§G2.4）
- GET /industry-semantics/{type}?as_of= ：as_of 之后创建的版本不可见
  （纯读）；响应携 as_of。

### 5. GET 去隐式写库（§G2.4/§G2.5）
- /views/industry 不再隐式 build 快照（industry_map/global_context）：
  无快照 → 诚实置空 disclosures.snapshot=not_built_yet；
  快照由研究管线或显式 Command 生成（**修复：删除 GET 隐式写库路径**）；
- 测试断言：无快照标的 GET 后 industry_map_snapshots 零新行。

### 6. Artifact 注册失败显形（§G2.6）
- 语义对象 Artifact 注册 `except: pass` **废除** → 失败时
  `provenance_status=INCOMPLETE_PROVENANCE` + provenance_error 落响应；
  成功 → complete。

### 7. 五轴 Global Position（§G2.7）
- 新端点 `GET /industry-graph/chains/{id}/global-position?instrument_id=`：
  **资源**（上游 producer，链视角）/ **产能**（capacity+exposure）/
  **成本**（触及公司环节的 cost/price 传导边）/ **技术**（证据支撑的
  driver/transmission 语义对象）/ **政策**（policy 语义+policy_transmission 边）；
  每轴 ok/insufficient 显形，不再固定空页；
- UI：产业链图 tab 增加五轴面板（ok 显示条目数；insufficient 显形）。

## 测试（tests/test_g2_semantics_pit.py，7 用例）

| # | 场景 | 结果 |
|---|---|---|
| 1 | Ownership Gate（相关 OK/跨产业 422/未来 422） | PASS |
| 2 | 图谱链接（缺 edge 422；合法→chain 回填落库+provenance 状态） | PASS |
| 3 | 服务端温度（warming 计算 + observed_at=2099 伪造忽略 + basis） | PASS |
| 4 | 信任门（低信任 D 级证据不计入，lower_trust_obs=1 披露） | PASS |
| 5 | GET as_of 重放（历史不可见/当前可见） | PASS |
| 6 | GET 零隐式写库（无快照标的 → not_built_yet + 零新行） | PASS |
| 7 | 五轴（resource/capacity ok；cost/technology/policy insufficient→加 driver 后 technology ok；缺链 404） | PASS |
（R3 温度测试与 phase H 视图测试按新契约更新：R3 温度测试改为服务端语义 +
伪造 observed_at 忽略验证；phase H 测试改为显式建快照 Command 前置）

## 全量回归

```text
backend pytest 全量：exit 0，0 FAILED（474 collected）
frontend：tsc PASS + vitest 35/35 + build PASS
```

## 状态

IMPLEMENTED / INTEGRATED / TESTED。
Gap→G3：Experience 规则组件输出（mechanism/preconditions/signals 结构化字段）
与 Approval 接 Confirmation Gate。
