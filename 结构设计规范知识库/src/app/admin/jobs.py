import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from .models import Job, utc_now
from .storage import JobStore, job_store
from ..core.request_context import current_request_id, reset_request_id, set_request_id


Workflow = Callable[[Job, JobStore], dict[str, Any]]


class JobManager:
    def __init__(self, store: JobStore = job_store) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = Lock()

    def submit(self, job_type: str, params: dict[str, Any], workflow: Workflow) -> Job:
        job = Job(type=job_type, params=params, request_id=current_request_id())
        self.store.save(job)
        self.store.append_log(job.job_id, "info", f"任务已创建: {job_type}")
        self.executor.submit(self._run, job, workflow)
        return job

    def _run(self, job: Job, workflow: Workflow) -> None:
        request_token = set_request_id(job.request_id) if job.request_id else None
        try:
            with self.lock:
                job.status = "running"
                job.started_at = utc_now()
                job.step = "starting"
                self.store.save(job)
                self.store.append_log(job.job_id, "info", "任务开始")
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
                    self.store.append_log(job.job_id, "error", str(exc))
                    logging.exception(
                        "job_failed",
                        extra={
                            "extra_data": {
                                "job_id": job.job_id,
                                "job_type": job.type,
                                "status": job.status,
                            }
                        },
                    )
                finally:
                    job.finished_at = utc_now()
                    self.store.save(job)
        finally:
            if request_token is not None:
                reset_request_id(request_token)


job_manager = JobManager()
