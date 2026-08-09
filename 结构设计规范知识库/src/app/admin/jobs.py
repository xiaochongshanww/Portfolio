import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock, Thread
from typing import Any
from uuid import uuid4

from ..core.config import settings
from ..core.request_context import current_request_id, reset_request_id, set_request_id
from .models import Job, utc_now
from .storage import JobStore, job_store

Workflow = Callable[[Job, JobStore], dict[str, Any]]


class JobManager:
    def __init__(
        self,
        store: JobStore = job_store,
        *,
        heartbeat_seconds: float = 15.0,
        worker_id: str | None = None,
    ) -> None:
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds 必须大于 0")
        self.store = store
        self.heartbeat_seconds = heartbeat_seconds
        self.worker_id = worker_id or uuid4().hex
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="knowledge-job")
        self.lock = Lock()

    def reconcile_interrupted_jobs(self) -> dict[str, Any]:
        result = self.store.recover_interrupted(self.worker_id)
        if result["recovered_count"]:
            logging.warning(
                "interrupted_jobs_recovered",
                extra={
                    "extra_data": {
                        "worker_id": self.worker_id,
                        "recovered_count": result["recovered_count"],
                    }
                },
            )
        if result["corrupt_count"]:
            logging.error(
                "corrupt_job_records_detected",
                extra={
                    "extra_data": {
                        "worker_id": self.worker_id,
                        "corrupt_count": result["corrupt_count"],
                    }
                },
            )
        return result

    def submit(self, job_type: str, params: dict[str, Any], workflow: Workflow) -> Job:
        job = Job(
            type=job_type,
            params=params,
            request_id=current_request_id(),
            worker_id=self.worker_id,
        )
        self.store.save(job)
        self.store.append_log(job.job_id, "info", f"任务已创建: {job_type}")
        self.executor.submit(self._run, job, workflow)
        return job

    def _heartbeat_loop(self, job_id: str, stop: Event) -> None:
        while not stop.wait(self.heartbeat_seconds):
            if not self.store.heartbeat(job_id, self.worker_id):
                return

    def _run(self, job: Job, workflow: Workflow) -> None:
        request_token = set_request_id(job.request_id) if job.request_id else None
        heartbeat_stop = Event()
        heartbeat_thread: Thread | None = None
        try:
            with self.lock:
                started_at = utc_now()
                job.worker_id = self.worker_id
                job.status = "running"
                job.started_at = started_at
                job.heartbeat_at = started_at
                job.progress_at = started_at
                job.step = "starting"
                job.error = ""
                job.error_code = ""
                job.recovery = {}
                self.store.save(job)
                self.store.append_log(job.job_id, "info", "任务开始")
                heartbeat_thread = Thread(
                    target=self._heartbeat_loop,
                    args=(job.job_id, heartbeat_stop),
                    name=f"job-heartbeat-{job.job_id}",
                    daemon=True,
                )
                heartbeat_thread.start()
                logging.info(
                    "job_started",
                    extra={"extra_data": {"job_id": job.job_id, "job_type": job.type}},
                )
                try:
                    job.outputs = workflow(job, self.store) or {}
                    job.status = "succeeded"
                    job.step = "finished"
                    self.store.append_log(job.job_id, "info", "任务完成")
                    logging.info(
                        "job_completed",
                        extra={
                            "extra_data": {
                                "job_id": job.job_id,
                                "job_type": job.type,
                                "status": job.status,
                            }
                        },
                    )
                except Exception as exc:
                    job.status = "failed"
                    job.step = "failed"
                    job.error = str(exc)
                    job.error_code = job.error_code or "WORKFLOW_FAILED"
                    self.store.append_log(
                        job.job_id,
                        "error",
                        str(exc),
                        error_code=job.error_code,
                    )
                    logging.exception(
                        "job_failed",
                        extra={
                            "extra_data": {
                                "job_id": job.job_id,
                                "job_type": job.type,
                                "status": job.status,
                                "error_code": job.error_code,
                            }
                        },
                    )
                finally:
                    heartbeat_stop.set()
                    if heartbeat_thread is not None:
                        heartbeat_thread.join(timeout=max(1.0, self.heartbeat_seconds * 2))
                    finished_at = utc_now()
                    job.finished_at = finished_at
                    job.progress_at = finished_at
                    self.store.save(job)
        finally:
            heartbeat_stop.set()
            if request_token is not None:
                reset_request_id(request_token)


job_manager = JobManager(heartbeat_seconds=settings.job_heartbeat_seconds)
