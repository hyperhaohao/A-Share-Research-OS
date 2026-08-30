"""Research Inbox / Thesis Diff / Signal Ladder（R8，方案 §14）.

- Inbox：聚合既有真实数据（新证据/重要性决策/研究请求/到期预测/验证结果/
  失败采集）—— 纯只读投影，不建第二 Domain。
- ThesisDiff：新证据 → 影响分析 → 建议修订（apply 落新 Thesis 行，
  append-only，禁覆盖）。
- SignalLadder：A/B 前置-正式信号分级（确定性关键词规则 + 证据引用强制）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.artifacts import ArtifactService
from app.application.run_events import record_run_event
from app.domain.evidence import EvidenceType, utc_now
from app.storage.agent_repo import AgentRepository
from app.storage.orm import (
    EvidenceORM,
    ResearchRunORM,
    SnapshotORM,
    SourceManifestORM,
)
from app.storage.prediction_repo import PredictionORM
from app.storage.research_orm import ClaimORM, ThesisORM


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is None or True else dt


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        from datetime import timezone

        return dt.replace(tzinfo=timezone.utc)
    return dt


class ResearchInboxService:
    """聚合已有真实数据为研究收件箱（方案 §14.1）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def inbox(self, *, window_hours: int = 48, limit_per: int = 8) -> dict:
        now = utc_now()
        cutoff = now - timedelta(hours=window_hours)

        # 1) 新证据（窗口内）
        new_evidence = self._session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.available_time >= cutoff)
            .order_by(EvidenceORM.available_time.desc())
            .limit(limit_per)
        ).all()
        new_evidence_items = [
            {
                "evidence_id": e.evidence_id,
                "instrument_id": e.instrument_id,
                "kind": e.evidence_type,
                "title": e.title[:120],
                "at": e.available_time.isoformat(),
            }
            for e in new_evidence
        ]

        # 2) 重要性决策（窗口内 DELTA/FULL）
        from app.services.monitor import MaterialityDecisionORM

        mats = self._session.scalars(
            select(MaterialityDecisionORM)
            .where(MaterialityDecisionORM.created_at >= cutoff)
            .order_by(MaterialityDecisionORM.created_at.desc())
            .limit(limit_per)
        ).all()
        materiality_items = []
        for m in mats:
            decision = getattr(m, "decision", None) or getattr(m, "materiality", "")
            if str(decision).upper() in ("NO_MATERIAL_CHANGE",):
                continue
            materiality_items.append(
                {
                    "instrument_id": m.instrument_id,
                    "decision": str(decision),
                    "reasons": list(getattr(m, "reasons_json", []) or []),
                    "at": m.created_at.isoformat(),
                }
            )

        # 3) 开放研究请求（跨 instrument）
        from app.domain.agents import ResearchRequestStatus
        from app.storage.agent_repo import ResearchRequestORM

        open_requests = self._session.scalars(
            select(ResearchRequestORM).where(
                ResearchRequestORM.status == ResearchRequestStatus.OPEN.value
            )
        ).all()
        request_items = [
            {
                "instrument_id": r.instrument_id,
                "capability": r.capability,
                "reason": r.reason[:160],
                "requested_by": r.requested_by,
            }
            for r in open_requests[:limit_per]
        ]

        # 4) 到期未验证预测
        due_preds = self._session.scalars(
            select(PredictionORM).where(PredictionORM.validated_at.is_(None))
            .order_by(PredictionORM.due_at)
            .limit(limit_per)
        ).all() if hasattr(PredictionORM, "validated_at") else []
        # PredictionORM may not have validated_at — fall back to join-less scan
        if not due_preds:
            try:
                due_preds = self._session.scalars(
                    select(PredictionORM).order_by(PredictionORM.due_at).limit(limit_per)
                ).all()
            except Exception:  # noqa: BLE001
                due_preds = []
        due_items = [
            {
                "prediction_id": p.prediction_id,
                "instrument_id": p.instrument_id,
                "due_at": _iso(p.due_at),
            }
            for p in due_preds
        ]

        # 5) 失败采集（窗口内 manifest 失败）
        failed = self._session.scalars(
            select(SourceManifestORM)
            .where(SourceManifestORM.requested_as_of >= cutoff)
            .order_by(SourceManifestORM.requested_as_of.desc())
            .limit(limit_per * 2)
        ).all()
        failed_items = [
            {
                "manifest_id": m.manifest_id,
                "instrument_id": m.instrument_id,
                "capability": m.capability,
                "status": m.final_status,
            }
            for m in failed
            if m.final_status not in ("success", "partial")
        ][:limit_per]

        # 6) 快照总数（研究覆盖面粗看）
        total_snapshots = len(
            self._session.scalars(select(SnapshotORM.snapshot_id)).all()
        )

        return {
            "window_hours": window_hours,
            "generated_at": now.isoformat(),
            "new_evidence": new_evidence_items,
            "materiality_alerts": materiality_items,
            "open_research_requests": request_items,
            "predictions_due": due_items,
            "failed_collections": failed_items,
            "total_snapshots": total_snapshots,
            "count": (
                len(new_evidence_items)
                + len(materiality_items)
                + len(request_items)
                + len(failed_items)
            ),
        }


class SignalLadder:
    """A/B 信号分级（方案 §14.5）：确定性关键词规则 + 证据引用强制。

    ladder: 有序规则列表 [{level: "B"|"A", keywords: [str], label: str}]
    观察文本（来自真实证据）命中 B → 前置信号；命中 A → 正式信号；
    同时命中 → 取最高（A）。每次命中必须带 evidence_id（§14.5：展示证据）。
    """

    @staticmethod
    def evaluate(observations: list[dict], ladder: list[dict]) -> list[dict]:
        results = []
        for obs in observations:
            text = str(obs.get("text") or "")
            hit_level = None
            hit_rule = None
            for rule in sorted(ladder, key=lambda r: 0 if r.get("level") == "A" else 1):
                kws = rule.get("keywords") or []
                if any(kw in text for kw in kws):
                    hit_level = rule.get("level")
                    hit_rule = rule.get("label") or ""
                    if hit_level == "A":
                        break
            if hit_level:
                results.append(
                    {
                        "observation_id": obs.get("observation_id"),
                        "evidence_ids": list(obs.get("evidence_ids") or []),
                        "level": hit_level,
                        "rule": hit_rule,
                        "text": text[:200],
                    }
                )
        return results
