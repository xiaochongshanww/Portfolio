import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, Lock, Thread
from typing import Any
from uuid import uuid4

from ..core.config import settings
from ..core.job_cancellation import (
    JobCancelled,
    bind_job_cancellation,
    raise_if_job_cancelled,
    reset_job_cancellation,
)
from ..core.request_context import current_request_id, reset_request_id, set_request_id
from .models import Job, utc_now
from .storage import JobStore, job_store

Workflow = Callable[[Job, JobStore], dict[str, Any]]
CANCELLABLE_JOB_TYPES = {"rebuild", "source_rebuild"}


class JobCancellationError(ValueError):
    pass


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
        self._state_lock = Lock()
        self._cancel_events: dict[str, Event] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._jobs: dict[str, Job] = {}

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
        with self._state_lock:
            self.store.save(job)
            self.store.append_log(job.job_id, "info", f"任务已创建: {job_type}")
            cancel_event = Event()
            self._jobs[job.job_id] = job
            self._cancel_events[job.job_id] = cancel_event
            self._futures[job.job_id] = self.executor.submit(
                self._run,
                job,
                workflow,
                cancel_event,
            )
        return job

    def cancel(self, job_id: str) -> Job:
        with self._state_lock:
            job = self._jobs.get(job_id)
            if job is None:
                record = self.store.read(job_id)
                if record is None:
                    raise FileNotFoundError(f"任务不存在: {job_id}")
                if record.get("type") not in CANCELLABLE_JOB_TYPES:
                    raise JobCancellationError("仅支持取消知识库构建任务")
                raise JobCancellationError("该任务不由当前 API 进程执行，无法安全取消")
            if job.type not in CANCELLABLE_JOB_TYPES:
                raise JobCancellationError("仅支持取消知识库构建任务")
            if job.status not in {"queued", "running"}:
                raise JobCancellationError("任务已经结束，不能取消")
            if job.step == "activate_version":
                raise JobCancellationError("候选版本正在原子激活，不能在提交阶段取消")

            cancel_event = self._cancel_events[job_id]
            cancel_event.set()
            job.cancellation_requested = True
            future = self._futures.get(job_id)
            if job.status == "queued" and future is not None and future.cancel():
                self._mark_cancelled(job, "排队中的构建任务已取消")
                self.store.save(job)
                self.store.append_log(job_id, "info", "排队中的构建任务已取消")
                self._forget_job(job_id)
                return job

            job.progress = {
                "stage": "cancelling",
                "message": "已收到取消请求，等待当前解析或处理步骤安全停止",
            }
            job.progress_at = utc_now()
            self.store.save(job)
            self.store.append_log(job_id, "warning", "已收到构建任务取消请求")
            return job

    @staticmethod
    def _mark_cancelled(job: Job, message: str) -> None:
        now = utc_now()
        job.status = "cancelled"
        job.cancellation_requested = True
        job.step = "cancelled"
        job.error = message
        job.error_code = "JOB_CANCELLED"
        job.progress = {"stage": "cancelled", "message": message}
        job.finished_at = now
        job.progress_at = now

    def _forget_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        self._cancel_events.pop(job_id, None)
        self._futures.pop(job_id, None)

    def _heartbeat_loop(self, job_id: str, stop: Event) -> None:
        while not stop.wait(self.heartbeat_seconds):
            if not self.store.heartbeat(job_id, self.worker_id):
                return

    def _run(self, job: Job, workflow: Workflow, cancel_event: Event | None = None) -> None:
        cancel_event = cancel_event or Event()
        request_token = set_request_id(job.request_id) if job.request_id else None
        cancellation_token = bind_job_cancellation(cancel_event, self._state_lock)
        heartbeat_stop = Event()
        heartbeat_thread: Thread | None = None
        try:
            with self.lock:
                with self._state_lock:
                    if cancel_event.is_set():
                        self._mark_cancelled(job, "排队中的构建任务已取消")
                        self.store.save(job)
                        self.store.append_log(job.job_id, "info", "排队中的构建任务已取消")
                        return
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
                    with self._state_lock:
                        raise_if_job_cancelled()
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
                except JobCancelled as exc:
                    with self._state_lock:
                        self._mark_cancelled(job, str(exc))
                        self.store.append_log(
                            job.job_id, "info", str(exc), error_code="JOB_CANCELLED"
                        )
                except Exception as exc:
                    with self._state_lock:
                        if cancel_event.is_set():
                            self._mark_cancelled(job, "任务已按请求取消")
                            self.store.append_log(
                                job.job_id,
                                "info",
                                job.error,
                                error_code="JOB_CANCELLED",
                            )
                        else:
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
            with self._state_lock:
                self._forget_job(job.job_id)
            reset_job_cancellation(cancellation_token)
            if request_token is not None:
                reset_request_id(request_token)


job_manager = JobManager(heartbeat_seconds=settings.job_heartbeat_seconds)
