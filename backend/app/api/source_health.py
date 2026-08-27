"""Source health API (任务书 §84: source health 在 UI 可见)."""

from __future__ import annotations

from fastapi import APIRouter

from app.sources.runtime import get_runtime

router = APIRouter(tags=["system"])


@router.get("/source-health")
def source_health() -> dict:
    snapshot = get_runtime().registry.health.snapshot()
    return {
        "providers": [h.as_dict() for h in snapshot],
        "count": len(snapshot),
    }
