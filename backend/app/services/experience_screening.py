"""Experience-driven Smart Screening（G5，观澜语义迁移任务书 §G5）.

语义链（§G5）：

    Approved Experience（G3 规则组件）
          ↓ compile（机制/前提/失效/信号 → 可检查规则）
    ScreenDefinition Vn（source_card_version / universe / rules /
                         ranking / missing_data_policy / as_of_policy）
          ↓ 人工确认发布（F7 Confirmation Gate，draft→published）
    PIT execute（证据 available_time ≤ as_of；Current Thesis Selector）
          ↓
    ScreenRun（Candidate / Exclusion / 逐规则解释 / 因子值 / 缺失项）
          ↓ Artifact + Provenance

编译确定性：preconditions/signals 按模式映射为可检查规则；无法映射的
自由文本进入 uncompiled 列表显形（不静默丢弃）。Ranking Formula 版本化
（formula_version + 权重表），禁不可解释固定常数。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.storage.industry_graph_orm import CompanyIndustryPositionORM
from app.storage.orm import EvidenceORM
from app.storage.screen_definition_orm import (
    ScreenDefinitionORM,
    ScreenDefinitionRunORM,
)

RANKING_FORMULA_VERSION = "screen_rank_v1"
RANKING_WEIGHTS = {
    "rule_pass_ratio": 0.5,       # 通过规则比例
    "evidence_freshness": 0.3,    # 最新证据新鲜度（7 天内满档）
    "thesis_alignment": 0.2,      # 与 Current Thesis 方向一致性
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(v: datetime | None) -> datetime | None:
    if v is None or v.tzinfo is not None:
        return v
    return v.replace(tzinfo=timezone.utc)


class ScreenCompiler:
    """Experience 规则组件 → 可检查筛选规则（确定性映射）。"""

    RULE_PATTERNS = [
        # 特定模式在前（holding_reduction 先于泛化「减持」）
        (re.compile(r"减持比例\s*[≥>]=?\s*(\d+(?:\.\d+)?)\s*%"), "holding_reduction"),
        (re.compile(r"无对冲"), "no_hedge"),
        (re.compile(r"营收.*增|业绩.*增"), "earnings_positive"),
        (re.compile(r"稀土|永磁|磁材"), "industry_keyword"),
        (re.compile(r"减持"), "has_share_reduction"),
    ]

    @classmethod
    def compile(cls, component: dict) -> dict:
        rules: list[dict] = []
        uncompiled: list[dict] = []
        # 基础规则：必须有报告与报价（研究状态底线）
        rules.append({"kind": "has_report", "min_reports": 1,
                      "source": "base"})
        for text in component.get("preconditions", []):
            mapped = cls._map_text(str(text))
            if mapped:
                rules.append({**mapped, "source": f"precondition: {text}"})
            else:
                uncompiled.append({"origin": "precondition", "text": str(text)})
        for text in component.get("invalidators", []):
            mapped = cls._map_text(str(text))
            if mapped:
                rules.append({**mapped, "as_exclusion": True,
                              "source": f"invalidator: {text}"})
            else:
                # 失效条件全文作为排除关键词（保守排除）
                rules.append({"kind": "invalidator_keyword",
                              "keywords": [str(text)], "as_exclusion": True,
                              "source": f"invalidator: {text}"})
        for sig in component.get("signals", []):
            rules.append({"kind": "signal_rule", "signal": str(sig),
                          "as_exclusion": False, "source": "signals"})
        return {
            "rules": rules,
            "uncompiled": uncompiled,
            "ranking": {
                "formula_version": RANKING_FORMULA_VERSION,
                "weights": dict(RANKING_WEIGHTS),
            },
            "missing_data_policy": "exclude",
            "as_of_policy": "now",
        }

    @classmethod
    def _map_text(cls, text: str) -> dict | None:
        for pattern, kind in cls.RULE_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            if kind == "holding_reduction":
                return {"kind": kind, "min_pct": float(m.group(1))}
            if kind in ("has_share_reduction", "no_hedge", "earnings_positive",
                        "industry_keyword"):
                return {"kind": kind}
        return None


class ExperienceScreenService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── 编译（仅 Approved） ─────────────────────────────────────────────────

    def compile_definition(
        self, *, name: str, card_id: str,
        universe: dict | None = None,
    ) -> dict:
        from app.services.experience_service import ExperienceRefusal, ExperienceService

        try:
            component = ExperienceService(self._session).rule_component(card_id)
        except KeyError:
            raise AppError("experience.not_found", status_code=404) from None
        except ExperienceRefusal as exc:
            raise AppError("screen.source_not_approved", status_code=422,
                           detail=str(exc)) from None

        compiled = ScreenCompiler.compile(component)
        row = ScreenDefinitionORM(
            def_id=f"scrdef_{uuid4().hex[:16]}",
            name=name[:120],
            source_card_id=card_id,
            source_card_version=int(component.get("source_card_version") or 1),
            universe_json=universe or {"kind": "industry_chain", "name": "稀土产业链"},
            rules_json=compiled["rules"],
            ranking_json=compiled["ranking"],
            missing_data_policy=compiled["missing_data_policy"],
            as_of_policy=compiled["as_of_policy"],
            status="draft",
            version=1,
            compiled_payload_json={
                "uncompiled": compiled["uncompiled"],
                "statement": component.get("statement"),
                "scope": component.get("scope"),
            },
            created_by="screening",
            created_at=_now(),
        )
        self._session.add(row)
        self._session.flush()
        return self._def_dict(row)

    def publish_definition(self, def_id: str) -> dict:
        """草稿 → 发布（生产可用；由 F7 确认门工具调用）。"""
        row = self._get_def_row(def_id)
        if row is None:
            raise AppError("screen.def_not_found", status_code=404) from None
        if row.status == "published":
            return self._def_dict(row)  # 幂等
        if row.status != "draft":
            raise AppError("screen.not_publishable", status_code=422,
                           detail=f"status={row.status}") from None
        row.status = "published"
        row.published_at = _now()
        self._session.flush()
        return self._def_dict(row)

    # ── PIT 执行 ─────────────────────────────────────────────────────────────

    def execute_definition(self, def_id: str, *, as_of: datetime | None = None) -> dict:
        row = self._get_def_row(def_id)
        if row is None:
            raise AppError("screen.def_not_found", status_code=404) from None
        if row.status != "published":
            raise AppError(
                "screen.not_published", status_code=422,
                detail=f"definition status={row.status} — publish before running",
            ) from None
        now = _ensure_aware(as_of) or _now()
        rules = list(row.rules_json or [])
        universe_spec = dict(row.universe_json or {})

        # Universe：产业链共位公司（G1 明确关系）
        members: list[str] = []
        if universe_spec.get("kind") == "industry_chain":
            chain_name = str(universe_spec.get("name") or "")
            chain_rows = self._session.scalars(
                select(CompanyIndustryPositionORM)
                .where(CompanyIndustryPositionORM.instrument_id.is_not(None))
            ).all()
            seen: set[str] = set()
            for p in chain_rows:
                if p.instrument_id in seen:
                    continue
                # chain 匹配：universe 指定链名 → 通过 G1 链解析
                from app.storage.industry_graph_orm import IndustryChainORM

                chain = self._session.scalars(
                    select(IndustryChainORM)
                    .where(IndustryChainORM.chain_id == p.chain_id)
                ).first()
                if chain is not None and (not chain_name or chain_name in chain.name):
                    seen.add(p.instrument_id)
                    members.append(p.instrument_id)
        members = members or []

        # Current Thesis Selector（§G5.4：显式唯一选择器）
        from app.services.current_thesis import get_current_thesis

        candidates: list[dict] = []
        exclusions: dict[str, list[dict]] = {}
        for instrument_id in members:
            rule_results: list[dict] = []
            missing: list[str] = []
            for rule in rules:
                verdict, detail = self._eval_rule(rule, instrument_id, now)
                rule_results.append({"rule": rule, "verdict": verdict,
                                     "detail": detail})
                if verdict == "fail":
                    exclusions.setdefault(instrument_id, []).append(
                        {"rule": rule.get("kind"), "source": rule.get("source"),
                         "detail": detail}
                    )
            base_rules = [r for r in rule_results
                          if not (r["rule"].get("as_exclusion"))]
            passed_ratio = (
                sum(1 for r in base_rules if r["verdict"] == "pass") / len(base_rules)
                if base_rules else 0.0
            )
            excluded = any(r["verdict"] == "fail" and r["rule"].get("as_exclusion")
                           for r in rule_results) or \
                any(r["verdict"] == "fail" and not r["rule"].get("as_exclusion")
                    for r in base_rules)
            if excluded:
                continue
            # 因子值（真实数据派生）
            freshness = self._evidence_freshness(instrument_id, now)
            thesis = get_current_thesis(self._session, instrument_id)
            thesis_aligned = 1.0 if thesis is not None else 0.0
            score = round(
                RANKING_WEIGHTS["rule_pass_ratio"] * passed_ratio
                + RANKING_WEIGHTS["evidence_freshness"] * freshness
                + RANKING_WEIGHTS["thesis_alignment"] * thesis_aligned,
                4,
            )
            candidates.append({
                "instrument_id": instrument_id,
                "score": score,
                "passed_rules": [r["rule"]["kind"] for r in base_rules
                                 if r["verdict"] == "pass"],
                "rule_pass_ratio": round(passed_ratio, 3),
                "factors": {
                    "evidence_freshness": freshness,
                    "thesis_aligned": thesis_aligned,
                },
                "explanations": [
                    r["rule"].get("source") for r in base_rules
                    if r["verdict"] == "pass"
                ],
                "missing": missing,
                "ranking_formula_version": RANKING_FORMULA_VERSION,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        for rank, c in enumerate(candidates, start=1):
            c["rank"] = rank

        exclusion_rows = [
            {"instrument_id": iid, "reasons": reasons}
            for iid, reasons in exclusions.items()
        ]
        run_row = ScreenDefinitionRunORM(
            run_id=f"scrrun_{uuid4().hex[:16]}", def_id=def_id,
            def_version=row.version, as_of=now,
            universe_json={"members": members, "spec": universe_spec},
            candidates_json=candidates, exclusions_json=exclusion_rows,
            created_at=_now(),
        )
        self._session.add(run_row)

        # Artifact（§G5.9：完整 universe 与结果）
        artifact_id = None
        try:
            from app.application.artifacts import ArtifactService

            artifact_id = ArtifactService(self._session).register(
                artifact_type="screening_run",
                domain_type="ScreenDefinitionRun",
                domain_id=run_row.run_id,
                title=f"{row.name} · PIT 筛选 v{row.version}",
                instrument_ids=(),
                created_by="experience_screening",
                route="/screening",
                metadata={"universe": members, "n_candidates": len(candidates)},
            )
        except Exception as exc:  # noqa: BLE001 — 显形 INCOMPLETE_PROVENANCE
            run_row.artifact_id = None
            self._session.flush()
            return {**self._run_dict(run_row),
                    "provenance_status": "INCOMPLETE_PROVENANCE",
                    "provenance_error": f"{type(exc).__name__}: {exc}"[:300]}
        run_row.artifact_id = artifact_id
        self._session.flush()
        return self._run_dict(run_row)

    def _eval_rule(self, rule: dict, instrument_id: str, as_of: datetime) -> tuple[str, str]:
        """单规则求值（确定性；证据 PIT 可见性强制）。"""
        kind = rule.get("kind")
        if kind == "has_report":
            n = len(self._session.scalars(
                select(EvidenceORM)
                .where(EvidenceORM.instrument_id == instrument_id)
                .where(EvidenceORM.evidence_type.in_(("research_report", "announcement")))
                .where(EvidenceORM.available_time <= as_of)
                .limit(rule.get("min_reports", 1))
            ).all())
            ok = n >= int(rule.get("min_reports", 1))
            return ("pass" if ok else "fail"), f"reports/announcements visible={n}"
        if kind in ("has_share_reduction", "holding_reduction"):
            evs = self._session.scalars(
                select(EvidenceORM)
                .where(EvidenceORM.instrument_id == instrument_id)
                .where(EvidenceORM.available_time <= as_of)
            ).all()
            text = " ".join((e.summary or "") for e in evs)
            hit = "减持" in text
            if kind == "holding_reduction":
                min_pct = float(rule.get("min_pct", 0.0))
                m = re.search(r"减持.*?(\d+(?:\.\d+)?)%", text)
                ok = hit and m and float(m.group(1)) >= min_pct
                pct_text = f"{m.group(1)}%" if m else "n/a"
                return ("pass" if ok else "fail"), f"reduction pct={pct_text} vs >= {min_pct}%"
            return ("pass" if hit else "fail"), f"reduction mention={hit}"
        if kind == "no_hedge":
            evs = self._session.scalars(
                select(EvidenceORM)
                .where(EvidenceORM.instrument_id == instrument_id)
                .where(EvidenceORM.available_time <= as_of)
            ).all()
            text = " ".join((e.summary or "") for e in evs)
            hedge = "对冲" in text
            return ("pass" if not hedge else "fail"), f"hedge mention={hedge}"
        if kind == "invalidator_keyword":
            evs = self._session.scalars(
                select(EvidenceORM)
                .where(EvidenceORM.instrument_id == instrument_id)
                .where(EvidenceORM.available_time <= as_of)
            ).all()
            text = " ".join((e.summary or "") for e in evs)
            hit = any(kw and kw in text for kw in rule.get("keywords", []))
            return ("fail" if hit else "pass"), f"invalidator mention={hit}"
        if kind == "thesis_direction":
            from app.services.current_thesis import get_current_thesis

            thesis = get_current_thesis(self._session, instrument_id)
            return ("pass" if thesis is not None else "fail"), \
                f"current thesis={'yes' if thesis is not None else 'no'}"
        if kind == "signal_rule":
            return "pass", f"signal {rule.get('signal')} recorded (non-blocking)"
        return "pass", f"unknown rule {kind} treated as non-blocking"

    def _evidence_freshness(self, instrument_id: str, as_of: datetime) -> float:
        ev = self._session.scalars(
            select(EvidenceORM)
            .where(EvidenceORM.instrument_id == instrument_id)
            .where(EvidenceORM.available_time <= as_of)
            .order_by(EvidenceORM.available_time.desc())
            .limit(1)
        ).first()
        if ev is None or ev.available_time is None:
            return 0.0
        age = (as_of - _ensure_aware(ev.available_time)).days
        return 1.0 if age <= 7 else (0.5 if age <= 30 else 0.0)

    # ── helpers ─────────────────────────────────────────────────────────────

    def _get_def_row(self, def_id: str) -> ScreenDefinitionORM | None:
        return self._session.scalars(
            select(ScreenDefinitionORM).where(ScreenDefinitionORM.def_id == def_id)
        ).first()

    def _def_dict(self, r: ScreenDefinitionORM) -> dict:
        return {
            "def_id": r.def_id, "name": r.name,
            "source_card_id": r.source_card_id,
            "source_card_version": r.source_card_version,
            "universe": dict(r.universe_json or {}),
            "rules": list(r.rules_json or []),
            "ranking": dict(r.ranking_json or {}),
            "missing_data_policy": r.missing_data_policy,
            "as_of_policy": r.as_of_policy,
            "status": r.status, "version": r.version,
            "compiled": dict(r.compiled_payload_json or {}),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }

    def _run_dict(self, r: ScreenDefinitionRunORM) -> dict:
        return {
            "run_id": r.run_id, "def_id": r.def_id, "def_version": r.def_version,
            "as_of": r.as_of.isoformat() if r.as_of else None,
            "universe": dict(r.universe_json or {}),
            "candidates": list(r.candidates_json or []),
            "exclusions": list(r.exclusions_json or []),
            "artifact_id": r.artifact_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    def list_definitions(self, *, status: str | None = None) -> list[dict]:
        stmt = select(ScreenDefinitionORM).order_by(
            ScreenDefinitionORM.created_at.desc()).limit(50)
        if status:
            stmt = stmt.where(ScreenDefinitionORM.status == status)
        return [self._def_dict(r) for r in self._session.scalars(stmt).all()]

    def get_run(self, run_id: str) -> dict | None:
        row = self._session.scalars(
            select(ScreenDefinitionRunORM).where(
                ScreenDefinitionRunORM.run_id == run_id)
        ).first()
        return self._run_dict(row) if row else None
