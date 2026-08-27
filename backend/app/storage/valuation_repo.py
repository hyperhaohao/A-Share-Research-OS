"""Valuation persistence + service (M10)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, Float, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.valuation import (
    ValuationMethod,
    ValuationResult,
    dcf_valuation,
    ddm_valuation,
    ev_ebitda_valuation,
    historical_percentile,
    pe_valuation,
    pb_valuation,
    peer_comps_valuation,
    ps_valuation,
)
from app.storage.agent_repo import _ensure_utc
from app.storage.orm import Base


class ValuationORM(Base):
    __tablename__ = "valuations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    valuation_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)

    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    thesis_id: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(24), index=True, nullable=True)

    method: Mapped[str] = mapped_column(String(32))
    computable: Mapped[bool] = mapped_column(default=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    inputs_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ValuationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_id: str = Field(min_length=3, max_length=32)
    snapshot_id: str = Field(min_length=8, max_length=32)
    thesis_id: str | None = None
    scenario_id: str | None = None
    method: ValuationMethod
    inputs: dict = Field(default_factory=dict)


def compute(method: ValuationMethod, inputs: dict) -> ValuationResult:
    """Dispatch to the deterministic method with explicit input names."""
    getters = {
        "pe": lambda: pe_valuation(
            inputs.get("price"), inputs.get("eps_ttm"), inputs.get("target_pe")
        ),
        "pb": lambda: pb_valuation(
            inputs.get("price"), inputs.get("bvps"), inputs.get("target_pb")
        ),
        "ps": lambda: ps_valuation(
            inputs.get("price"), inputs.get("revenue_per_share"), inputs.get("target_ps")
        ),
        "ev_ebitda": lambda: ev_ebitda_valuation(
            inputs.get("price"),
            inputs.get("shares_outstanding"),
            inputs.get("net_debt"),
            inputs.get("ebitda"),
            inputs.get("target_multiple", 0) or 0,
        ),
        "dcf": lambda: dcf_valuation(
            inputs.get("price"),
            inputs.get("shares_outstanding"),
            inputs.get("fcf_projections"),
            inputs.get("wacc", 0.0) or 0.0,
            inputs.get("terminal_growth", -1.0)
            if inputs.get("terminal_growth") is not None
            else 0.0,
            inputs.get("net_debt", 0.0),
        ),
        "ddm": lambda: ddm_valuation(
            inputs.get("price"),
            inputs.get("dividend_per_share"),
            inputs.get("dividend_growth", 0.0) or 0.0,
            inputs.get("discount_rate", 0.0) or 0.0,
        ),
        "historical_percentile": lambda: historical_percentile(
            inputs.get("price"),
            inputs.get("current_multiple"),
            inputs.get("historical_multiples"),
            inputs.get("multiple_name", "pe"),
        ),
        "peer_comps": lambda: peer_comps_valuation(
            inputs.get("price"),
            inputs.get("current_metric"),
            inputs.get("peer_multiples"),
            inputs.get("metric_name", "pe"),
        ),
    }
    runner = getters[method.value]
    return runner()


class ValuationRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def save(self, result: ValuationResult, payload: ValuationIn) -> str:
        row = ValuationORM(
            valuation_id=f"val_{uuid4().hex[:16]}",
            instrument_id=payload.instrument_id,
            snapshot_id=payload.snapshot_id,
            thesis_id=payload.thesis_id,
            scenario_id=payload.scenario_id,
            method=result.method.value,
            computable=result.computable,
            value=result.value,
            inputs_json=result.inputs_used,
            result_json={
                "detail": result.detail,
                "missing": result.missing,
            },
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return row.valuation_id

    def list_for(self, instrument_id: str, snapshot_id: str | None = None) -> list[dict]:
        stmt = select(ValuationORM).where(ValuationORM.instrument_id == instrument_id)
        if snapshot_id is not None:
            stmt = stmt.where(ValuationORM.snapshot_id == snapshot_id)
        rows = self._session.scalars(stmt.order_by(ValuationORM.created_at.desc())).all()
        return [
            {
                "valuation_id": r.valuation_id,
                "instrument_id": r.instrument_id,
                "snapshot_id": r.snapshot_id,
                "thesis_id": r.thesis_id,
                "scenario_id": r.scenario_id,
                "method": r.method,
                "computable": r.computable,
                "value": r.value,
                "inputs": r.inputs_json,
                "detail": (r.result_json or {}).get("detail", {}),
                "missing": (r.result_json or {}).get("missing", []),
                "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None,
            }
            for r in rows
        ]
