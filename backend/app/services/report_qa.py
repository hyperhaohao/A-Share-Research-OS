"""Report Q&A (任务书 §42): Explain vs Refresh — strictly separated.

Explain answers from the report's own research state ONLY. It performs no
collection: zero source calls, zero new evidence, zero new manifests. Tests
assert the fact base is byte-identical before and after.

Refresh re-checks with fresh data: it runs the collector, builds a new
snapshot, and reports an impact diff (new/removed evidence, affected
claims). The two modes are distinct API operations that must never blend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.llm_provider import get_llm_provider as _get_provider
from app.domain.evidence import utc_now
from app.services.evidence_collector import collect_capability_evidence
from app.storage.orm import Base
from app.storage.research_repo import ResearchRepository
from app.storage.repository import EvidenceRepository
from app.storage.snapshot_repo import SnapshotRepository


class ReportAskORM(Base):
    __tablename__ = "report_asks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ask_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    report_id: Mapped[str] = mapped_column(String(24), index=True)
    mode: Mapped[str] = mapped_column(String(8), index=True)
    question: Mapped[str] = mapped_column(default="")
    answer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportQAService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._snapshots = SnapshotRepository(session)
        self._evidence = EvidenceRepository(session)
        self._research = ResearchRepository(session)

    # -- Explain: zero new data ------------------------------------------------
    def explain(self, report_row: dict, question: str) -> dict:
        """Answer from the frozen research state; never touches sources."""
        snapshot = self._snapshots.get(report_row["snapshot_id"])
        if snapshot is None:
            raise KeyError(report_row["snapshot_id"])
        pinned = set(snapshot.evidence_ids)
        evidence = {
            e.evidence_id: e
            for e in self._evidence.list_for_instrument(
                snapshot.instrument_id, visible_at=snapshot.as_of
            )
            if e.evidence_id in pinned
        }
        claims = self._research.list_claims(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )
        theses = self._research.list_theses(
            snapshot.instrument_id, snapshot_id=snapshot.snapshot_id
        )

        # Deterministic matching: route the question to claims/theses whose
        # text shares keywords with it. No LLM required for the honest path.
        keywords = [w for w in question.replace("？", " ").split() if len(w) >= 2]

        def _matches(text: str) -> bool:
            return any(w in text for w in keywords) if keywords else True

        matched_claims = [c for c in claims if _matches(c.statement)]
        matched_theses = [
            t for t in theses if _matches(t.title) or _matches(t.description)
        ]

        answer_claims = [
            {
                "claim_id": c.claim_id,
                "statement": c.statement,
                "evidence_ids": list(c.supporting_evidence_refs),
                "confidence": c.confidence,
            }
            for c in (matched_claims or claims)
        ]
        answer_theses = [
            {"thesis_id": t.thesis_id, "title": t.title, "risks": list(t.risks)}
            for t in (matched_theses or theses)
        ]
        cited_evidence = sorted(
            {ev for a in answer_claims for ev in a["evidence_ids"] if ev in evidence}
        )
        sources = sorted({evidence[ev].source for ev in cited_evidence if ev in evidence})

        return {
            "mode": "explain",
            "question": question,
            "data_policy": "frozen-state-only; no source calls performed",
            "claims": answer_claims,
            "theses": answer_theses,
            "citations": cited_evidence,
            "sources": sources,
            "snapshot_id": snapshot.snapshot_id,
        }

    # -- Refresh: fresh data + impact diff --------------------------------------
    def refresh(self, report_row: dict, *, capabilities: list[str] | None = None) -> dict:
        instrument_id = report_row["instrument_id"]
        old_snapshot = self._snapshots.get(report_row["snapshot_id"])
        if old_snapshot is None:
            raise KeyError(report_row["snapshot_id"])
        old_ids = set(old_snapshot.evidence_ids)

        caps = capabilities or ["market_data", "financials", "announcements"]
        manifest_ids = []
        for capability in caps:
            outcome = collect_capability_evidence(
                instrument_id, capability, repo=self._evidence, fresh=True
            )
            manifest_ids.append(outcome.manifest.manifest_id)

        new_snapshot = self._snapshots.build(
            instrument_id, utc_now(), evidence_repo=self._evidence
        )
        new_ids = set(new_snapshot.evidence_ids)

        added = sorted(new_ids - old_ids)
        removed = sorted(old_ids - new_ids)

        # Claims affected: those citing evidence that disappeared from the
        # visible set. Newly added evidence cannot invalidate anything yet —
        # it simply informs the next run.
        claims = self._research.list_claims(
            instrument_id, snapshot_id=old_snapshot.snapshot_id
        )
        affected = [
            c.claim_id
            for c in claims
            if set(c.supporting_evidence_refs) & set(removed)
            or set(c.opposing_evidence_refs) & set(removed)
        ]

        return {
            "mode": "refresh",
            "old_snapshot_id": old_snapshot.snapshot_id,
            "new_snapshot_id": new_snapshot.snapshot_id,
            "new_evidence_ids": added,
            "removed_evidence_ids": removed,
            "affected_claim_ids": affected,
            "manifest_ids": manifest_ids,
        }

    # -- Copilot (R3.3): LLM narrative over the frozen context ------------------
    def explain_with_llm(self, report_row: dict, question: str) -> dict:
        """LLM-composed answer over the deterministic context. The answer's
        citations are validated against the context (boundary rule, 整改 §16):
        the LLM cannot cite evidence it was not given, and no evidence or
        claims are created by this path."""
        base = self.explain(report_row, question)
        provider = _get_provider()
        if provider is None:
            return {**base, "narrative_kind": "deterministic"}

        context_claims = [
            {"claim_id": c["claim_id"], "statement": c["statement"]}
            for c in base["claims"]
        ]
        prompt = (
            "Question: " + question + "\n\n"
            "You are answering strictly from the context below. "
            "Cite claim ids as [claim:<id>]. Do not invent facts or numbers.\n"
            "Claims: " + repr(context_claims) + "\n"
            "Theses: " + repr(base["theses"]) + "\n"
            "Evidence ids: " + repr(base["citations"]) + "\n"
        )
        answer = provider.generate_text(
            prompt,
            system="Evidence-first research copilot. Use only the provided context.",
        )
        # boundary validation: citations mentioned must exist in context
        import re as _re

        cited = set(_re.findall(r"\[claim:(clm_[0-9a-f]+)\]", answer))
        known = {c["claim_id"] for c in base["claims"]}
        invalid = sorted(cited - known)
        return {
            **base,
            "narrative_kind": "llm",
            "narrative": answer,
            "narrative_provider": provider.model_info()["model"],
            "invalid_citations": invalid,
        }

    # -- audit log ---------------------------------------------------------------
    def log_ask(self, report_id: str, mode: str, question: str, answer: dict) -> str:
        row = ReportAskORM(
            ask_id=f"ask_{uuid4().hex[:16]}",
            report_id=report_id,
            mode=mode,
            question=question,
            answer_json=answer,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return row.ask_id
