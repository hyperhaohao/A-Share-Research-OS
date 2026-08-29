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

    def approve(self, card_id: str, verdict: str | None) -> dict:
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        validations = self._repo.list_validations(card_id)
        if not validations:
            raise ExperienceRefusal("approve requires at least one validation (§13 验→用)")
        row.status = ExperienceStatus.APPROVED
        row.verdict = (verdict or "approved").strip()[:500]
        row.updated_at = datetime.now(timezone.utc)
        return self._repo.save_card(row)

    def reject(self, card_id: str, reason: str | None) -> dict:
        row = self._repo.get_card_row(card_id)
        if row is None:
            raise KeyError(card_id)
        row.status = ExperienceStatus.REJECTED
        row.verdict = (reason or "rejected").strip()[:500]
        row.updated_at = datetime.now(timezone.utc)
        return self._repo.save_card(row)

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
