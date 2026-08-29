"""Global macro numeric provider — 全球宏观数值层（V2 深度扩展 b，总纲 §11）.

固定指标集的真实市场数值（指数/商品），来自腾讯行情源（与本机网络兼容；
东财 push2 对本机网络不可达）。数值层与资讯层（macro_policy）共同构成
全球宏观坐标 —— 数值永远带来源与市场时间，绝不编造。
"""

from __future__ import annotations

from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    utc_now,
)
from app.sources.http import http_json
from app.sources.provider import BaseProvider

_QUOTE_URL = "https://qt.gtimg.cn/q"

# 固定指标集：代码 → 展示名（数值全部来自真实行情源）
INDICATORS: tuple[tuple[str, str], ...] = (
    ("sh000001", "上证指数"),
    ("usDJI", "道琼斯工业指数"),
    ("usNDX", "纳斯达克100"),
    ("hkHSI", "恒生指数"),
    ("hf_GC", "COMEX黄金"),
    ("hf_OIL", "布伦特原油"),
)


class TencentGlobalMacroProvider(BaseProvider):
    """全球宏观数值：指数与商品的真实行情数值层."""

    provider_id = "tencent_global_macro"
    capabilities = frozenset({"global_macro"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        attempted_at = utc_now()
        codes = ",".join(code for code, _name in INDICATORS)
        data, failure = http_json(
            _QUOTE_URL,
            params={"q": codes},
            timeout=self._timeout_s,
            encoding="gbk",
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        raw = data if isinstance(data, str) else ""
        indicators = self._parse(raw)
        if not indicators:
            return self._no_data(
                request, "macro quote feed returned no usable indicators",
                attempted_at=attempted_at,
            )

        payload = {
            "indicators": indicators,
            "indicator_count": len(indicators),
            "macro_provider": self.provider_id,
        }
        record = SourceRecord(
            subject=request.instrument_id,
            kind="global_macro",
            payload=payload,
            event_time=None,
            available_time=utc_now(),
            source_uri=_QUOTE_URL,
        )
        return self._success([record], request, attempted_at=attempted_at)

    @staticmethod
    def _parse(raw: str) -> list[dict]:
        """Parse both tencent response shapes:
        stock rows ``v_xxx="1~name~code~price~..."`` and
        futures rows ``v_xxx="price,change,...,name"``."""
        indicators: list[dict] = []
        wanted = dict(INDICATORS)
        for line in raw.split(";"):
            line = line.strip()
            if "=" not in line or "~" not in line and "," not in line:
                continue
            head, _, body = line.partition("=")
            code = head.removeprefix("v_").strip()
            name = wanted.get(code)
            if name is None:
                continue
            values = body.strip().strip('"').split("~" if "~" in body else ",")
            if code.startswith("hf_"):
                price = values[0] if values else ""
                change = values[1] if len(values) > 1 else ""
                market_time = values[12] if len(values) > 12 else ""
                display = values[-1] if values else name
                indicators.append(
                    {
                        "code": code,
                        "name": f"{name}（{display}）" if display else name,
                        "value": _to_float(price),
                        "change": _to_float(change),
                        "market_time": market_time,
                    }
                )
                continue
            # stock shape: f3=price, f4=prev close, f32=change_pct (index 32)
            price = values[3] if len(values) > 3 else ""
            prev = values[4] if len(values) > 4 else ""
            change = values[32] if len(values) > 32 else ""
            market_time = values[30] if len(values) > 30 else ""
            indicators.append(
                {
                    "code": code,
                    "name": name,
                    "value": _to_float(price),
                    "change": _to_float(change) if change else None,
                    "market_time": market_time,
                }
            )
        return [i for i in indicators if i["value"] is not None]


def _to_float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None
