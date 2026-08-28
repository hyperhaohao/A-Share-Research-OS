"""Announcements providers (R1.2).

Primary:  CNINFO (巨潮资讯) — the statutory disclosure platform (authority A2).
Fallback: Eastmoney announcement feed (authority B2 — major financial data
          platform relaying official disclosure content).

The CNINFO feed was observed timing out (504) from this network during the
R1 endpoint survey; the fallback chain is exactly the mechanism designed for
that: CNINFO fails → registry falls through → Eastmoney serves.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.instrument import Exchange
from app.sources.base import (
    SourceRecord,
    SourceRequest,
    SourceResult,
    SourceStatus,
    utc_now,
)
from app.sources.http import http_json, http_post_json
from app.sources.provider import BaseProvider

_CNINFO_QUERY = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
_CNINFO_TOPSEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
_CNINFO_STATIC = "http://static.cninfo.com.cn/"
_EM_ANN = "https://np-anotice-stock.eastmoney.com/api/security/ann"


def _ts_to_dt(ms: float | int | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class CninfoAnnouncementsProvider(BaseProvider):
    """法定披露平台（巨潮）— authority A2."""

    provider_id = "cninfo_announcements"
    capabilities = frozenset({"announcements"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        exchange_str, code = instrument_id.split(":", 1)
        attempted_at = utc_now()

        # step 1: orgId lookup (required by the CNINFO query API)
        org_data, failure = http_post_json(
            _CNINFO_TOPSEARCH, data={"keyWord": code, "maxNum": 10}
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)
        orgs = org_data or []
        org_id = None
        for org in orgs:
            if org.get("code") == code:
                org_id = org.get("orgId")
                break
        if not org_id:
            return self._no_data(
                request, f"no cninfo orgId for {instrument_id}", attempted_at=attempted_at
            )

        # step 2: announcement query
        query, failure = http_post_json(
            _CNINFO_QUERY,
            data={
                "pageNum": 1,
                "pageSize": int(request.params.get("limit", 10)),
                "column": "sse" if exchange_str == "SSE" else "szse",
                "tabName": "fulltext",
                "stock": f"{code},{org_id}",
                "seDate": request.params.get("date_range", ""),
                "searchkey": request.params.get("keyword", ""),
            },
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        announcements = (query or {}).get("announcements") or []
        if not announcements:
            return self._no_data(
                request, "no announcements in range", attempted_at=attempted_at
            )

        records: list[SourceRecord] = []
        for item in announcements[: int(request.params.get("limit", 10))]:
            title = (item.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")
            if not title or title == "公告摘要":
                continue
            url_path = item.get("adjunctUrl") or ""
            announced = _ts_to_dt(item.get("announcementTime") or item.get("announcementStamp"))
            records.append(
                SourceRecord(
                    subject=instrument_id,
                    kind="announcement",
                    payload={
                        "title": title,
                        "announcement_id": item.get("announcementId"),
                        "column": item.get("columnName"),
                    },
                    event_time=announced,
                    available_time=announced or utc_now(),
                    source_uri=_CNINFO_STATIC + url_path if url_path else None,
                )
            )
        if not records:
            return self._no_data(request, "no usable announcements", attempted_at=attempted_at)
        return self._success(records, request, attempted_at=attempted_at)


class EastmoneyAnnouncementsProvider(BaseProvider):
    """东方财富公告转载流 — authority B2（重大金融数据平台转载法定披露内容）。"""

    provider_id = "eastmoney_announcements"
    capabilities = frozenset({"announcements"})

    def fetch(self, request: SourceRequest) -> SourceResult:
        instrument_id = request.instrument_id
        if not instrument_id or ":" not in instrument_id:
            raise ValueError(f"malformed instrument_id: {instrument_id!r}")
        _exchange, code = instrument_id.split(":", 1)
        attempted_at = utc_now()

        data, failure = http_json(
            _EM_ANN,
            params={
                "sr": -1,
                "page_size": int(request.params.get("limit", 10)),
                "page_index": 1,
                "ann_type": "A",
                "client_source": "web",
                "stock_list": code,
            },
        )
        if failure is not None:
            return self._failure(request, failure[0], failure[1], attempted_at=attempted_at)

        items = ((data or {}).get("data") or {}).get("list") or []
        records: list[SourceRecord] = []
        for item in items[: int(request.params.get("limit", 10))]:
            title = item.get("title") or ""
            if not title:
                continue
            notice_date = item.get("notice_date") or item.get("eiTime") or ""
            try:
                announced = datetime.fromisoformat(notice_date.strip().replace(" ", "T")).replace(
                    tzinfo=timezone(timedelta(hours=8))
                )
            except ValueError:
                announced = utc_now()
            art_code = item.get("art_code") or ""
            records.append(
                SourceRecord(
                    subject=instrument_id,
                    kind="announcement",
                    payload={
                        "title": title,
                        "announcement_id": art_code,
                        "columns": [c.get("column_name") for c in item.get("columns", [])],
                    },
                    event_time=announced,
                    available_time=announced,
                    source_uri=f"https://data.eastmoney.com/notices/detail/{code}/{art_code}.html",
                )
            )
        if not records:
            return self._no_data(request, "no announcements", attempted_at=attempted_at)
        return self._success(records, request, attempted_at=attempted_at)
