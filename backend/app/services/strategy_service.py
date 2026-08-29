"""Strategy Lab service (V2 Phase F, 总纲 §21/§22/§46/§47).

§46: 筛选候选 → 策略定义。§47: 跨标的回测 → 失败案例显形 → StrategyValidation；
未通过不可进入正式 Monitor（Phase G 未建），v1 一律标 EXPERIMENTAL。
回测数据只来自真实日线（与验证工作流同一条 Data 路径）；数据不可得时
回测诚实失败，绝不编造收益。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.strategy import (
    BacktestStatus,
    StrategyBacktestRunORM,
    StrategyRepository,
    StrategyStatus,
    StrategyVersionORM,
)
from app.application.artifacts import ArtifactService, RelationType
from app.services.workflow_service import collect_daily_bars, forward_returns


class StrategyRefusal(ValueError):
    """Explicit refusal — never a silent pass (§47)."""


def _short_hex() -> str:
    return uuid4().hex[:12]


class StrategyService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = StrategyRepository(session)

    # -- 组装（§46） -----------------------------------------------------------------

    def create_from_screening(self, screening_run_id: str, name: str | None = None) -> dict:
        """Assemble a versioned strategy from a screening run + its card."""
        from app.application.screening import ScreeningRepository
        from app.application.experience import ExperienceRepository

        run = ScreeningRepository(self._session).get_run(screening_run_id)
        if run is None:
            raise KeyError(screening_run_id)
        if run["status"] != "completed":
            raise StrategyRefusal("source screening run has not completed")
        card = None
        if run.get("card_id"):
            card = ExperienceRepository(self._session).get_card(run["card_id"])
        candidates = run["candidates"]
        if not candidates:
            raise StrategyRefusal("screening run produced no candidates to assemble from")

        philosophy = (card["mechanism"] if card else "")[:2000] or "筛选候选的既有研究状态"
        base_name = (name or (card["title"] if card else None) or "筛选候选策略").strip()[:128]
        universe = [
            {"instrument_id": c["instrument_id"], "code": c["code"], "name": c["name"], "rank": c["rank"]}
            for c in candidates
        ]
        now = datetime.now(timezone.utc)
        row = StrategyVersionORM(
            version_id=f"strat_{_short_hex()}",
            name=base_name,
            version_no=self._repo.next_version_no(base_name),
            philosophy=philosophy,
            source_card_id=run.get("card_id") or "",
            source_screening_run_id=screening_run_id,
            universe_json=universe,
            entry_policy_json={"kind": "forward_return", "horizon_days": 20, "threshold_pct": 0.0},
            exit_policy_json={"kind": "horizon_end"},
            risk_policy_json={"kind": "disclose_failures", "max_candidates": len(universe)},
            status=StrategyStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        version = self._repo.add_version(row)
        self._register_artifact(version)
        return version

    # -- 跨标的回测（§47） --------------------------------------------------------------

    def start_backtest(self, version_id: str) -> dict:
        """Create a running backtest row (API returns 202, worker executes)."""
        version_row = self._repo.get_version_row(version_id)
        if version_row is None:
            raise KeyError(version_id)
        now = datetime.now(timezone.utc)
        return self._repo.add_backtest(
            StrategyBacktestRunORM(
                backtest_id=f"bt_{_short_hex()}",
                version_id=version_id,
                status=BacktestStatus.RUNNING,
                created_at=now,
                updated_at=now,
            )
        )

    def run_backtest_from_backtest(self, backtest: dict) -> dict:
        return self.run_backtest(backtest["version_id"], backtest=backtest)

    def run_backtest(self, version_id: str, *, backtest: dict | None = None) -> dict:
        version_row = self._repo.get_version_row(version_id)
        if version_row is None:
            raise KeyError(version_id)
        version = self._repo.get_version(version_id)
        entry = version["entry_policy"]
        horizon = max(1, min(int(entry.get("horizon_days", 20)), 250))
        threshold = float(entry.get("threshold_pct", 0.0))

        if backtest is None:
            backtest = self.start_backtest(version_id)
        from app.application.run_events import record_run_event

        record_run_event(
            self._session, backtest["backtest_id"], "backtest_started",
            {"version_id": version_id, "horizon_days": horizon,
             "threshold_pct": threshold, "universe": len(version["universe"])},
        )
        results: list[dict] = []
        errors: list[str] = []
        for member in version["universe"]:
            instrument_id = member["instrument_id"]
            try:
                bars = collect_daily_bars(self._session, instrument_id)
            except Exception as exc:  # noqa: BLE001 — per-instrument failure disclosed
                errors.append(f"{member.get('name', instrument_id)}: {exc}")
                results.append(
                    {
                        "instrument_id": instrument_id,
                        "name": member.get("name"),
                        "status": "no_data",
                        "error": str(exc)[:200],
                    }
                )
                continue
            returns = forward_returns(bars, horizon, threshold)
            if not returns:
                results.append(
                    {
                        "instrument_id": instrument_id,
                        "name": member.get("name"),
                        "status": "insufficient_samples",
                        "samples": 0,
                    }
                )
                continue
            hits = sum(1 for r in returns if r >= threshold)
            results.append(
                {
                    "instrument_id": instrument_id,
                    "name": member.get("name"),
                    "status": "ok",
                    "samples": len(returns),
                    "hit_rate_pct": round(hits / len(returns) * 100, 2),
                    "avg_return_pct": round(sum(returns) / len(returns), 3),
                    "best_return_pct": round(max(returns), 2),
                    "worst_return_pct": round(min(returns), 2),
                    "window": f"{bars[0]['date']} → {bars[-1]['date']}",
                }
            )

        ok_results = [r for r in results if r.get("status") == "ok"]
        if not ok_results:
            def fail(p: dict) -> dict:
                p["status"] = BacktestStatus.FAILED
                p["error"] = "; ".join(errors)[:300] or "no instrument produced usable bars"
                return p
            backtest = self._repo.update_backtest(backtest["backtest_id"], fail)
            record_run_event(
                self._session, backtest["backtest_id"], "backtest_failed",
                {"error": backtest["error"]},
            )
            return backtest

        aggregate = {
            "instruments_backtested": len(ok_results),
            "instruments_no_data": len(results) - len(ok_results),
            "portfolio_avg_return_pct": round(
                sum(r["avg_return_pct"] for r in ok_results) / len(ok_results), 3
            ),
            "portfolio_avg_hit_rate_pct": round(
                sum(r["hit_rate_pct"] for r in ok_results) / len(ok_results), 2
            ),
            "horizon_days": horizon,
            "threshold_pct": threshold,
            "errors": errors[:20],
        }
        # §22: failures are shown as they are — negative averages are failure cases
        failure_cases = [
            {
                "instrument_id": r["instrument_id"],
                "name": r.get("name"),
                "avg_return_pct": r["avg_return_pct"],
                "hit_rate_pct": r["hit_rate_pct"],
                "reason": "平均收益为负" if r["avg_return_pct"] < 0 else "命中率不足 50%",
            }
            for r in ok_results
            if r["avg_return_pct"] < 0 or r["hit_rate_pct"] < 50
        ]

        def complete(p: dict) -> dict:
            p["results"] = results
            p["aggregate"] = aggregate
            p["failure_cases"] = failure_cases
            p["status"] = BacktestStatus.COMPLETED
            return p
        backtest = self._repo.update_backtest(backtest["backtest_id"], complete)
        record_run_event(
            self._session, backtest["backtest_id"], "backtest_completed",
            {"portfolio_avg_return_pct": aggregate.get("portfolio_avg_return_pct"),
             "failure_cases": len(failure_cases)},
        )
        self._register_backtest_artifact(version, backtest)
        return backtest

    # -- 验证门槛（§47） ----------------------------------------------------------------

    def validate_version(self, version_id: str) -> dict:
        version_row = self._repo.get_version_row(version_id)
        if version_row is None:
            raise KeyError(version_id)
        backtests = self._repo.list_backtests(version_id)
        completed = [b for b in backtests if b["status"] == BacktestStatus.COMPLETED]
        if not completed:
            raise StrategyRefusal(
                "validate requires at least one completed cross-instrument backtest (§47)"
            )
        latest = completed[0]
        aggregate = latest["aggregate"]
        avg = aggregate.get("portfolio_avg_return_pct")
        verdict = (
            f"EXPERIMENTAL：组合平均收益 {avg}%（§47 全套验证未完成，禁止进入正式盯盘）"
        )
        version_row.status = StrategyStatus.EXPERIMENTAL
        version_row.verdict = verdict[:500]
        version_row.updated_at = datetime.now(timezone.utc)
        return self._repo.save_version(version_row)

    # -- reads ----------------------------------------------------------------------

    def list_versions(self, *, limit: int = 50) -> list[dict]:
        return self._repo.list_versions(limit=limit)

    def get_version_detail(self, version_id: str) -> dict | None:
        version = self._repo.get_version(version_id)
        if version is None:
            return None
        return {
            **version,
            "backtests": self._repo.list_backtests(version_id),
        }

    # -- artifact --------------------------------------------------------------------

    def _register_artifact(self, version: dict) -> str:
        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="strategy_version",
            domain_type="StrategyVersion",
            domain_id=version["version_id"],
            title=f"{version['name']}（策略 v{version['version_no']}）",
            summary=version["philosophy"][:2000] or None,
            created_by="strategy",
            route="/strategy",
        )
        screening_artifact = service.by_domain("ScreeningRun", version["source_screening_run_id"])
        if screening_artifact is not None:
            service.link(
                from_artifact_id=artifact_id,
                to_artifact_id=screening_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
        if version.get("source_card_id"):
            card_artifact = service.by_domain("ExperienceCard", version["source_card_id"])
            if card_artifact is not None:
                service.link(
                    from_artifact_id=artifact_id,
                    to_artifact_id=card_artifact["artifact_id"],
                    relation=RelationType.GENERATED_FROM,
                )
        return artifact_id

    def _register_backtest_artifact(self, version: dict, backtest: dict) -> str:
        service = ArtifactService(self._session)
        artifact_id = service.register(
            artifact_type="strategy_backtest",
            domain_type="StrategyBacktestRun",
            domain_id=backtest["backtest_id"],
            title=f"{version['name']} · 跨标的回测（{backtest['aggregate'].get('instruments_backtested', 0)} 标的）",
            summary=str(backtest["aggregate"].get("portfolio_avg_return_pct", "")),
            created_by="strategy",
            route="/strategy",
        )
        version_artifact = service.by_domain("StrategyVersion", version["version_id"])
        if version_artifact is not None:
            service.link(
                from_artifact_id=artifact_id,
                to_artifact_id=version_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
        return artifact_id
