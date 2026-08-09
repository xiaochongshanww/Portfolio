from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

ACTIVE_STATUSES = {"queued", "running"}


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_seconds(value: Any, now: datetime) -> float | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return max(0.0, (now - parsed).total_seconds())


def diagnose_job(
    job: dict[str, Any],
    *,
    stale_after_seconds: int,
    heartbeat_timeout_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    if stale_after_seconds <= 0 or heartbeat_timeout_seconds <= 0:
        raise ValueError("任务诊断阈值必须大于 0")
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    status = str(job.get("status") or "")
    progress_anchor = job.get("progress_at") or job.get("started_at") or job.get("created_at")
    progress_age = _age_seconds(progress_anchor, current_time)
    heartbeat_age = _age_seconds(job.get("heartbeat_at"), current_time)
    stalled = (
        status in ACTIVE_STATUSES
        and progress_age is not None
        and progress_age > stale_after_seconds
    )
    heartbeat_stale = (
        status == "running"
        and heartbeat_age is not None
        and heartbeat_age > heartbeat_timeout_seconds
    )

    reason = ""
    if job.get("error_code") == "PROCESS_RESTARTED":
        reason = "process_restarted"
    elif stalled and heartbeat_stale:
        reason = "no_progress_and_heartbeat_stale"
    elif stalled:
        reason = "no_progress"
    elif heartbeat_stale:
        reason = "heartbeat_stale"

    return {
        **job,
        "diagnostics": {
            "stalled": stalled,
            "heartbeat_stale": heartbeat_stale,
            "reason": reason,
            "progress_age_seconds": round(progress_age, 3) if progress_age is not None else None,
            "heartbeat_age_seconds": round(heartbeat_age, 3) if heartbeat_age is not None else None,
            "stale_after_seconds": stale_after_seconds,
            "heartbeat_timeout_seconds": heartbeat_timeout_seconds,
        },
    }


def diagnose_jobs(
    jobs: Iterable[dict[str, Any]],
    *,
    stale_after_seconds: int,
    heartbeat_timeout_seconds: int,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current_time = now or datetime.now(UTC)
    return [
        diagnose_job(
            job,
            stale_after_seconds=stale_after_seconds,
            heartbeat_timeout_seconds=heartbeat_timeout_seconds,
            now=current_time,
        )
        for job in jobs
    ]
