"""Screening service (V2 Phase E, 总纲 §19/§20/§45).

按经验卡发起全市场筛选（§45）：ExperienceCard → ScreenDefinition(强类型
规则) → ScreeningRun → Candidate List。

v1 强类型规则（全部由真实研究状态求值，绝不发明）：
    has_report        有 ≥N 份完整研究报告
    thesis_direction  最新论点方向（支撑主张 vs 反对主张）
    has_quote         有可见行情证据

每个候选（§20）携带 rank/score/matched_rules/factor_scores/explanation，
解释由真实事实拼装；被排除原因按规则聚合披露（为什么没选中）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.screening import (
    ScreeningRepository,
    ScreeningStatus,
)
from app.storage.instrument_repo import InstrumentRegistryORM
from app.storage.report_repo import ReportORM
from app.storage.research_orm import ThesisORM
from app.domain.evidence import EvidenceType
from app.storage.orm import EvidenceORM


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_RULES: list[dict] = [
    {"kind": "has_report", "min_reports": 1},
    {"kind": "thesis_direction", "direction": "any"},
    {"kind": "has_quote"},
]


class ScreeningService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ScreeningRepository(session)

    def create_from_card(self, card_id: str, rules: list[dict] | None = None) -> dict:
        """§45: approved experience card → screening run（后台执行）。"""
        from app.application.experience import ExperienceRepository

        card = ExperienceRepository(self._session).get_card(card_id)
        if card is None:
            raise KeyError(card_id)
        return self._repo.create_run(card_id=card_id, rules=rules or DEFAULT_RULES)

    def execute(self, run: dict) -> dict:
        from app.application.run_events import record_run_event

        run = self._repo.get_run(run["run_id"]) or run
        record_run_event(
            self._session, run["run_id"], "screening_started",
            {"card_id": run["card_id"], "rules": run["rules"]},
        )
        try:
            candidates, excluded, universe_size = self._evaluate(run)
        except Exception as exc:  # noqa: BLE001 — failure is run state (visible)
            error_text = str(exc)[:300]

            def fail(p: dict) -> dict:
                p["status"] = ScreeningStatus.FAILED
                p["error"] = error_text
                return p
            run = self._repo.update_run(run["run_id"], fail)
            record_run_event(
                self._session, run["run_id"], "screening_failed", {"error": error_text}
            )
            return run

        def complete(p: dict) -> dict:
            p["candidates"] = candidates
            p["excluded_summary"] = excluded
            p["universe_size"] = universe_size
            p["status"] = ScreeningStatus.COMPLETED
            return p
        run = self._repo.update_run(run["run_id"], complete)
        record_run_event(
            self._session, run["run_id"], "screening_completed",
            {"candidates": len(candidates), "universe": universe_size},
        )
        self._register_artifact(run)
        return run

    # -- evaluation -----------------------------------------------------------------

    def _evaluate(self, run: dict) -> tuple[list[dict], dict, int]:
        from app.application.experience import ExperienceRepository

        rules = run["rules"]
        card_title = None
        if run.get("card_id"):
            card = ExperienceRepository(self._session).get_card(run["card_id"])
            card_title = card["title"] if card else None
        rows = self._session.scalars(
            select(InstrumentRegistryORM).order_by(InstrumentRegistryORM.code)
        ).all()
        universe_size = len(rows)
        report_counts = dict(
            self._session.execute(
                select(ReportORM.instrument_id, func.count(ReportORM.id))
                .group_by(ReportORM.instrument_id)
            ).all()
        )
        latest_quotes: set[str] = set(
            self._session.scalars(
                select(EvidenceORM.instrument_id).where(
                    EvidenceORM.evidence_type == "market_quote"
                )
            ).all()
        )
        thesis_rows = self._session.scalars(select(ThesisORM)).all()
        latest_thesis: dict[str, ThesisORM] = {}
        for t in thesis_rows:
            keep = latest_thesis.get(t.instrument_id)
            if keep is None or (t.created_at and keep.created_at and t.created_at > keep.created_at):
                latest_thesis[t.instrument_id] = t

        candidates: list[dict] = []
        excluded: dict[str, int] = {r["kind"]: 0 for r in rules}
        excluded_examples: dict[str, str] = {}
        for row in rows:
            reports = int(report_counts.get(row.instrument_id, 0))
            thesis = latest_thesis.get(row.instrument_id)
            supporting = len(thesis.supporting_claims_json or []) if thesis else 0
            opposing = len(thesis.opposing_claims_json or []) if thesis else 0
            if supporting > opposing:
                direction = "up"
            elif opposing > supporting:
                direction = "down"
            else:
                direction = "neutral"
            has_quote = row.instrument_id in latest_quotes

            factor_scores: dict[str, str] = {
                "has_report": f"{reports}",
                "thesis_direction": direction,
                "has_quote": "yes" if has_quote else "no",
            }
            matched: list[str] = []
            failed_rule: str | None = None
            for rule in rules:
                kind = rule["kind"]
                if kind == "has_report":
                    ok = reports >= int(rule.get("min_reports", 1))
                    label = f"完整研究报告 ≥{rule.get('min_reports', 1)}（实际 {reports}）"
                elif kind == "thesis_direction":
                    want = rule.get("direction", "any")
                    ok = want == "any" or direction == want
                    label = f"论点方向 {want}（实际 {direction}，支撑 {supporting}/反对 {opposing}）"
                elif kind == "has_quote":
                    ok = has_quote
                    label = "有可见行情证据" + ("" if has_quote else "（缺失）")
                else:
                    ok = False
                    label = f"未知规则 {kind}"
                if ok:
                    matched.append(label)
                else:
                    failed_rule = failed_rule or kind
                    excluded[kind] = excluded.get(kind, 0) + 1
                    excluded_examples.setdefault(kind, row.name or row.code)

            if failed_rule is not None:
                continue

            score = 60 + min(reports, 5) * 5 + (15 if direction == "up" else 0) + (10 if has_quote else 0)
            name = row.name if row.name and row.name != row.code else row.code
            basis = f"经验依据来自研究卡《{card_title}》" if card_title else "经验依据来自既有研究状态"
            explanation = (
                f"{name}（{row.code}）命中全部 {len(rules)} 条规则：" +
                "；".join(matched) +
                f"。{basis}。"
            )
            risks: list[str] = []
            if direction == "neutral":
                risks.append("最新论点多空均衡，方向证据不足")
            if reports <= 1:
                risks.append("研究覆盖薄（报告 ≤1 份），结论稳健性有限")
            candidates.append(
                {
                    "instrument_id": row.instrument_id,
                    "code": row.code,
                    "name": name,
                    "rank": 0,
                    "score": score,
                    "factor_scores": factor_scores,
                    "matched_rules": matched,
                    "experience_card_refs": [run["card_id"]] if run["card_id"] else [],
                    "explanation": explanation,
                    "risks": risks,
                }
            )

        candidates.sort(key=lambda c: (-c["score"], c["code"]))
        for i, c in enumerate(candidates, start=1):
            c["rank"] = i
        excluded_summary = {
            "universe_size": universe_size,
            "candidate_count": len(candidates),
            "excluded_by_rule": excluded,
            "examples": excluded_examples,
        }
        return candidates[:50], excluded_summary, universe_size

    def _register_artifact(self, run: dict) -> None:
        from app.application.artifacts import ArtifactService, RelationType

        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="screening_run",
            domain_type="ScreeningRun",
            domain_id=run["run_id"],
            title=f"筛选运行 {run['run_id'][:8]}（候选 {len(run['candidates'])}）",
            summary=(
                f"全市场 {run['excluded_summary'].get('universe_size', 0)} 标的按 "
                f"{len(run['rules'])} 条规则筛选，入选 {len(run['candidates'])}。"
            ),
            instrument_ids=(),
            created_by="screening",
            route="/screening",
        )
        if run.get("card_id"):
            card_artifact = service.by_domain("ExperienceCard", run["card_id"])
            if card_artifact is not None:
                service.link(
                    from_artifact_id=artifact_id,
                    to_artifact_id=card_artifact["artifact_id"],
                    relation=RelationType.GENERATED_FROM,
                )
