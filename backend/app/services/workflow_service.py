"""Workflow DAG execution (V2 Phase D, 总纲 §73/§44).

最小强类型 DAG（§73 第一批）：

    Data(bars) → Rule(forward_return) → Validation(evaluate) → Output(persist)

- Data 只读真实证据层：通过 historical_data 能力采集真实日线（PIT 可见），
  采集失败 → 节点失败 → 工作流失败（显形，绝不编造）。
- Rule 是强类型参数对象：horizon_days + threshold_pct 的前向收益规则。
- Validation 输出确定性指标（样本/命中率/收益分布）；样本为 0 时如实
  报告「样本不足」，不伪造结论。
- Output 把指标写为经验卡的 quant validation 记录（§72 衔接）并注册
  workflow_run Artifact（generated_from experience_card）。
- 每个节点完成即写 RunEvent（§37：workflow-run 通用）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application.workflow import (
    NodeStatus,
    WorkflowRepository,
    WorkflowStatus,
)
from app.domain.evidence import EvidenceType
from app.storage.repository import EvidenceRepository


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_nodes() -> list[dict]:
    """The fixed first-batch DAG shape (§73): typed node descriptors."""
    return [
        {"node_id": "n_data", "kind": "data", "title": "采集历史日线", "status": NodeStatus.PENDING,
         "detail": None, "error": None},
        {"node_id": "n_rule", "kind": "rule", "title": "前向收益规则", "status": NodeStatus.PENDING,
         "detail": None, "error": None},
        {"node_id": "n_validation", "kind": "validation", "title": "指标评估", "status": NodeStatus.PENDING,
         "detail": None, "error": None},
        {"node_id": "n_output", "kind": "output", "title": "落库与注册", "status": NodeStatus.PENDING,
         "detail": None, "error": None},
    ]


class WorkflowService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)

    # -- draft ---------------------------------------------------------------------

    def create_from_card(
        self, card_id: str, *, horizon_days: int = 20, threshold_pct: float = 0.0
    ) -> dict:
        """§44: ExperienceCard → workflow draft（立即后台执行，202）。"""
        from app.application.experience import ExperienceRepository
        from app.services.commander import INTENT_TITLES  # noqa: F401 — scope note only

        card = ExperienceRepository(self._session).get_card(card_id)
        if card is None:
            raise KeyError(card_id)
        params = {
            "rule": "forward_return",
            "horizon_days": max(1, min(int(horizon_days), 250)),
            "threshold_pct": float(threshold_pct),
        }
        return self._repo.create_run(
            instrument_id=card["instrument_id"],
            kind="card_quant_validation",
            params=params,
            nodes=build_nodes(),
            card_id=card_id,
        )

    # -- execution -------------------------------------------------------------------

    def execute(self, run: dict) -> dict:
        """Run all nodes in order; first failure stops the DAG (visible)."""
        from app.application.run_events import record_run_event

        run = self._repo.get_run(run["run_id"]) or run
        record_run_event(
            self._session, run["run_id"], "workflow_started",
            {"card_id": run["card_id"], "params": run["params"]},
        )
        failed: str | None = None
        for node in run["nodes"]:
            if node["status"] in (NodeStatus.OK, NodeStatus.FAILED):
                continue
            run = self._mark(run["run_id"], node["node_id"], status=NodeStatus.RUNNING)
            try:
                detail = self._run_node(node["kind"], run)
            except Exception as exc:  # noqa: BLE001 — node failure is run state
                failed = node["title"]
                run = self._mark(
                    run["run_id"], node["node_id"],
                    status=NodeStatus.FAILED, error=str(exc)[:300],
                )
                break
            run = self._mark(run["run_id"], node["node_id"], status=NodeStatus.OK, detail=detail)

        status = WorkflowStatus.FAILED if failed else WorkflowStatus.COMPLETED

        def finalize(p: dict) -> dict:
            p["status"] = status
            if failed:
                p["error"] = failed
            return p
        run = self._repo.update_run(run["run_id"], finalize)
        from app.application.run_events import record_run_event

        record_run_event(
            self._session, run["run_id"],
            "workflow_completed" if status == WorkflowStatus.COMPLETED else "workflow_failed",
            {"card_id": run["card_id"], "status": status},
        )
        return run

    def _mark(self, run_id: str, node_id: str, **patch) -> dict:
        def mutate(p: dict) -> dict:
            for n in p["nodes"]:
                if n["node_id"] == node_id:
                    n.update(patch)
            return p
        run = self._repo.update_run(run_id, mutate)
        from app.application.run_events import record_run_event

        record_run_event(
            self._session, run_id, "node_updated",
            {"node_id": node_id, **{k: v for k, v in patch.items() if k != "detail"}},
        )
        return run

    # -- nodes -------------------------------------------------------------------------

    def _run_node(self, kind: str, run: dict) -> str:
        if kind == "data":
            return self._node_data(run)
        if kind == "rule":
            return self._node_rule(run)
        if kind == "validation":
            return self._node_validation(run)
        if kind == "output":
            return self._node_output(run)
        raise ValueError(f"unknown node kind: {kind}")

    def _node_data(self, run: dict) -> str:
        """Collect REAL daily bars through the historical_data capability."""
        from app.services.evidence_collector import collect_capability_evidence

        outcome = collect_capability_evidence(
            run["instrument_id"], "historical_data",
            repo=EvidenceRepository(self._session),
            params={"bars": 1200},
        )
        if outcome.manifest.final_status not in ("success", "partial") or not outcome.created_ids:
            raise ValueError(
                f"historical bars unavailable ({outcome.manifest.final_status})"
            )
        bars = self._load_bars(run["instrument_id"])
        if len(bars) < 2:
            raise ValueError("fewer than 2 usable bars")
        return f"{len(bars)} 根日线（{bars[0]['date']} → {bars[-1]['date']}）"

    def _load_bars(self, instrument_id: str) -> list[dict]:
        """Newest kline evidence's bars, chronological."""
        evidence_repo = EvidenceRepository(self._session)
        now = datetime.now(timezone.utc)
        kline = [
            e for e in evidence_repo.list_for_instrument(instrument_id, visible_at=now)
            if e.evidence_type is EvidenceType.MARKET_QUOTE
            and (e.metadata or {}).get("bar_count") is not None
            and isinstance((e.metadata or {}).get("bars"), list)
        ]
        if not kline:
            return []
        newest = max(kline, key=lambda e: e.available_time)
        bars = [b for b in newest.metadata["bars"] if isinstance(b, dict) and b.get("close")]
        bars.sort(key=lambda b: b["date"])
        return bars

    def _node_rule(self, run: dict) -> str:
        """Apply the typed forward-return rule over the bar series."""
        bars = self._load_bars(run["instrument_id"])
        horizon = int(run["params"].get("horizon_days", 20))
        threshold = float(run["params"].get("threshold_pct", 0.0))
        returns: list[float] = []
        for i in range(len(bars) - horizon):
            base = float(bars[i]["close"])
            later = float(bars[i + horizon]["close"])
            if base > 0:
                returns.append((later / base - 1) * 100)
        metrics = {
            "samples": len(returns),
            "threshold_pct": threshold,
            "horizon_days": horizon,
        }
        def merge(p: dict) -> dict:
            p["metrics"] = {**p.get("metrics", {}), **metrics, "forward_returns": returns[:500]}
            return p
        self._repo.update_run(run["run_id"], merge)
        return f"horizon={horizon} 交易日，样本 {len(returns)}"

    def _node_validation(self, run: dict) -> str:
        metrics = dict(run.get("metrics") or {})
        returns = metrics.get("forward_returns") or []
        threshold = float(metrics.get("threshold_pct", 0.0))
        if not returns:
            metrics.update(
                {
                    "hit_rate_pct": None,
                    "avg_return_pct": None,
                    "best_return_pct": None,
                    "worst_return_pct": None,
                    "note": "样本不足（0）—— 无法给出命中率，如实披露",
                }
            )
            summary = "样本不足（0）—— 无有效前向收益样本"
        else:
            hits = sum(1 for r in returns if r >= threshold)
            metrics.update(
                {
                    "hit_rate_pct": round(hits / len(returns) * 100, 2),
                    "avg_return_pct": round(sum(returns) / len(returns), 3),
                    "best_return_pct": round(max(returns), 2),
                    "worst_return_pct": round(min(returns), 2),
                    "note": None,
                }
            )
            summary = (
                f"命中 {hits}/{len(returns)}（{metrics['hit_rate_pct']}%）· "
                f"平均 {metrics['avg_return_pct']:+.3f}% · "
                f"区间 [{metrics['worst_return_pct']:+.2f}%, {metrics['best_return_pct']:+.2f}%]"
            )
        metrics.pop("forward_returns", None)  # series is internal, not persisted
        def merge(p: dict) -> dict:
            p["metrics"] = {**p.get("metrics", {}), **metrics}
            return p
        self._repo.update_run(run["run_id"], merge)
        return summary

    def _node_output(self, run: dict) -> str:
        """Persist the quant validation on the card + register the artifact."""
        from app.application.experience import (
            ExperienceRepository,
            ExperienceStatus,
            ExperienceValidationORM,
        )
        from app.application.artifacts import ArtifactService, RelationType
        from uuid import uuid4

        card_id = run.get("card_id")
        if not card_id:
            return "无关联卡片，指标仅存于工作流运行"
        repo = ExperienceRepository(self._session)
        card_row = repo.get_card_row(card_id)
        if card_row is None:
            raise ValueError(f"card vanished: {card_id}")
        metrics = dict(run.get("metrics") or {})
        note = metrics.get("note")
        summary = (
            f"量化验证（前向收益 h={metrics.get('horizon_days')}）：{note}"
            if note
            else (
                f"量化验证（前向收益 h={metrics.get('horizon_days')}）："
                f"命中率 {metrics.get('hit_rate_pct')}%，平均 {metrics.get('avg_return_pct')}%"
            )
        )
        validation = repo.add_validation(
            ExperienceValidationORM(
                validation_id=f"expv_{uuid4().hex[:12]}",
                card_id=card_id,
                method="quant",
                cases_json=[
                    {
                        "workflow_run_id": run["run_id"],
                        "rule": run["params"].get("rule"),
                        "horizon_days": metrics.get("horizon_days"),
                        "threshold_pct": metrics.get("threshold_pct"),
                        "samples": metrics.get("samples"),
                        "hit_rate_pct": metrics.get("hit_rate_pct"),
                        "avg_return_pct": metrics.get("avg_return_pct"),
                    }
                ],
                summary=summary,
                created_at=datetime.now(timezone.utc),
            )
        )
        if card_row.status in (ExperienceStatus.REFINED, ExperienceStatus.DRAFT):
            card_row.status = ExperienceStatus.VALIDATING
            card_row.updated_at = datetime.now(timezone.utc)
            repo.save_card(card_row)

        service = ArtifactService(self._session)
        card_artifact = service.by_domain("ExperienceCard", card_id)
        wf_artifact = service.register(
            artifact_type="workflow_run",
            domain_type="WorkflowRun",
            domain_id=run["run_id"],
            title=f"{card_row.title} · 量化验证工作流",
            summary=summary[:2000] or None,
            instrument_ids=(run["instrument_id"],),
            created_by="workflow",
            route="/experience",
        )
        if card_artifact is not None:
            service.link(
                from_artifact_id=wf_artifact,
                to_artifact_id=card_artifact["artifact_id"],
                relation=RelationType.GENERATED_FROM,
            )
        return summary
