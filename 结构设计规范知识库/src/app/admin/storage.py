from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from src.pipeline.paths import DATA_DIR

from ..core.request_context import current_request_id
from .models import Job, utc_now


JOBS_DIR = DATA_DIR / "jobs"
JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
INTERRUPTED_ERROR_CODE = "PROCESS_RESTARTED"
INVALID_RECORD_ERROR_CODE = "JOB_RECORD_INVALID"


class JobStore:
    def __init__(self, jobs_dir: Path = JOBS_DIR) -> None:
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        if not JOB_ID_PATTERN.fullmatch(job_id):
            raise ValueError(f"非法任务标识: {job_id!r}")
        return job_id

    def job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{self._validate_job_id(job_id)}.json"

    def log_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{self._validate_job_id(job_id)}.jsonl"

    @staticmethod
    def _read_payload(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("任务记录必须是 JSON 对象")
        return payload

    def _read_job_payload(self, path: Path) -> dict[str, Any]:
        payload = self._read_payload(path)
        filename_job_id = self._validate_job_id(path.stem)
        payload_job_id = str(payload.get("job_id") or "")
        if not payload_job_id:
            raise ValueError("任务记录缺少 job_id")
        self._validate_job_id(payload_job_id)
        if payload_job_id != filename_job_id:
            raise ValueError(
                f"任务记录 job_id 与文件名不一致: {payload_job_id!r} != {filename_job_id!r}"
            )
        return payload

    @staticmethod
    def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex[:8]}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _invalid_record(path: Path, exc: Exception) -> dict[str, Any]:
        try:
            modified_at = path.stat().st_mtime
            timestamp = datetime.fromtimestamp(modified_at, timezone.utc).isoformat()
        except OSError:
            timestamp = ""
        return {
            "job_id": path.stem,
            "type": "unknown",
            "status": "failed",
            "step": "invalid_record",
            "error_code": INVALID_RECORD_ERROR_CODE,
            "error": f"任务记录损坏: {exc}",
            "created_at": timestamp,
            "finished_at": timestamp,
            "updated_at": timestamp,
            "record_path": str(path),
        }

    def save(self, job: Job) -> None:
        with self._lock:
            now = utc_now()
            job.updated_at = now
            payload = job.to_dict()
            path = self.job_path(job.job_id)
            if path.exists():
                try:
                    current = self._read_job_payload(path)
                except (OSError, json.JSONDecodeError, ValueError):
                    current = {}
                current_heartbeat = str(current.get("heartbeat_at") or "")
                if (
                    current.get("worker_id") == payload.get("worker_id")
                    and current_heartbeat > str(payload.get("heartbeat_at") or "")
                ):
                    job.heartbeat_at = current_heartbeat
                    payload["heartbeat_at"] = current_heartbeat
            self._atomic_write(path, payload)

    def read(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            path = self.job_path(job_id)
            if not path.exists():
                return None
            try:
                return self._read_job_payload(path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                return self._invalid_record(path, exc)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            paths = sorted(
                self.jobs_dir.glob("*.json"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            jobs: list[dict[str, Any]] = []
            for path in paths:
                try:
                    jobs.append(self._read_job_payload(path))
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    jobs.append(self._invalid_record(path, exc))
            return jobs

    def _append_log_locked(self, job_id: str, payload: dict[str, Any]) -> None:
        with self.log_path(job_id).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            handle.flush()

    def append_log(self, job_id: str, level: str, message: str, **extra: Any) -> None:
        request_id = str(extra.pop("request_id", "") or current_request_id())
        payload = {
            "ts": utc_now(),
            "level": level,
            "message": message,
            **({"request_id": request_id} if request_id else {}),
            **extra,
        }
        with self._lock:
            self._append_log_locked(job_id, payload)

    def logs(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            path = self.log_path(job_id)
            if not path.exists():
                return []
            lines = path.read_text(encoding="utf-8").splitlines()
            result: list[dict[str, Any]] = []
            for line in lines[-max(1, limit):]:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    payload = {
                        "ts": "",
                        "level": "error",
                        "message": f"任务日志记录损坏: {exc}",
                        "error_code": "JOB_LOG_RECORD_INVALID",
                    }
                result.append(payload if isinstance(payload, dict) else {"message": str(payload)})
            return result

    def heartbeat(self, job_id: str, worker_id: str, *, at: str | None = None) -> bool:
        with self._lock:
            path = self.job_path(job_id)
            if not path.exists():
                return False
            try:
                payload = self._read_job_payload(path)
            except (OSError, json.JSONDecodeError, ValueError):
                return False
            if payload.get("status") != "running" or payload.get("worker_id") != worker_id:
                return False
            heartbeat_at = at or utc_now()
            payload["heartbeat_at"] = heartbeat_at
            payload["updated_at"] = heartbeat_at
            self._atomic_write(path, payload)
            return True

    def recover_interrupted(self, worker_id: str, *, at: str | None = None) -> dict[str, Any]:
        recovered_at = at or utc_now()
        recovered: list[dict[str, Any]] = []
        corrupt: list[dict[str, str]] = []
        with self._lock:
            for path in sorted(self.jobs_dir.glob("*.json")):
                try:
                    payload = self._read_job_payload(path)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    corrupt.append({"path": str(path), "error": str(exc)})
                    continue
                previous_status = str(payload.get("status") or "")
                previous_worker_id = str(payload.get("worker_id") or "")
                if previous_status not in {"queued", "running"} or previous_worker_id == worker_id:
                    continue
                job_id = str(payload.get("job_id") or path.stem)
                try:
                    self._validate_job_id(job_id)
                except ValueError as exc:
                    corrupt.append({"path": str(path), "error": str(exc)})
                    continue
                recovery = {
                    "reason": "process_restarted",
                    "previous_status": previous_status,
                    "previous_worker_id": previous_worker_id,
                    "recovered_by_worker_id": worker_id,
                    "recovered_at": recovered_at,
                }
                payload.update(
                    {
                        "status": "failed",
                        "step": "interrupted",
                        "error_code": INTERRUPTED_ERROR_CODE,
                        "error": "API 进程已重启，原任务无法安全续跑；请核对候选产物后重新提交。",
                        "finished_at": recovered_at,
                        "progress_at": recovered_at,
                        "updated_at": recovered_at,
                        "recovery": recovery,
                    }
                )
                self._atomic_write(path, payload)
                self._append_log_locked(
                    job_id,
                    {
                        "ts": recovered_at,
                        "level": "error",
                        "message": payload["error"],
                        "error_code": INTERRUPTED_ERROR_CODE,
                        "recovery": recovery,
                    },
                )
                recovered.append(
                    {
                        "job_id": job_id,
                        "type": str(payload.get("type") or "unknown"),
                        "previous_status": previous_status,
                    }
                )
        return {
            "recovered_count": len(recovered),
            "corrupt_count": len(corrupt),
            "recovered": recovered,
            "corrupt": corrupt,
        }


job_store = JobStore()
