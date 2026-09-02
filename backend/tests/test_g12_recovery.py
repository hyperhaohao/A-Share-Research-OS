"""G12 — 长任务/并发/失败恢复（观澜语义迁移任务书 §G12）.

覆盖：
  - paused 状态：queued → paused → 泵跳过；resume → queued 恢复执行；
  - dead-letter：超过重试上限的任务标记 dead_letter（可 retry 恢复）；
  - heartbeat：claim 记录 worker 存活时间。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from app.storage.repository import EvidenceRepository
from app.domain.evidence import AuthorityLevel, EvidenceRecord, EvidenceType, FactStatus


@pytest.fixture()
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    app.state._test_factory = factory
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


NOW = datetime.now(timezone.utc)
TARGET = "SZSE:000831"


def _pump(client, times: int = 1) -> None:
    for _ in range(times):
        client.post("/api/v1/tasks/scheduler/tick")


def _seed_evidence(client) -> str:
    factory = client.app.state._test_factory
    session = factory()
    try:
        at = NOW - timedelta(days=1)
        rec = EvidenceRecord(
            instrument_id=TARGET,
            evidence_type=EvidenceType.ANNOUNCEMENT,
            title="公告",
            summary="公司披露重大事项",
            source="provider_g12",
            source_type="exchange",
            authority_level=AuthorityLevel.A1,
            fact_status=FactStatus.OFFICIAL_DISCLOSURE,
            event_time=at,
            available_time=at,
            ingested_time=at + timedelta(minutes=1),
            revision_time=at + timedelta(minutes=1),
        )
        evidence_id, _ = EvidenceRepository(session).save(rec)
        session.commit()
        return evidence_id
    finally:
        session.close()


def test_task_pause_resume_flow(client):
    _seed_evidence(client)
    submitted = client.post("/api/v1/command/tasks", json={
        "tool_name": "search_evidence",
        "arguments": {"instrument_id": TARGET},
    })
    task_id = submitted.json()["task"]["task_id"]

    paused = client.post(f"/api/v1/command/tasks/{task_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["task"]["status"] == "paused"

    _pump(client, times=1)
    task = next(t for t in client.get("/api/v1/command/tasks").json()["results"]
                if t["task_id"] == task_id)
    assert task["status"] == "paused"  # paused 不被泵认领

    resumed = client.post(f"/api/v1/command/tasks/{task_id}/resume")
    assert resumed.json()["task"]["status"] == "queued"
    _pump(client, times=1)
    task = next(t for t in client.get("/api/v1/command/tasks").json()["results"]
                if t["task_id"] == task_id)
    assert task["status"] == "succeeded"  # 恢复后执行


def test_dead_letter_marker_on_exhausted_retries(client):
    submitted = client.post("/api/v1/command/tasks", json={
        "tool_name": "create_experience_card",
        "arguments": {"report_id": "rpt_missing9999"},
        "max_attempts": 2,
    })
    task_id = submitted.json()["task"]["task_id"]
    _pump(client, times=3)
    from sqlalchemy import select
    from app.application.background_orm import BackgroundTaskORM
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
        ).first()
        assert row.status == "failed"
        assert row.dead_letter is True  # dead-letter 标记
        assert row.attempts == 2
    finally:
        session.close()


def test_claim_records_heartbeat(client):
    _seed_evidence(client)
    submitted = client.post("/api/v1/command/tasks", json={
        "tool_name": "search_evidence",
        "arguments": {"instrument_id": TARGET},
    })
    task_id = submitted.json()["task"]["task_id"]
    _pump(client, times=1)
    from sqlalchemy import select
    from app.application.background_orm import BackgroundTaskORM
    factory = client.app.state._test_factory
    session = factory()
    try:
        row = session.scalars(
            select(BackgroundTaskORM).where(BackgroundTaskORM.task_id == task_id)
        ).first()
        assert row.heartbeat_at is not None  # worker 存活信号
    finally:
        session.close()
