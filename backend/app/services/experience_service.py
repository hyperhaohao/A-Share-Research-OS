"""ExperienceCard flow service (V2 Phase C, 总纲 §13/§43/§72).

原 → 炼 → 验 → 用，带版本、Evidence、PIT 和 Validation：

  create_from_report  原+炼：从报告的结构化研究状态确定性提炼
                      （thesis/claims/evidence → statement/mechanism/条件），
                      保留完整来源（§43）；LLM 只做润色，从不创造事实。
  validate            验（v1 Case validation）：以来源快照为案例，计算
                      PIT 入场价 → 最新可见价的远期收益（信息记录，
                      不伪造通过/失败）。
  approve/reject      用：至少一次验证后才允许批准（§13）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

from app.ai.llm_provider import get_llm_provider

from app.application.conversation import _ensure_utc
from app.application.experience import (
    ExperienceCardORM,
    ExperienceCardVersionORM,
    ExperienceRepository,
    ExperienceStatus,
    ExperienceValidationORM,
)
from app.application.artifacts import ArtifactService, RelationType
from app.domain.evidence import EvidenceType
from app.storage.manifest_repo import ReportVersionORM
from app.storage.research_orm import ClaimORM
from app.storage.research_repo import ResearchRepository
from app.storage.report_repo import ReportRepository
from app.storage.repository import EvidenceRepository
from app.services.instrument_service import InstrumentService


class ExperienceRefusal(ValueError):
    """Explicit refusal — the flow never invents content or skips a gate."""


class ExperienceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ExperienceRepository(session)

    # -- 原 + 炼 ------------------------------------------------------------------

    def create_from_report(self, report_id: str, *, quant_expression: str | None = None) -> dict:
        """Deterministically distill one report's research state into a card.

        Every field comes from persisted research objects; the source links
        (report_id / report_version_id / claim_ids / evidence_ids) are kept
        on the card (§43)."""
        report = ReportRepository(self._session).get(report_id)
        if report is None:
            raise KeyError(report_id)
        instrument_id = report["instrument_id"]
        snapshot_id = report["snapshot_id"]

        version_row = self._session.scalars(
            select(ReportVersionORM)
            .where(ReportVersionORM.report_id == report_id)
            .order_by(ReportVersionORM.version_no.desc(), ReportVersionORM.id.desc())
        ).first()
        if version_row is None:
            raise ExperienceRefusal("report has no rendered version")

        theses = ResearchRepository(self._session).list_theses(
            instrument_id, snapshot_id=snapshot_id
        )
        if not theses:
            raise ExperienceRefusal("report's research state has no thesis to distill")
        thesis = max(theses, key=lambda t: t.created_at)

        claim_ids = [*thesis.supporting_claims, *thesis.opposing_claims]
        claim_rows = (
            self._session.scalars(
                select(ClaimORM).where(ClaimORM.claim_id.in_(claim_ids))
            ).all()
            if claim_ids
            else []
        )
        statements = [c.statement for c in claim_rows if c.statement]
        evidence_ids: list[str] = []
        for c in claim_rows:
            evidence_ids.extend(c.supporting_evidence_refs_json or [])
            evidence_ids.extend(c.opposing_evidence_refs_json or [])
        evidence_ids = list(dict.fromkeys(evidence_ids))

        statement = (thesis.description or thesis.title).strip()[:2000]
        mechanism = "；".join(statements[:3]).strip()[:4000] or statement
        applicable = [
            *thesis.trigger_conditions,
            *thesis.catalysts,
        ]
        invalid = [
            *thesis.invalidate_conditions,
            *thesis.risks,
        ]

        now = datetime.now(timezone.utc)
        card_id = f"exp_{uuid4().hex[:12]}"
        row = ExperienceCardORM(
            card_id=card_id,
            instrument_id=instrument_id,
            title=thesis.title[:256],
            category="research_pattern",
            statement=statement,
            mechanism=mechanism,
            applicable_conditions_json=list(applicable)[:20],
            invalid_conditions_json=list(invalid)[:20],
            source_report_id=report_id,
            source_report_version_id=version_row.version_id,
            source_snapshot_id=snapshot_id,
            source_claim_ids_json=list(claim_ids),
            source_evidence_ids_json=evidence_ids[:200],
            status=ExperienceStatus.REFINED,  # 炼 completed deterministically
            quant_expression=(quant_expression or None),
            confidence=thesis.confidence,
            refine_method="deterministic",
            created_at=now,
            updated_at=now,
        )
        card = self._repo.add_card(row)
        self._repo.add_version(
            ExperienceCardVersionORM(
                card_id=card_id,
                version_no=1,
                statement=statement,
                mechanism=mechanism,
                applicable_conditions_json=list(applicable)[:20],
                invalid_conditions_json=list(invalid)[:20],
                confidence=thesis.confidence,
                method="deterministic",
                created_at=now,
            )
        )
        self._register_artifact(card)
        return card

    # -- 炼（LLM 润色，可选） -------------------------------------------------------

    def refine_with_llm(self, card_id: str) -> dict:
        """Bump the version with LLM-polished prose. Content still comes only
        from the card's own research state — the LLM never adds facts. Without
        a configured provider this refuses explicitly (the deterministic
        refine at creation is the baseline)."""
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        provider = get_llm_provider()
        if provider is None:
            raise ExperienceRefusal(
                "LLM provider not configured; the card already carries the "
                "deterministic refine from its research state"
            )
        prompt = (
            "把以下研究经验润色为更精确的机制描述，不得添加任何新事实、新数据或"
            f"新条件。\n标题：{row.title}\n陈述：{row.statement}\n机制：{row.mechanism}"
        )
        polished = provider.generate_text(prompt, system="只润色既有内容，禁止新增事实。")
        now = datetime.now(timezone.utc)
        new_no = row.current_version + 1
        self._repo.add_version(
            ExperienceCardVersionORM(
                card_id=card_id,
                version_no=new_no,
                statement=row.statement,
                mechanism=polished.strip()[:4000],
                applicable_conditions_json=list(row.applicable_conditions_json or []),
                invalid_conditions_json=list(row.invalid_conditions_json or []),
                confidence=row.confidence,
                method="llm",
                created_at=now,
            )
        )
        row.mechanism = polished.strip()[:4000]
        row.current_version = new_no
        row.refine_method = "llm"
        row.updated_at = now
        card = self._repo.save_card(row)
        self._register_artifact(card)
        return card

    # -- 炼（LLM 结构化精炼，R6 方案 §12.2） ---------------------------------------

    _REFINE_SCHEMA = (
        '{"observation": str, "mechanism": str, "preconditions": [str], '
        '"expected_outcome": str, "counter_example": str, "failure_conditions": [str], '
        '"applicable_scope": str, "invalidators": [str], "research_checklist": [str]}'
    )

    def refine_structured(self, card_id: str) -> dict:
        """R6 LLM 结构化精炼（方案 §12.2 九字段）。

        输入 = 卡自身的 research state（statement/mechanism/conditions）；
        输出 = 九字段结构（LLM 重述与组织，禁止新事实 —— prompt 约束 +
        提交者字段 extractor=llm_refine_v1 可审计）。无 KEY → 显式 422。
        原文（statement/mechanism）与炼果（refined_json）双存。
        """
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        provider = get_llm_provider()
        if provider is None:
            raise ExperienceRefusal(
                "LLM provider not configured; structured refinement requires "
                "ASRO_LLM_API_KEY (the deterministic refine remains the baseline)"
            )
        parts = [
            "你是 A 股研究方法提炼器。把下面的研究经验整理为九字段 JSON（",
            self._REFINE_SCHEMA,
            "）。硬性约束：不得添加任何新事实/新数据/新数字/新事件；"
            "只能重述、归纳、拆分输入内容；原文中的数字必须原样保留。",
            "标题：" + row.title,
            "陈述：" + row.statement,
            "机制：" + row.mechanism,
            "适用条件：" + repr(row.applicable_conditions_json),
            "失效条件：" + repr(row.invalid_conditions_json),
        ]
        prompt = chr(10).join(parts)
        raw = provider.generate_structured(prompt, schema_hint=self._REFINE_SCHEMA)
        import json as _json

        try:
            parsed = _json.loads(raw)
        except ValueError as exc:
            raise ExperienceRefusal(f"refine output not valid JSON: {exc}") from None
        required = ("observation", "mechanism", "preconditions", "expected_outcome",
                    "counter_example", "failure_conditions", "applicable_scope",
                    "invalidators", "research_checklist")
        missing = [k for k in required if k not in parsed]
        if missing:
            raise ExperienceRefusal(f"refine output missing fields: {missing}")

        now = datetime.now(timezone.utc)
        new_no = row.current_version + 1
        refined = {k: parsed[k] for k in required}
        refined["extractor"] = "llm_refine_v1"

        self._repo.add_version(
            ExperienceCardVersionORM(
                card_id=card_id,
                version_no=new_no,
                statement=row.statement,
                mechanism=row.mechanism,
                applicable_conditions_json=list(row.applicable_conditions_json or []),
                invalid_conditions_json=list(row.invalid_conditions_json or []),
                confidence=row.confidence,
                method="llm_structured",
                created_at=now,
            )
        )
        row.refined_json = refined  # type: ignore[attr-defined] — column added in R6
        row.current_version = new_no
        row.refine_method = "llm_structured"
        row.updated_at = now
        card = self._repo.save_card(row)
        self._register_artifact(card)
        return card

    # -- 验 ------------------------------------------------------------------------

    def validate_case(self, card_id: str) -> dict:
        """v1 Case validation: the source snapshot is the case — PIT entry
        price vs newest visible quote price. Informational; approval still
        requires a human/flow action."""
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        evidence_repo = EvidenceRepository(self._session)

        from app.storage.orm import SnapshotORM

        snapshot = self._session.scalars(
            select(SnapshotORM).where(SnapshotORM.snapshot_id == row.source_snapshot_id)
        ).first()
        if snapshot is None:
            raise ExperienceRefusal("source snapshot missing")
        pinned_ids = {item["evidence_id"] for item in (snapshot.items_json or [])}
        entry = self._pinned_price(row.instrument_id, pinned_ids, snapshot.as_of)
        if entry is None:
            raise ExperienceRefusal("no pinned quote in the source snapshot (PIT)")
        now = datetime.now(timezone.utc)
        all_evidence = evidence_repo.list_for_instrument(row.instrument_id, visible_at=now)
        exits = [
            e for e in all_evidence
            if e.evidence_type is EvidenceType.MARKET_QUOTE
            and (e.metadata or {}).get("price") is not None
        ]
        if not exits:
            raise ExperienceRefusal("no visible quote price to measure the forward return")
        exit_ev = max(exits, key=lambda e: e.available_time)
        exit_price = float(exit_ev.metadata["price"])
        forward_pct = round((exit_price / entry - 1) * 100, 2)

        validation = self._repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=card_id,
                method="case",
                verdict="inconclusive",  # 方向预测记录由 G8 因果链接入
                cases_json=[
                    {
                        "instrument_id": row.instrument_id,
                        "report_id": row.source_report_id,
                        "as_of": snapshot.as_of.isoformat(),
                        "entry_price": entry,
                        "exit_price": exit_price,
                        "exit_observed_at": exit_ev.available_time.isoformat(),
                        "forward_return_pct": forward_pct,
                    }
                ],
                summary=(
                    f"案例验证：自 {snapshot.as_of.date()} 入场价 {entry} → "
                    f"最新可见价 {exit_price}，远期收益 {forward_pct:+.2f}%"
                ),
                created_at=now,
            )
        )
        row.status = ExperienceStatus.VALIDATING
        row.updated_at = now
        self._repo.save_card(row)
        return validation

    # -- 用 ------------------------------------------------------------------------

    # -- 验（R6 非量化验证方法，方案 §12.3） ----------------------------------------

    _NONQUANT_METHODS = (
        "counterexample_search",
        "historical_evidence_validation",
        "cross_company_validation",
        "expert_review",
    )

    def validate_non_quant(self, card_id: str, method: str, *, note: str | None = None) -> dict:
        """非量化验证路由（方案 §12.3）：每个方法都有确定性真实行为或显式
        记录；禁止 IC/回测回潮，禁止伪造结果。"""
        if method not in self._NONQUANT_METHODS:
            raise ExperienceRefusal(f"unknown non-quant validation method: {method}")
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        now = datetime.now(timezone.utc)

        if method == "counterexample_search":
            return self._validate_counterexample_search(row, now)
        if method == "historical_evidence_validation":
            return self._validate_historical(row, now)
        if method == "cross_company_validation":
            return self._validate_cross_company(row, now)
        validation = self._repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=card_id,
                method="expert_review",
                cases_json=[{"note": (note or "专家/用户复核记录").strip()[:300]}],
                summary="人工复核记录（专家/用户 review）",
                created_at=now,
            )
        )
        return validation

    def _validate_counterexample_search(self, row, now) -> dict:
        """反例搜索（方案 §12.3）：在本标的当前可见证据语料中做确定性检索，
        命中负面共现句即引用落档；搜不到 = 「语料中未见反例」（≠没有反例）。"""
        from app.domain.evidence import EvidenceType

        corpus = EvidenceRepository(self._session).list_for_instrument(
            row.instrument_id, visible_at=datetime.now(timezone.utc)
        )
        counter_hits = []
        for e in corpus:
            neg_words = ("低于", "下滑", "失效", "未能", "否认", "不适用", "回落")
            if e.evidence_type in (EvidenceType.NEWS, EvidenceType.INDUSTRY_DATA) and any(
                neg in (e.summary or "") for neg in neg_words
            ):
                counter_hits.append(
                    {
                        "evidence_id": e.evidence_id,
                        "summary": (e.summary or "")[:160],
                        "basis": "同标的语料负面证据共现（确定性检索）",
                    }
                )
            if len(counter_hits) >= 5:
                break
        validation = self._repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=row.card_id,
                verdict="fail" if counter_hits else "pass",
                method="counterexample_search",
                cases_json=counter_hits,
                summary=(
                    f"语料反例检索：命中 {len(counter_hits)} 条（语料范围=本标的"
                    f"当前可见证据；未见反例≠不存在反例）"
                ),
                created_at=now,
            )
        )
        return validation

    def _validate_historical(self, row, now) -> dict:
        """历史证据验证（方案 §12.3）：按既有历史快照逐个做 PIT 入场→其后
        报价的前向核对（复用 case validation 的 PIT 纪律）。"""
        from sqlalchemy import select

        from app.storage.orm import SnapshotORM

        snaps = self._session.scalars(
            select(SnapshotORM)
            .where(SnapshotORM.instrument_id == row.instrument_id)
            .order_by(SnapshotORM.as_of)
            .limit(12)
        ).all()
        cases = []
        for snap in snaps:
            pinned = {item["evidence_id"] for item in (snap.items_json or [])}
            entry = self._pinned_price(row.instrument_id, pinned, snap.as_of)
            if entry is None:
                continue
            exits = [
                e for e in EvidenceRepository(self._session).list_for_instrument(
                    row.instrument_id, visible_at=datetime.now(timezone.utc)
                )
                if e.evidence_type is EvidenceType.MARKET_QUOTE
                and (e.metadata or {}).get("price") is not None
                and e.available_time > _ensure_utc(snap.as_of)
            ]
            if not exits:
                continue
            exit_ev = min(exits, key=lambda e: e.available_time)
            forward_pct = round((float(exit_ev.metadata["price"]) / entry - 1) * 100, 2)
            cases.append(
                {
                    "snapshot_id": snap.snapshot_id,
                    "entry_price": entry,
                    "exit_price": float(exit_ev.metadata["price"]),
                    "forward_pct": forward_pct,
                    "as_of": snap.as_of.isoformat(),
                }
            )
        if not cases:
            raise ExperienceRefusal(
                "no historical snapshot/quote pairs to validate (PIT)"
            )
        avg = round(sum(c["forward_pct"] for c in cases) / len(cases), 3)
        return self._repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=row.card_id,
                verdict="inconclusive",
                method="historical_evidence_validation",
                cases_json=cases,
                summary=f"历史证据验证 {len(cases)} 个快照：平均前向 {avg:+.2f}%",
                created_at=now,
            )
        )

    def _validate_cross_company(self, row, now) -> dict:
        """跨公司验证（方案 §12.3）：对同业板块成员（真实关系源）逐个核对
        行情可得性（诚实标注，不做收益推断）。"""
        from app.services.research_map_service import ResearchMapService

        related = ResearchMapService(self._session).latest_map(row.instrument_id) or {}
        members = list(related.get("related_instruments") or [])[:6]
        if not members:
            raise ExperienceRefusal(
                "no related instruments (board relations) for cross-company validation"
            )
        cases = []
        for m in members:
            member_id = m.get("instrument_id")
            if not member_id:
                continue
            quotes = [
                e for e in EvidenceRepository(self._session).list_for_instrument(
                    member_id, visible_at=datetime.now(timezone.utc)
                )
                if e.evidence_type is EvidenceType.MARKET_QUOTE
                and (e.metadata or {}).get("price") is not None
            ]
            cases.append(
                {
                    "instrument_id": member_id,
                    "name": m.get("name"),
                    "has_quote": bool(quotes),
                    "price": quotes[0].metadata.get("price") if quotes else None,
                }
            )
        return self._repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=row.card_id,
                verdict="inconclusive",
                method="cross_company_validation",
                cases_json=cases,
                summary=f"跨公司核对（同业板块成员 {len(cases)} 家，行情可得性如实标注）",
                created_at=now,
            )
        )

    def approve(self, card_id: str, verdict: str | None) -> dict:
        """§G3.3：至少一项明确 PASS 的有效验证；关键 FAIL 未解决禁止批准；
        §G3.4：决定写入 Audit Event。"""
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        validations = self._repo.list_validations(card_id)
        if not validations:
            raise ExperienceRefusal("approve requires at least one validation (§13 验→用)")
        fail_verdicts = [v for v in validations
                         if str((v.get("verdict") or "")).lower() == "fail"]
        if fail_verdicts:
            raise ExperienceRefusal(
                f"approve blocked: {len(fail_verdicts)} FAIL validation(s) unresolved "
                "(§G3.3 关键 FAIL 未解决禁止批准)"
            )
        passed = [v for v in validations
                  if str((v.get("verdict") or "")).lower() == "pass"]
        if not passed:
            raise ExperienceRefusal(
                "approve requires at least one explicitly PASS validation (§G3.3)"
            )
        row.status = ExperienceStatus.APPROVED
        row.verdict = (verdict or "approved").strip()[:500]
        row.updated_at = datetime.now(timezone.utc)
        saved = self._repo.save_card(row)
        self._audit(card_id, "experience_approved", {"verdict": row.verdict})
        return saved

    def reject(self, card_id: str, reason: str | None) -> dict:
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        row.status = ExperienceStatus.REJECTED
        row.verdict = (reason or "rejected").strip()[:500]
        row.updated_at = datetime.now(timezone.utc)
        saved = self._repo.save_card(row)
        self._audit(card_id, "experience_rejected", {"reason": (reason or "")[:200]})
        return saved

    def _audit(self, card_id: str, event_type: str, payload: dict) -> None:
        from app.application.run_events import record_run_event

        record_run_event(
            self._session, f"audit_exp_{card_id[-8:]}", event_type,
            {"card_id": card_id, **payload},
        )

    # -- 规则组件（§G3.5：Approved Experience 输出机器可消费规则） ----------------

    def rule_component(self, card_id: str) -> dict:
        """Approved Experience → 机器可消费规则组件（非描述文本）。

        未批准/被拒 → 422（未验证经验不得进入生产 Screening，§G3 DoD）。
        组件由 G5 ScreenDefinition 编译消费。
        """
        card = self._repo.get_card(card_id)
        if card is None:
            raise KeyError(card_id)
        if card.get("status") != ExperienceStatus.APPROVED:
            raise ExperienceRefusal(
                f"rule component requires an APPROVED experience (current: {card.get('status')})"
            )
        row = self._repo.get_card_row(card_id)
        return {
            "kind": "experience_rule_component",
            "component_version": 1,
            "card_id": card_id,
            "source_card_version": card.get("current_version"),
            "statement": card.get("statement"),
            "mechanism_terms": [
                t.strip() for t in (card.get("mechanism") or "").split("；") if t.strip()
            ][:8],
            "preconditions": list(row.applicable_conditions_json or []),
            "invalidators": list(row.invalid_conditions_json or []),
            "signals": list(row.signals_json or []),
            "scope": dict(row.scope_json or {}),
            "usage_guidance": row.usage_guidance,
            "counterexamples": list(row.counterexamples_json or []),
            "validation_method": row.validation_method,
            "instrument_scope": [card.get("instrument_id")],
            "compiled_at": datetime.now(timezone.utc).isoformat(),
        }

    # -- 版本 Diff（§G3.6） -------------------------------------------------------

    def version_diff(self, card_id: str, v1: int, v2: int) -> dict:
        """两个版本的字段级 Diff（append-only 版本链）。"""
        versions = {v["version_no"]: v for v in self._repo.list_versions(card_id)}
        if v1 not in versions or v2 not in versions:
            raise KeyError(f"version not found")
        a, b = versions[v1], versions[v2]
        fields = ("statement", "mechanism", "applicable_conditions",
                  "invalid_conditions", "signals", "scope", "usage_guidance",
                  "counterexamples", "confidence", "method")
        diff = []
        for f in fields:
            va, vb = a.get(f), b.get(f)
            if va != vb:
                diff.append({"field": f, "v1": va, "v2": vb})
        return {"card_id": card_id, "v1": v1, "v2": v2,
                "changed_fields": [d["field"] for d in diff], "diff": diff}

    # -- 非量化指标（§G3.7） ------------------------------------------------------

    def validation_metrics(self, card_id: str) -> dict:
        """真实非量化验证指标：样本数/跨度/前向收益分布。

        方向 IC 依赖预测方向记录（G8 因果链接入）——当前 honest INSUFFICIENT；
        样本 <3 → 整体 INSUFFICIENT（不造数值）。
        """
        from statistics import mean

        card = self._repo.get_card(card_id)
        if card is None:
            raise KeyError(card_id)
        validations = self._repo.list_validations(card_id)
        cases = []
        for v in validations:
            for c in (v.get("cases") or []):
                if isinstance(c, dict) and c.get("forward_return_pct") is not None:
                    cases.append(c)
        n = len(cases)
        if n < 3:
            return {
                "card_id": card_id, "n_cases": n, "status": "INSUFFICIENT",
                "note": "样本数 <3 → 指标 INSUFFICIENT（§G3.7 不造数值）",
            }
        returns = [float(c["forward_return_pct"]) for c in cases]
        dates = sorted(str(c.get("exit_observed_at") or "") for c in cases)
        span_days = None
        if dates and dates[0] and dates[-1]:
            try:
                d0 = datetime.fromisoformat(dates[0].replace("Z", "+00:00"))
                d1 = datetime.fromisoformat(dates[-1].replace("Z", "+00:00"))
                span_days = int((d1 - d0).total_seconds() // 86400)
            except ValueError:
                span_days = None
        positive = sum(1 for r in returns if r > 0)
        return {
            "card_id": card_id, "status": "ok", "n_cases": n,
            "span_days": span_days,
            "forward_return": {
                "mean_pct": round(mean(returns), 3),
                "min_pct": round(min(returns), 3),
                "max_pct": round(max(returns), 3),
                "positive_rate": round(positive / n, 3),
            },
            "directional_ic": "INSUFFICIENT",
            "directional_ic_note": "预测方向记录由 Replay 因果链接入后提供（G8）",
            "basis": "validated_case_records",
        }


    # -- reads ----------------------------------------------------------------------

    def list_cards(self, *, limit: int = 50) -> list[dict]:
        return self._repo.list_cards(limit=limit)

    def get_card_detail(self, card_id: str) -> dict | None:
        card = self._repo.get_card(card_id)
        if card is None:
            return None
        return {
            **card,
            "versions": self._repo.list_versions(card_id),
            "validations": self._repo.list_validations(card_id),
        }

    # -- helpers ----------------------------------------------------------------------

    def _pinned_price(self, instrument_id: str, pinned: set[str], as_of: datetime) -> float | None:
        evidence_repo = EvidenceRepository(self._session)
        quotes = [
            e
            for e in evidence_repo.list_for_instrument(instrument_id, visible_at=as_of)
            if e.evidence_id in pinned and e.evidence_type is EvidenceType.MARKET_QUOTE
        ]
        for record in sorted(quotes, key=lambda e: e.available_time, reverse=True):
            price = (record.metadata or {}).get("price")
            if isinstance(price, (int, float)) and price > 0:
                return float(price)
        return None

    def _register_artifact(self, card: dict) -> str:
        profile = InstrumentService(self._session).get_profile(
            card["instrument_id"], allow_remote=False
        )
        name = f"{profile.name} · {profile.code}" if profile else card["instrument_id"]
        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="experience_card",
            domain_type="ExperienceCard",
            domain_id=card["card_id"],
            title=f"{card['title']}（经验卡 v{card['current_version']}）",
            summary=card["statement"][:2000] or None,
            instrument_ids=(card["instrument_id"],),
            as_of_time=None,
            version=card["current_version"],
            created_by="experience",
            route="/experience",
        )
        report_artifact = service.by_domain("Report", card["source_report_id"])
        if report_artifact is not None:
            service.link(
                from_artifact_id=artifact_id,
                to_artifact_id=report_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
        return artifact_id

    # -- 用（R6 Playbook：已批准经验检索，§12.4） -----------------------------------

    def playbook_search(self, query: str, *, limit: int = 10) -> list[dict]:
        """Playbook = 已批准经验的检索面。条目是研究方法/启发（question
        generator / checklist），不是事实依据 —— 故意不带 authority/
        fact_status（那些是 Evidence 字段），Memory/Evidence 边界由结构锁死。"""
        rows = [
            c for c in self._repo.list_cards(limit=200)
            if c.get("status") == "APPROVED"
        ]
        q = (query or "").strip()
        results = []
        for r in rows:
            hay = " ".join(
                p for p in [
                    r.get("title") or "", r.get("statement") or "",
                    r.get("mechanism") or "",
                ] if p
            )
            if q and q not in hay:
                continue
            results.append(
                {
                    "card_id": r.get("card_id"),
                    "title": r.get("title"),
                    "statement": (r.get("statement") or "")[:200],
                    "mechanism": (r.get("mechanism") or "")[:200],
                    "applicable_conditions": list(r.get("applicable_conditions") or [])[:4],
                    "confidence": r.get("confidence"),
                }
            )
            if len(results) >= limit:
                break
        return results
