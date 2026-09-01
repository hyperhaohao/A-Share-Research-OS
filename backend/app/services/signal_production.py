"""Production Signal Evaluation（F3，第三轮整改任务书 §6 P0-C）.

正式 API 契约（§6.2）：调用方只传 instrument_id + evidence_ids；后端自动完成

    Evidence Load → Instrument Ownership Gate → Source Trust → Evidence Type
    → Entity Resolution → BUILTIN_SIGNAL_RULES → Negative / State Transition Gate
    → Signal Result + Provenance

§6.3 返回要求：rule_id / signal_level / event_type / matched_evidence_ids /
trust_gate / type_gate / entity_gate / state_transition / rejected_reasons。

实体来源（§6.3.4）：Instrument Registry（name + aliases）；F4 扩展
Entity Dictionary / 关系图。禁止任何 000831 专属硬编码清单。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.signal_rules import BUILTIN_SIGNAL_RULES, SignalRule
from app.domain.source_trust import trust_for_evidence
from app.storage.orm import EvidenceORM
from app.storage.research_orm import ClaimORM  # noqa: F401 (reserved for claim-linked entities)
from app.services.instrument_service import InstrumentService

# 单次评估的有界上限（慢查询/负载保护；超出显式披露，不静默截断）
MAX_EVIDENCE = 50
MAX_REJECTED_TRACE = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_registry_entities(session: Session, instrument_id: str) -> list[str]:
    """Instrument Registry → 实体名（name + aliases）。解析失败返回空并显式降级。"""
    profile = InstrumentService(session).get_profile(instrument_id, allow_remote=False)
    if profile is None:
        return []
    return [n for n in (profile.name, *profile.aliases) if n]


def _gate(passed: bool, observed, required) -> dict:
    return {"passed": passed, "observed": observed, "required": list(required)}


def evaluate_production_signals(
    session: Session,
    instrument_id: str,
    evidence_ids: list[str] | None = None,
) -> dict:
    """BUILTIN_SIGNAL_RULES 生产评估（带完整门迹与拒绝原因）。"""
    now = _now_iso()

    # ---- Evidence Load + Instrument Ownership Gate（§6.2/§6.3.2） -------------
    rejected_evidence: list[dict] = []
    rows: list[EvidenceORM] = []
    if evidence_ids:
        found = session.scalars(
            select(EvidenceORM).where(EvidenceORM.evidence_id.in_(evidence_ids[:MAX_EVIDENCE]))
        ).all()
        by_id = {r.evidence_id: r for r in found}
        for eid in evidence_ids[:MAX_EVIDENCE]:
            row = by_id.get(eid)
            if row is None:
                rejected_evidence.append(
                    {"evidence_id": eid, "reason": "evidence_not_found"}
                )
            elif row.instrument_id != instrument_id:
                # Ownership Gate：跨标的证据显式拒绝，不污染本标的信号
                rejected_evidence.append(
                    {
                        "evidence_id": eid,
                        "reason": "cross_instrument",
                        "detail": f"belongs to {row.instrument_id}",
                    }
                )
            else:
                rows.append(row)
    else:
        rows = list(
            session.scalars(
                select(EvidenceORM)
                .where(EvidenceORM.instrument_id == instrument_id)
                .order_by(EvidenceORM.available_time.desc())
                .limit(MAX_EVIDENCE)
            ).all()
        )

    if len(evidence_ids or []) > MAX_EVIDENCE:
        rejected_evidence.append(
            {"evidence_id": "*",
             "reason": "limit_exceeded",
             "detail": f"evidence_ids capped at {MAX_EVIDENCE} per evaluation"}
        )

    # ---- Source Trust + Entity Resolution（§6.2 自动加载） --------------------
    registry_entities = _resolve_registry_entities(session, instrument_id)
    obs: list[dict] = []
    for row in rows:
        text = f"{row.title or ''} {row.summary or ''}".strip()
        trust = trust_for_evidence(row.authority_level, row.evidence_type)
        # 实体 = Registry 名称/别名命中文本 + Registry 名单本身（供 entity gate）
        entities = [n for n in registry_entities if n and n in text]
        entities.extend(n for n in registry_entities if n and n not in entities)
        obs.append(
            {
                "evidence_id": row.evidence_id,
                "text": text,
                "evidence_type": row.evidence_type,
                "trust": trust.value,
                "entities": entities,
            }
        )

    # ---- BUILTIN_SIGNAL_RULES 评估（逐证据 × 逐规则门迹） ---------------------
    fired_by_rule: dict[str, dict] = {}
    rejected_trace: list[dict] = []
    trace_overflow = 0

    for o in obs:
        for rule in BUILTIN_SIGNAL_RULES:
            reasons: list[str] = []

            # 1) 正向 pattern
            matched = next((p for p in rule.positive_patterns if p in o["text"]), None)
            if matched is None:
                reasons.append("no_positive_pattern_hit")

            # 2) Negative / State Transition Gate（§5.3：否定标记阻止射向信号）
            negative_hit = next(
                (n for n in rule.negative_patterns if n in o["text"]), None
            )
            if negative_hit is not None:
                reasons.append(f"negative_pattern:{negative_hit}")

            # 3) Source Trust gate
            trust_ok = (
                not rule.required_source_trust
                or o["trust"] in rule.required_source_trust
            )
            if not trust_ok:
                reasons.append(
                    f"trust_gate:observed={o['trust']},"
                    f"required={'|'.join(rule.required_source_trust)}"
                )

            # 4) Evidence Type gate（§6.3.3：required_evidence_types 必须真实执行）
            type_ok = (
                not rule.required_evidence_types
                or o["evidence_type"] in rule.required_evidence_types
            )
            if not type_ok:
                reasons.append(
                    f"type_gate:observed={o['evidence_type']},"
                    f"required={'|'.join(rule.required_evidence_types)}"
                )

            # 5) Entity gate
            entity_ok = not rule.required_entities or any(
                ent in o["text"] for ent in rule.required_entities
            )
            if not entity_ok:
                reasons.append(
                    f"entity_gate:required={'|'.join(rule.required_entities)}"
                )

            if reasons:
                if len(rejected_trace) < MAX_REJECTED_TRACE:
                    rejected_trace.append(
                        {
                            "evidence_id": o["evidence_id"],
                            "rule_id": rule.rule_id,
                            "rejected_reasons": reasons,
                        }
                    )
                else:
                    trace_overflow += 1
                continue

            # ---- FIRED：完整门迹 + Provenance（§6.3） ------------------------
            entry = fired_by_rule.get(rule.rule_id)
            gate_detail = {
                "trust_gate": _gate(True, o["trust"], rule.required_source_trust),
                "type_gate": _gate(True, [o["evidence_type"]], rule.required_evidence_types),
                "entity_gate": _gate(
                    True, o["entities"] or None, rule.required_entities
                ),
            }
            if entry is None:
                fired_by_rule[rule.rule_id] = {
                    "signal_id": f"sig_{uuid4().hex[:16]}",
                    "rule_id": rule.rule_id,
                    "rule_name": rule.label,
                    "signal_level": rule.level,
                    "level": rule.level,  # 兼容旧消费方
                    "event_type": rule.event_type,
                    "matched_pattern": matched,
                    "matched_evidence_ids": [o["evidence_id"]],
                    "evidence_ids": [o["evidence_id"]],  # 兼容旧消费方
                    "source_trust": o["trust"],
                    "entities": o["entities"][:6],
                    "state_transition": rule.state_transition,
                    "trust_gate": gate_detail["trust_gate"],
                    "type_gate": gate_detail["type_gate"],
                    "entity_gate": gate_detail["entity_gate"],
                    "rejected_reasons": [],
                    "reason": (
                        f"{rule.label}: 命中「{matched}」"
                        f"（信任 {o['trust']}，类型 {o['evidence_type']}）"
                    ),
                    "detected_at": now,
                }
            else:
                entry["matched_evidence_ids"].append(o["evidence_id"])
                entry["evidence_ids"].append(o["evidence_id"])

    results = list(fired_by_rule.values())
    rejected: dict = {
        "trace": rejected_trace,
        "count": len(rejected_trace),
        "truncated": trace_overflow,
    }
    return {
        "instrument_id": instrument_id,
        "count": len(results),
        "results": results,
        "rejected": rejected,
        "rejected_evidence": rejected_evidence,
        "evaluated": {
            "evidence_count": len(obs),
            "rules": len(BUILTIN_SIGNAL_RULES),
            "registry_entities_resolved": bool(registry_entities),
        },
    }
