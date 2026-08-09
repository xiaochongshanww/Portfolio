import time
from collections import Counter
from datetime import UTC, datetime
from threading import Lock


def _route_group(path: str) -> str:
    if path.endswith("/chat/completions"):
        return "chat"
    for prefix, group in (
        ("/admin/", "admin"),
        ("/corrections/", "corrections"),
        ("/page-images/", "page_images"),
        ("/images/", "images"),
        ("/knowledge/", "knowledge"),
        ("/static/", "static"),
    ):
        if path.startswith(prefix):
            return group
    if path in {"/health", "/ready", "/metrics", "/models", "/v1/models", "/"}:
        return path.strip("/") or "root"
    return "other"


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_monotonic = time.monotonic()
        self.started_at = datetime.now(UTC).isoformat()
        self.requests_total = 0
        self.responses_total = 0
        self.requests_in_flight = 0
        self.chat_requests_total = 0
        self.chat_errors_total = 0
        self.retrieval_errors_total = 0
        self.llm_errors_total = 0
        self.errors_total = 0
        self.last_error = ""
        self.last_error_at = ""
        self.requests_by_group: Counter[str] = Counter()
        self.responses_by_status: Counter[str] = Counter()
        self.errors_by_code: Counter[str] = Counter()
        self._duration_count = 0
        self._duration_total_ms = 0
        self._duration_max_ms = 0

    def request_started(self, path: str) -> None:
        with self._lock:
            self.requests_total += 1
            self.requests_in_flight += 1
            self.requests_by_group[_route_group(path)] += 1
            if path.endswith("/chat/completions"):
                self.chat_requests_total += 1

    def increment_request(self, path: str) -> None:
        self.request_started(path)

    def request_finished(self, path: str, status_code: int, duration_ms: int) -> None:
        del path
        with self._lock:
            self.responses_total += 1
            self.requests_in_flight = max(0, self.requests_in_flight - 1)
            self.responses_by_status[str(status_code)] += 1
            self._duration_count += 1
            self._duration_total_ms += max(0, duration_ms)
            self._duration_max_ms = max(self._duration_max_ms, duration_ms)

    def increment_error(self, code: str, path: str = "") -> None:
        with self._lock:
            self.errors_total += 1
            normalized = str(code)
            self.last_error = normalized
            self.last_error_at = datetime.now(UTC).isoformat()
            self.errors_by_code[normalized] += 1
            if path.endswith("/chat/completions"):
                self.chat_errors_total += 1
            if code in {"KNOWLEDGE_BASE_NOT_READY", "NO_RETRIEVAL_RESULTS"}:
                self.retrieval_errors_total += 1
            if code in {"LLM_REQUEST_FAILED", "LLM_STREAM_FAILED"}:
                self.llm_errors_total += 1

    def snapshot(self) -> dict:
        with self._lock:
            average = (
                round(self._duration_total_ms / self._duration_count, 2)
                if self._duration_count
                else 0
            )
            return {
                "started_at": self.started_at,
                "uptime_seconds": int(time.monotonic() - self._started_monotonic),
                "requests_total": self.requests_total,
                "responses_total": self.responses_total,
                "requests_in_flight": self.requests_in_flight,
                "chat_requests_total": self.chat_requests_total,
                "chat_errors_total": self.chat_errors_total,
                "retrieval_errors_total": self.retrieval_errors_total,
                "llm_errors_total": self.llm_errors_total,
                "errors_total": self.errors_total,
                "last_error": self.last_error,
                "last_error_at": self.last_error_at,
                "requests_by_group": dict(sorted(self.requests_by_group.items())),
                "responses_by_status": dict(sorted(self.responses_by_status.items())),
                "errors_by_code": dict(sorted(self.errors_by_code.items())),
                "request_duration_ms": {
                    "count": self._duration_count,
                    "average": average,
                    "max": self._duration_max_ms,
                },
            }


metrics = Metrics()
