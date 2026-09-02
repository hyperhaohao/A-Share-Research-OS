"""Research Product Compilers（R8-C7，方案 §11.4/§11.5/§11.6）.

三类市场级研究产品编译器：从 Inbox/语义对象/证据语料聚合真实数据。
不走管线（非 instrument-scoped），而是市场级只读投影 + 编译。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

from app.domain.research_products import get_contract
from app.storage.orm import EvidenceORM
from app.storage.agent_repo import AgentRepository
from app.domain.agents import ResearchRequestStatus


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class MarketProductCompiler:
    """市场级研究产品编译器（非 instrument-scoped）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _recent_evidence(self, hours: int = 48, limit: int = 50) -> list:
        cutoff = _utc() - timedelta(hours=hours)
        return self._session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.available_time >= cutoff)
            .order_by(EvidenceORM.available_time.desc())
            .limit(limit)
        ).all()

    def compile_mainline_radar(self) -> dict:
        """主线雷达（方案 §11.4）：叙事 → 证据 → 驱动 → 产业映射 → 反方。"""
        from app.application.industry_semantic import IndustrySemanticRepository

        sem_repo = IndustrySemanticRepository(self._session)
        drivers = sem_repo.latest_by_type("driver", limit=20)
        narratives = sem_repo.latest_by_type("narrative", limit=20)
        recent = self._recent_evidence(48, 30)

        # 产业映射：driver/narrative 的 industry_id → 相关标的
        lines = []
        for d in drivers:
            lines.append({
                "kind": "driver",
                "industry": d["industry_id"],
                "title": d["title"],
                "direction": d.get("direction") or "uncertain",
                "evidence_count": len(d.get("evidence_refs") or []),
            })
        for n in narratives:
            lines.append({
                "kind": "narrative",
                "industry": n["industry_id"],
                "title": n["title"],
                "status": n.get("status") or "emerging",
                "evidence_count": len(n.get("evidence_refs") or []),
            })
        for e in recent[:10]:
            if "稀土" in (e.summary or "") or "有色" in (e.summary or ""):
                lines.append({
                    "kind": "evidence",
                    "industry": "有色",
                    "title": (e.summary or "")[:120],
                    "direction": None,
                    "evidence_count": 1,
                })

        return {
            "product_type": "MAINLINE_RADAR",
            "compiled_at": _utc().isoformat(),
            "items": lines,
            "count": len(lines),
            "note": "主线雷达 = 叙事/驱动/证据 聚合（非涨幅榜）",
        }

    def compile_overseas_mapping(self) -> dict:
        """海外映射（方案 §11.5）：海外事件 → 影响 → 中国映射（每条挂证据）。"""
        # F12（§10.5）：诚实命名 —— 关键词证据雷达 ≠ 完整海外映射；
        # 映射链缺口显形（missing_chain），不得冒充 Mapping
        overseas_kw = ("海外", "美股", "美联储", "美国", "欧洲", "欧盟", "美元", "关税", "出口")
        recent = self._recent_evidence(72, 100)
        overseas_ev = [
            e for e in recent
            if any(kw in (e.summary or "") for kw in overseas_kw)
        ]
        items = []
        for e in overseas_ev[:15]:
            items.append({
                "evidence_id": e.evidence_id,
                "title": (e.summary or "")[:160],
                "at": e.available_time.isoformat() if e.available_time else None,
                "kind": e.evidence_type,
            })
        return {
            "product_type": "OVERSEAS_EVIDENCE_RADAR",
            "mapping_depth": "evidence_radar",
            "missing_chain": [
                "global_industry_mapping",
                "china_industry_mapping",
                "a_share_company_mapping",
                "transmission_evidence_chain",
            ],
            "compiled_at": _utc().isoformat(),
            "items": items,
            "count": len(items),
            "note": "海外证据雷达（每条必须挂证据，禁止无证据荐股）；完整海外映射链未接入，缺口显形（§10.5）",
        }

    def compile_daily_brief(self) -> dict:
        """每日研究简报（方案 §11.6）：Inbox + Thesis 变化 + 信号 + 请求聚合。"""
        from app.services.research_inbox import ResearchInboxService

        inbox = ResearchInboxService(self._session).inbox(window_hours=24, limit_per=10)
        sections = []

        if inbox["new_evidence"]:
            sections.append({
                "title": "新证据",
                "items": [
                    {"text": f"{e['instrument_id']} {e['title'][:80]}", "at": e.get("at")}
                    for e in inbox["new_evidence"][:5]
                ],
            })
        if inbox["materiality_alerts"]:
            sections.append({
                "title": "重要性预警",
                "items": [
                    {"text": f"{m['instrument_id']} {m['decision']}", "at": m.get("at")}
                    for m in inbox["materiality_alerts"][:5]
                ],
            })
        if inbox["open_research_requests"]:
            sections.append({
                "title": "待补研究请求",
                "items": [
                    {"text": f"{r['instrument_id']} {r['capability']} {r['reason'][:60]}", "at": None}
                    for r in inbox["open_research_requests"][:5]
                ],
            })
        # F12（§10.6）：Thesis 变化 / 信号命中 / 到期验证 / 建议下一步
        if inbox.get("thesis_changes"):
            sections.append({
                "title": "Thesis 变化",
                "items": [
                    {"text": f"{c['instrument_id']} {c['title'][:70]}", "at": c.get("revision_at")}
                    for c in inbox["thesis_changes"][:5]
                ],
            })
        if inbox.get("signal_ladder_hits"):
            sections.append({
                "title": "信号命中",
                "items": [
                    {"text": f"{h['instrument_id']} {h['signal_level']} {h['rule_id']}", "at": None}
                    for h in inbox["signal_ladder_hits"][:5]
                ],
            })
        if inbox.get("predictions_due"):
            sections.append({
                "title": "即将到期验证",
                "items": [
                    {"text": str(p.get("instrument_id", "")) + " " + str(p.get("prediction_id", ""))[:16],
                     "at": p.get("due_at")}
                    for p in inbox["predictions_due"][:5]
                ],
            })
        recommended = []
        non_quote = [e for e in inbox["new_evidence"] if e.get("kind") != "market_quote"]
        if non_quote:
            recommended.append(
                "对 " + non_quote[0]["instrument_id"] + " 启动 Delta 研究（窗口内有新非行情证据）"
            )
        if inbox.get("signal_ladder_hits"):
            h0 = inbox["signal_ladder_hits"][0]
            recommended.append("复核 " + h0["instrument_id"] + " 的 " + h0["signal_level"] + " 级信号")
        if inbox.get("failed_collections"):
            recommended.append("检查失败采集源（Source Health）")
        if inbox.get("predictions_due"):
            recommended.append("处理即将到期的预测验证")
        if recommended:
            sections.append({"title": "建议下一步", "items": [{"text": r, "at": None} for r in recommended]})
        if inbox["failed_collections"]:
            sections.append({
                "title": "采集失败",
                "items": [
                    {"text": f"{f['instrument_id']} {f['capability']} {f['status']}", "at": None}
                    for f in inbox["failed_collections"][:5]
                ],
            })

        return {
            "product_type": "DAILY_RESEARCH_BRIEF",
            "compiled_at": _utc().isoformat(),
            "sections": sections,
            "section_count": len(sections),
            "note": "研究简报 = Inbox/Thesis/信号 聚合（非行情播报）",
        }


    # ── G9：编译持久化（Artifact/Version/PIT/Provenance） ────────────────────

    def compile_and_register(self, kind: str) -> dict:
        """编译 + 版本落库 + Artifact 注册（§G9：临时 dict 不再冒充产品）。

        kind: mainline_radar | overseas_mapping | daily_brief
        返回 {compile_id, product_type, version, as_of, artifact_id, product,
              diff_vs_previous}
        """
        from app.application.artifacts import ArtifactService
        from app.storage.research_product_orm import ResearchProductCompileORM

        if kind == "mainline_radar":
            product = self.compile_mainline_radar()
        elif kind == "overseas_mapping":
            product = self.compile_overseas_mapping()
        elif kind == "daily_brief":
            product = self.compile_daily_brief()
        else:
            raise ValueError(f"unknown product kind: {kind}")

        prev_version = self._session.scalars(
            select(ResearchProductCompileORM)
            .where(ResearchProductCompileORM.product_type == product["product_type"])
            .order_by(ResearchProductCompileORM.version.desc())
            .limit(1)
        ).first()
        version = (prev_version.version + 1) if prev_version is not None else 1

        artifact_id = None
        provenance_status = "complete"
        try:
            artifact_id = ArtifactService(self._session).register(
                artifact_type="research_product",
                domain_type="ResearchProduct",
                domain_id=f"{product['product_type']}:{version}",
                title=f"{product['product_type']} v{version}",
                instrument_ids=(),
                created_by="research_products",
                route="/research-products",
                as_of_time=None,
                version=version,
            )
        except Exception as exc:  # noqa: BLE001 — 显形 INCOMPLETE_PROVENANCE（§G2.6）
            provenance_status = "INCOMPLETE_PROVENANCE"
            artifact_error = f"{type(exc).__name__}: {exc}"[:200]

        row = ResearchProductCompileORM(
            compile_id=f"cmp_{uuid4().hex[:16]}",
            product_type=product["product_type"],
            version=version,
            as_of=_utc(),
            payload_json=product,
            artifact_id=artifact_id,
            provenance_status=provenance_status,
            created_at=_utc(),
        )
        self._session.add(row)
        self._session.flush()

        # 与上一版差异（§G9：每版可查看与上一版变化）
        diff = {"version": version, "previous_version": prev_version.version if prev_version else None,
                "changed": True if prev_version is None else None}
        if prev_version is not None:
            prev_items = prev_version.payload_json.get("items") or prev_version.payload_json.get("sections") or []
            cur_items = product.get("items") or product.get("sections") or []
            diff = {
                "version": version,
                "previous_version": prev_version.version,
                "previous_items": len(prev_items),
                "current_items": len(cur_items),
                "changed": len(prev_items) != len(cur_items),
            }
        out = {
            "compile_id": row.compile_id, "product_type": product["product_type"],
            "version": version, "as_of": row.as_of.isoformat(),
            "artifact_id": artifact_id, "provenance_status": provenance_status,
            "product": product, "diff_vs_previous": diff,
        }
        if provenance_status != "complete":
            out["provenance_error"] = locals().get("artifact_error", "artifact registration failed")
        return out

    def list_compiles(self, product_type: str | None = None, *, limit: int = 20) -> list[dict]:
        from app.storage.research_product_orm import ResearchProductCompileORM

        stmt = select(ResearchProductCompileORM).order_by(
            ResearchProductCompileORM.created_at.desc()).limit(limit)
        if product_type:
            stmt = stmt.where(ResearchProductCompileORM.product_type == product_type)
        return [
            {"compile_id": r.compile_id, "product_type": r.product_type,
             "version": r.version, "as_of": r.as_of.isoformat() if r.as_of else None,
             "artifact_id": r.artifact_id, "provenance_status": r.provenance_status}
            for r in self._session.scalars(stmt).all()
        ]

    def compile_diff(self, product_type: str, v1: int, v2: int) -> dict:
        from app.storage.research_product_orm import ResearchProductCompileORM

        rows = {
            r.version: r for r in self._session.scalars(
                select(ResearchProductCompileORM)
                .where(ResearchProductCompileORM.product_type == product_type)
                .order_by(ResearchProductCompileORM.version.asc())
            ).all()
        }
        if v1 not in rows or v2 not in rows:
            raise ValueError("version not found")
        a, b = rows[v1], rows[v2]
        return {
            "product_type": product_type, "v1": v1, "v2": v2,
            "v1_as_of": a.as_of.isoformat(), "v2_as_of": b.as_of.isoformat(),
            "v1_items": len((a.payload_json or {}).get("items") or []),
            "v2_items": len((b.payload_json or {}).get("items") or []),        }
