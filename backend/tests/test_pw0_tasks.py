"""PW0/PW2 — task schedule specs, delete, and run-now."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import create_app
from app.scheduler.tasks import compute_next_run, validate_schedule
from app.sources.runtime import reset_runtime
from app.storage.orm import Base


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


def test_compute_next_run_wall_clock():
    # today 18:00 local → daily 08:30 fires tomorrow morning
    after = datetime(2026, 8, 27, 18, 0).astimezone()
    nxt = compute_next_run("daily:08:30", after)
    assert nxt.tzinfo is not None
    local = nxt.astimezone()
    assert (local.hour, local.minute) == (8, 30)
    assert local.date() == (after + timedelta(days=1)).date()

    # weekly:MON skips to the next Monday
    monday_target = compute_next_run("weekly:MON:09:00", after).astimezone()
    assert monday_target.weekday() == 0 and (monday_target.hour, monday_target.minute) == (9, 0)
    assert monday_target > after

    # weekdays:17:30 skips Saturday/Sunday
    friday = datetime(2026, 8, 28, 18, 0).astimezone()
    assert friday.weekday() == 4  # Friday
    nxt = compute_next_run("weekdays:17:30", friday).astimezone()
    assert nxt.weekday() == 0  # Monday

    # interval stays additive
    base = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    assert compute_next_run("interval:300", base) == base + timedelta(seconds=300)


def test_schedule_validation_rejects_malformed():
    for bad in ("daily:25:00", "weekly:MON", "interval:x", "whenever:08:30", "weekly:FRI:99:99"):
        with pytest.raises(ValueError):
            validate_schedule(bad)
    for good in ("interval:300", "daily:08:30", "weekdays:08:30", "weekly:FRI:17:30"):
        validate_schedule(good)


def test_create_task_with_daily_schedule(client):
    created = client.post(
        "/api/v1/tasks",
        json={"instrument": "600519", "task_type": "periodic_full_research",
              "schedule": "daily:08:30"},
    )
    assert created.status_code == 201
    task = created.json()["task"]
    assert task["schedule"] == "daily:08:30"
    # first run happens at the scheduled time, not instantly
    nxt = datetime.fromisoformat(task["next_run_at"])
    assert (nxt.astimezone().hour, nxt.astimezone().minute) == (8, 30)


def test_create_task_rejects_bad_schedule(client):
    resp = client.post(
        "/api/v1/tasks",
        json={"instrument": "600519", "task_type": "monitor", "schedule": "daily:99:00"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "task.schedule_invalid"


def test_delete_task_keeps_it_deletable_when_idle(client):
    task = client.post(
        "/api/v1/tasks",
        json={"instrument": "600519", "task_type": "monitor"},
    ).json()["task"]
    assert client.delete(f"/api/v1/tasks/{task['task_id']}").status_code == 204
    remaining = client.get("/api/v1/tasks").json()
    assert all(t["task_id"] != task["task_id"] for t in remaining["results"])
    # deleting again is a clean 404
    assert client.delete(f"/api/v1/tasks/{task['task_id']}").status_code == 404


def test_delete_running_task_is_409(client):
    from app.scheduler.tasks import TaskRepository
    from app.domain.evidence import utc_now

    task = client.post(
        "/api/v1/tasks",
        json={"instrument": "600519", "task_type": "monitor"},
    ).json()["task"]
    with session_scope_factory(client) as session:
        repo = TaskRepository(session)
        repo.claim(task["task_id"], utc_now())  # forces status=running
    resp = client.delete(f"/api/v1/tasks/{task['task_id']}")
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "task.running"


def test_run_now_executes_single_task(client, monkeypatch):
    """POST /tasks/{id}/run runs exactly this task's handler in the background."""
    import time

    from app.scheduler.tasks import TaskType

    import app.api.tasks as tasks_api

    executed = []
    original = dict(tasks_api.HANDLERS)
    tasks_api.HANDLERS[TaskType.MONITOR] = lambda session, task: executed.append(task.task_id)
    try:
        task = client.post(
            "/api/v1/tasks",
            json={"instrument": "600519", "task_type": "monitor", "schedule": "interval:3600"},
        ).json()["task"]
        resp = client.post(f"/api/v1/tasks/{task['task_id']}/run")
        assert resp.status_code == 202
        assert resp.json()["status"] == "running"
        for _ in range(100):
            if executed:
                break
            time.sleep(0.05)
        assert executed == [task["task_id"]]
        for _ in range(100):
            rows = client.get("/api/v1/tasks").json()["results"]
            if rows[0]["status"] == "idle" and rows[0]["last_run_at"]:
                break
            time.sleep(0.05)
        assert rows[0]["status"] == "idle"
    finally:
        tasks_api.HANDLERS.clear()
        tasks_api.HANDLERS.update(original)


def session_scope_factory(client):
    from app.db import session_scope

    return session_scope(client.app.state._test_factory)
