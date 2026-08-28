"""Eastmoney news + macro/policy providers (R1.4 / R1.7).

News: keyword search over eastmoney's article index. Authority C2
(secondary media) — media news must never sit at the same authority level
as official announcements (整改 §6.6).

Macro/policy: the same index filtered by policy topics and an official-source
keyword whitelist; items mentioning an official body carry authority B2 with
fact_status media_report (a media report OF a policy is not the government's
own publication — B1 is reserved for direct official publications).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.domain.instrument import Exchange
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    utc_now,
)
from app.sources.http import http_json
from app.sources.provider import BaseProvider

_SEARCH = "https://search-api-web.eastmoney.com/search/jsonp"
_CB = "cb"

_OFFICIAL_BODIES = (
    "央行", "中国人民银行", "国务院", "证监会", "发改委", "财政部",
    "统计局", "工信部", "金融监管总局", "国资委",
)


def _search_param(keyword: str, page_size: int) -> str:
    return json.dumps(
        {
            "uid": "",
            "keyword": keyword,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "0",
                    "sort": "time",
                    "pageIndex": 1,
                    "pageSize": page_size,
                    "preTag": "",
                    "postTag": "",
                }
            },
        },
        ensure_ascii=False,
    )


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text or "")


def _parse_date(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw.strip().replace(" ", "T")).replace(
            tzinfo=timezone(timedelta(hours=8))
        )
    except ValueError:
        return utc_now()


class _BaseNewsProvider(BaseProvider):
    def _search(self, keyword: str, limit: int) -> tuple[list[dict], tuple | None]:
        data, failure = http_json(
            _SEARCH,
            params={"cb": _CB, "param": _search_param(keyword, limit)},
            jsonp=True,
            timeout=self._timeout_s,
        )
        if failure is not None:
            return [], failure
        result = ((data or {}).get("result") or {}).get("cmsArticleWebOld") or []
        return result, None

    def _record(self, subject: str, item: dict) -> SourceRecord:
        published = _parse_date(item.get("date") or "")
        title = _strip_html(item.get("title") or "")
        content = _strip_html(item.get("content") or "")[:600]
        return SourceRecord(
            subject=subject,
            kind="news",
            payload={
                "title": title,
                "summary": content,
                "article_code": item.get("code"),
                "media_source": "eastmoney",
            },
            event_time=published,
            available_time=published,
            source_uri=f"https://finance.eastmoney.com/a/{item.get('code')}.html",
        )

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._timeout_s = timeout


class EastmoneyNewsProvider(_BaseNewsProvider):
    """公司新闻 — authority C2（二级媒体，低于正式公告）。"""

    provider_id = "eastmoney_news"
    capabilities = frozenset({"news"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange_str, code = instrument_id.split(":", 1)
        Exchange(exchange_str)  # validate
        attempted_at = utc_now()

        keyword = request.params.get("keyword")
        if not keyword:
            from app.domain.catalog import default_catalog

            matches = default_catalog().resolve(instrument_id, limit=1)
            keyword = matches[0].instrument.name if matches else code
        limit = int(request.params.get("limit", 8))

        items, failure = self._search(keyword, limit)
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)
        records = [self._record(instrument_id, i) for i in items if i.get("title")]
        if not records:
            return self._no_data(
                request, f"no news for {keyword}", attempted_at=attempted_at
            )
        return self._success(records, request, attempted_at=attempted_at)


class EastmoneyMacroPolicyProvider(_BaseNewsProvider):
    """宏观/政策 — 按主题/行业/关键词检索，官方机构提及时标注。"""

    provider_id = "eastmoney_macro_policy"
    capabilities = frozenset({"macro_policy"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        keyword = request.params.get("keyword") or request.params.get("topic")
        if not keyword:
            raise ValueError("macro_policy requires params.keyword or params.topic")
        attempted_at = utc_now()
        subject = request.params.get("subject") or "MACRO:POLICY"
        limit = int(request.params.get("limit", 8))

        items, failure = self._search(f"{keyword} 政策", limit)
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        records: list[SourceRecord] = []
        for item in items:
            if not item.get("title"):
                continue
            text = f"{item.get('title', '')}{item.get('content', '')}"
            mentions_official = any(body in text for body in _OFFICIAL_BODIES)
            record = self._record(subject, item)
            records.append(
                SourceRecord(
                    subject=record.subject,
                    kind=record.kind,
                    payload={
                        **record.payload,
                        "topic": keyword,
                        "mentions_official_body": mentions_official,
                        "official_bodies": [b for b in _OFFICIAL_BODIES if b in text],
                    },
                    event_time=record.event_time,
                    available_time=record.available_time,
                    source_uri=record.source_uri,
                )
            )
        if not records:
            return self._no_data(
                request, f"no policy news for {keyword}", attempted_at=attempted_at
            )
        return self._success(records, request, attempted_at=attempted_at)
