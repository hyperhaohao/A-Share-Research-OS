"""R1 — 统一权威生产模型 Facade（观澜语义迁移任务书 §R1）.

所有跨模块生产流程（REST API / Workflow 节点 / Commander / Golden）必须
通过本 Facade 调用同一组 Application Service，保证：

  - Approved Experience → ScreenDefinition 只有一条生产路径（G5 编译器）；
  - ScreenRun → StrategyDefinition 只有一条生产路径（本 Facade
    ``create_strategy_from_screen_run``）；
  - 每个 StrategyDefinitionVersion 可反查唯一
    ScreenDefinitionVersion / ScreenRun / ExperienceVersion 因果链；
  - input_digest（源 ID 规范化哈希）+ idempotency_key 保证重复提交幂等；
  - 旧 create_from_screening 路径封存（只读兼容，不再产生新生产对象）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.storage.screen_definition_orm import (
    ScreenDefinitionORM,
    ScreenDefinitionRunORM,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ResearchProductionFacade:
    """权威生产路径 Facade（R1）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_strategy_from_screen_run(
        self, *,
        screen_run_id: str,
        name: str | None = None,
        confirmation_id: str | None = None,
    ) -> dict:
        """ScreenRun → StrategyDefinitionVersion（权威路径）。

        - ScreenRun 必须存在且其 ScreenDefinition 已发布；
        - universe = ScreenRun 候选（真实筛选结果）；
        - entry/exit/risk 从来源 ScreenDefinition 的 ranking/experience
          component 派生（可解释默认 + 来源标注）；
        - input_digest + idempotency_key：同源重复提交返回既有版本；
        - 因果链：source_screen_definition_id / source_screen_run_id /
          source_version_ids_json = [card_version, def_version, run_id]。
        """
        from app.application.strategy import (
            StrategyRepository,
            StrategyVersionORM,
            StrategyStatus,
        )

        run_row = self._session.scalars(
            select(ScreenDefinitionRunORM)
            .where(ScreenDefinitionRunORM.run_id == screen_run_id)
        ).first()
        if run_row is None:
            raise AppError("screen.run_not_found", status_code=404) from None
        def_row = self._session.scalars(
            select(ScreenDefinitionORM)
            .where(ScreenDefinitionORM.def_id == run_row.def_id)
        ).first()
        if def_row is None or def_row.status != "published":
            raise AppError(
                "screen.definition_not_published", status_code=422,
                detail=f"definition status={def_row.status if def_row else None}",
            ) from None

        idem = f"strategy:{run_row.run_id}:{run_row.def_version}"
        existing = self._session.scalars(
            select(StrategyVersionORM)
            .where(StrategyVersionORM.idempotency_key == idem)
        ).first()
        if existing is not None:
            from app.services.strategy_service import StrategyService

            return StrategyService(self._session).get_version_detail(
                existing.version_id)

        candidates = list(run_row.candidates_json or [])
        universe = [
            {"instrument_id": c["instrument_id"], "rank": c.get("rank"),
             "score": c.get("score")}
            for c in candidates
        ]
        experience_rules = def_row.rules_json or []
        entry_rules = [
            {"kind": "quote_move", "pct": 3.0, "window": 10,
             "origin": "default (experience rule engine pending factor layer)"}
        ]
        exit_rules = [{"kind": "max_hold_days", "days": 20,
                       "origin": "default"}]
        risk_rules = [{"kind": "max_drawdown", "pct": 15.0,
                       "origin": "default"}]

        source_version_ids = [
            def_row.source_card_id, str(def_row.source_card_version),
            def_row.def_id, str(def_row.version), run_row.run_id,
        ]
        digest_payload = {
            "screen_run_id": screen_run_id,
            "def_version": run_row.def_version,
            "universe": sorted(u["instrument_id"] for u in universe),
            "entry_rules": entry_rules, "exit_rules": exit_rules,
            "risk_rules": risk_rules,
        }
        input_digest = _digest(digest_payload)

        now = _now()
        existing_versions = self._session.scalars(
            select(StrategyVersionORM)
            .where(StrategyVersionORM.name == (name or def_row.name))
        ).all()
        version_no = (max(v.version_no for v in existing_versions) + 1
                      if existing_versions else 1)

        row = StrategyVersionORM(
            version_id=f"strat_{uuid4().hex[:12]}",
            name=(name or def_row.name)[:120],
            version_no=version_no,
            philosophy=(def_row.compiled_payload_json or {}).get("statement",
                        "experience-driven strategy")[:2000],
            source_card_id=def_row.source_card_id,
            source_screening_run_id=screen_run_id,
            source_screen_definition_id=def_row.def_id,
            source_screen_run_id=screen_run_id,
            input_digest=input_digest,
            source_version_ids_json=source_version_ids,
            confirmation_id=confirmation_id,
            idempotency_key=idem,
            universe_json=universe,
            entry_policy_json={"entry_rules": entry_rules},
            exit_policy_json={"exit_rules": exit_rules},
            risk_policy_json={"risk_rules": risk_rules},
            status=StrategyStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return {
            "version_id": row.version_id,
            "version_no": row.version_no,
            "name": row.name,
            "input_digest": input_digest,
            "source_version_ids": source_version_ids,
            "idempotency_key": idem,
        }
