"""Scheduler tests: idempotency, retry, recovery, concurrency (任务书 §49)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.sources.runtime import reset_runtime
from app.storage.orm import Base
from tests.test_research_api import RAW_OK


STATE: dict = {}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    STATE["factory"] = factory

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    reset_runtime()
    yield TestClient(app)
    reset_runtime()


def _quote(price: str) -> httpx.Response:
    body = RAW_OK.replace("1648.00~1651.00", f"{price}~1651.00", 1)
    return httpx.Response(200, content=body.encode("gbk"))


def _create_task(client, instrument: str = "600519", task_type: str = "monitor", schedule: str | None = "interval:0") -> dict:
    resp = client.post(
        "/api/v1/tasks",
        json={"instrument": instrument, "task_type": task_type, "schedule": schedule},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["task"]


def test_task_creation_and_listing(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    task = _create_task(client)
    assert task["task_id"].startswith("task_")
    assert task["enabled"] is True
    assert task["next_run_at"] is not None

    listed = client.get("/api/v1/tasks").json()
    assert listed["count"] == 1

    # due immediately (interval:0) → tick runs it
    tick = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] in tick["claimed"]
    assert task["task_id"] in tick["succeeded"]

    updated = client.get("/api/v1/tasks").json()["results"][0]
    assert updated["last_run_at"] is not None
    assert updated["attempts"] == 0  # reset after success


def test_idempotency_second_tick_not_due(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    task = _create_task(client, schedule="interval:3600")  # hourly
    first = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] in first["claimed"]

    # second immediate tick: not due again → nothing claimed
    second = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] not in second["claimed"]


def test_failure_retries_with_backoff_then_fails(client, monkeypatch):
    """A handler that always raises → attempts increment → backoff → FAILED."""
    from app.scheduler.scheduler import HANDLERS
    from app.scheduler.tasks import TaskType

    def always_fails(session, task):
        raise RuntimeError("boom")

    monkeypatch.setitem(HANDLERS, TaskType.MONITOR, always_fails)

    task = _create_task(client, schedule="interval:0")
    t1 = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] in t1["failed"]
    t2 = client.post("/api/v1/tasks/scheduler/tick").json()
    # backoff: next_run_at pushed out → not due immediately
    assert task["task_id"] not in t2["claimed"]


def test_concurrency_one_running_per_instrument(client, monkeypatch):
    """While one task for an instrument is RUNNING, another cannot be claimed."""
    from app.domain.evidence import utc_now
    from app.db import get_session_factory
    from app.scheduler.scheduler import Scheduler
    from app.scheduler.tasks import ResearchTaskORM, TaskRepository

    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    _create_task(client, schedule="interval:0")
    _create_task(client, schedule="interval:0")

    session = STATE['factory']()
    try:
        repo = TaskRepository(session)
        due = repo.due_tasks(utc_now())
        assert len(due) == 2
        claimed = repo.claim(due[0].task_id, utc_now())
        assert claimed is not None
        blocked = repo.claim(due[1].task_id, utc_now())
        assert blocked is None
        result = Scheduler(session).tick()
        # claim() deferred the busy instrument's second task by 30s, so the
        # tick does not claim it; it stays idle with a future next_run_at
        assert due[1].task_id not in result.claimed
        deferred = repo.get(due[1].task_id)
        assert deferred.status.value == "idle"
        assert deferred.next_run_at is not None
        repo.complete(due[0].task_id, utc_now(), success=True)
    finally:
        session.close()


def test_recovery_of_interrupted_task(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    task = _create_task(client, schedule="interval:0")

    # simulate a crash: mark running with an old running_since directly
    from datetime import timedelta

    from sqlalchemy import update as _update

    from app.domain.evidence import utc_now
    from app.db import get_session_factory
    from app.scheduler.scheduler import Scheduler
    from app.scheduler.tasks import ResearchTaskORM, TaskRepository

    session = STATE['factory']()
    try:
        repo = TaskRepository(session)
        now = utc_now()
        repo.claim(task["task_id"], now)
        session.execute(
            _update(ResearchTaskORM)
            .where(ResearchTaskORM.task_id == task["task_id"])
            .values(running_since=now - timedelta(seconds=3600))
        )
        session.commit()

        result = Scheduler(session).tick()
        assert task["task_id"] in result.recovered
        recovered = repo.get(task["task_id"])
        assert recovered.status.value == "idle"
        assert recovered.next_run_at is not None
    finally:
        session.close()


def test_disable_task_stops_execution(client, monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: _quote("1648.00"))
    task = _create_task(client, schedule="interval:0")
    client.patch(f"/api/v1/tasks/{task['task_id']}", params={"enabled": False})

    tick = client.post("/api/v1/tasks/scheduler/tick").json()
    assert task["task_id"] not in tick["claimed"]
