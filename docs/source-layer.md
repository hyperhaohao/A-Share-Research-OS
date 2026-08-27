# Source Layer

> 契约：`backend/app/sources/base.py`；语义蓝本 OpenAlpha CN providers/base.py（MIT，已注明）。

## SourceResult 八态

```text
success | no_data | partial | network_error | rate_limit | parse_error | auth_error | source_unavailable
```

不变量：success 必须携带 ≥1 记录；no_data 必须给出原因；失败禁止携带记录且必须给出
error_type；retryable 与状态分类联动（网络/限流/不可用可重试，解析/认证不可）。

## Provider 契约（capability-based）

```python
class SourceProvider(Protocol):
    provider_id: str
    capabilities: frozenset[str]   # market_data / financials / announcements / …
    def fetch(self, request: SourceRequest) -> SourceResult: ...
```

不要求实现全部能力；registry 按能力筛选并按注册顺序 fallback。provider 抛出的异常
由 registry 捕获并转为显式 SOURCE_UNAVAILABLE（provider 崩溃不击穿调度）。

## 已实现 Provider

| provider | capability | 说明 |
|----------|-----------|------|
| tencent_quote | market_data | 腾讯实时行情（GBK 字段布局，live 验证过），无 key |

新增 provider：继承 `BaseProvider`，用 `_success/_no_data/_failure` 构造结果并在
`app/sources/runtime.py` 注册。

## fallback / 缓存 / health

- fallback：SUCCESS/PARTIAL 即停；NO_DATA 与失败继续；全链耗尽返回合成
  SOURCE_UNAVAILABLE（永不静默空返回）。
- 缓存：按能力 TTL（market_data 5s … instrument 24h）；`from_cache` 透明标注；
  Refresh 流程用 `fresh=True` 旁路。
- health：每 (provider, capability) 记录最近状态与连续失败数，3 次失败判不可用；
  `GET /api/v1/source-health` 暴露。
