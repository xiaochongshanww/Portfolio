from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from threading import Event
from typing import Any


class JobCancelled(RuntimeError):
    """Raised at a cooperative cancellation checkpoint in a managed job."""


@dataclass(frozen=True)
class JobCancellationContext:
    event: Event
    state_lock: Any


_current_context: ContextVar[JobCancellationContext | None] = ContextVar(
    "current_job_cancellation_context",
    default=None,
)


def bind_job_cancellation(event: Event, state_lock: Any) -> Token:
    return _current_context.set(JobCancellationContext(event, state_lock))


def reset_job_cancellation(token: Token) -> None:
    _current_context.reset(token)


def job_cancellation_requested() -> bool:
    context = _current_context.get()
    return bool(context and context.event.is_set())


def raise_if_job_cancelled() -> None:
    if job_cancellation_requested():
        raise JobCancelled("任务已按请求取消")


@contextmanager
def job_cancellation_safe_section() -> Iterator[None]:
    """Serialize a short irreversible commit against cancellation requests."""
    context = _current_context.get()
    if context is None:
        yield
        return
    with context.state_lock:
        raise_if_job_cancelled()
        yield
