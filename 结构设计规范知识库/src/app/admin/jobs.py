from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from .models import Job, utc_now
from .storage import JobStore, job_store


Workflow = Callable[[Job, JobStore], dict[str, Any]]


class JobManager:
    def __init__(self, store: JobStore = job_store) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = Lock()

    def submit(self, job_type: str, params: dict[str, Any], workflow: Workflow) -> Job:
        job = Job(type=job_type, params=params)
        self.store.save(job)
        self.store.append_log(job.job_id, "info", f"任务已创建: {job_type}")
        self.executor.submit(self._run, job, workflow)
        return job

    def _run(self, job: Job, workflow: Workflow) -> None:
        with self.lock:
            job.status = "running"
            job.started_at = utc_now()
            job.step = "starting"
            self.store.save(job)
            self.store.append_log(job.job_id, "info", "任务开始")
            try:
                job.outputs = workflow(job, self.store) or {}
                job.status = "succeeded"
                job.step = "finished"
                self.store.append_log(job.job_id, "info", "任务完成")
            except Exception as exc:
                job.status = "failed"
                job.step = "failed"
                job.error = str(exc)
                self.store.append_log(job.job_id, "error", str(exc))
            finally:
                job.finished_at = utc_now()
                self.store.save(job)


job_manager = JobManager()
