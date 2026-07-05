from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.pipeline.paths import DATA_DIR

from .models import Job, utc_now


JOBS_DIR = DATA_DIR / "jobs"


class JobStore:
    def __init__(self, jobs_dir: Path = JOBS_DIR) -> None:
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def log_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.jsonl"

    def save(self, job: Job) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.job_path(job.job_id).write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def read(self, job_id: str) -> dict[str, Any] | None:
        path = self.job_path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        jobs = []
        for path in sorted(self.jobs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        return jobs

    def append_log(self, job_id: str, level: str, message: str, **extra: Any) -> None:
        payload = {"ts": utc_now(), "level": level, "message": message, **extra}
        with self.log_path(job_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def logs(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        path = self.log_path(job_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]


job_store = JobStore()
