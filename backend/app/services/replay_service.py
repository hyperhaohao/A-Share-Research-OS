"""Replay feedback service (V2 Phase J, 总纲 §79/§50/§53).

完整复盘回灌闭环的最后编排：

    Decision → Prediction(已验证) → RegressionReview →
    ExperienceCard v(n+1) → StrategyVersion v(n+1) → ResearchExperience

- §50：Decision 不是 Prediction —— 回灌不伪造预测，只使用已存在的
  成熟验证；
- 教训来自确定性归因（RegressionReviewService），append-only（§53）；
- 找不到已验证预测 → 显式拒绝（链条上缺环是事实，不假装闭环）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

class ReplayRefusal(ValueError):
    """Explicit refusal — a broken chain is disclosed, never papered over."""


class ReplayFeedbackService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def feedback_from_decision(self, decision_id: str) -> dict:
        from app.api.regression import RegressionRepository
        from app.application.experience import (
            ExperienceRepository,
            ExperienceCardVersionORM,
        )
        from app.application.strategy_monitor import DecisionRecordORM
        from app.domain.regression import RegressionReviewService
        from app.domain.evidence import utc_now
        from app.domain.regression import ResearchExperience
        from app.api.regression import ExperienceRepository as _ExperienceRepo
        from app.services.strategy_service import StrategyService
        from app.storage.prediction_repo import (
            PredictionORM,
            PredictionRepository,
            ValidationRepository,
        )

        decision_row = self._session.scalars(
            select(DecisionRecordORM).where(DecisionRecordORM.decision_id == decision_id)
        ).first()
        if decision_row is None:
            raise KeyError(decision_id)

        strategy_repo = StrategyService(self._session)
        version = strategy_repo.get_version_detail(decision_row.version_id)
        if version is None:
            raise ReplayRefusal("the decision's strategy version no longer exists")

        # -- Decision → 已验证 Prediction（§50 + §G8.1：严格因果链） -----------
        # G8：Prediction 必须直接引用本 Decision（decision_id 因果引用）；
        # 无因果链接的 Prediction（即使同 universe）不得进入 Replay。
        candidate_rows = (
            self._session.scalars(
                select(PredictionORM)
                .where(PredictionORM.decision_id == decision_id)
                .order_by(PredictionORM.created_at.desc(), PredictionORM.id.desc())
            ).all()
        )
        predictions = PredictionRepository(self._session)
        validations = ValidationRepository(self._session)
        chosen = None
        for row in candidate_rows:
            validation = validations.get_for_prediction(row.prediction_id)
            if validation is not None:
                chosen = (row, validation)
                break
        if chosen is None:
            raise ReplayRefusal(
                "no validated prediction on this decision's chain yet — "
                "wait for a prediction to mature and validate (§79 缺环显形)"
            )
        prediction_row, validation = chosen
        prediction = predictions.get(prediction_row.prediction_id)
        assert prediction is not None

        # -- RegressionReview（确定性归因） -----------------------------------
        review = RegressionReviewService().review(prediction, validation)
        review_id = RegressionRepository(self._session).save(review)

        # -- ExperienceCard v(n+1)（教训进版本，append-only） -------------------
        card_row = None
        if version.get("source_card_id"):
            card_row = ExperienceRepository(self._session).get_card_row(
                version["source_card_id"]
            )
        card_version_no = None
        if card_row is not None:
            lesson = review.lesson_summary or "本次验证未产生新归因"
            new_no = card_row.current_version + 1
            now = datetime.now(timezone.utc)
            ExperienceRepository(self._session).add_version(
                ExperienceCardVersionORM(
                    card_id=card_row.card_id,
                    version_no=new_no,
                    statement=card_row.statement,
                    mechanism=(card_row.mechanism + f"；复盘教训：{lesson}")[:4000],
                    applicable_conditions_json=list(card_row.applicable_conditions_json or []),
                    invalid_conditions_json=list(card_row.invalid_conditions_json or []),
                    confidence=card_row.confidence,
                    method="review",
                    created_at=now,
                )
            )
            card_row.mechanism = (card_row.mechanism + f"；复盘教训：{lesson}")[:4000]
            card_row.current_version = new_no
            card_row.updated_at = now
            ExperienceRepository(self._session).save_card(card_row)
            card_version_no = new_no

        # -- StrategyVersion v(n+1)（重组即拾取新卡片内容） ----------------------
        # G8（§G8.5）：rule_error 归因 → **可执行规则修改**（出场止损放宽为
        # 观测不利波动的 1.2 倍，确定性、可解释），非仅改描述
        from app.domain.regression import AttributionDimension

        rule_error = any(a.dimension == AttributionDimension.RULE_ERROR
                         for a in review.attributions)
        strategy_v2 = None
        rule_feedback = None
        if rule_error:
            adverse = max(
                (abs(float(c.get("forward_return_pct") or 0.0))
                 for c in (getattr(validation, "cases", None) or [])),
                default=0.0,
            )
            new_stop = round(max(3.0, adverse * 1.2), 2)
            # 直接克隆旧版本行 → v(n+1)（不依赖 screening run 存在）；
            # 规则体可执行修改：exit_rules 追加 stop_loss（确定性）
            from app.application.strategy import (
                StrategyRepository as _SR2,
                StrategyVersionORM as _VORM,
            )

            old_row = _SR2(self._session).get_version_row(version["version_id"])
            new_row = _VORM(
                version_id=f"strat_{uuid4().hex[:12]}",
                name=old_row.name,
                version_no=old_row.version_no + 1,
                philosophy=old_row.philosophy,
                source_card_id=old_row.source_card_id,
                source_screening_run_id=old_row.source_screening_run_id,
                universe_json=list(old_row.universe_json or []),
                entry_policy_json=dict(old_row.entry_policy_json or {}),
                exit_policy_json=dict(old_row.exit_policy_json or {}),
                risk_policy_json=dict(old_row.risk_policy_json or {}),
                status=old_row.status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            exit_rules = list((new_row.exit_policy_json or {}).get("exit_rules") or [])
            exit_rules.append({"kind": "stop_loss", "pct": new_stop,
                               "origin": f"replay rule_error (adverse {adverse:.2f}%)"})
            new_row.exit_policy_json = {**(new_row.exit_policy_json or {}),
                                        "exit_rules": exit_rules}
            self._session.add(new_row)
            self._session.flush()
            strategy_v2 = {"version_id": new_row.version_id}
            rule_feedback = {
                "strategy_version_id": new_row.version_id,
                "changed_exit_rules": exit_rules,
                "old_version_id": version["version_id"],
            }
        if strategy_v2 is None and version.get("source_screening_run_id"):
            # 源筛选运行可能已不可用 —— 诚实跳过 v2（不伪造版本）
            try:
                strategy_v2 = strategy_repo.create_from_screening(
                    version["source_screening_run_id"], version["name"]
                )
            except KeyError:
                strategy_v2 = None

        # -- ResearchExperience（append-only 教训，§53） ------------------------
        # F4（任务书 §7.1）：教训置信度由确定性归因的归因条数计算（非固定 0.6）：
        # value = 0.50 + 0.05 × min(归因数, 4)，basis 随条目披露、模型版本可追溯
        _n_attr = len(review.attributions)
        _lesson_value = round(0.50 + 0.05 * min(_n_attr, 4), 4)
        experience = ResearchExperience(
            context=(
                f"决策 {decision_id}（{decision_row.decision}）复盘：策略 "
                f"{version['name']} v{version['version_no']}"
            ),
            lesson=review.lesson_summary or "本次验证未产生新归因",
            related_research_type="strategy_review",
            confidence=_lesson_value,
            supporting_validations=(validation.validation_id,),
        )
        experience_id = _ExperienceRepo(self._session).save(experience)

        # -- artifacts ---------------------------------------------------------
        from app.application.artifacts import ArtifactService, RelationType

        service = ArtifactService(self._session)
        review_artifact = service.register(
            artifact_type="review",
            domain_type="RegressionReview",
            domain_id=review_id,
            title=f"复盘回灌 {review_id[:8]}（{version['name']}）",
            summary=review.lesson_summary or None,
            instrument_ids=(prediction.instrument_id,),
            created_by="replay",
            route="/predictions",
        )
        prediction_artifact = service.by_domain("PredictionRecord", prediction.prediction_id)
        if prediction_artifact is None:
            # direct-repository predictions (no API path) get registered here —
            # same shape as the API registration, never left out of provenance
            from app.services.instrument_service import InstrumentService

            profile = InstrumentService(self._session).get_profile(
                prediction.instrument_id, allow_remote=False
            )
            name = f"{profile.name} · {profile.code}" if profile else prediction.instrument_id
            prediction_artifact_id = service.register(
                artifact_type="prediction",
                domain_type="PredictionRecord",
                domain_id=prediction.prediction_id,
                title=f"{name} · {prediction.horizon.value} 预测",
                instrument_ids=(prediction.instrument_id,),
                as_of_time=prediction.as_of,
                created_by="replay",
                route="/predictions",
            )
        else:
            prediction_artifact_id = prediction_artifact["artifact_id"]
        service.link(
            from_artifact_id=review_artifact,
            to_artifact_id=prediction_artifact_id,
            relation=RelationType.GENERATED_FROM,
        )
        if strategy_v2 is not None:
            strategy_artifact = service.by_domain("StrategyVersion", strategy_v2["version_id"])
            if strategy_artifact is not None:
                service.link(
                    from_artifact_id=strategy_artifact["artifact_id"],
                    to_artifact_id=review_artifact,
                    relation=RelationType.GENERATED_FROM,
                )

        return {
            "review_id": review_id,
            "lesson_summary": review.lesson_summary,
            "attributions": [a.model_dump(mode="json") for a in review.attributions],
            "experience_id": experience_id,
            "card_version_no": card_version_no,
            "strategy_v2": strategy_v2,
            "rule_feedback": rule_feedback,
            "validation_id": validation.validation_id,
            "prediction_id": prediction.prediction_id,
            "as_of": utc_now().isoformat(),
        }
