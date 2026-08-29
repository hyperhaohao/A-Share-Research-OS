"""Industry relations provider — 同业板块成员（V2 深度扩展 a，总纲 §10/§52）.

产业链关系源 v1：东财行业板块成员。链路：
    suggest（板块检索，industry_label → BK 代码）→ clist（板块成员列表）
成员即真实同业公司（交易所公认的板块归属，basis 可溯源）。

诚实边界：任一环节失败 → 显式 failure（产业地图回落到证据文本共现并
披露），绝不编造成员。
"""

from __future__ import annotations

from app.domain.code_norm import normalize_code
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    utc_now,
)
from app.sources.http import http_json
from app.sources.provider import BaseProvider

_SUGGEST_URL = "https://searchapi.eastmoney.com/api/suggest/get"
_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_SUGGEST_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"


class EastmoneyIndustryRelationsProvider(BaseProvider):
    """同业板块成员：industry_label → 东财行业板块 → 成员公司列表."""

    provider_id = "eastmoney_industry_relations"
    capabilities = frozenset({"industry_relations"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        keyword = (request.params.get("keyword") or "").strip()
        if not keyword:
            raise ValueError("industry_relations requires params.keyword")
        attempted_at = utc_now()

        board = self._find_board(keyword)
        if board is None:
            return self._no_data(
                request, f"no board found for industry {keyword!r}",
                attempted_at=attempted_at,
            )
        board_code, board_name = board

        members, failure = self._board_members(board_code)
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)
        if not members:
            return self._no_data(
                request, f"board {board_code} has no members", attempted_at=attempted_at
            )

        payload = {
            "industry_label": keyword,
            "board_code": board_code,
            "board_name": board_name,
            "members": members,
            "member_count": len(members),
            "relations_provider": self.provider_id,
        }
        record = SourceRecord(
            subject=f"BOARD:{board_code}",
            kind="industry_relations",
            payload=payload,
            event_time=None,
            available_time=utc_now(),
            source_uri=_CLIST_URL,
        )
        return self._success([record], request, attempted_at=attempted_at)

    def _find_board(self, keyword: str) -> tuple[str, str] | None:
        data, failure = http_json(
            _SUGGEST_URL,
            params={
                "input": keyword,
                "type": "14",
                "token": _SUGGEST_TOKEN,
                "count": 10,
            },
            timeout=self._timeout_s,
        )
        if failure is not None or not data:
            return None
        items = ((data or {}).get("QuotationCodeTable") or {}).get("Data") or []
        for item in items:
            code = item.get("Code") or ""
            name = item.get("Name") or ""
            if code.startswith("BK") and item.get("MktNum") == "90":
                return code, name
        return None

    def _board_members(self, board_code: str) -> tuple[list[dict], tuple[object, str] | None]:
        data, failure = http_json(
            _CLIST_URL,
            params={
                "pn": 1,
                "pz": 100,
                "fs": f"b:{board_code}",
                "fields": "f12,f14",
                "fid": "f3",
            },
            timeout=self._timeout_s,
        )
        if failure is not None:
            return [], failure
        diff = ((data or {}).get("data") or {}).get("diff") or {}
        items = list(diff.values()) if isinstance(diff, dict) else (diff or [])
        members: list[dict] = []
        for item in items:
            code = str(item.get("f12") or "")
            name = str(item.get("f14") or "")
            if not code or len(code) != 6 or not code.isdigit():
                continue
            instrument_id = self._to_instrument_id(code)
            if instrument_id is None:
                continue
            members.append({"code": code, "name": name, "instrument_id": instrument_id})
        return members, None

    @staticmethod
    def _to_instrument_id(code: str) -> str | None:
        """A-share code prefix → canonical instrument id (structural prefix
        rules are authoritative; non-A-share members are skipped)."""
        from app.domain.instrument import instrument_id_for

        try:
            _resolved, exchange, _board = normalize_code(code)
        except Exception:  # noqa: BLE001 — non-A-share member codes are skipped
            return None
        return instrument_id_for(exchange, code)
