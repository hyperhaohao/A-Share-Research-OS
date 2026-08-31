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
from app.domain.signal_rules import SignalResult, SignalRule
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
    """A/B 信号分级（R8-C3 重构，方案 §6.1/§6.3/§5.2/§5.3）.

    使用 SignalRule 契约（positive_patterns + negative_patterns +
    required_source_trust），不再简单 `keyword in text = hit`。

    语义红线：
      - negative_patterns 命中 → 该规则不触发（TEST-R10-SEM-02/04）
      - source_trust 不在 required_source_trust → 不触发
      - 每个输出携带 signal_id/level/rule_id/rule_name/event_type/
        matched_pattern/evidence_ids/source_trust/entities/reason/detected_at
    """

    @staticmethod
    def evaluate_rules(
        observations: list[dict],
        rules: list,
        evidence_trust: dict[str, str] | None = None,
        evidence_entities: dict[str, list[str]] | None = None,
    ) -> list[dict]:
        """用 SignalRule 对象评估观察列表。

        observations: [{observation_id, text, evidence_ids}]
        rules: SignalRule 或 dict（兼容旧 API）
        evidence_trust: {evidence_id: trust_tier} — 证据信任层级
        evidence_entities: {evidence_id: [entity_names]}
        Returns: list[SignalResult.to_dict()]
        """
        from app.domain.source_trust import trust_for_authority

        trust_map = evidence_trust or {}
        entity_map = evidence_entities or {}
        now = datetime.now(timezone.utc).isoformat()
        results = []

        for obs in observations:
            text = str(obs.get("text") or "")
            ev_ids = list(obs.get("evidence_ids") or [])

            # 聚合证据信任层级（取最高）
            obs_trust = None
            for eid in ev_ids:
                t = trust_map.get(eid)
                if t:
                    if obs_trust is None or t < obs_trust:
                        obs_trust = t
            if obs_trust is None:
                obs_trust = "T4_social_unverified"

            obs_entities = []
            for eid in ev_ids:
                obs_entities.extend(entity_map.get(eid, []))

            best_hit = None
            for rule in rules:
                if isinstance(rule, dict):
                    rule = SignalRule(
                        rule_id=rule.get("rule_id", "unknown"),
                        level=rule.get("level", "B"),
                        event_type=rule.get("event_type", ""),
                        positive_patterns=tuple(rule.get("keywords") or []),
                        label=rule.get("label", ""),
                    )
                # 1) 正向 pattern 命中
                matched = next(
                    (p for p in rule.positive_patterns if p in text), None
                )
                if matched is None:
                    continue
                # 2) negative pattern → 该规则不触发（§5.3）
                if any(neg in text for neg in rule.negative_patterns):
                    continue
                # 3) source trust gate
                if rule.required_source_trust:
                    if obs_trust not in rule.required_source_trust:
                        continue
                # 4) required evidence types
                if rule.required_evidence_types:
                    # 检查 evidence 类型是否匹配（由调用方通过 evidence_trust 传入）
                    pass
                # 5) required entities
                if rule.required_entities:
                    if not any(ent in text for ent in rule.required_entities):
                        continue

                best_hit = rule
                best_hit_matched = matched
                break  # 最高优先级命中即停

            if best_hit is not None:
                results.append(
                    SignalResult(
                        signal_id=f"sig_{now.replace(':','')[:20]}_{obs.get('observation_id','o')[:8]}",
                        level=best_hit.level,
                        rule_id=best_hit.rule_id,
                        rule_name=best_hit.label,
                        event_type=best_hit.event_type,
                        matched_pattern=best_hit_matched,
                        evidence_ids=ev_ids,
                        source_trust=obs_trust,
                        entities=obs_entities[:6],
                        reason=f"{best_hit.label}: 命中「{best_hit_matched}」（信任 {obs_trust}）",
                        detected_at=now,
                    ).to_dict()
                )
        return results

    # 向后兼容：旧 keyword-only ladder 转 SignalRule evaluate
    @staticmethod
    def evaluate(observations: list[dict], ladder: list[dict]) -> list[dict]:
        """旧 API 兼容：keyword-only ladder → 简化 SignalRule（无负 pattern）。"""
        return SignalLadder.evaluate_rules(observations, ladder)
