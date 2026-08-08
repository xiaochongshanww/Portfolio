from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    type: str
    params: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    job_id: str = field(default_factory=lambda: uuid4().hex[:12])
    status: str = "queued"
    step: str = "queued"
    progress: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    error_code: str = ""
    created_at: str = field(default_factory=utc_now)
    started_at: str = ""
    finished_at: str = ""
    worker_id: str = ""
    heartbeat_at: str = ""
    progress_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    recovery: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
