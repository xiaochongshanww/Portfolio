from dataclasses import dataclass
from threading import Lock


@dataclass
class MetricsSnapshot:
    requests_total: int
    chat_requests_total: int
    chat_errors_total: int
    retrieval_errors_total: int
    llm_errors_total: int
    errors_total: int
    last_error: str


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.requests_total = 0
        self.chat_requests_total = 0
        self.chat_errors_total = 0
        self.retrieval_errors_total = 0
        self.llm_errors_total = 0
        self.errors_total = 0
        self.last_error = ""

    def increment_request(self, path: str) -> None:
        with self._lock:
            self.requests_total += 1
            if path.endswith("/chat/completions"):
                self.chat_requests_total += 1

    def increment_error(self, code: str, path: str = "") -> None:
        with self._lock:
            self.errors_total += 1
            self.last_error = code
            if path.endswith("/chat/completions"):
                self.chat_errors_total += 1
            if code in {"KNOWLEDGE_BASE_NOT_READY", "NO_RETRIEVAL_RESULTS"}:
                self.retrieval_errors_total += 1
            if code in {"LLM_REQUEST_FAILED", "LLM_STREAM_FAILED"}:
                self.llm_errors_total += 1

    def snapshot(self) -> dict:
        with self._lock:
            return MetricsSnapshot(
                requests_total=self.requests_total,
                chat_requests_total=self.chat_requests_total,
                chat_errors_total=self.chat_errors_total,
                retrieval_errors_total=self.retrieval_errors_total,
                llm_errors_total=self.llm_errors_total,
                errors_total=self.errors_total,
                last_error=self.last_error,
            ).__dict__


metrics = Metrics()

