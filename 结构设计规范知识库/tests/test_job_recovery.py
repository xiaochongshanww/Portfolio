import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.api import admin
from src.app.admin.job_diagnostics import diagnose_job
from src.app.admin.jobs import JobManager
from src.app.admin.models import Job
from src.app.admin.storage import INTERRUPTED_ERROR_CODE, JobStore
from src.app.main import lifespan
from src.quality.gate import summarize_jobs


def _wait_for(predicate, timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("等待条件超时")


def test_job_store_serializes_concurrent_heartbeat_and_progress_atomically(tmp_path: Path):
    store = JobStore(tmp_path)
    job = Job(type="rebuild", worker_id="worker-a", status="running")
    job.heartbeat_at = "2026-08-08T00:00:00+00:00"
    store.save(job)

    def write_progress():
        for index in range(30):
            job.step = f"step-{index}"
            job.progress_at = f"2026-08-08T00:00:{index:02d}+00:00"
            store.save(job)

    def write_heartbeat():
        for index in range(30):
            assert store.heartbeat(
                job.job_id,
                "worker-a",
                at=f"2026-08-08T00:01:{index:02d}+00:00",
            )

    progress_thread = Thread(target=write_progress)
    heartbeat_thread = Thread(target=write_heartbeat)
    progress_thread.start()
    heartbeat_thread.start()
    progress_thread.join()
    heartbeat_thread.join()

    payload = json.loads(store.job_path(job.job_id).read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["heartbeat_at"] == "2026-08-08T00:01:29+00:00"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_startup_recovery_marks_only_foreign_active_jobs_and_is_idempotent(tmp_path: Path):
    store = JobStore(tmp_path)
    queued = Job(type="evaluate", status="queued", worker_id="old-worker")
    running = Job(type="rebuild", status="running", worker_id="old-worker")
    current = Job(type="audit", status="running", worker_id="new-worker")
    succeeded = Job(type="review", status="succeeded", worker_id="old-worker")
    for job in (queued, running, current, succeeded):
        store.save(job)

    recovered_at = "2026-08-08T01:02:03+00:00"
    first = store.recover_interrupted("new-worker", at=recovered_at)
    second = store.recover_interrupted("new-worker", at="2026-08-08T01:03:00+00:00")

    assert first["recovered_count"] == 2
    assert second["recovered_count"] == 0
    for job in (queued, running):
        payload = store.read(job.job_id)
        assert payload["status"] == "failed"
        assert payload["step"] == "interrupted"
        assert payload["error_code"] == INTERRUPTED_ERROR_CODE
        assert payload["recovery"]["previous_status"] in {"queued", "running"}
        assert payload["recovery"]["recovered_by_worker_id"] == "new-worker"
        assert store.logs(job.job_id)[-1]["error_code"] == INTERRUPTED_ERROR_CODE
    assert store.read(current.job_id)["status"] == "running"
    assert store.read(succeeded.job_id)["status"] == "succeeded"


def test_corrupt_job_record_remains_visible_without_blocking_recovery(tmp_path: Path):
    store = JobStore(tmp_path)
    valid = Job(type="audit", status="running", worker_id="old-worker")
    store.save(valid)
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")

    result = store.recover_interrupted("new-worker")
    jobs = store.list()

    assert result["recovered_count"] == 1
    assert result["corrupt_count"] == 1
    invalid = next(job for job in jobs if job.get("error_code") == "JOB_RECORD_INVALID")
    assert invalid["status"] == "failed"
    assert "任务记录损坏" in invalid["error"]


def test_job_id_mismatch_is_reported_as_corrupt_and_never_writes_foreign_log(tmp_path: Path):
    store = JobStore(tmp_path)
    mismatched = Job(type="audit", status="running", worker_id="old-worker")
    payload = mismatched.to_dict()
    payload["job_id"] = "different-job"
    store.job_path(mismatched.job_id).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    result = store.recover_interrupted("new-worker")
    record = store.read(mismatched.job_id)

    assert result["recovered_count"] == 0
    assert result["corrupt_count"] == 1
    assert record["error_code"] == "JOB_RECORD_INVALID"
    assert "与文件名不一致" in record["error"]
    assert not store.log_path("different-job").exists()


def test_job_manager_writes_live_heartbeat_and_stops_at_terminal_state(tmp_path: Path):
    store = JobStore(tmp_path)
    manager = JobManager(store, heartbeat_seconds=0.02, worker_id="worker-live")
    started = Event()
    release = Event()

    def workflow(_job, _store):
        started.set()
        assert release.wait(2)
        return {"ok": True}

    job = manager.submit("audit", {}, workflow)
    assert started.wait(1)
    initial = store.read(job.job_id)["heartbeat_at"]
    updated = _wait_for(
        lambda: (
            payload
            if (payload := store.read(job.job_id))["heartbeat_at"] > initial
            else None
        )
    )
    release.set()
    finished = _wait_for(
        lambda: (
            payload
            if (payload := store.read(job.job_id))["status"] == "succeeded"
            else None
        )
    )
    manager.executor.shutdown(wait=True)

    assert updated["worker_id"] == "worker-live"
    assert finished["finished_at"]
    terminal_heartbeat = finished["heartbeat_at"]
    time.sleep(0.05)
    assert store.read(job.job_id)["heartbeat_at"] == terminal_heartbeat


def test_diagnostics_separate_progress_stall_from_worker_heartbeat():
    now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    job = {
        "job_id": "abc",
        "type": "rebuild",
        "status": "running",
        "started_at": (now - timedelta(hours=4)).isoformat(),
        "progress_at": (now - timedelta(hours=3)).isoformat(),
        "heartbeat_at": (now - timedelta(seconds=10)).isoformat(),
    }

    diagnosed = diagnose_job(
        job,
        stale_after_seconds=7200,
        heartbeat_timeout_seconds=60,
        now=now,
    )

    assert diagnosed["diagnostics"]["stalled"] is True
    assert diagnosed["diagnostics"]["heartbeat_stale"] is False
    assert diagnosed["diagnostics"]["reason"] == "no_progress"
    assert diagnosed["diagnostics"]["progress_age_seconds"] == 10800


def test_diagnostics_and_quality_gate_fall_back_for_legacy_jobs():
    now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    legacy = {
        "job_id": "legacy",
        "type": "rebuild",
        "status": "running",
        "started_at": (now - timedelta(hours=3)).isoformat(),
    }
    recent_progress = {
        **legacy,
        "job_id": "recent",
        "progress_at": (now - timedelta(minutes=5)).isoformat(),
    }

    legacy_diagnostic = diagnose_job(
        legacy,
        stale_after_seconds=7200,
        heartbeat_timeout_seconds=60,
        now=now,
    )
    summary = summarize_jobs([legacy, recent_progress], now=now, stale_after=timedelta(hours=2))

    assert legacy_diagnostic["diagnostics"]["stalled"] is True
    assert legacy_diagnostic["diagnostics"]["heartbeat_stale"] is False
    assert summary["stale_active_count"] == 1
    assert summary["stale_active_jobs"][0]["job_id"] == "legacy"


def test_lifespan_reconciles_jobs_before_retrieval_initialization(monkeypatch):
    calls: list[str] = []
    recovery = {"recovered_count": 1, "corrupt_count": 0, "recovered": [], "corrupt": []}
    monkeypatch.setattr(
        "src.app.main.job_manager.reconcile_interrupted_jobs",
        lambda: calls.append("recover") or recovery,
    )
    monkeypatch.setattr(
        "src.app.main.retrieval_state.initialize",
        lambda: calls.append("retrieval"),
    )
    app = SimpleNamespace(state=SimpleNamespace())

    async def exercise():
        async with lifespan(app):
            calls.append("yield")

    asyncio.run(exercise())

    assert calls == ["recover", "retrieval", "yield"]
    assert app.state.job_recovery == recovery


def test_admin_job_endpoints_expose_diagnostics_and_validate_job_ids(
    tmp_path: Path,
    monkeypatch,
):
    store = JobStore(tmp_path)
    job = Job(type="rebuild", status="running", worker_id="worker-live")
    job.started_at = "2000-01-01T00:00:00+00:00"
    job.progress_at = "2000-01-01T00:00:00+00:00"
    job.heartbeat_at = "2000-01-01T00:00:00+00:00"
    store.save(job)
    store.append_log(job.job_id, "info", "task log")
    monkeypatch.setattr(admin, "job_store", store)
    contract_app = FastAPI()
    contract_app.include_router(admin.router)
    client = TestClient(contract_app)

    listed = client.get("/admin/jobs")
    detail = client.get(f"/admin/jobs/{job.job_id}")
    logs = client.get(f"/admin/jobs/{job.job_id}/logs?limit=0")
    invalid = client.get("/admin/jobs/bad.id")

    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["diagnostics"]["stalled"] is True
    assert listed.json()["jobs"][0]["diagnostics"]["heartbeat_stale"] is True
    assert detail.status_code == 200
    assert detail.json()["diagnostics"]["reason"] == "no_progress_and_heartbeat_stale"
    assert logs.status_code == 200
    assert logs.json()["logs"][0]["message"] == "task log"
    assert invalid.status_code == 400
